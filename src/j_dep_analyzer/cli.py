"""Typer CLI entry point for J-Dep Analyzer."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from j_dep_analyzer.db import create_sqlite_engine, init_db
from j_dep_analyzer.db_models import Artifact, DependencyEdge
from j_dep_analyzer.exceptions import JDepError
from j_dep_analyzer.graph import build_graph, reverse_dependencies
from j_dep_analyzer.parser import parse_pom
from j_dep_analyzer.scanner import find_pom_files
from j_dep_analyzer.visualize import build_dependency_tree
from j_dep_analyzer.visualize_html import export_pyvis

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
        raise typer.Exit(code=1) from None


@app.command()
def ingest(
    root: Annotated[
        Path,
        typer.Argument(help="Root folder to scan for pom.xml / *.pom (or a single POM file)."),
    ],
    db: Annotated[Path, typer.Option("--db", help="SQLite db path.")] = Path("dependencies.db"),
) -> None:
    """Scan POMs, normalize data, and persist into SQLite (SQLModel)."""
    try:
        engine = create_sqlite_engine(db)
        init_db(engine)

        pom_files = find_pom_files(root)
        if not pom_files:
            console.print("[bold red]Error:[/bold red] No POM files found.")
            raise typer.Exit(code=1)

        projects = []
        for p in pom_files:
            try:
                projects.append(parse_pom(p))
            except JDepError as exc:
                console.print(f"[bold red]Error:[/bold red] {exc}")

        with Session(engine) as session:
            for proj in projects:
                a = proj.project
                a_gav = a.compact()
                if session.get(Artifact, a_gav) is None:
                    session.add(
                        Artifact(
                            gav=a_gav,
                            group_id=a.group_id,
                            artifact_id=a.artifact_id,
                            version=a.version,
                        )
                    )

                for dep in proj.dependencies:
                    b = dep.gav
                    b_gav = b.compact()
                    if session.get(Artifact, b_gav) is None:
                        session.add(
                            Artifact(
                                gav=b_gav,
                                group_id=b.group_id,
                                artifact_id=b.artifact_id,
                                version=b.version,
                            )
                        )

                    session.add(
                        DependencyEdge(
                            from_gav=a_gav,
                            to_gav=b_gav,
                            scope=dep.scope,
                            optional=dep.optional,
                        )
                    )
                    try:
                        session.flush()
                    except IntegrityError:
                        session.rollback()

            session.commit()

        console.print(f"[green]Ingested[/green] {len(projects)} POM(s) into [bold]{db}[/bold].")
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from None


@app.command()
def reverse(
    target: Annotated[str, typer.Argument(help="Target GAV: groupId:artifactId:version")],
    db: Annotated[Path, typer.Option("--db", help="SQLite db path.")] = Path("dependencies.db"),
    limit: Annotated[int, typer.Option("--limit", help="Max rows to print.")] = 200,
) -> None:
    """Show who depends on TARGET (reverse dependencies / predecessors)."""
    try:
        engine = create_sqlite_engine(db)
        with Session(engine) as session:
            edges = session.exec(select(DependencyEdge)).all()

        g = build_graph([])
        for e in edges:
            g.add_node(e.from_gav)
            g.add_node(e.to_gav)
            g.add_edge(e.from_gav, e.to_gav, scope=e.scope, optional=e.optional)

        preds = reverse_dependencies(g, target)
        table = Table(title=f"Reverse dependencies (who depends on {target})")
        table.add_column("#", style="dim", width=6)
        table.add_column("Dependent (predecessor)")

        if not preds:
            console.print(table)
            console.print("[dim]No reverse dependencies found (or target not in graph).[/dim]")
            return

        for i, gav in enumerate(preds[:limit], start=1):
            table.add_row(str(i), gav)
        console.print(table)

        if len(preds) > limit:
            console.print(f"[dim]Truncated: showing {limit}/{len(preds)}[/dim]")
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from None


@app.command()
def html(
    root: Annotated[
        Path,
        typer.Argument(help="Root folder to scan for pom.xml / *.pom (or a single POM file)."),
    ],
    out: Annotated[Path, typer.Option("--out", help="Output HTML file path.")] = Path("deps.html"),
) -> None:
    """Scan POMs and export an interactive HTML dependency graph (Pyvis)."""
    try:
        pom_files = find_pom_files(root)
        if not pom_files:
            console.print("[bold red]Error:[/bold red] No POM files found.")
            raise typer.Exit(code=1)

        projects = []
        for p in pom_files:
            try:
                projects.append(parse_pom(p))
            except JDepError as exc:
                console.print(f"[bold red]Error:[/bold red] {exc}")

        g = build_graph(projects)
        out_path = export_pyvis(g, out)
        console.print(f"[green]Wrote[/green] {out_path}")
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from None


def main() -> None:
    """Console-script entry point."""
    app()
