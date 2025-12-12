"""Rich rendering utilities for Maven dependency visualization."""

from __future__ import annotations

from rich.tree import Tree

from j_dep_analyzer.models import MavenProject


def build_dependency_tree(model: MavenProject) -> Tree:
    """Build a Rich Tree representing the project's direct dependencies.

    Args:
        model: Parsed Maven project model.

    Returns:
        A Rich Tree object for rendering.
    """
    root = Tree(f"[bold]{model.project.compact()}[/bold]")
    if not model.dependencies:
        root.add("[dim]No direct dependencies found[/dim]")
        return root

    deps_branch = root.add("dependencies")
    for dep in model.dependencies:
        deps_branch.add(dep.label())
    return root
