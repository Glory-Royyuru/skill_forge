"""Graded evidence: the single write path for learner-model updates.

Every graded interaction (Teacher session answer, diagnostic answer, Rapid
Round answer) is recorded as an `EvidenceEvent` and updates the student's
persisted BKT estimate in `learner_concepts`.

Sources carry different weights. A weight w < 1 applies a damped BKT update,

    p_after = p_before + w · (BKT(p_before, answer) − p_before),

so a Rapid Round answer moves the estimate half as far as a teaching-session
answer. This is a documented heuristic, not a fitted model: timed retrieval is
weaker evidence of understanding than an untimed, scaffolded question.

Flashcard self-reports are NOT graded evidence and never pass through here
(see `skillforge.learner.flashcards`).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from skillforge.db.models import EvidenceEvent, LearnerConcept
from skillforge.teacher.learner_model import BKTLearnerModel, LearnerModel, get_learner_model

SOURCE_WEIGHTS = {"session": 1.0, "diagnostic": 1.0, "rapid_round": 0.5}
MAX_RESPONSE_MS = 10 * 60 * 1000


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def clean_response_ms(value: int | None) -> int | None:
    """Response time is optional and secondary; discard implausible values."""
    if value is None or value <= 0 or value > MAX_RESPONSE_MS:
        return None
    return int(value)


def record(
    db: Session,
    *,
    user_id: int,
    concept_id: str,
    question: dict,
    source: str,
    ref_id: int | None,
    correct: bool,
    response_ms: int | None = None,
    model: LearnerModel | None | object = ...,
) -> EvidenceEvent:
    """Record one graded answer and update the persisted learner model.

    The caller owns the transaction (commits). `model=...` means "the
    configured learner model"; None records evidence without a BKT update.
    """
    weight = SOURCE_WEIGHTS[source]
    model = get_learner_model() if model is ... else model
    p_before = p_after = None
    if model is not None:
        lc = db.scalar(
            select(LearnerConcept).where(
                LearnerConcept.user_id == user_id, LearnerConcept.concept_id == concept_id
            )
        )
        prior = lc.p_known if lc is not None else model.init([concept_id])[concept_id]
        knowledge = {concept_id: prior}
        full = model.update(knowledge, concept_id, question["difficulty"], correct)
        p_before = prior
        p_after = round(prior + weight * (full - prior), 4)
        if lc is None:
            lc = LearnerConcept(
                user_id=user_id,
                concept_id=concept_id,
                model=model.name,
                p_known=p_after,
                attempts=0,
                correct=0,
            )
            db.add(lc)
        lc.model = model.name
        lc.p_known = p_after
        lc.attempts = (lc.attempts or 0) + 1
        lc.correct = (lc.correct or 0) + (1 if correct else 0)
        lc.updated_at = utcnow()
    event = EvidenceEvent(
        user_id=user_id,
        concept_id=concept_id,
        question_id=question["id"],
        source=source,
        ref_id=ref_id,
        correct=correct,
        difficulty=question["difficulty"],
        cognitive_type=question.get("cognitive_type"),
        weight=weight,
        response_ms=clean_response_ms(response_ms),
        p_before=p_before,
        p_after=p_after,
        created_at=utcnow(),
    )
    db.add(event)
    return event


def default_model() -> LearnerModel:
    """A model to use for priors when the configured one is disabled."""
    return get_learner_model() or BKTLearnerModel()
