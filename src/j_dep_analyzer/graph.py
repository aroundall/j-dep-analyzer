from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from typing import Any

import networkx as nx

from j_dep_analyzer.models import MavenProject


def build_graph(projects: Iterable[MavenProject]) -> nx.DiGraph:
    """Build a directed graph where A -> B means A depends on B."""
    g = nx.DiGraph()
    for proj in projects:
        a = proj.project.compact()
        g.add_node(a)
        for dep in proj.dependencies:
            b = dep.gav.compact()
            g.add_node(b)
            g.add_edge(a, b, scope=dep.scope, optional=dep.optional)
    return g


def reverse_dependencies(g: nx.DiGraph, target_gav: str) -> list[str]:
    """Return predecessors of target_gav (who depends on it)."""
    if target_gav not in g:
        return []
    return sorted(list(g.predecessors(target_gav)))


def _split_gav(gav: str) -> tuple[str, str, str]:
    parts = (gav or "").split(":")
    if len(parts) >= 3:
        return parts[0] or "Unknown", parts[1] or "Unknown", parts[2] or "Unknown"
    if len(parts) == 2:
        return parts[0] or "Unknown", parts[1] or "Unknown", "Unknown"
    if len(parts) == 1:
        return "Unknown", parts[0] or "Unknown", "Unknown"
    return "Unknown", "Unknown", "Unknown"


def aggregated_node_id(gav: str, *, show_group: bool, show_version: bool) -> str:
    """Map an atomic `group:artifact:version` id to an aggregated node id.

    This is the *core* of node aggregation:
        - show_group=True,  show_version=True  => group:artifact:version (no aggregation)
        - show_group=True,  show_version=False => group:artifact          (merge versions)
        - show_group=False, show_version=True  => artifact:version        (merge groups)
        - show_group=False, show_version=False => artifact                (merge both)

    Newcomer note:
        The returned string becomes the node ID used by Cytoscape.js.
        If two atomic nodes map to the same ID, they become one merged node.
    """
    group_id, artifact_id, version = _split_gav(gav)
    if show_group and show_version:
        return f"{group_id}:{artifact_id}:{version}"
    if show_group and not show_version:
        return f"{group_id}:{artifact_id}"
    if (not show_group) and show_version:
        return f"{artifact_id}:{version}"
    return artifact_id


def aggregate_graph(g: nx.DiGraph, *, show_group: bool, show_version: bool) -> nx.DiGraph:
    """Aggregate nodes by toggles; merge edges while preserving scope metadata.

    What "aggregate" means here:
        We build a *new* graph where multiple original nodes can collapse into one.
        Edges are re-wired to the merged node IDs.

    Metadata handling:
        - Node: `merged_count` counts how many atomic nodes ended up in this node.
        - Edge: when multiple edges collapse, scopes are combined into a comma list.
    """
    out = nx.DiGraph()

    def ensure_node(node_id: str) -> None:
        if out.has_node(node_id):
            return
        group_id, artifact_id, version = _split_gav(
            node_id if node_id.count(":") >= 2 else f"Unknown:{node_id}:Unknown"
        )
        out.add_node(
            node_id,
            group_id=group_id,
            artifact_id=artifact_id,
            version=version,
            merged_count=0,
        )

    for node_id in g.nodes:
        new_id = aggregated_node_id(str(node_id), show_group=show_group, show_version=show_version)
        ensure_node(new_id)
        # How many original nodes were merged into this aggregated node.
        out.nodes[new_id]["merged_count"] += 1

    for u, v, data in g.edges(data=True):
        uu = aggregated_node_id(str(u), show_group=show_group, show_version=show_version)
        vv = aggregated_node_id(str(v), show_group=show_group, show_version=show_version)
        ensure_node(uu)
        ensure_node(vv)

        scope = (data or {}).get("scope") or "compile"
        optional = (data or {}).get("optional")

        if out.has_edge(uu, vv):
            # Merge edge metadata for collapsed edges (same uu -> vv after aggregation).
            scopes = out.edges[uu, vv].get("_scopes", set())
            scopes.add(scope)
            out.edges[uu, vv]["_scopes"] = scopes
            out.edges[uu, vv]["optional_any"] = bool(out.edges[uu, vv].get("optional_any")) or bool(optional)
        else:
            out.add_edge(uu, vv, _scopes={scope}, optional_any=bool(optional))

    for uu, vv in out.edges:
        scopes = out.edges[uu, vv].get("_scopes", set())
        out.edges[uu, vv]["scope"] = ", ".join(sorted(scopes)) if scopes else "compile"

    return out


