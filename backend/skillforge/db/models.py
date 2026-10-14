"""SQLAlchemy 2.x ORM models for every SkillForge table.

Phase 0 uses ``Base.metadata.create_all`` directly (see
:func:`skillforge.db.session.init_db`); Alembic migrations come later once
the schema has settled.

A note on ``tasks.ground_truth_json``: per CLAUDE.md, ground truth for
validation/test tasks must never be reachable from learner- or
teacher-facing code. This model just defines the column; the isolation is
an access-pattern concern enforced starting in Phase 1, when the
environment and evaluator modules are built (the evaluator should be the
only code path that reads this column for non-train splits).
"""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from skillforge.db.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    config_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Environment(Base):
    __tablename__ = "environments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(32), default="1")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SkillMemoryVersion(Base):
    __tablename__ = "skill_memory_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))
    version: Mapped[int] = mapped_column(Integer)
    content_json: Mapped[dict] = mapped_column(JSON)
    # Version number (not a row id) of the memory this was patched from.
    parent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    patch_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Demonstration(Base):
    __tablename__ = "demonstrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))
    trace_json: Mapped[dict] = mapped_column(JSON)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Clarification(Base):
    __tablename__ = "clarifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"))
    seed: Mapped[int] = mapped_column(Integer)
    split: Mapped[str] = mapped_column(String(16))  # train | validation | test
    request: Mapped[str] = mapped_column(Text)
    initial_state_json: Mapped[dict] = mapped_column(JSON)
    # See module docstring: keep this out of learner/teacher-facing code paths.
    ground_truth_json: Mapped[dict] = mapped_column(JSON)


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    condition: Mapped[str] = mapped_column(String(64))  # e.g. baseline_a, baseline_b, trained
    status: Mapped[str] = mapped_column(String(32), default="pending")
    config_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"))
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    memory_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trajectory_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id"))
    category: Mapped[str] = mapped_column(String(64))
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class Intervention(Base):
    __tablename__ = "interventions"

    id: Mapped[int] = mapped_column(primary_key=True)
    diagnosis_id: Mapped[int] = mapped_column(ForeignKey("diagnoses.id"))
    patch_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Version number (not a row id) the patch produced.
    resulting_version: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"))
    split: Mapped[str] = mapped_column(String(16))
    memory_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable: calls can happen outside a training session (e.g. ad hoc
    # extraction, health checks, tests).
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("training_sessions.id"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(16))  # teacher | learner
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(128))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    config_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- Student platform (accounts, curriculum, learning, timetable) ------------
#
# Everything below belongs to the multi-student Teacher Agent. Student-owned
# rows carry a `user_id`; API code must always filter by the authenticated
# user's id (see `skillforge.auth.deps`).


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stored normalized (trimmed, lower-case); unique.
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    # Optional college registration number (e.g. "22071A6601").
    student_id: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    # scrypt hash, never the password (see `skillforge.auth.security`).
    password_hash: Mapped[str] = mapped_column(String(255))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def is_verified(self) -> bool:
        return self.email_verified_at is not None


class AuthSession(Base):
    """A login. The browser holds the random token in an HttpOnly cookie; only
    its SHA-256 hash is stored, so a database leak does not leak sessions."""

    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# Curriculum. Primary keys are stable slugs from the seed content
# (`skillforge.teacher.content`), so re-seeding is an idempotent upsert.


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    code: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(120))
    short_name: Mapped[str] = mapped_column(String(24))
    kind: Mapped[str] = mapped_column(String(16))  # theory | laboratory | mandatory | foundation
    description: Mapped[str] = mapped_column(Text)
    unit_label: Mapped[str] = mapped_column(String(16), default="Unit")
    position: Mapped[int] = mapped_column(Integer)
    # Curriculum area (schema version 3): "vnr-aiml-r22" or "foundations".
    area: Mapped[str] = mapped_column(String(32), default="vnr-aiml-r22")


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # f"{subject_id}:{number}"
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"), index=True)
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(16))
    position: Mapped[int] = mapped_column(Integer)
    # {"intro", "body", "key_points"}; null for topics without a question bank yet.
    lesson_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Curated further reading (schema version 3): [{"title", "url", "publisher", "concepts"?}]
    resources_json: Mapped[list | None] = mapped_column(JSON, nullable=True)


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)  # f"{topic_id}/{key}"
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(120))
    reteach: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)


