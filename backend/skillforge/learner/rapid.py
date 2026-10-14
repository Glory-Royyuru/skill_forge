"""Rapid Round: 60 seconds of quick retrieval practice.

It measures retrieval fluency under time pressure, which is weaker evidence
of understanding than a Teacher session, so each answer is recorded with
evidence weight 0.5 (a damped BKT update, see `learner.evidence`).

The server owns the clock: a round has a deadline, and answers arriving
after it (beyond a small network grace period) are refused.

Question choice: reviewed Foundational/Intermediate questions, round-robin
across concepts the student has practised (the point is retrieval of
familiar material), least-recently-seen first, topped up from unstarted
topics if needed.

Results are described without judgement; speed only ever qualifies a
result ("Slow but accurate"), it never lowers mastery.
"""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from statistics import median

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from skillforge.db.models import EvidenceEvent, RapidRound
from skillforge.learner import evidence
from skillforge.learner.evidence import utcnow
from skillforge.learner.state import LearnerState
from skillforge.teacher import curriculum

DURATION_SECONDS = 60
GRACE_SECONDS = 3
ROUND_SIZE = 10
FAST_MS = 6000


class RapidError(ValueError):
    pass


def _naive(dt):
    return dt.replace(tzinfo=None) if dt is not None and dt.tzinfo else dt


def choose_questions(db: Session, state: LearnerState) -> list[str]:
    seen = Counter(
        db.scalars(select(EvidenceEvent.question_id).where(EvidenceEvent.user_id == state.user_id))
    )
    practised = sorted(state.assessed(), key=lambda c: c.p_known or 0)
    pools = []
    for c in practised:
        _, topic = curriculum.get_topic(c.topic_id)
        qs = [
            q
            for q in topic["questions"]
            if q["concept"] == c.key and q["difficulty"] <= 2 and curriculum.is_reviewed(q)
        ]
        qs.sort(key=lambda q: (seen[q["id"]], q["difficulty"], q["id"]))
        if qs:
            pools.append(qs)
    chosen: list[str] = []
    while pools and len(chosen) < ROUND_SIZE:
        for pool in list(pools):
            if pool:
                q = pool.pop(0)
                if q["id"] not in chosen:
                    chosen.append(q["id"])
            if not pool:
                pools.remove(pool)
            if len(chosen) >= ROUND_SIZE:
                break
    if len(chosen) < ROUND_SIZE:
        for tid in curriculum.topic_ids():
            _, topic = curriculum.get_topic(tid)
            for q in topic["questions"]:
                if q["difficulty"] == 1 and curriculum.is_reviewed(q) and q["id"] not in chosen:
                    chosen.append(q["id"])
                    break
            if len(chosen) >= ROUND_SIZE:
                break
    return chosen


def start(db: Session, state: LearnerState) -> RapidRound:
    # Close any round left open (e.g. the tab was closed).
    db.execute(
        update(RapidRound)
        .where(RapidRound.user_id == state.user_id, RapidRound.status == "active")
        .values(status="finished", finished_at=utcnow())
    )
    now = utcnow()
    r = RapidRound(
        user_id=state.user_id,
        status="active",
        question_ids=choose_questions(db, state),
        responses=[],
        duration_seconds=DURATION_SECONDS,
        started_at=now,
        deadline_at=now + timedelta(seconds=DURATION_SECONDS),
    )
    db.add(r)
    db.flush()
    return r


def remaining_seconds(r: RapidRound) -> float:
    return max(0.0, (_naive(r.deadline_at) - utcnow()).total_seconds())


def view(r: RapidRound) -> dict:
    questions = []
    for qid in r.question_ids:
        subject, topic, q = curriculum.find_question(qid)
        questions.append(
            {
                **curriculum.public_question(topic, q),
                "topic_title": topic["title"],
                "subject_name": subject["short_name"],
            }
        )
    return {
        "id": r.id,
        "status": r.status,
        "duration_seconds": r.duration_seconds,
        "remaining_seconds": round(remaining_seconds(r), 1) if r.status == "active" else 0,
        "questions": questions,
        "answered": [x["question_id"] for x in r.responses],
    }


def answer(
    db: Session, user_id: int, r: RapidRound, question_id: str, choice: int, response_ms: int | None
) -> dict:
    if r.status != "active":
        raise RapidError("This round has finished.")
    if utcnow() > _naive(r.deadline_at) + timedelta(seconds=GRACE_SECONDS):
        raise RapidError("Time is up for this round.")
    if question_id not in r.question_ids or question_id in {x["question_id"] for x in r.responses}:
        raise RapidError("That question is not open in this round.")
    _, topic, q = curriculum.find_question(question_id)
    if not 0 <= choice < len(q["options"]):
        raise RapidError("Choice is out of range.")
    correct = choice == q["answer"]
    evidence.record(
        db,
        user_id=user_id,
        concept_id=curriculum.concept_id(topic["id"], q["concept"]),
        question=q,
        source="rapid_round",
        ref_id=r.id,
        correct=correct,
        response_ms=response_ms,
    )
    r.responses = [
        *r.responses,
        {
            "question_id": question_id,
            "choice": choice,
            "correct": correct,
            "response_ms": evidence.clean_response_ms(response_ms),
        },
    ]
    return {"correct": correct, "correct_choice": q["answer"]}


def label(accuracy: float | None, median_ms: int | None, attempted: int) -> tuple[str, str]:
    if attempted == 0:
        return "No answers recorded", "Try again when you have a minute; nothing was counted."
    if accuracy >= 0.8 and (median_ms is None or median_ms <= FAST_MS):
        return "Strong retrieval", "You recalled these quickly and accurately."
    if accuracy >= 0.8:
        return (
            "Slow but accurate",
            "Your answers were right; speed will come with practice. Accuracy matters more.",
        )
    if accuracy >= 0.5:
        return (
            "Mixed retrieval",
            "Some concepts came back easily, others did not. The ones you missed are worth a review.",
        )
    return (
        "Needs review",
        "Several of these concepts are not coming back yet. A short review session will help.",
    )


def finish(r: RapidRound) -> dict:
    if r.status == "active":
        r.status = "finished"
        r.finished_at = utcnow()
    attempted = len(r.responses)
    correct = sum(1 for x in r.responses if x["correct"])
    times = [x["response_ms"] for x in r.responses if x.get("response_ms")]
    med = int(median(times)) if times else None
    accuracy = correct / attempted if attempted else None
    per_concept: dict[str, dict] = {}
    for x in r.responses:
        subject, topic, q = curriculum.find_question(x["question_id"])
        name = topic["concepts"][q["concept"]]["name"]
        item = per_concept.setdefault(
            name, {"concept": name, "topic_title": topic["title"], "attempted": 0, "correct": 0}
        )
        item["attempted"] += 1
        item["correct"] += 1 if x["correct"] else 0
    headline, detail = label(accuracy, med, attempted)
    elapsed = None
    if r.finished_at and r.started_at:
        elapsed = min(
            r.duration_seconds, round((_naive(r.finished_at) - _naive(r.started_at)).total_seconds())
        )
    return {
        "id": r.id,
        "attempted": attempted,
        "correct": correct,
        "total_questions": len(r.question_ids),
        "accuracy": accuracy,
        "median_response_ms": med,
        "elapsed_seconds": elapsed,
        "headline": headline,
        "detail": detail,
        "concepts": sorted(per_concept.values(), key=lambda c: c["correct"] / c["attempted"]),
        "note": "Rapid Round measures quick recall. It counts as lighter evidence than a Teacher session.",
    }
