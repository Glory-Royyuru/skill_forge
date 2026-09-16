from __future__ import annotations

import pytest

from skillforge.db.database import Database


@pytest.fixture()
def db(tmp_path):
    """A fresh, isolated SQLite-backed Database for one test."""
    database = Database(f"sqlite:///{tmp_path / 'test.db'}")
    database.init()
    yield database
    database.engine.dispose()
