"""Minimal API surface for the frontend: start a run, fetch its results,
fetch one attempt's trajectory, fetch the policy document.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from skillforge.cli.run_cmd import RunError, run_condition, summary_from_db
from skillforge.db.helpers import get_attempt
from skillforge.envs.ecommerce.tools import load_policy_document

router = APIRouter()


class RunRequest(BaseModel):
    condition: str
    split: str = "validation"
    n: int = 5
    seed: int = 1
    provider: str | None = None
    model: str | None = None
    max_cost: float | None = None
    dry_run: bool = True


@router.post("/run")
def start_run(body: RunRequest, request: Request) -> dict:
    db = request.app.state.db
    # Without a configured provider key, force dry_run so the frontend demo
    # always works — never silently attempt (and fail) a real network call.
    settings = request.app.state.settings
    has_key = bool(settings.anthropic_api_key or settings.openai_api_key)
    dry_run = body.dry_run or not has_key
    try:
        return run_condition(
            db,
            body.condition,
            split=body.split,
            n=body.n,
            seed=body.seed,
            provider=body.provider,
            model=body.model,
            max_cost=body.max_cost,
            dry_run=dry_run,
        )
    except RunError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs/{session_id}")
def get_run(session_id: int, request: Request) -> dict:
    db = request.app.state.db
    summary = summary_from_db(db, session_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="no such session")
    return summary


@router.get("/attempts/{attempt_id}")
def get_attempt_endpoint(attempt_id: int, request: Request) -> dict:
    db = request.app.state.db
    with db.session() as session:
        attempt = get_attempt(session, attempt_id)
        if attempt is None:
            raise HTTPException(status_code=404, detail="no such attempt")
        return {
            "id": attempt.id,
            "session_id": attempt.session_id,
            "task_id": attempt.task_id,
            "tokens": attempt.tokens,
            "cost": attempt.cost,
            "result": attempt.result_json,
            "trajectory": attempt.trajectory_json,
        }


@router.get("/policy")
def get_policy() -> dict:
    return {"version": "v1", "text": load_policy_document()}
