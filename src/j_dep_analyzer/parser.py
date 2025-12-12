"""Parse Maven pom.xml files using lxml."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from j_dep_analyzer.exceptions import PomModelError, PomNotFoundError, PomParseError
from j_dep_analyzer.models import Dependency, GAV, MavenProject


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


def parse_pom(path: str | Path) -> MavenProject:
    """Parse a Maven pom.xml and extract direct dependencies.

    Notes:
        - Namespace handling: uses `local-name()` XPath so it works with or without XML namespaces.
        - Property placeholders like `${...}` are preserved as-is (hook left for future resolution).

    Args:
        path: Path to a pom.xml.

    Raises:
        PomModelError: If required fields are missing.

    Returns:
        A `MavenProject` containing project GAV and a list of dependencies.
    """
    pom_path = Path(path)
    root = _parse_xml(pom_path)

    group_id = _text_first(root, "/*[local-name()='project']/*[local-name()='groupId']")
    artifact_id = _text_first(root, "/*[local-name()='project']/*[local-name()='artifactId']")
    version = _text_first(root, "/*[local-name()='project']/*[local-name()='version']")

    # Maven allows inheriting groupId/version from parent; keep minimal for now.
    if group_id is None:
        group_id = _text_first(
            root,
            "/*[local-name()='project']/*[local-name()='parent']/*[local-name()='groupId']",
        )
    if version is None:
        version = _text_first(
            root,
            "/*[local-name()='project']/*[local-name()='parent']/*[local-name()='version']",
        )

    if artifact_id is None:
        raise PomModelError("Missing required <artifactId> in pom.xml")
    if group_id is None:
        raise PomModelError("Missing required <groupId> (or parent <groupId>) in pom.xml")

    project_gav = GAV(group_id=group_id, artifact_id=artifact_id, version=version)

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

        # Preserve ${...} placeholders as-is; future hook could resolve via <properties>.
        if dep_group_id is None or dep_artifact_id is None:
            continue

        deps.append(
            Dependency(
                gav=GAV(group_id=dep_group_id, artifact_id=dep_artifact_id, version=dep_version),
                scope=dep_scope,
                optional=dep_optional,
            )
        )

    return MavenProject(project=project_gav, dependencies=deps)
