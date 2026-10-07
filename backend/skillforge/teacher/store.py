"""Persistence and progress analytics for Teacher Agent sessions.

Reuses the existing schema instead of adding tables: each teaching session
is a `TrainingSession` row with ``condition="teacher"`` whose
``config_json`` holds the engine's session state. The skill / agent /
environment rows it hangs off are created on demand via the shared
`db.helpers` get-or-create functions.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from skillforge.db.database import Database
from skillforge.db.helpers import create_training_session, get_or_create_agent, get_or_create_skill
from skillforge.db.models import Environment, TrainingSession
from skillforge.teacher import engine
from skillforge.teacher.curriculum import SUBJECTS, get_topic, public_curriculum, topic_ids

CONDITION = "teacher"
ENVIRONMENT_NAME = "teacher_curriculum"
SKILL_NAME = "adaptive_teacher"
AGENT_NAME = "teacher-agent"


def _owner_ids(session) -> tuple[int, int]:
    env = session.scalar(select(Environment).where(Environment.name == ENVIRONMENT_NAME))
    if env is None:
        env = Environment(name=ENVIRONMENT_NAME, version="1")
        session.add(env)
        session.commit()
        session.refresh(env)
    skill = get_or_create_skill(session, env.id, name=SKILL_NAME)
    agent = get_or_create_agent(session, name=AGENT_NAME, provider="deterministic", model="rule-based")
    return skill.id, agent.id


def _iso(dt: datetime | None) -> str | None:
    # SQLite hands back naive datetimes; they are UTC.
    if dt is None:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).isoformat()


# --- CRUD --------------------------------------------------------------------


def create_session(db: Database, state: dict, created_at: datetime | None = None) -> int:
    with db.session() as session:
        # Only one active session at a time: starting a new one shelves the old.
        for row in session.scalars(
            select(TrainingSession).where(
                TrainingSession.condition == CONDITION, TrainingSession.status == "active"
            )
        ):
            row.status = "abandoned"
        session.commit()
        skill_id, agent_id = _owner_ids(session)
        row = create_training_session(session, skill_id, agent_id, condition=CONDITION, config=state)
        row.status = state["status"]
        if created_at is not None:
            row.created_at = created_at
        session.commit()
        return row.id


def load_session(db: Database, session_id: int) -> dict | None:
    with db.session() as session:
        row = session.get(TrainingSession, session_id)
        if row is None or row.condition != CONDITION:
            return None
        return copy.deepcopy(row.config_json)


def save_session(db: Database, session_id: int, state: dict) -> None:
    with db.session() as session:
        row = session.get(TrainingSession, session_id)
        row.config_json = copy.deepcopy(state)  # reassign so SQLAlchemy sees the JSON change
        row.status = state["status"]
        session.commit()


def _rows(db: Database) -> list[tuple[int, str, dict, datetime | None]]:
    with db.session() as session:
        rows = session.scalars(
            select(TrainingSession)
            .where(TrainingSession.condition == CONDITION)
            .order_by(TrainingSession.created_at, TrainingSession.id)
        ).all()
        return [(r.id, r.status, copy.deepcopy(r.config_json), r.created_at) for r in rows]


def prior_mastery(db: Database, topic_id: str) -> float | None:
    """Mastery from the most recent completed session on this topic."""
    latest = None
    for _, status, state, _ in _rows(db):
        if status == "completed" and state["topic_id"] == topic_id:
            latest = state["mastery"]
    return latest


def prior_knowledge(db: Database, topic_id: str) -> dict[str, float] | None:
    """Learner-model concept estimates from the most recent completed
    session on this topic, so the model picks up where it left off."""
    latest = None
    for _, status, state, _ in _rows(db):
        if status == "completed" and state["topic_id"] == topic_id and state.get("learner_model"):
            latest = dict(state["learner_model"]["knowledge"])
    return latest


# --- Demo seed ---------------------------------------------------------------

# (topic, pattern of correct/incorrect answers, days ago). Chosen so the
# dashboard opens with a mix of strong, developing, and weak results.
DEMO_HISTORY = [
    ("lists", [True, True, True, True, True], 4),
    ("decision-trees", [True, True, False, True, True], 2),
    ("binary-search", [True, False, False, True, False], 1),
]


def _simulate(topic_id: str, pattern: list[bool]) -> dict:
    _, topic = get_topic(topic_id)
    state = engine.start_session(topic_id)
    for ok in pattern:
        if state["status"] != "active":
            break
        q = next(x for x in topic["questions"] if x["id"] == state["current_question_id"])
        choice = q["answer"] if ok else (q["answer"] + 1) % len(q["options"])
        engine.submit_answer(state, q["id"], choice)
    state["demo"] = True
    return state


def seed_demo_history(db: Database) -> bool:
    """Populate a small sample learning history on an empty database so the
    dashboard and progress pages have something to show on first launch.
    Returns True if anything was seeded.
    """
    if _rows(db):
        return False
    now = datetime.now(UTC).replace(tzinfo=None)
    for topic_id, pattern, days_ago in DEMO_HISTORY:
        create_session(db, _simulate(topic_id, pattern), created_at=now - timedelta(days=days_ago, hours=3))
    return True


# --- Progress ----------------------------------------------------------------


def _session_summary(session_id: int, state: dict, created_at: datetime | None) -> dict:
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
        "created_at": _iso(created_at),
    }


def topic_progress(db: Database) -> dict[str, dict]:
    """Per-topic latest/best mastery from completed sessions."""
    out: dict[str, dict] = {
        tid: {"mastery": None, "best": None, "sessions": 0, "status": "not_started"} for tid in topic_ids()
    }
    for _, status, state, _ in _rows(db):
        if status != "completed":
            continue
        p = out.get(state["topic_id"])
        if p is None:
            continue
        p["sessions"] += 1
        p["mastery"] = state["mastery"]
        p["best"] = max(p["best"] or 0.0, state["mastery"])
    for p in out.values():
        if p["mastery"] is None:
            continue
        p["status"] = "mastered" if p["mastery"] >= engine.PROFICIENT else "in_progress"
    return out


def curriculum_with_progress(db: Database) -> list[dict]:
    progress = topic_progress(db)
    subjects = public_curriculum()
    for s in subjects:
        for t in s["topics"]:
            t["progress"] = progress[t["id"]]
            t["session_length"] = min(engine.QUESTIONS_PER_SESSION, t["question_count"])
    return subjects


def active_session(db: Database) -> dict | None:
    for session_id, status, state, created_at in reversed(_rows(db)):
        if status == "active":
            view = engine.session_view(state)
            return {
                "id": session_id,
                "topic_id": view["topic_id"],
                "topic_title": view["topic_title"],
                "subject_name": view["subject_name"],
                "question_number": view["question_number"],
                "max_questions": view["max_questions"],
                "mastery": view["mastery"],
                "created_at": _iso(created_at),
            }
    return None


def progress_overview(db: Database) -> dict:
    rows = _rows(db)
    completed = [(i, s, c) for i, status, s, c in rows if status == "completed"]
    tp = topic_progress(db)

    started = [p["mastery"] for p in tp.values() if p["mastery"] is not None]
    overall = sum(started) / len(started) if started else None

    subjects = []
    for s in SUBJECTS:
        ms = [tp[t["id"]]["mastery"] or 0.0 for t in s["topics"]]
        subjects.append(
            {
                "id": s["id"],
                "name": s["name"],
                "mastery": sum(ms) / len(ms),
                "topics_started": sum(1 for t in s["topics"] if tp[t["id"]]["mastery"] is not None),
                "topics_total": len(s["topics"]),
                "topics": [
                    {"id": t["id"], "title": t["title"], **tp[t["id"]]} for t in s["topics"]
                ],
            }
        )

    answered = sum(len(s["answers"]) for _, s, _ in completed)
    correct = sum(sum(1 for a in s["answers"] if a["correct"]) for _, s, _ in completed)

    # Strengths / areas to improve: from the latest completed session per topic.
    latest_by_topic: dict[str, dict] = {}
    for _, s, _ in completed:
        latest_by_topic[s["topic_id"]] = s
    strengths, improve = [], []
    for tid in topic_ids():
        s = latest_by_topic.get(tid)
        if s is None:
            continue
        report = engine.build_report(s)
        for c in report["concepts"]:
            item = {"concept": c["name"], "topic_id": tid, "topic_title": report["topic_title"]}
            if c["status"] == "strong":
                strengths.append(item)
            elif c["status"] in ("weak", "developing"):
                improve.append({**item, "status": c["status"]})
    improve.sort(key=lambda x: 0 if x["status"] == "weak" else 1)

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
        first_subject, first_topic = SUBJECTS[0], SUBJECTS[0]["topics"][0]
        recommended = {
            "topic_id": first_topic["id"],
            "topic_title": first_topic["title"],
            "subject_name": first_subject["name"],
            "headline": f"Start with {first_topic['title']}",
            "reason": "A good first topic: short, concrete, and it sets up later lessons.",
            "from_session_id": None,
        }

    recent = [_session_summary(i, s, c) for i, s, c in reversed(completed)][:8]

    return {
        "overall_mastery": overall,
        "topics_started": len(started),
        "topics_total": len(tp),
        "topics_mastered": sum(1 for p in tp.values() if p["status"] == "mastered"),
        "sessions_completed": len(completed),
        "questions_answered": answered,
        "correct_answers": correct,
        "accuracy": correct / answered if answered else None,
        "subjects": subjects,
        "strengths": strengths,
        "areas_to_improve": improve,
        "recommended": recommended,
        "active_session": active_session(db),
        "recent_sessions": recent,
    }
