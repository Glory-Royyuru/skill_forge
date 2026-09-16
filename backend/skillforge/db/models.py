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

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
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
