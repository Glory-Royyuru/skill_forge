"""Helpers for learner-layer tests: a seeded DB with a student, and a way to
record graded evidence directly (optionally backdated)."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import update

from skillforge.db.models import EvidenceEvent, User
from skillforge.learner import evidence
from skillforge.learner.evidence import utcnow
from skillforge.teacher import curriculum
from skillforge.teacher.seed import load_curriculum, seed_curriculum


def seeded(db) -> int:
    seed_curriculum(db)
    load_curriculum(db)
    with db.session() as s:
        u = User(email="t@example.com", name="Test Student", password_hash="x", email_verified_at=utcnow())
        s.add(u)
        s.commit()
        return u.id


def answer(
    db,
    user_id: int,
    question_id: str,
    correct: bool,
    source: str = "session",
    days_ago: float = 0,
    response_ms: int | None = None,
) -> None:
    _, topic, q = curriculum.find_question(question_id)
    with db.session() as s:
        e = evidence.record(
            s,
            user_id=user_id,
            concept_id=curriculum.concept_id(topic["id"], q["concept"]),
            question=q,
            source=source,
            ref_id=None,
            correct=correct,
            response_ms=response_ms,
        )
        s.flush()
        if days_ago:
            s.execute(
                update(EvidenceEvent)
                .where(EvidenceEvent.id == e.id)
                .values(created_at=utcnow() - timedelta(days=days_ago))
            )
        s.commit()


def choice_for(question_id: str, correct: bool) -> int:
    _, _, q = curriculum.find_question(question_id)
    return q["answer"] if correct else (q["answer"] + 1) % len(q["options"])
