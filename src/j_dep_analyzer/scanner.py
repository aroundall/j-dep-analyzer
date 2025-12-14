from __future__ import annotations

from pathlib import Path


def find_pom_files(root: Path) -> list[Path]:
    """Find Maven POM files under root (pom.xml and *.pom).

    Args:
        root: A directory to scan recursively, or a single pom file.

    Returns:
        Sorted unique list of POM files.
    """
    if root.is_file():
        return [root]

    poms: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        name = p.name.lower()
        if name == "pom.xml" or name.endswith(".pom"):
            poms.append(p)
    return sorted(set(poms))
