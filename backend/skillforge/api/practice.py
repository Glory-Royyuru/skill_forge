"""Practice mode: a human learner works a case interactively through the
same Environment/Evaluator the Learner agent uses — no LLM involved.

In-progress cases live in `app.state.practice_sessions` (in-memory; a
single local demo process, no multi-user concerns per product scope).
Completed cases are persisted as ordinary `Attempt` rows (condition = the
practice mode) so Progress/Cases can read from the existing DB instead of
a second store.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from skillforge.db.helpers import (
    create_training_session,
    db_task_id,
    get_or_create_agent,
    get_or_create_skill,
    save_attempt,
)
from skillforge.db.models import Attempt, TrainingSession
from skillforge.db.models import Environment as DBEnvironment
from skillforge.envs.base import Action
from skillforge.envs.ecommerce.environment import EcommerceRefundEnvironment
from skillforge.envs.ecommerce.explain import difficulty_for_rules, explain_decision, missed_checks, rule_tags
from skillforge.envs.ecommerce.generator import DEFAULT_N, generate_tasks
from skillforge.envs.ecommerce.persistence import (
    count_tasks_by_split,
    get_or_create_environment,
    load_tasks,
    save_tasks,
)

router = APIRouter()

MODES = {"guided", "practice", "challenge"}
MODE_DIFFICULTY = {"guided": "beginner", "practice": "intermediate", "challenge": "advanced"}
HINT_PENALTY = 0.05

TOOL_INFO = {
    "search_orders": ("Search Orders", "Find orders by keyword, order id, or customer name."),
    "view_order": ("Get Order", "Retrieve full order details, including item and delivery info."),
    "view_customer": ("Get Customer", "Retrieve the customer's profile, including VIP status."),
    "view_policy": ("View Policy", "Look up the relevant section of the refund policy."),
    "view_order_history": ("Check Account", "Review the customer's recent refund history."),
}
TERMINAL_INFO = {
    "process_refund": "Process Refund",
    "reject_refund": "Reject Request",
    "escalate": "Escalate",
}


@dataclass
class PracticeSession:
    env: EcommerceRefundEnvironment
    task: Any
    mode: str
    difficulty: str
    training_session_id: int
    tools_called: set = field(default_factory=set)
    tool_log: list = field(default_factory=list)


def _ensure_tasks(db) -> DBEnvironment:
    with db.session() as session:
        env_row = get_or_create_environment(session)
        counts = count_tasks_by_split(session, env_row.id)
        env_id = env_row.id
    if not counts:
        tasks = generate_tasks(seed=1, n=DEFAULT_N)
        with db.session() as session:
            save_tasks(session, env_id, seed=1, tasks=tasks)
    with db.session() as session:
        return get_or_create_environment(session)


def _pick_task(db, env_id: int, mode: str):
    target_difficulty = MODE_DIFFICULTY[mode]
    with db.session() as session:
        pool = load_tasks(session, env_id, split="validation")
        prior = select(TrainingSession).where(TrainingSession.condition == mode)
        n_prior = len(session.scalars(prior).all())

    candidates = [
        t for t in pool if difficulty_for_rules(t.ground_truth["rules_involved"]) == target_difficulty
    ]
    if not candidates:
        candidates = pool
    return candidates[n_prior % len(candidates)]


class StartRequest(BaseModel):
    mode: str = "practice"


@router.post("/practice/start")
def start_case(body: StartRequest, request: Request) -> dict:
    if body.mode not in MODES:
        raise HTTPException(status_code=400, detail=f"unknown mode: {body.mode}")
    db = request.app.state.db
    env_row = _ensure_tasks(db)

    with db.session() as session:
        skill = get_or_create_skill(session, env_row.id, name="ecommerce_practice")
        agent = get_or_create_agent(session, name="human-learner", provider="human", model="n/a")
        training_session = create_training_session(
            session, skill.id, agent.id, condition=body.mode, config={"mode": body.mode}
        )
        session_id = training_session.id
        case_number = len(session.scalars(select(Attempt)).all()) + 1

    task = _pick_task(db, env_row.id, body.mode)
    difficulty = difficulty_for_rules(task.ground_truth["rules_involved"])

    env = EcommerceRefundEnvironment()
    env.reset(task)

    case_id = uuid.uuid4().hex[:12]
    request.app.state.practice_sessions[case_id] = PracticeSession(
        env=env, task=task, mode=body.mode, difficulty=difficulty, training_session_id=session_id
    )

    tools = [
        {"name": name, "display_name": info[0], "description": info[1]} for name, info in TOOL_INFO.items()
    ]
    return {
        "case_id": case_id,
        "case_number": case_number,
        "mode": body.mode,
        "difficulty": difficulty,
        "request": task.request,
        "tools": tools,
        "terminal_actions": [{"name": k, "display_name": v} for k, v in TERMINAL_INFO.items()],
    }


class ToolRequest(BaseModel):
    case_id: str
    tool: str
    args: dict[str, Any] = {}


@router.post("/practice/tool")
def call_tool(body: ToolRequest, request: Request) -> dict:
    ps: PracticeSession | None = request.app.state.practice_sessions.get(body.case_id)
    if ps is None:
        raise HTTPException(status_code=404, detail="no such case (it may have already been resolved)")
    result = ps.env.execute_action(Action(tool=body.tool, args=body.args))
    if result.ok:
        ps.tools_called.add(body.tool)
    ps.tool_log.append(
        {
            "tool": body.tool,
            "args": body.args,
            "ok": result.ok,
            "output": result.output,
            "error": result.error,
        }
    )
    return {"ok": result.ok, "output": result.output, "error": result.error}


class DecisionRequest(BaseModel):
    case_id: str
    action: str
    args: dict[str, Any] = {}
    hints_used: int = 0


def _build_feedback(evaluation, tools_called: set, hints_used: int) -> dict:
    raw_score = evaluation.score
    penalized_score = max(0.0, raw_score - HINT_PENALTY * hints_used)
    did_well = []
    if "view_order" in tools_called:
        did_well.append("Verified order information")
    if "view_customer" in tools_called:
        did_well.append("Checked customer status")
    if "view_policy" in tools_called:
        did_well.append("Consulted policy")
    if evaluation.success:
        did_well.append("Selected the appropriate action")
    return {
        "success": evaluation.success,
        "critical": evaluation.critical,
        "error_type": evaluation.error_type,
        "score": round(penalized_score * 100),
        "raw_score": round(raw_score * 100),
        "hints_used": hints_used,
        "decision": evaluation.actual.get("action"),
        "did_well": did_well,
        "missed": missed_checks(evaluation.rules_involved, tools_called),
        "explanation": explain_decision(evaluation.rules_involved),
        "rule_tags": rule_tags(evaluation.rules_involved),
    }


@router.post("/practice/decision")
def submit_decision(body: DecisionRequest, request: Request) -> dict:
    sessions = request.app.state.practice_sessions
    ps: PracticeSession | None = sessions.get(body.case_id)
    if ps is None:
        raise HTTPException(status_code=404, detail="no such case (it may have already been resolved)")
    if body.action not in TERMINAL_INFO:
        raise HTTPException(status_code=400, detail=f"unknown action: {body.action}")

    result = ps.env.execute_action(Action(tool=body.action, args=body.args))
    if not result.ok:
        raise HTTPException(status_code=400, detail=f"invalid decision: {result.error}")

    evaluation = ps.env.evaluate()
    feedback = _build_feedback(evaluation, ps.tools_called, body.hints_used)

    trajectory = {
        "tool_log": ps.tool_log,
        "decision": {"action": body.action, "args": body.args},
        "hints_used": body.hints_used,
        "difficulty": ps.difficulty,
        "mode": ps.mode,
    }
    db = request.app.state.db
    with db.session() as session:
        attempt = save_attempt(
            session,
            ps.training_session_id,
            db_task_id(ps.task.id),
            trajectory=trajectory,
            result=asdict(evaluation),
            tokens=0,
            cost=0.0,
        )
        attempt_id = attempt.id

    del sessions[body.case_id]
    feedback["attempt_id"] = attempt_id
    feedback["trajectory"] = trajectory
    return feedback


def _feedback_from_result(result: dict, trajectory: dict) -> dict:
    tools_called = {e["tool"] for e in trajectory.get("tool_log", []) if e.get("ok")}
    hints_used = trajectory.get("hints_used", 0)

    class _Evaluation:
        pass

    ev = _Evaluation()
    ev.score = result["score"]
    ev.success = result["success"]
    ev.critical = result["critical"]
    ev.error_type = result["error_type"]
    ev.actual = result["actual"]
    ev.rules_involved = result["rules_involved"]
    return _build_feedback(ev, tools_called, hints_used)


@router.get("/practice/result/{attempt_id}")
def get_result(attempt_id: int, request: Request) -> dict:
    db = request.app.state.db
    with db.session() as session:
        attempt = session.get(Attempt, attempt_id)
        if attempt is None:
            raise HTTPException(status_code=404, detail="no such attempt")
        result, trajectory = attempt.result_json, attempt.trajectory_json or {}

    feedback = _feedback_from_result(result, trajectory)
    feedback["attempt_id"] = attempt_id
    feedback["trajectory"] = trajectory
    return feedback


@router.get("/cases")
def list_cases(request: Request, limit: int = 50) -> list[dict]:
    """A case library listing: difficulty and rule *tags* (translated, not
    raw R-codes) are shown even before an attempt — a category hint, not
    the answer. Status/score come from the learner's own attempt history,
    matched by task id.
    """
    db = request.app.state.db
    env_row = _ensure_tasks(db)
    with db.session() as session:
        tasks = load_tasks(session, env_row.id, split="validation", limit=limit)
        attempts_by_task: dict[int, dict] = {}
        for a in session.scalars(select(Attempt).order_by(Attempt.created_at)).all():
            attempts_by_task[a.task_id] = {
                "status": "Resolved" if a.result_json["success"] else "Needs review",
                "score": round(a.result_json["score"] * 100),
                "last_attempt": a.created_at.isoformat() if a.created_at else None,
            }

    cases = []
    for t in tasks:
        tid = db_task_id(t.id)
        rules = t.ground_truth["rules_involved"]
        attempt_info = attempts_by_task.get(tid)
        cases.append(
            {
                "case_id": tid,
                "difficulty": difficulty_for_rules(rules).capitalize(),
                "tags": rule_tags(rules),
                "status": attempt_info["status"] if attempt_info else "Not attempted",
                "score": attempt_info["score"] if attempt_info else None,
                "last_attempt": attempt_info["last_attempt"] if attempt_info else None,
            }
        )
    return cases
