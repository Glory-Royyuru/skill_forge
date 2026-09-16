"""Engine/session-factory construction and table creation.

Kept free of global singletons on purpose: each caller (the FastAPI app,
the CLI, tests) builds its own :class:`~skillforge.db.database.Database`
from a URL, so tests can point at an isolated temp SQLite file without
fighting module-level caching.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from skillforge.db import models  # noqa: F401  (ensures models register on Base.metadata)
from skillforge.db.base import Base


def make_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
