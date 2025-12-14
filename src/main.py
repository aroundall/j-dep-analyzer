from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import networkx as nx
from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from j_dep_analyzer.db import create_sqlite_engine, init_db
from j_dep_analyzer.db_models import Artifact, DependencyEdge
from j_dep_analyzer.graph import (
    aggregate_graph,
    aggregated_node_id,
    graph_to_cytoscape_elements,
    nodes_within_depth,
)
from j_dep_analyzer.parser import parse_pom

BASE_DIR = Path(__file__).resolve().parent
PKG_DIR = BASE_DIR / "j_dep_analyzer"
TEMPLATES_DIR = PKG_DIR / "templates"
STATIC_DIR = PKG_DIR / "static"

DB_PATH = Path(os.getenv("JDEP_DB_PATH", "dependencies.db")).resolve()

app = FastAPI(title="J-Dep Analyzer")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def _startup() -> None:
    engine = create_sqlite_engine(DB_PATH)
    init_db(engine)


def _engine():
    """Create a SQLModel engine for the configured SQLite DB.

    Newcomer note:
        We intentionally create a new engine on demand rather than keeping a global
        one. For a small demo app this is fine and keeps startup simple.
    """
    return create_sqlite_engine(DB_PATH)


def _load_atomic_graph(session: Session) -> nx.DiGraph:
    """Load the *atomic* dependency graph from the database.

    Atomic graph means: every node is a full `group:artifact:version` (GAV).

    Edge direction follows Maven dependency semantics:
        A -> B means "A depends on B".
    """
    g = nx.DiGraph()

    for a in session.exec(select(Artifact)).all():
        g.add_node(a.gav)

    for e in session.exec(select(DependencyEdge)).all():
        g.add_node(e.from_gav)
        g.add_node(e.to_gav)
        g.add_edge(e.from_gav, e.to_gav, scope=e.scope, optional=e.optional)

    return g


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> Any:
    """Dashboard page.

    It contains an upload widget and a global dependency graph.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "db_path": str(DB_PATH),
        },
    )


@app.get("/graph/global", response_class=HTMLResponse)
def graph_global(request: Request) -> Any:
    # DESIGN.md calls this out as the global graph view. Keep it as an alias to the dashboard.
    return home(request)


@app.get("/list", response_class=HTMLResponse)
def list_page(request: Request) -> Any:
    return templates.TemplateResponse(
        "list.html",
        {
            "request": request,
            "db_path": str(DB_PATH),
        },
    )


@app.get("/visualize/{root_id}", response_class=HTMLResponse)
def visualize(request: Request, root_id: str) -> Any:
    """Detail page centered on a selected artifact (root_id).

    root_id is a string key we use everywhere; usually it is a full GAV.
    We also pre-split it for the left "info card".
    """
    g, a, v = _split_gav(root_id)
    return templates.TemplateResponse(
        "visualize.html",
        {
            "request": request,
            "root_id": root_id,
            "root_group": g,
            "root_artifact": a,
            "root_version": v,
            "db_path": str(DB_PATH),
        },
    )


@app.get("/details/{root_id}", response_class=HTMLResponse)
def details(request: Request, root_id: str) -> Any:
    return visualize(request, root_id)


@app.get("/dependencies/list", response_class=HTMLResponse)
def dependencies_list(request: Request) -> Any:
    return templates.TemplateResponse(
        "dependencies_list.html",
        {
            "request": request,
            "db_path": str(DB_PATH),
        },
    )


@app.get("/partials/artifacts-table", response_class=HTMLResponse)
def artifacts_table_partial(request: Request, q: str | None = None, limit: int = 200) -> Any:
    with Session(_engine()) as session:
        stmt = select(Artifact)
        if q:
            stmt = stmt.where(Artifact.artifact_id.contains(q))
        artifacts = session.exec(stmt.limit(limit)).all()

    return templates.TemplateResponse(
        "partials/artifacts_table.html",
        {
            "request": request,
            "artifacts": artifacts,
            "q": q or "",
            "limit": limit,
        },
    )


def _split_gav(gav: str) -> tuple[str, str, str]:
    """Split a GAV string into (group, artifact, version).

    Maven coordinates are typically 3-part, but in this app we defensively handle
    partial strings to keep the UI resilient.
    """
    parts = (gav or "").split(":")
    if len(parts) >= 3:
        return parts[0] or "Unknown", parts[1] or "Unknown", parts[2] or "Unknown"
    if len(parts) == 2:
        return parts[0] or "Unknown", parts[1] or "Unknown", "Unknown"
    if len(parts) == 1:
        return "Unknown", parts[0] or "Unknown", "Unknown"
    return "Unknown", "Unknown", "Unknown"


def _display_key(
    gav: str,
    artifact: Artifact | None,
    *,
    ignore_group: bool,
    ignore_version: bool,
) -> tuple[str, str, str, str]:
    """Build an aggregation/display key for the dependencies table.

    This is used by the "Dependencies (Pair List)" view to optionally *merge*
    rows when the user ticks "Ignore Version" and/or "Ignore GroupId".
    The returned tuple contains:
      - key: internal dedup key (string)
      - group_disp / artifact_disp / version_disp: what to display in the table
    """
    if artifact is not None:
        g, a, v = artifact.group_id or "Unknown", artifact.artifact_id, artifact.version or "Unknown"
    else:
        g, a, v = _split_gav(gav)

    if ignore_group and ignore_version:
        key = a
    elif ignore_group and not ignore_version:
        key = f"{a}:{v}"
    elif (not ignore_group) and ignore_version:
        key = f"{g}:{a}"
    else:
        key = f"{g}:{a}:{v}"

    group_disp = "" if ignore_group else g
    version_disp = "" if ignore_version else v

    return key, group_disp, a, version_disp


def _dependency_rows(
    *,
    q: str | None,
    ignore_version: bool,
    ignore_group: bool,
    limit: int,
) -> list[dict[str, Any]]:
    """Compute the dependencies list rows, optionally aggregated.

    Why a helper?
        Both the table partial and the CSV export should produce exactly the same
        rows for the same query parameters.
    """
    q_norm = (q or "").strip().lower()

    with Session(_engine()) as session:
        edges = session.exec(select(DependencyEdge).limit(2000)).all()

        gavs: set[str] = set()
        for e in edges:
            gavs.add(e.from_gav)
            gavs.add(e.to_gav)

        artifacts_by_gav: dict[str, Artifact] = {}
        if gavs:
            artifacts = session.exec(select(Artifact).where(Artifact.gav.in_(list(gavs)))).all()
            artifacts_by_gav = {a.gav: a for a in artifacts}

    rows: list[dict[str, Any]] = []

    if ignore_group or ignore_version:
        agg: dict[tuple[str, str], dict[str, Any]] = {}
        for e in edges:
            src_art = artifacts_by_gav.get(e.from_gav)
            tgt_art = artifacts_by_gav.get(e.to_gav)

            src_key, sg, sa, sv = _display_key(
                e.from_gav,
                src_art,
                ignore_group=ignore_group,
                ignore_version=ignore_version,
            )
            tgt_key, tg, ta, tv = _display_key(
                e.to_gav,
                tgt_art,
                ignore_group=ignore_group,
                ignore_version=ignore_version,
            )

            if q_norm:
                if q_norm not in (sa or "").lower() and q_norm not in (ta or "").lower():
                    continue

            k = (src_key, tgt_key)
            if k not in agg:
                agg[k] = {
                    "source_group": sg,
                    "source_artifact": sa,
                    "source_version": sv,
                    "target_group": tg,
                    "target_artifact": ta,
                    "target_version": tv,
                    "scopes": set(),
                    # DESIGN.md: click should go to Group 1 (source).
                    "details_id": e.from_gav,
                }
            agg[k]["scopes"].add(e.scope or "compile")

        for item in agg.values():
            rows.append(
                {
                    **{k: v for k, v in item.items() if k != "scopes"},
                    "scope": ", ".join(sorted(item["scopes"])) if item["scopes"] else "compile",
                }
            )
    else:
        for e in edges:
            src_art = artifacts_by_gav.get(e.from_gav)
            tgt_art = artifacts_by_gav.get(e.to_gav)
            _, sg, sa, sv = _display_key(e.from_gav, src_art, ignore_group=False, ignore_version=False)
            _, tg, ta, tv = _display_key(e.to_gav, tgt_art, ignore_group=False, ignore_version=False)

            if q_norm:
                if q_norm not in (sa or "").lower() and q_norm not in (ta or "").lower():
                    continue

            rows.append(
                {
                    "source_group": sg,
                    "source_artifact": sa,
                    "source_version": sv,
                    "target_group": tg,
                    "target_artifact": ta,
                    "target_version": tv,
                    "scope": e.scope or "compile",
                    # DESIGN.md: click should go to Group 1 (source).
                    "details_id": e.from_gav,
                }
            )

    return rows[:limit]


@app.get("/partials/dependencies-table", response_class=HTMLResponse)
def dependencies_table_partial(
    request: Request,
    q: str | None = None,
    ignore_version: bool = False,
    ignore_group: bool = False,
    limit: int = 300,
) -> Any:
    rows = _dependency_rows(q=q, ignore_version=ignore_version, ignore_group=ignore_group, limit=limit)

    return templates.TemplateResponse(
        "partials/dependencies_table.html",
        {
            "request": request,
            "rows": rows,
            "q": q or "",
            "ignore_version": ignore_version,
            "ignore_group": ignore_group,
            "limit": limit,
        },
    )


@app.get("/api/dependencies/export")
def export_dependencies_csv(
    q: str | None = None,
    ignore_version: bool = False,
    ignore_group: bool = False,
    limit: int = 2000,
) -> StreamingResponse:
    rows = _dependency_rows(q=q, ignore_version=ignore_version, ignore_group=ignore_group, limit=limit)

    def _iter() -> Any:
        import csv
        import io

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "source_group",
                "source_artifact",
                "source_version",
                "target_group",
                "target_artifact",
                "target_version",
                "scope",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r.get("source_group", ""),
                    r.get("source_artifact", ""),
                    r.get("source_version", ""),
                    r.get("target_group", ""),
                    r.get("target_artifact", ""),
                    r.get("target_version", ""),
                    r.get("scope", ""),
                ]
            )

        yield buf.getvalue()

    headers = {"Content-Disposition": "attachment; filename=dependencies.csv"}
    return StreamingResponse(_iter(), media_type="text/csv; charset=utf-8", headers=headers)


@app.post("/api/upload", response_class=HTMLResponse)
async def upload_poms(request: Request, files: list[UploadFile] = File(...)) -> Any:
    parsed = 0
    ingested_edges = 0
    ingested_projects = 0

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        projects = []

        for f in files:
            data = await f.read()
            if not data:
                continue
            filename = Path(f.filename or "upload.pom").name
            p = tmpdir / filename
            p.write_bytes(data)
            projects.append(parse_pom(p))

        with Session(_engine()) as session:
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

                    scope = dep.scope or "compile"
                    optional = dep.optional

                    exists = session.exec(
                        select(DependencyEdge)
                        .where(DependencyEdge.from_gav == a_gav)
                        .where(DependencyEdge.to_gav == b_gav)
                        .where(DependencyEdge.scope == scope)
                        .where(DependencyEdge.optional == optional)
                    ).first()

                    if exists is None:
                        session.add(
                            DependencyEdge(
                                from_gav=a_gav,
                                to_gav=b_gav,
                                scope=scope,
                                optional=optional,
                            )
                        )
                        ingested_edges += 1

                ingested_projects += 1

            session.commit()

        parsed = len(projects)

    return templates.TemplateResponse(
        "partials/upload_status.html",
        {
            "request": request,
            "parsed": parsed,
            "ingested_projects": ingested_projects,
            "ingested_edges": ingested_edges,
            "db_path": str(DB_PATH),
        },
    )


@app.get("/api/artifacts", response_class=JSONResponse)
def api_artifacts(limit: int = 500) -> dict[str, Any]:
    with Session(_engine()) as session:
        artifacts = session.exec(select(Artifact).limit(limit)).all()

    return {
        "items": [
            {
                "gav": a.gav,
                "group_id": a.group_id,
                "artifact_id": a.artifact_id,
                "version": a.version,
            }
            for a in artifacts
        ]
    }


@app.get("/api/graph/data", response_class=JSONResponse)
def api_graph_data(
    root_id: str | None = None,
    direction: str = Query("forward", pattern="^(forward|reverse)$"),
    depth: int | None = Query(None, ge=1),
    show_group: bool = True,
    show_version: bool = True,
    aggregate_group: bool | None = None,
    aggregate_version: bool | None = None,
) -> dict[str, Any]:
    """Return dependency graph data in Cytoscape.js `elements` format.

    Data flow (high level):
        1) Load atomic graph from DB (nodes are full GAV)
        2) Aggregate nodes based on show_group/show_version
        3) Optionally cut to a BFS neighborhood (root + depth)
        4) Convert to Cytoscape elements and return JSON

    Parameters:
        - root_id: optional, focus on a node
        - direction: forward (A -> B) or reverse (who depends on B)
        - depth: optional BFS depth; None means "All"
        - show_group/show_version: how node IDs are aggregated and how labels render

    Compatibility:
        DESIGN.md uses aggregate_group/aggregate_version with inverted meaning.
    """
    # Back-compat with design doc param naming.
    if aggregate_group is not None:
        show_group = not aggregate_group
    if aggregate_version is not None:
        show_version = not aggregate_version

    with Session(_engine()) as session:
        atomic = _load_atomic_graph(session)

    g = aggregate_graph(atomic, show_group=show_group, show_version=show_version)

    root_key: str | None = None
    if root_id:
        root_key = aggregated_node_id(root_id, show_group=show_group, show_version=show_version)

    if root_key and g.has_node(root_key):
        # Reduce payload size: only return a neighborhood when a root is selected.
        keep = nodes_within_depth(g, root_key, direction=direction, depth=depth)
        g = g.subgraph(keep).copy()

    elements = graph_to_cytoscape_elements(
        g,
        root_id=root_key,
        direction=direction,
        show_version=show_version,
    )

    return {
        "elements": elements,
        "meta": {
            "root_id": root_id,
            "root_key": root_key,
            "direction": direction,
            "depth": depth,
            "show_group": show_group,
            "show_version": show_version,
            "node_count": g.number_of_nodes(),
            "edge_count": g.number_of_edges(),
        },
    }
