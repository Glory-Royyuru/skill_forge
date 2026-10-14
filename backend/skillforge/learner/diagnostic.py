"""Onboarding diagnostic: a short, evidence-gathering starting point.

One question per subject that has a question bank (9 today: the eight VNR
courses and DSA),
each a reviewed Intermediate question, preferring "understand"/"apply"
items over pure recall. Answers are graded deterministically and recorded
as normal evidence (BKT update included); a skipped question records
nothing. Because the BKT update from one answer is modest and mastery needs
several answers (see `learner.state`), the diagnostic can establish a
starting point but can never mark anything mastered.

The student does not see correctness during the diagnostic; the summary at
the end shows each answer with its explanation.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from skillforge.db.models import Diagnostic, UserPreference
from skillforge.learner import evidence
from skillforge.learner.evidence import utcnow
from skillforge.teacher import curriculum
from skillforge.teacher.curriculum import LEVEL_NAMES

PREFERRED_TYPES = ("understand", "apply", "analyze", "recall")


class DiagnosticError(ValueError):
    pass


def choose_questions() -> list[str]:
    chosen = []
    for s in curriculum.subjects():
        candidates = []
        for tid in curriculum.assessable_in_subject(s["id"]):
            _, topic = curriculum.get_topic(tid)
            for q in topic["questions"]:
                if curriculum.is_reviewed(q) and q["difficulty"] == 2:
                    candidates.append(q)
        if candidates:
            candidates.sort(key=lambda q: PREFERRED_TYPES.index(q.get("cognitive_type") or "recall"))
            chosen.append(candidates[0]["id"])
    return chosen


def latest(db: Session, user_id: int) -> Diagnostic | None:
    return db.scalar(
        select(Diagnostic).where(Diagnostic.user_id == user_id).order_by(Diagnostic.id.desc()).limit(1)
    )


def preference(db: Session, user_id: int) -> UserPreference:
    pref = db.get(UserPreference, user_id)
    if pref is None:
        pref = UserPreference(user_id=user_id, mode="student", theme="auto", diagnostic_skipped=False)
        db.add(pref)
        db.flush()
    return pref


def status(db: Session, user_id: int) -> str:
    d = latest(db, user_id)
    if d is not None and d.status == "completed":
        return "completed"
    if d is not None and d.status == "active":
        return "active"
    pref = db.get(UserPreference, user_id)
    return "skipped" if pref is not None and pref.diagnostic_skipped else "none"


def start(db: Session, user_id: int) -> Diagnostic:
    d = latest(db, user_id)
    if d is not None and d.status == "active":
        return d
    if d is not None and d.status == "completed":
        raise DiagnosticError("You have already completed the diagnostic.")
    questions = choose_questions()
    if not questions:
        raise DiagnosticError("No reviewed questions are available for a diagnostic.")
    d = Diagnostic(
        user_id=user_id, status="active", question_ids=questions, responses=[], created_at=utcnow()
    )
    db.add(d)
    db.flush()
    return d


def view(d: Diagnostic) -> dict:
    answered = len(d.responses)
    current = None
    if d.status == "active" and answered < len(d.question_ids):
        subject, topic, q = curriculum.find_question(d.question_ids[answered])
        current = {
            **curriculum.public_question(topic, q),
            "subject_name": subject["name"],
            "topic_title": topic["title"],
        }
    return {
        "id": d.id,
        "status": d.status,
        "total": len(d.question_ids),
        "answered": answered,
        "current_question": current,
        "summary": summary(d) if d.status == "completed" else None,
    }


def answer(
    db: Session, user_id: int, d: Diagnostic, question_id: str, choice: int | None, response_ms: int | None
) -> None:
    if d.status != "active":
        raise DiagnosticError("This diagnostic is already complete.")
    answered = len(d.responses)
    if question_id != d.question_ids[answered]:
        raise DiagnosticError("That is not the current diagnostic question.")
    subject, topic, q = curriculum.find_question(question_id)
    if choice is not None and not 0 <= choice < len(q["options"]):
        raise DiagnosticError("Choice is out of range.")
    correct = None if choice is None else choice == q["answer"]
    if choice is not None:
        evidence.record(
            db,
            user_id=user_id,
            concept_id=curriculum.concept_id(topic["id"], q["concept"]),
            question=q,
            source="diagnostic",
            ref_id=d.id,
            correct=correct,
            response_ms=response_ms,
        )
    d.responses = [*d.responses, {"question_id": question_id, "choice": choice, "correct": correct}]
    if len(d.responses) == len(d.question_ids):
        d.status = "completed"
        d.completed_at = utcnow()


def summary(d: Diagnostic) -> dict:
    items = []
    for r in d.responses:
        subject, topic, q = curriculum.find_question(r["question_id"])
        skipped = r["choice"] is None
        items.append(
            {
                "subject_name": subject["name"],
                "subject_id": subject["id"],
                "topic_id": topic["id"],
                "topic_title": topic["title"],
                "concept_name": topic["concepts"][q["concept"]]["name"],
                "difficulty_label": LEVEL_NAMES[q["difficulty"]],
                "prompt": q["prompt"],
                "your_answer": None if skipped else q["options"][r["choice"]],
                "correct_answer": q["options"][q["answer"]],
                "correct": r["correct"],
                "skipped": skipped,
                "explanation": q["explanation"],
                "starting_point": (
                    "Not assessed (skipped)"
                    if skipped
                    else "Start at Intermediate"
                    if r["correct"]
                    else "Start at Foundational"
                ),
            }
        )
    answered = [i for i in items if not i["skipped"]]
    return {
        "answered": len(answered),
        "correct": sum(1 for i in answered if i["correct"]),
        "skipped": len(items) - len(answered),
        "items": items,
        "note": "This is a starting point, not a measure of mastery: one answer per subject is weak "
        "evidence. Your estimates will sharpen as you study.",
    }
