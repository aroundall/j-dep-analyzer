"""Typer CLI entry point for J-Dep Analyzer."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from j_dep_analyzer.exceptions import JDepError
from j_dep_analyzer.parser import parse_pom
from j_dep_analyzer.visualize import build_dependency_tree

app = typer.Typer(add_completion=False, help="Analyze Maven pom.xml dependencies.")
console = Console()


@app.command()
def analyze(
    pom: Annotated[Path, typer.Argument(help="Path to a Maven pom.xml file.")],
    show_path: Annotated[bool, typer.Option("--show-path", help="Show the pom path header.")] = True,
) -> None:
    """Parse a pom.xml and print a dependency tree."""
    try:
        model = parse_pom(pom)
        if show_path:
            console.print(f"[dim]{pom}[/dim]")
        console.print(build_dependency_tree(model))
    except JDepError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


def main() -> None:
    """Console-script entry point."""
    app()