def nodes_within_depth(
    g: nx.DiGraph,
    root: str,
    *,
    direction: str,
    depth: int | None,
) -> set[str]:
    """Return nodes within BFS depth from root.

    direction:
        - "forward": traverse successors
        - "reverse": traverse predecessors
    depth:
        - None means "All"

    Newcomer note:
      This is a standard BFS (breadth-first search). We use it to avoid returning
      a huge graph when users only want "1 layer" or "2 layers" around a node.
    """
    if not root or not g.has_node(root):
        return set(g.nodes)

    if depth is None:
        if direction == "reverse":
            return {root, *nx.ancestors(g, root)}
        return {root, *nx.descendants(g, root)}

    q: deque[tuple[str, int]] = deque([(root, 0)])
    seen: set[str] = {root}

    while q:
        node, dist = q.popleft()
        if dist >= depth:
            continue

        nbrs = g.predecessors(node) if direction == "reverse" else g.successors(node)
        for nb in nbrs:
            nb_str = str(nb)
            if nb_str in seen:
                continue
            seen.add(nb_str)
            q.append((nb_str, dist + 1))

    return seen


def graph_to_cytoscape_elements(
    g: nx.DiGraph,
    *,
    root_id: str | None = None,
    direction: str = "forward",
    show_version: bool = True,
) -> list[dict[str, Any]]:
    """Convert graph to Cytoscape.js `elements` format.

    Cytoscape expects a flat list like:
        - { data: {id, label, ...}, classes: "..." } for nodes
        - { data: {id, source, target, ...} } for edges

    We also add CSS-like classes to nodes so the frontend can style:
        - root: selected node
        - highlight: in reverse view, nodes that depend on the root
        - aggregated: version-hidden nodes
    """
    highlight: set[str] = set()
    if root_id and g.has_node(root_id) and direction == "reverse":
        # In reverse mode, highlight all ancestors (i.e. who depends on root).
        highlight = {str(n) for n in nx.ancestors(g, root_id)}

    elements: list[dict[str, Any]] = []

    for node_id, data in g.nodes(data=True):
        node_str = str(node_id)
        label = node_str
        if not show_version:
            label = (data or {}).get("artifact_id") or _split_gav(node_str)[1] or node_str

        classes: list[str] = []
        if root_id and node_str == root_id:
            classes.append("root")
        if node_str in highlight:
            classes.append("highlight")
        if not show_version:
            classes.append("aggregated")

        elements.append(
            {
                "data": {
                    "id": node_str,
                    "label": label,
                    "group_id": (data or {}).get("group_id"),
                    "artifact_id": (data or {}).get("artifact_id"),
                    "version": (data or {}).get("version"),
                    "merged_count": int((data or {}).get("merged_count") or 0),
                },
                "classes": " ".join(classes),
            }
        )

    for u, v, data in g.edges(data=True):
        u_str = str(u)
        v_str = str(v)
        elements.append(
            {
                "data": {
                    "id": f"{u_str}__{v_str}",
                    "source": u_str,
                    "target": v_str,
                    "scope": (data or {}).get("scope") or "compile",
                    "optional": bool((data or {}).get("optional_any")),
                }
            }
        )

    return elements
