from __future__ import annotations

import csv
import io

import main

from fastapi.testclient import TestClient

from fastapi.testclient import TestClient


def test_export_page_lists_tables() -> None:
    client = TestClient(main.app)
    res = client.get("/export")
    assert res.status_code == 200

    html = res.text
    assert "Database Export" in html
    # SQLModel tables in this app
    assert "artifact" in html
    assert "dependencyedge" in html
    assert "/export/artifact.csv" in html
    assert "/export/dependencyedge.csv" in html


def test_export_table_csv_artifact_has_header_and_rows(tmp_path) -> None:
    # Insert one row via the app's DB engine.
    from sqlmodel import Session
    from uuid import uuid4

    from j_dep_analyzer.db_models import Artifact

    # Use TestClient as context manager to trigger startup event (init_db)
    with TestClient(main.app) as client:
        gav = f"test:{uuid4().hex}:1"
        with Session(main._engine()) as session:
            session.add(Artifact(gav=gav, group_id="test", artifact_id="a", version="1"))
            session.commit()

        res = client.get("/export/artifact.csv")
        assert res.status_code == 200
        assert res.headers.get("content-type", "").startswith("text/csv")

        reader = csv.reader(io.StringIO(res.text))
        rows = list(reader)
        assert rows[0] == ["gav", "group_id", "artifact_id", "version"]
        assert [gav, "test", "a", "1"] in rows


def test_export_table_csv_rejects_invalid_table_name() -> None:
    client = TestClient(main.app)
    res = client.get("/export/artifact;drop.csv")
    assert res.status_code == 400


def test_export_table_csv_404_for_unknown_table() -> None:
    client = TestClient(main.app)
    res = client.get("/export/not_a_table.csv")
    assert res.status_code == 404


def test_export_dependencies_csv_not_truncated_by_hidden_limit(tmp_path) -> None:
    # Regression test: the dependencies export used to silently truncate because
    # the backend limited edges to 2000 inside the row builder.
    from pathlib import Path
    from sqlmodel import Session
    from uuid import uuid4

    from j_dep_analyzer.config import DatabaseConfig
    from j_dep_analyzer.db import create_sqlite_engine, init_db
    from j_dep_analyzer.db_models import Artifact, DependencyEdge

    # Save original config and cached engine
    old_config = main.db_config
    old_cached_engine = main._cached_engine

    try:
        # Create test config with temporary database
        test_db_path = tmp_path / "deps-test.db"
        main.db_config = DatabaseConfig(
            db_type="sqlite",
            sqlite_path=test_db_path,
        )
        # Reset cached engine so _engine() creates a new one with new config
        main._cached_engine = None
        init_db(create_sqlite_engine(test_db_path))

        sink_gav = f"test:sink:{uuid4().hex}"
        with Session(main._engine()) as session:
            session.add(Artifact(gav=sink_gav, group_id="test", artifact_id="sink", version="1"))

            edge_count = 2505
            for i in range(edge_count):
                src_gav = f"test:src{i}:{uuid4().hex}"
                session.add(Artifact(gav=src_gav, group_id="test", artifact_id=f"src{i}", version="1"))
                session.add(
                    DependencyEdge(
                        from_gav=src_gav,
                        to_gav=sink_gav,
                        scope="compile",
                        optional=False,
                    )
                )

            session.commit()

        client = TestClient(main.app)
        res = client.get("/api/dependencies/export")
        assert res.status_code == 200
        assert res.headers.get("content-type", "").startswith("text/csv")

        lines = [ln for ln in res.text.splitlines() if ln.strip()]
        # Header + one row per inserted edge.
        assert len(lines) == edge_count + 1
    finally:
        main.db_config = old_config
        main._cached_engine = old_cached_engine
