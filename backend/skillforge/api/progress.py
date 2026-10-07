"""GET /api/progress — learner analytics, derived entirely from persisted
`Attempt` rows for practice-mode `TrainingSession`s (no separate learner
DB; reuses the existing schema, per product scope).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import select

from skillforge.db.models import Attempt, TrainingSession

router = APIRouter()

PRACTICE_MODES = {"guided", "practice", "challenge"}
SKILL_NAMES = ["Policy Understanding", "Tool Selection", "Evidence Gathering", "Decision Accuracy"]


def _empty_progress() -> dict:
    return {
        "cases_completed": 0,
        "accuracy": None,
        "average_score": None,
        "average_steps": None,
        "critical_errors": 0,
        "current_streak": 0,
        "best_streak": 0,
        "level": "Beginner",
        "xp": 0,
        "skills": {name: None for name in SKILL_NAMES},
        "areas_to_improve": [],
        "recent": [],
    }


def _level_for(cases: int, accuracy: float) -> str:
    if cases < 5:
        return "Beginner"
    if cases < 20 or accuracy < 0.75:
        return "Intermediate"
    return "Advanced"


@router.get("/progress")
def get_progress(request: Request) -> dict:
    db = request.app.state.db
    with db.session() as session:
        pairs = list(
            session.execute(
                select(Attempt, TrainingSession)
                .join(TrainingSession, Attempt.session_id == TrainingSession.id)
                .where(TrainingSession.condition.in_(PRACTICE_MODES))
                .order_by(Attempt.created_at)
            ).all()
        )

    if not pairs:
        return _empty_progress()

    n = len(pairs)
    successes = [a.result_json["success"] for a, _ in pairs]
    scores = [a.result_json["score"] for a, _ in pairs]
    criticals = sum(1 for a, _ in pairs if a.result_json["critical"])
    steps = [len((a.trajectory_json or {}).get("tool_log", [])) + 1 for a, _ in pairs]

    current_streak = 0
    for ok in reversed(successes):
        if not ok:
            break
        current_streak += 1
    best_streak = 0
    running = 0
    for ok in successes:
        running = running + 1 if ok else 0
        best_streak = max(best_streak, running)

    accuracy = sum(successes) / n
    average_score = sum(scores) / n

    view_order_ok, view_customer_ok, view_policy_ok = 0, 0, 0
    tool_calls_total, tool_calls_ok = 0, 0
    advanced_attempts, advanced_successes = 0, 0
    for a, _ in pairs:
        traj = a.trajectory_json or {}
        called = {e["tool"] for e in traj.get("tool_log", []) if e.get("ok")}
        if "view_order" in called:
            view_order_ok += 1
        if "view_customer" in called:
            view_customer_ok += 1
        if "view_policy" in called:
            view_policy_ok += 1
        for e in traj.get("tool_log", []):
            tool_calls_total += 1
            if e.get("ok"):
                tool_calls_ok += 1
        if traj.get("difficulty") in ("intermediate", "advanced"):
            advanced_attempts += 1
            if a.result_json["success"]:
                advanced_successes += 1

    skills = {
        "Decision Accuracy": accuracy,
        "Evidence Gathering": ((view_order_ok + view_customer_ok) / (2 * n)),
        "Tool Selection": (tool_calls_ok / tool_calls_total) if tool_calls_total else 1.0,
        "Policy Understanding": (advanced_successes / advanced_attempts) if advanced_attempts else accuracy,
    }
    areas_to_improve = [name for name, v in sorted(skills.items(), key=lambda kv: kv[1]) if v < 0.75][:2]

    recent = [
        {
            "case_id": a.id,
            "task_id": a.task_id,
            "result": "Resolved" if a.result_json["success"] else "Needs review",
            "score": round(a.result_json["score"] * 100),
            "difficulty": (a.trajectory_json or {}).get("difficulty", "intermediate"),
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a, _ in pairs[-10:][::-1]
    ]

    return {
        "cases_completed": n,
        "accuracy": accuracy,
        "average_score": average_score,
        "average_steps": sum(steps) / n,
        "critical_errors": criticals,
        "current_streak": current_streak,
        "best_streak": best_streak,
        "level": _level_for(n, accuracy),
        "xp": n * 10 + sum(scores) * 10,
        "skills": skills,
        "areas_to_improve": areas_to_improve,
        "recent": recent,
    }
