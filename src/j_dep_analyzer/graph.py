from __future__ import annotations

from collections.abc import Iterable

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
