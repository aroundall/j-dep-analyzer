"""Parse Maven pom.xml files using lxml."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

from lxml import etree

from j_dep_analyzer.exceptions import PomModelError, PomNotFoundError, PomParseError
from j_dep_analyzer.models import Dependency, GAV, MavenProject, UNKNOWN_VERSION


_PLACEHOLDER_RE = re.compile(r"\$\{([^}]+)\}")


def _text_first(node: etree._Element, xpath_expr: str) -> str | None:
    """Get text of the first matching element using namespace-agnostic XPath.

    Args:
        node: Root element to query under.
        xpath_expr: XPath expression (should use local-name()).

    Returns:
        Text content if found and non-empty, otherwise None.
    """
    found = node.xpath(xpath_expr)
    if not found:
        return None
    first = found[0]
    if isinstance(first, etree._Element):
        text = (first.text or "").strip()
        return text or None
    if isinstance(first, str):
        text = first.strip()
        return text or None
    return None


def _bool_text(value: str | None) -> bool | None:
    """Convert Maven boolean-ish text to bool.

    Args:
        value: String like 'true'/'false' or None.

    Returns:
        True/False for recognized values, otherwise None.
    """
    if value is None:
        return None
    v = value.strip().lower()
    if v == "true":
        return True
    if v == "false":
        return False
    return None


def _parse_xml(path: Path) -> etree._Element:
    """Parse an XML file and return its root element.

    Args:
        path: Path to the pom.xml file.

    Raises:
        PomNotFoundError: If the file does not exist.
        PomParseError: If XML cannot be parsed.

    Returns:
        Root XML element.
    """
    if not path.exists():
        raise PomNotFoundError(f"pom.xml not found: {path}")
    try:
        parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
        tree = etree.parse(str(path), parser=parser)
        return tree.getroot()
    except (OSError, etree.XMLSyntaxError) as exc:
        raise PomParseError(f"Failed to parse pom.xml: {path}") from exc


def _resolve_placeholders(value: str, props: Mapping[str, str]) -> str:
    """Resolve ${...} placeholders using provided properties.

    Unknown placeholders are preserved as-is.
    """
    current = value
    for _ in range(5):
        changed = False

        def _sub(m: re.Match[str]) -> str:
            nonlocal changed
            key = m.group(1)
            replacement = props.get(key)
            if replacement:
                changed = True
                return replacement
            return m.group(0)

        nxt = _PLACEHOLDER_RE.sub(_sub, current)
        current = nxt
        if not changed:
            break
    return current


def _normalize_version(value: str | None, props: Mapping[str, str]) -> str:
    """Resolve and normalize a Maven version string.

    Rules:
      - Missing version => "Unknown"
      - If placeholders remain after resolution (e.g. "${x.y}"), treat as unresolved => "Unknown"
    """
    if value is None:
        return UNKNOWN_VERSION

    resolved = _resolve_placeholders(value, props).strip()
    if not resolved:
        return UNKNOWN_VERSION

    if _PLACEHOLDER_RE.search(resolved):
        return UNKNOWN_VERSION

    return resolved


def _parse_properties(root: etree._Element) -> dict[str, str]:
    props: dict[str, str] = {}
    nodes = root.xpath("/*[local-name()='project']/*[local-name()='properties']/*")
    for n in nodes:
        if not isinstance(n, etree._Element):
            continue
        key = etree.QName(n).localname
        val = (n.text or "").strip()
        if key and val:
            props[key] = val
    return props


def parse_pom(path: str | Path) -> MavenProject:
    """Parse a Maven pom.xml and extract direct dependencies.

    Notes:
        - Namespace handling: uses `local-name()` XPath so it works with or without XML namespaces.
                - Property placeholders like `${...}` are resolved when possible.
                    If a version cannot be resolved, it is stored as "Unknown".

    Args:
        path: Path to a pom.xml.

    Raises:
        PomModelError: If required fields are missing.

    Returns:
        A `MavenProject` containing project GAV and a list of dependencies.
    """
    pom_path = Path(path)
    root = _parse_xml(pom_path)

    raw_group_id = _text_first(root, "/*[local-name()='project']/*[local-name()='groupId']")
    raw_artifact_id = _text_first(root, "/*[local-name()='project']/*[local-name()='artifactId']")
    raw_version = _text_first(root, "/*[local-name()='project']/*[local-name()='version']")

    parent_group_id = _text_first(
        root,
        "/*[local-name()='project']/*[local-name()='parent']/*[local-name()='groupId']",
    )
    parent_version = _text_first(
        root,
        "/*[local-name()='project']/*[local-name()='parent']/*[local-name()='version']",
    )

    if raw_artifact_id is None:
        raise PomModelError("Missing required <artifactId> in pom.xml")

    raw_group_id = raw_group_id or parent_group_id
    raw_version = raw_version or parent_version

    if raw_group_id is None:
        raise PomModelError("Missing required <groupId> (or parent <groupId>) in pom.xml")

    props = _parse_properties(root)
    effective_version = raw_version or UNKNOWN_VERSION
    builtins: dict[str, str] = {
        "project.groupId": raw_group_id,
        "project.artifactId": raw_artifact_id,
        "project.version": effective_version,
        "pom.groupId": raw_group_id,
        "pom.artifactId": raw_artifact_id,
        "pom.version": effective_version,
        "groupId": raw_group_id,
        "artifactId": raw_artifact_id,
        "version": effective_version,
    }
    merged_props = {**props, **builtins}

    group_id = _resolve_placeholders(raw_group_id, merged_props)
    version = _normalize_version(effective_version, merged_props)

    project_gav = GAV(group_id=group_id, artifact_id=raw_artifact_id, version=version)

    deps: list[Dependency] = []
    dep_nodes = root.xpath(
        "/*[local-name()='project']"
        "/*[local-name()='dependencies']"
        "/*[local-name()='dependency']"
    )

    for dep in dep_nodes:
        dep_group_id = _text_first(dep, "./*[local-name()='groupId']")
        dep_artifact_id = _text_first(dep, "./*[local-name()='artifactId']")
        dep_version = _text_first(dep, "./*[local-name()='version']")
        dep_scope = _text_first(dep, "./*[local-name()='scope']")
        dep_optional = _bool_text(_text_first(dep, "./*[local-name()='optional']"))

        if dep_group_id is None or dep_artifact_id is None:
            continue

        dep_version = _normalize_version(dep_version, merged_props)

        deps.append(
            Dependency(
                gav=GAV(group_id=dep_group_id, artifact_id=dep_artifact_id, version=dep_version),
                scope=dep_scope,
                optional=dep_optional,
            )
        )

    return MavenProject(project=project_gav, dependencies=deps)
