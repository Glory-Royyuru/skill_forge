"""Practice modes: personalised flashcards and Rapid Round.

(Prefix /study: /practice is used by the original e-commerce practice API.)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from skillforge.api.learner import TzOffset, context
from skillforge.auth.deps import Student
from skillforge.db.models import RapidRound
from skillforge.learner import flashcards, rapid, recommend
from skillforge.learner import state as learner_state

router = APIRouter(prefix="/study")


class CardBody(BaseModel):
    card_id: str = Field(max_length=160)


class ReviewBody(CardBody):
    rating: str = Field(max_length=16)


class RapidAnswer(BaseModel):
    question_id: str = Field(max_length=48)
    choice: int
    response_ms: int | None = Field(default=None, ge=0)


@router.get("/flashcards")
def deck(request: Request, user: Student, tz_offset: int = TzOffset) -> dict:
    state, ctx = context(request, user.id, tz_offset)
    class_subjects = {c["subject_id"] for c in recommend.upcoming_classes(ctx.timetable, ctx.local_now)}
    with request.app.state.db.session() as s:
        cards = flashcards.build_deck(s, state, class_subjects)
    return {
        "cards": cards,
        "note": "Cards are chosen from your own answers. Rating a card is a self-check: it helps order "
        "your reviews but does not change your mastery.",
    }


@router.post("/flashcards/reveal")
def reveal(body: CardBody, request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        try:
            return {"card_id": body.card_id, "back": flashcards.reveal(s, user.id, body.card_id)}
        except flashcards.CardError as e:
            raise HTTPException(status_code=404, detail="Card not found.") from e


@router.post("/flashcards/review")
def review(body: ReviewBody, request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        try:
            flashcards.review(s, user.id, body.card_id, body.rating)
        except flashcards.CardError as e:
            raise HTTPException(
                status_code=400 if body.rating not in flashcards.RATINGS else 404, detail=str(e)
            ) from e
        s.commit()
    return {"recorded": True}


def _owned_round(s, user_id: int, round_id: int) -> RapidRound:
    r = s.scalar(select(RapidRound).where(RapidRound.id == round_id, RapidRound.user_id == user_id))
    if r is None:
        raise HTTPException(status_code=404, detail="Round not found.")
    return r


@router.post("/rapid/start")
def start_round(request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        state = learner_state.build(s, user.id)
        r = rapid.start(s, state)
        s.commit()
        return rapid.view(r)


@router.get("/rapid/{round_id}")
def get_round(round_id: int, request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        r = _owned_round(s, user.id, round_id)
        out = rapid.view(r)
        if r.status == "finished":
            out["results"] = rapid.finish(r)
        return out


@router.post("/rapid/{round_id}/answer")
def answer_round(round_id: int, body: RapidAnswer, request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        r = _owned_round(s, user.id, round_id)
        try:
            result = rapid.answer(s, user.id, r, body.question_id, body.choice, body.response_ms)
        except rapid.RapidError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        s.commit()
        return {**result, "remaining_seconds": round(rapid.remaining_seconds(r), 1)}


@router.post("/rapid/{round_id}/finish")
def finish_round(round_id: int, request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        r = _owned_round(s, user.id, round_id)
        results = rapid.finish(r)
        s.commit()
        return results
