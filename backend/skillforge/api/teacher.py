"""Teacher Agent API: curriculum, teaching sessions, reports, progress.

The backend is the source of truth for questions, answer keys, scoring,
mastery, and difficulty adaptation; the frontend only ever sees the open
question without its answer (see `curriculum.public_question`).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from skillforge.teacher import engine, store

router = APIRouter(prefix="/teacher")


class StartRequest(BaseModel):
    topic_id: str


class AnswerRequest(BaseModel):
    question_id: str
    choice: int


def _load(request: Request, session_id: int) -> dict:
    state = store.load_session(request.app.state.db, session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="session not found")
    return state


def _view(session_id: int, state: dict) -> dict:
    return {"id": session_id, **engine.session_view(state)}


@router.get("/topics")
def list_topics(request: Request) -> dict:
    return {"subjects": store.curriculum_with_progress(request.app.state.db)}


@router.post("/session/start")
def start_session(body: StartRequest, request: Request) -> dict:
    db = request.app.state.db
    try:
        state = engine.start_session(
            body.topic_id,
            prior_mastery=store.prior_mastery(db, body.topic_id),
            prior_knowledge=store.prior_knowledge(db, body.topic_id),
        )
    except engine.TeacherError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    session_id = store.create_session(db, state)
    return _view(session_id, state)


@router.get("/session/{session_id}")
def get_session(session_id: int, request: Request) -> dict:
    return _view(session_id, _load(request, session_id))


@router.post("/session/{session_id}/answer")
def answer(session_id: int, body: AnswerRequest, request: Request) -> dict:
    state = _load(request, session_id)
    try:
        feedback = engine.submit_answer(state, body.question_id, body.choice)
    except engine.TeacherError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    store.save_session(request.app.state.db, session_id, state)
    return {"feedback": feedback, "session": _view(session_id, state)}


@router.get("/session/{session_id}/report")
def report(session_id: int, request: Request) -> dict:
    state = _load(request, session_id)
    if state["status"] != "completed":
        raise HTTPException(status_code=409, detail="session is not complete yet")
    return {"id": session_id, **engine.build_report(state)}


@router.get("/progress")
def progress(request: Request) -> dict:
    return store.progress_overview(request.app.state.db)