class Question(Base):
    """Answer keys live here and leave the server only after an answer is
    submitted (see `curriculum.public_question`)."""

    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), index=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), index=True)
    difficulty: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[str] = mapped_column(Text)
    options_json: Mapped[list] = mapped_column(JSON)
    answer_index: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(Text)
    why_wrong_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    position: Mapped[int] = mapped_column(Integer)
    # Question metadata (schema version 2).
    # recall | understand | apply | analyze
    cognitive_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # reviewed: checked and used everywhere; draft: excluded from analytics; retired: never served.
    quality: Mapped[str] = mapped_column(String(16), default="reviewed")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str | None] = mapped_column(String(160), nullable=True)


class LearningSession(Base):
    """One Teacher Agent session. `state_json` is the engine's full session
    state; the other columns are denormalized for queries and reports."""

    __tablename__ = "learning_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | completed | abandoned
    state_json: Mapped[dict] = mapped_column(JSON)
    mastery: Mapped[float] = mapped_column(Float, default=0.0)
    answered_count: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Answer(Base):
    """One graded answer, with the adaptive decision the Teacher took after it."""

    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("learning_sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"))
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)  # 1-based position within the session
    choice: Mapped[int] = mapped_column(Integer)
    correct: Mapped[bool] = mapped_column(Boolean)
    verdict: Mapped[str] = mapped_column(String(16))  # correct | incorrect | needs_review
    difficulty: Mapped[int] = mapped_column(Integer)
    mastery_after: Mapped[float] = mapped_column(Float)
    known_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    known_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)  # schema version 2
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LearnerConcept(Base):
    """Per-student learner-model state for one concept (BKT P(known))."""

    __tablename__ = "learner_concepts"
    __table_args__ = (UniqueConstraint("user_id", "concept_id", name="uq_learner_concept"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), index=True)
    model: Mapped[str] = mapped_column(String(16))  # e.g. "bkt"
    p_known: Mapped[float] = mapped_column(Float)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TimetableEntry(Base):
    """One weekly class slot. `source` records how the row was created
    ("manual" today); importers (PDF/image/Excel) add their own values."""

    __tablename__ = "timetable_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0 = Monday … 6 = Sunday
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"))
    faculty: Mapped[str | None] = mapped_column(String(120), nullable=True)
    room: Mapped[str | None] = mapped_column(String(60), nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SchemaMigration(Base):
    """Applied schema versions (see `skillforge.db.migrations`)."""

    __tablename__ = "schema_migrations"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String(255))
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- Learner intelligence (schema version 2) -----------------------------------------


class EvidenceEvent(Base):
    """One graded interaction, from any source, used to build the learner
    state. Teacher sessions, the onboarding diagnostic and Rapid Round all
    write here; each source carries a different evidence `weight` (see
    `skillforge.learner.evidence.SOURCE_WEIGHTS`). Grading is deterministic;
    `p_before`/`p_after` record the learner-model estimate around the answer."""

    __tablename__ = "evidence_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"))
    source: Mapped[str] = mapped_column(String(16))  # session | diagnostic | rapid_round
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # session / diagnostic / round id
    correct: Mapped[bool] = mapped_column(Boolean)
    difficulty: Mapped[int] = mapped_column(Integer)
    cognitive_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    weight: Mapped[float] = mapped_column(Float)
    # Secondary signal only; never used as a mastery score.
    response_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    p_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Diagnostic(Base):
    """The short onboarding diagnostic that establishes a starting point."""

    __tablename__ = "diagnostics"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | completed
    question_ids: Mapped[list] = mapped_column(JSON)
    # [{question_id, choice (null = skipped), correct}]
    responses: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RapidRound(Base):
    """A timed retrieval-practice round. The server owns the deadline."""

    __tablename__ = "rapid_rounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | finished
    question_ids: Mapped[list] = mapped_column(JSON)
    responses: Mapped[list] = mapped_column(JSON, default=list)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FlashcardReview(Base):
    """A student's self-report on a flashcard. A secondary signal: it orders
    review recommendations but never counts as a graded answer."""

    __tablename__ = "flashcard_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[str] = mapped_column(String(160))
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), index=True)
    rating: Mapped[str] = mapped_column(String(16))  # known | review | skipped
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    mode: Mapped[str] = mapped_column(String(16), default="student")  # student | ptm
    theme: Mapped[str] = mapped_column(String(16), default="auto")  # auto | none | <season>
    diagnostic_skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
