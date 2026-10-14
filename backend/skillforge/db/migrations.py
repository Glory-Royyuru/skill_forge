"""A minimal, versioned schema-migration runner.

SkillForge has no Alembic setup; until it needs one, schema changes are
expressed as ordered Python steps here. Each applied version is recorded in
the `schema_migrations` table, so `Database.init()` (called on every app and
CLI start) only runs what is pending — no database deletion required.

Rules for adding a migration:
- Append `(next_version, "description", function)` to `MIGRATIONS`.
- Functions receive a SQLAlchemy `Connection` inside a transaction.
- Make them idempotent (check the inspector before adding a column/table):
  a brand-new database gets the latest schema from the baseline step and
  then still runs every later step once.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Connection, Engine

from skillforge.db import models  # noqa: F401  (registers every table on Base.metadata)
from skillforge.db.base import Base
from skillforge.db.models import SchemaMigration


def _baseline(conn: Connection) -> None:
    # Creates every table that does not exist yet. On a database created
    # before migrations existed, this adds the new tables and leaves existing
    # ones untouched.
    Base.metadata.create_all(bind=conn)


def _add_column(conn: Connection, table: str, column: str, ddl: str) -> None:
    if column not in {c["name"] for c in inspect(conn).get_columns(table)}:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def _learner_intelligence(conn: Connection) -> None:
    """Question metadata, response time, and the learner-evidence tables
    (evidence log, diagnostic, Rapid Round, flashcard reviews, preferences).
    Existing session answers are copied into the evidence log so earlier
    learning history keeps counting."""
    from skillforge.db.models import (
        Diagnostic,
        EvidenceEvent,
        FlashcardReview,
        RapidRound,
        UserPreference,
    )

    models_v2 = (EvidenceEvent, Diagnostic, RapidRound, FlashcardReview, UserPreference)
    new_tables = [m.__table__ for m in models_v2]
    Base.metadata.create_all(bind=conn, tables=new_tables)
    _add_column(conn, "questions", "cognitive_type", "VARCHAR(16)")
    _add_column(conn, "questions", "quality", "VARCHAR(16) NOT NULL DEFAULT 'reviewed'")
    _add_column(conn, "questions", "active", "BOOLEAN NOT NULL DEFAULT 1")
    _add_column(conn, "questions", "source", "VARCHAR(160)")
    _add_column(conn, "answers", "response_ms", "INTEGER")

    if conn.execute(text("SELECT COUNT(*) FROM evidence_events")).scalar() == 0:
        conn.execute(text(
            "INSERT INTO evidence_events (user_id, concept_id, question_id, source, ref_id, correct, "
            "difficulty, cognitive_type, weight, response_ms, p_before, p_after, created_at) "
            "SELECT a.user_id, a.concept_id, a.question_id, 'session', a.session_id, a.correct, "
            "a.difficulty, q.cognitive_type, 1.0, a.response_ms, a.known_before, a.known_after, "
            "a.created_at "
            "FROM answers a LEFT JOIN questions q ON q.id = a.question_id"
        ))


def _curriculum_areas(conn: Connection) -> None:
    """Curriculum areas (VNR syllabus vs general foundations such as DSA) and
    curated further-reading resources per topic. Existing subjects are VNR."""
    _add_column(conn, "subjects", "area", "VARCHAR(32) NOT NULL DEFAULT 'vnr-aiml-r22'")
    _add_column(conn, "topics", "resources_json", "JSON")


MIGRATIONS: list[tuple[int, str, Callable[[Connection], None]]] = [
    (1, "Baseline: all tables, including student accounts, curriculum, learning sessions, "
        "learner model state and timetable", _baseline),
    (2, "Learner intelligence: question metadata, response time, evidence log, diagnostic, "
        "Rapid Round, flashcard reviews, user preferences", _learner_intelligence),
    (3, "Curriculum areas and further-reading resources", _curriculum_areas),
]


def applied_versions(engine: Engine) -> set[int]:
    if not inspect(engine).has_table(SchemaMigration.__tablename__):
        return set()
    with engine.connect() as conn:
        return set(conn.scalars(select(SchemaMigration.version)))


def upgrade(engine: Engine) -> list[int]:
    """Apply pending migrations in order; return the versions applied."""
    SchemaMigration.__table__.create(bind=engine, checkfirst=True)
    done = applied_versions(engine)
    ran: list[int] = []
    for version, description, step in MIGRATIONS:
        if version in done:
            continue
        with engine.begin() as conn:
            step(conn)
            conn.execute(
                SchemaMigration.__table__.insert().values(version=version, description=description)
            )
        ran.append(version)
    return ran


def current_version(engine: Engine) -> int:
    versions = applied_versions(engine)
    return max(versions) if versions else 0
