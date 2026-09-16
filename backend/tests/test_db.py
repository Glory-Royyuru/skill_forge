from __future__ import annotations

from sqlalchemy import inspect

from skillforge.db.database import Database
from skillforge.db.models import Environment

EXPECTED_TABLES = {
    "agents",
    "environments",
    "skills",
    "skill_memory_versions",
    "demonstrations",
    "clarifications",
    "tasks",
    "training_sessions",
    "attempts",
    "diagnoses",
    "interventions",
    "evaluations",
    "llm_calls",
    "experiments",
}


def test_create_all_tables(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'schema.db'}")
    database.init()

    inspector = inspect(database.engine)
    tables = set(inspector.get_table_names())

    assert EXPECTED_TABLES <= tables
    database.engine.dispose()


def test_insert_and_query_round_trip(db):
    with db.session() as session:
        env = Environment(name="ecommerce_refunds", version="1")
        session.add(env)
        session.commit()
        session.refresh(env)
        env_id = env.id
        assert env_id is not None

    with db.session() as session:
        fetched = session.get(Environment, env_id)
        assert fetched is not None
        assert fetched.name == "ecommerce_refunds"
        assert fetched.version == "1"
