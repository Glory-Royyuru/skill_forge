"""Per-student persistence and progress analytics for Teacher Agent sessions.

Every function takes the authenticated student's `user_id` and every query
filters on it, so one student can never read or change another's sessions,
answers or learner-model state.

Tables (see `skillforge.db.models`):
- `learning_sessions` — one row per session; `state_json` holds the engine
  state, the other columns are summaries for queries.
- `answers` — one row per graded answer, with the adaptive decision taken.
- `learner_concepts` — the student's learner-model estimate P(known) per
  concept, carried across sessions and topics' re-takes.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime

from sqlalchemy import func, select, update

from skillforge.db.database import Database
from skillforge.db.models import Answer, LearnerConcept, LearningSession
from skillforge.learner import evidence
from skillforge.learner import state as learner_state
from skillforge.teacher import curriculum, engine
from skillforge.teacher.learner_model import get_learner_model


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _iso(dt: datetime | None) -> str | None:
    # SQLite hands back naive datetimes; they are UTC.
    if dt is None:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).isoformat()


# --- Sessions ---------------------------------------------------------------------


def _owned(session_id: int, user_id: int):
    """Select a session only if it belongs to the student."""
    return select(LearningSession).where(LearningSession.id == session_id, LearningSession.user_id == user_id)


def create_session(db: Database, user_id: int, state: dict) -> int:
    with db.session() as s:
        # One active session per student: starting a new one shelves the old.
        s.execute(
            update(LearningSession)
            .where(LearningSession.user_id == user_id, LearningSession.status == "active")
            .values(status="abandoned")
        )
        row = LearningSession(
            user_id=user_id, topic_id=state["topic_id"], status=state["status"],
            state_json=copy.deepcopy(state), mastery=state["mastery"],
        )
        s.add(row)
        s.commit()
        return row.id


def load_session(db: Database, user_id: int, session_id: int) -> dict | None:
    """The engine state of a session the student owns, else None."""
    with db.session() as s:
        row = s.scalar(_owned(session_id, user_id))
        if row is None:
            return None
        state = copy.deepcopy(row.state_json)
        # A newer session may have shelved this one.
        if row.status == "abandoned":
            state["status"] = "abandoned"
        return state


def record_answer(
    db: Database, user_id: int, session_id: int, state: dict, feedback: dict, response_ms: int | None = None
) -> None:
    """Persist one graded answer atomically: the session state, the answer row
    with the Teacher's decision, and the evidence event (which also updates the
    student's persisted learner model; see `skillforge.learner.evidence`)."""
    answer = state["answers"][-1]
    topic_id = state["topic_id"]
    concept_id = curriculum.concept_id(topic_id, answer["concept"])
    lm = feedback.get("learner_model")
    with db.session() as s:
        row = s.scalar(_owned(session_id, user_id))
        if row is None:  # pragma: no cover - callers load the session first
            raise LookupError("session not found")
        row.state_json = copy.deepcopy(state)  # reassign so SQLAlchemy sees the JSON change
        row.status = state["status"]
        row.mastery = state["mastery"]
        row.answered_count = len(state["answers"])
        row.correct_count = sum(1 for a in state["answers"] if a["correct"])
        if state["status"] == "completed":
            row.completed_at = _now()

        s.add(Answer(
            session_id=session_id, user_id=user_id, question_id=answer["question_id"], concept_id=concept_id,
            number=len(state["answers"]), choice=answer["choice"], correct=answer["correct"],
            verdict=answer["verdict"], difficulty=answer["difficulty"], mastery_after=state["mastery"],
            known_before=lm["known_before"] if lm else None, known_after=lm["known_after"] if lm else None,
            decision_json={
                "adaptation": feedback["adaptation"],
                "transition": feedback["transition"],
                "next_concept": feedback.get("next_concept_name"),
                "targeting": lm.get("targeting") if lm else None,
            },
            response_ms=evidence.clean_response_ms(response_ms),
        ))
        model = get_learner_model(state["learner_model"]["name"]) if state.get("learner_model") else None
        evidence.record(
            s, user_id=user_id, concept_id=concept_id,
            question=curriculum.get_question(topic_id, answer["question_id"]), source="session",
            ref_id=session_id, correct=answer["correct"], response_ms=response_ms, model=model,
        )
        s.commit()


# --- Prior state used to DIAGNOSE a new session ------------------------------------


def prior_mastery(db: Database, user_id: int, topic_id: str) -> float | None:
    """Mastery from the student's most recent completed session on this topic."""
    with db.session() as s:
        return s.scalar(
            select(LearningSession.mastery)
            .where(LearningSession.user_id == user_id, LearningSession.topic_id == topic_id,
                   LearningSession.status == "completed")
            .order_by(LearningSession.completed_at.desc(), LearningSession.id.desc())
            .limit(1)
        )


