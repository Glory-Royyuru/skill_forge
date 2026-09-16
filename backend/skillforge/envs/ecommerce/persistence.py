"""Glue between in-memory `envs.base.Task` objects and the `environments`/
`tasks` DB tables from Phase 0.
"""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from skillforge.db.models import Environment as DBEnvironment
from skillforge.db.models import Task as DBTask
from skillforge.envs.base import Task
from skillforge.envs.ecommerce.environment import EcommerceRefundEnvironment
from skillforge.envs.ecommerce.generator import BUCKET_NAMES, classify_expected
from skillforge.envs.ecommerce.policy import Expected

ENVIRONMENT_VERSION = "1"


def get_or_create_environment(db: Session) -> DBEnvironment:
    row = db.scalar(select(DBEnvironment).where(DBEnvironment.name == EcommerceRefundEnvironment.name))
    if row is not None:
        return row
    row = DBEnvironment(name=EcommerceRefundEnvironment.name, version=ENVIRONMENT_VERSION)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def save_tasks(db: Session, environment_id: int, seed: int, tasks: list[Task]) -> int:
    """Replace any existing tasks for this (environment, seed) with the
    given set, so repeated `generate` calls for the same seed are
    idempotent rather than accumulating duplicate rows.
    """
    db.execute(
        delete(DBTask).where(DBTask.environment_id == environment_id, DBTask.seed == seed)
    )
    for task in tasks:
        db.add(
            DBTask(
                environment_id=environment_id,
                seed=task.seed,
                split=task.split,
                request=task.request,
                initial_state_json=task.initial_state,
                ground_truth_json=task.ground_truth,
            )
        )
    db.commit()
    return len(tasks)


def load_tasks(
    db: Session, environment_id: int, split: str | None = None, limit: int | None = None
) -> list[Task]:
    stmt = select(DBTask).where(DBTask.environment_id == environment_id)
    if split is not None:
        stmt = stmt.where(DBTask.split == split)
    stmt = stmt.order_by(DBTask.id)
    if limit is not None:
        stmt = stmt.limit(limit)
    rows = db.scalars(stmt).all()
    return [
        Task(
            id=f"db-{row.id}",
            seed=row.seed,
            split=row.split,
            request=row.request,
            initial_state=row.initial_state_json,
            ground_truth=row.ground_truth_json,
        )
        for row in rows
    ]


def count_tasks_by_split(db: Session, environment_id: int) -> dict[str, int]:
    rows = db.execute(
        select(DBTask.split, func.count(DBTask.id))
        .where(DBTask.environment_id == environment_id)
        .group_by(DBTask.split)
    ).all()
    return {split: count for split, count in rows}


def count_by_split_and_rule(db: Session, environment_id: int) -> dict[str, dict[str, int]]:
    """`{split: {rule_id: count}}`, read directly from `ground_truth_json`.

    This is dev/CLI tooling reading the DB directly for a coverage report —
    not a learner- or teacher-facing code path, so reading
    `ground_truth_json` here is fine (see PROGRESS.md Decisions log).
    """
    rows = db.scalars(select(DBTask).where(DBTask.environment_id == environment_id)).all()
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        split_counts = counts.setdefault(row.split, {})
        for rule_id in row.ground_truth_json.get("rules_involved", []):
            split_counts[rule_id] = split_counts.get(rule_id, 0) + 1
    return counts


def count_decision_stats(db: Session, environment_id: int) -> dict[str, dict[str, int]]:
    """`{split: {"total", "process_full", "process_adjusted", "reject",
    "escalate", "interaction", "r1_only"}}` — same dev/CLI-tooling
    justification as `count_by_split_and_rule` for reading
    `ground_truth_json` directly.
    """
    rows = db.scalars(select(DBTask).where(DBTask.environment_id == environment_id)).all()
    stats: dict[str, dict[str, int]] = {}
    for row in rows:
        split_stats = stats.setdefault(
            row.split, {"total": 0, "interaction": 0, "r1_only": 0, **dict.fromkeys(BUCKET_NAMES, 0)}
        )
        split_stats["total"] += 1
        expected = Expected(**row.ground_truth_json)
        bucket, interaction, r1_only = classify_expected(expected)
        split_stats[bucket] += 1
        if interaction:
            split_stats["interaction"] += 1
        if r1_only:
            split_stats["r1_only"] += 1
    return stats
