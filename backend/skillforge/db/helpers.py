"""Small get-or-create / query helpers for agents, skills, training
sessions, and attempts — shared by the CLI and the API so both go through
the same persistence logic.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from skillforge.db.models import Agent, Attempt, Skill, TrainingSession


def get_or_create_skill(db: Session, environment_id: int, name: str) -> Skill:
    row = db.scalar(select(Skill).where(Skill.environment_id == environment_id, Skill.name == name))
    if row is not None:
        return row
    row = Skill(name=name, environment_id=environment_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_or_create_agent(db: Session, name: str, provider: str, model: str) -> Agent:
    row = db.scalar(select(Agent).where(Agent.name == name))
    if row is not None:
        return row
    row = Agent(name=name, provider=provider, model=model, config_json={})
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_training_session(
    db: Session, skill_id: int, agent_id: int, condition: str, config: dict[str, Any]
) -> TrainingSession:
    row = TrainingSession(
        skill_id=skill_id, agent_id=agent_id, condition=condition, status="running", config_json=config
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def save_attempt(
    db: Session,
    session_id: int,
    task_id: int,
    trajectory: dict[str, Any],
    result: dict[str, Any],
    tokens: int,
    cost: float,
) -> Attempt:
    row = Attempt(
        session_id=session_id,
        task_id=task_id,
        trajectory_json=trajectory,
        result_json=result,
        tokens=tokens,
        cost=cost,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_attempt(db: Session, attempt_id: int) -> Attempt | None:
    return db.get(Attempt, attempt_id)


def db_task_id(task_id_str: str) -> int:
    """`envs.ecommerce.persistence.load_tasks` gives Task.id = f"db-{row.id}"."""
    return int(task_id_str.removeprefix("db-"))