def prior_knowledge(db: Database, user_id: int, topic_id: str) -> dict[str, float] | None:
    """The student's persisted learner-model estimates for this topic's
    concepts, keyed the way the engine expects, or None if there are none."""
    prefix = f"{topic_id}/"
    with db.session() as s:
        rows = s.execute(
            select(LearnerConcept.concept_id, LearnerConcept.p_known).where(
                LearnerConcept.user_id == user_id, LearnerConcept.concept_id.startswith(prefix)
            )
        ).all()
    return {cid[len(prefix):]: p for cid, p in rows} or None


# --- Progress --------------------------------------------------------------------


def _completed(db: Database, user_id: int) -> list[tuple[int, dict, datetime | None]]:
    with db.session() as s:
        rows = s.execute(
            select(LearningSession.id, LearningSession.state_json, LearningSession.completed_at)
            .where(LearningSession.user_id == user_id, LearningSession.status == "completed")
            .order_by(LearningSession.completed_at, LearningSession.id)
        ).all()
    return [(i, st, c) for i, st, c in rows]


def topic_progress(
    db: Database, user_id: int, state: learner_state.LearnerState | None = None
) -> dict[str, dict]:
    """Per assessable topic, derived from concept-level learner state:
    `mastery` is the mean estimated knowledge over the topic's assessed
    concepts (None until there is evidence), reported with `coverage`
    (assessed / total concepts); `status` follows `learner.state.topic_status`."""
    if state is None:
        with db.session() as s:
            state = learner_state.build(s, user_id)
    sessions: dict[str, int] = {}
    best: dict[str, float] = {}
    for _, st, _ in _completed(db, user_id):
        sessions[st["topic_id"]] = sessions.get(st["topic_id"], 0) + 1
        best[st["topic_id"]] = max(best.get(st["topic_id"], 0.0), st["mastery"])
    out = {}
    for tid in curriculum.topic_ids():
        summary = state.topic_summary(tid)
        out[tid] = {
            "mastery": summary["estimate"],
            "coverage": summary["coverage"],
            "concepts_assessed": summary["assessed"],
            "concepts_total": summary["total"],
            "attempts": summary["attempts"],
            "best": best.get(tid),  # best single-session score, kept for reference
            "sessions": sessions.get(tid, 0),
            "status": summary["status"],
            "needs_review": [c.name for c in state.by_topic(tid) if c.status == "needs_review"],
        }
    return out


def curriculum_with_progress(db: Database, user_id: int) -> list[dict]:
    progress = topic_progress(db, user_id)
    active = active_session(db, user_id)
    subjects = curriculum.public_curriculum()
    for s in subjects:
        for u in s["units"]:
            for t in u["topics"]:
                t["progress"] = progress.get(t["id"])
                t["session_length"] = min(engine.QUESTIONS_PER_SESSION, t["question_count"])
                t["active_session_id"] = active["id"] if active and active["topic_id"] == t["id"] else None
    return subjects


def active_session(db: Database, user_id: int) -> dict | None:
    with db.session() as s:
        row = s.scalar(
            select(LearningSession)
            .where(LearningSession.user_id == user_id, LearningSession.status == "active")
            .order_by(LearningSession.id.desc())
            .limit(1)
        )
        if row is None:
            return None
        view = engine.session_view(row.state_json)
        return {
            "id": row.id,
            "topic_id": view["topic_id"],
            "topic_title": view["topic_title"],
            "subject_name": view["subject_name"],
            "question_number": view["question_number"],
            "max_questions": view["max_questions"],
            "mastery": view["mastery"],
            "created_at": _iso(row.created_at),
        }


def learner_model_state(db: Database, user_id: int) -> dict:
    """The student's persisted concept estimates, summarized."""
    with db.session() as s:
        rows = s.execute(
            select(LearnerConcept.concept_id, LearnerConcept.p_known, LearnerConcept.attempts)
            .where(LearnerConcept.user_id == user_id)
            .order_by(LearnerConcept.p_known)
        ).all()
    concepts = []
    for cid, p, attempts in rows:
        topic_id, key = cid.split("/", 1)
        found = curriculum.get_topic(topic_id)
        if found is None:
            continue
        subject, topic = found
        concepts.append({
            "concept": topic["concepts"].get(key, {}).get("name", key),
            "topic_id": topic_id,
            "topic_title": topic["title"],
            "subject_name": subject["name"],
            "p_known": p,
            "attempts": attempts,
        })
    return {
        "tracked": len(concepts),
        "average": sum(c["p_known"] for c in concepts) / len(concepts) if concepts else None,
        "weakest": concepts[:4],
        "strongest": list(reversed(concepts[-4:])) if concepts else [],
    }


