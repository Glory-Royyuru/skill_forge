"""Teacher Agent API: curriculum, teaching sessions, reports, progress.

Every route requires a signed-in, verified student, and every session is
looked up by (session id, student id): another student's session id simply
returns 404. The backend is the source of truth for questions, answer keys,
grading, mastery, difficulty adaptation and the learner model; the frontend
only ever sees the open question without its answer
(see `curriculum.public_question`).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from skillforge.auth.deps import CurrentUser, Student
from skillforge.learner import selector
from skillforge.learner import state as learner_state
from skillforge.teacher import curriculum, engine, store

router = APIRouter(prefix="/teacher")


class StartRequest(BaseModel):
    topic_id: str = Field(max_length=64)
    # Optional, usually from a recommendation: concept key to focus first and
    # target starting difficulty (1-3).
    focus_concept: str | None = Field(default=None, max_length=64)
    target_difficulty: int | None = Field(default=None, ge=1, le=3)


class AnswerRequest(BaseModel):
    question_id: str = Field(max_length=48)
    choice: int
    # Optional, secondary signal only (never affects grading or mastery).
    response_ms: int | None = Field(default=None, ge=0)


def _load(request: Request, user: CurrentUser, session_id: int) -> dict:
    state = store.load_session(request.app.state.db, user.id, session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return state


def _view(session_id: int, state: dict) -> dict:
    return {"id": session_id, **engine.session_view(state)}


@router.get("/topics")
def list_topics(request: Request, user: Student) -> dict:
    return {"subjects": store.curriculum_with_progress(request.app.state.db, user.id)}


@router.post("/session/start")
def start_session(body: StartRequest, request: Request, user: Student) -> dict:
    db = request.app.state.db
    found = curriculum.get_topic(body.topic_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Topic not found.")
    if not curriculum.is_assessable(found[1]):
        raise HTTPException(status_code=409, detail="This topic does not have a question bank yet.")
    prior = store.prior_mastery(db, user.id, body.topic_id)
    with db.session() as s:
        plan = selector.plan_session(
            s, learner_state.build(s, user.id), body.topic_id, prior,
            focus_concept=body.focus_concept, target_difficulty=body.target_difficulty,
        )
    state = engine.start_session(
        body.topic_id,
        prior_mastery=prior,
        prior_knowledge=store.prior_knowledge(db, user.id, body.topic_id),
        start_level=plan["start_level"],
        focus_concept=plan["focus_concept"],
        exposure=plan["exposure"],
        diagnose_notes=plan["notes"],
    )
    session_id = store.create_session(db, user.id, state)
    return _view(session_id, state)


@router.get("/session/{session_id}")
def get_session(session_id: int, request: Request, user: Student) -> dict:
    return _view(session_id, _load(request, user, session_id))


@router.post("/session/{session_id}/answer")
def answer(
    session_id: int, body: AnswerRequest, request: Request, user: Student
) -> dict:
    state = _load(request, user, session_id)
    if state["status"] != "active":
        raise HTTPException(status_code=409, detail="This session is no longer active.")
    try:
        feedback = engine.submit_answer(state, body.question_id, body.choice)
    except engine.TeacherError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    store.record_answer(request.app.state.db, user.id, session_id, state, feedback, body.response_ms)
    return {"feedback": feedback, "session": _view(session_id, state)}


@router.get("/session/{session_id}/report")
def report(session_id: int, request: Request, user: Student) -> dict:
    state = _load(request, user, session_id)
    if state["status"] != "completed":
        raise HTTPException(status_code=409, detail="This session is not complete yet.")
    return {"id": session_id, **engine.build_report(state)}


@router.get("/progress")
def progress(request: Request, user: Student) -> dict:
    return store.progress_overview(request.app.state.db, user.id)
