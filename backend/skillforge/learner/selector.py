"""Question-selection inputs for a Teacher session, derived from learner state.

The Teacher engine still owns the turn-by-turn adaptive rules (difficulty
steps, remediation, confirmation). This module decides how a session STARTS
and what the engine should avoid or favour:

- start level   — from the student's concept evidence on the topic (and the
                  previous session's mastery), or an explicit target
                  difficulty coming from a recommendation;
- focus concept — the concept a recommendation targets (or the weakest one);
- exposure      — how many times the student has already answered each
                  question, so the engine prefers fresh questions;
- notes         — plain-language DIAGNOSE lines shown in the Teacher log.
"""

from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from skillforge.db.models import EvidenceEvent
from skillforge.learner.state import LearnerState
from skillforge.teacher import curriculum
from skillforge.teacher.curriculum import LEVEL_NAMES

INTERMEDIATE_START_ESTIMATE = 0.75
INTERMEDIATE_START_ATTEMPTS = 3
PRIOR_SESSION_START = 0.8


def exposure(db: Session, user_id: int, topic_id: str) -> dict[str, int]:
    prefix = f"{topic_id}/"
    rows = db.scalars(
        select(EvidenceEvent.question_id).where(
            EvidenceEvent.user_id == user_id, EvidenceEvent.concept_id.startswith(prefix)
        )
    ).all()
    return dict(Counter(rows))


def plan_session(
    db: Session,
    state: LearnerState,
    topic_id: str,
    prior_session_mastery: float | None,
    focus_concept: str | None = None,
    target_difficulty: int | None = None,
) -> dict:
    _, topic = curriculum.get_topic(topic_id)
    summary = state.topic_summary(topic_id)
    notes: list[str] = []

    if target_difficulty in (1, 2, 3):
        level = target_difficulty
        notes.append(f"Starting at the {LEVEL_NAMES[level]} level, as recommended for this concept.")
    elif prior_session_mastery is not None and prior_session_mastery >= PRIOR_SESSION_START:
        level = 2
        notes.append(
            f"Previous mastery was {round(prior_session_mastery * 100)}%. Skipping the basics and "
            "starting at the Intermediate level."
        )
    elif (
        summary["estimate"] is not None
        and summary["estimate"] >= INTERMEDIATE_START_ESTIMATE
        and summary["attempts"] >= INTERMEDIATE_START_ATTEMPTS
    ):
        level = 2
        notes.append(
            f"Your evidence on this topic (estimated {round(summary['estimate'] * 100)}% across "
            f"{summary['attempts']} graded answers) supports starting at the Intermediate level."
        )
    else:
        level = 1
        if prior_session_mastery is not None:
            notes.append(
                f"Previous mastery was {round(prior_session_mastery * 100)}%. Starting at the "
                "Foundational level to rebuild the base."
            )
        elif summary["assessed"]:
            notes.append(
                f"You have some evidence on this topic ({summary['attempts']} graded answers); "
                "starting at the Foundational level to confirm it."
            )
        else:
            notes.append(
                f"No previous evidence on {topic['title']}. Starting with a foundational baseline question."
            )

    if focus_concept not in topic["concepts"]:
        focus_concept = None
    if focus_concept:
        notes.append(f"Focusing first on {topic['concepts'][focus_concept]['name']}.")

    return {
        "start_level": level,
        "focus_concept": focus_concept,
        "exposure": exposure(db, state.user_id, topic_id),
        "notes": notes,
    }