def _session_summary(session_id: int, state: dict, completed_at: datetime | None) -> dict:
    report = engine.build_report(state)
    return {
        "id": session_id,
        "topic_id": report["topic_id"],
        "topic_title": report["topic_title"],
        "subject_name": report["subject_name"],
        "score": report["score"],
        "mastery": report["mastery"],
        "band": report["band"],
        "correct": report["correct"],
        "attempted": report["attempted"],
        "summary": report["summary"],
        "learner_model": report["learner_model"] is not None,
        "created_at": _iso(completed_at),
    }


def progress_overview(db: Database, user_id: int) -> dict:
    """Progress summary built on concept-level learner state (see
    `skillforge.learner.state` for the status rules and aggregation)."""
    with db.session() as s:
        state = learner_state.build(s, user_id)
    completed = _completed(db, user_id)
    tp = topic_progress(db, user_id, state)
    overall = state.overall()

    subjects = []
    for subj in curriculum.subjects():
        ids = curriculum.assessable_in_subject(subj["id"])
        summary = state.subject_summary(subj["id"])
        subjects.append({
            "id": subj["id"],
            "name": subj["name"],
            "short_name": subj["short_name"],
            "code": subj["code"],
            "mastery": summary["estimate"],
            "coverage": summary["coverage"],
            "concepts_assessed": summary["assessed"],
            "concepts_total": summary["total"],
            "topics_started": sum(1 for t in ids if tp[t]["status"] != "not_started"),
            "topics_total": len(ids),
            "topics": [{"id": t, "title": curriculum.get_topic(t)[1]["title"], **tp[t]} for t in ids],
        })

    with db.session() as s:
        answered = s.scalar(select(func.count(Answer.id)).where(Answer.user_id == user_id))
        correct = s.scalar(
            select(func.count(Answer.id)).where(Answer.user_id == user_id, Answer.correct.is_(True))
        )

    strengths = [
        {"concept": c.name, "topic_id": c.topic_id, "topic_title": c.topic_title, "p_known": c.p_known}
        for c in sorted(state.assessed(), key=lambda c: -(c.p_known or 0)) if c.status == "mastered"
    ]
    improve = [
        {"concept": c.name, "topic_id": c.topic_id, "topic_title": c.topic_title, "p_known": c.p_known,
         "status": "weak" if c.status == "needs_review" else "developing"}
        for c in sorted(state.assessed(), key=lambda c: (c.status != "needs_review", c.p_known or 0))
        if c.status in ("needs_review", "learning")
    ]

    if completed:
        last_id, last_state, _ = completed[-1]
        rec = engine.build_report(last_state)["recommendation"]
        recommended = {
            "topic_id": rec["next_topic_id"],
            "topic_title": rec["next_topic_title"],
            "subject_name": rec["next_subject_name"],
            "headline": rec["headline"],
            "reason": rec["text"],
            "from_session_id": last_id,
        }
    else:
        first = curriculum.topic_ids()[0]
        subject, topic = curriculum.get_topic(first)
        recommended = {
            "topic_id": first,
            "topic_title": topic["title"],
            "subject_name": subject["name"],
            "headline": f"Start with {topic['title']}",
            "reason": "Start your first learning session. Your teacher will diagnose where you are and "
            "adapt every question to you.",
            "from_session_id": None,
        }

    return {
        # Concept-level: mean estimated knowledge over assessed concepts, with coverage.
        "overall_mastery": overall["estimate"],
        "coverage": overall["coverage"],
        "concepts_assessed": overall["assessed"],
        "concepts_total": overall["total"],
        "concepts_mastered": overall["mastered"],
        "concepts_needs_review": overall["needs_review"],
        "topics_started": sum(1 for p in tp.values() if p["status"] != "not_started"),
        "topics_total": len(tp),
        "topics_mastered": sum(1 for p in tp.values() if p["status"] == "mastered"),
        "topics_needs_review": sum(1 for p in tp.values() if p["status"] == "needs_review"),
        "subjects_studied": sum(1 for s in subjects if s["concepts_assessed"]),
        "sessions_completed": len(completed),
        "questions_answered": answered,
        "correct_answers": correct,
        "accuracy": (correct / answered) if answered else None,
        "subjects": subjects,
        "strengths": strengths,
        "areas_to_improve": improve,
        "recommended": recommended,
        "active_session": active_session(db, user_id),
        "recent_sessions": [_session_summary(i, st, c) for i, st, c in reversed(completed)][:8],
        "learner_model": learner_model_state(db, user_id),
    }
