from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine


def create_sqlite_engine(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def init_db(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)
