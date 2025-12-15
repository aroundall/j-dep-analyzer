from __future__ import annotations

import csv
import io
import main

from fastapi.testclient import TestClient


def test_export_page_lists_tables() -> None:
    client = TestClient(main.app)
    res = client.get("/export")
    assert res.status_code == 200

    html = res.text
    assert "Export (CSV)" in html
    # SQLModel tables in this app
    assert "artifact" in html
    assert "dependencyedge" in html
    assert "/export/artifact.csv" in html
    assert "/export/dependencyedge.csv" in html


def test_export_table_csv_artifact_has_header_and_rows(tmp_path) -> None:
    # Insert one row via the app's DB engine.
    from sqlmodel import Session

    from j_dep_analyzer.db_models import Artifact

    with Session(main._engine()) as session:
        session.add(Artifact(gav="g:a:1", group_id="g", artifact_id="a", version="1"))
        session.commit()

    client = TestClient(main.app)
    res = client.get("/export/artifact.csv")
    assert res.status_code == 200
    assert res.headers.get("content-type", "").startswith("text/csv")

    reader = csv.reader(io.StringIO(res.text))
    rows = list(reader)
    assert rows[0] == ["gav", "group_id", "artifact_id", "version"]
    assert ["g:a:1", "g", "a", "1"] in rows


def test_export_table_csv_rejects_invalid_table_name() -> None:
    client = TestClient(main.app)
    res = client.get("/export/artifact;drop.csv")
    assert res.status_code == 400


def test_export_table_csv_404_for_unknown_table() -> None:
    client = TestClient(main.app)
    res = client.get("/export/not_a_table.csv")
    assert res.status_code == 404
