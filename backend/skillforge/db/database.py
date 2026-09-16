"""A small handle bundling an engine + session factory for one database URL.

Used instead of module-level globals so the FastAPI app, the CLI, and
tests can each own an independent ``Database`` (important for tests, which
each want their own temp SQLite file).
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from skillforge.db.session import init_db, make_engine, make_session_factory


class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = make_engine(database_url)
        self.session_factory = make_session_factory(self.engine)

    def init(self) -> None:
        """Create all tables that don't exist yet."""
        init_db(self.engine)

    def session(self) -> Session:
        return self.session_factory()

    def get_db(self) -> Generator[Session, None, None]:
        """FastAPI-style dependency: yields a session, closes it after."""
        db = self.session()
        try:
            yield db
        finally:
            db.close()
