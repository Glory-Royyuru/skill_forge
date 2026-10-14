"""Learner intelligence API: overview (dashboard), learner state, recommendations,
trends, calendar activity, PTM analysis, and the onboarding diagnostic.

Every route is scoped to the signed-in student. `tz_offset` is the browser's
`Date.getTimezoneOffset()` (minutes behind UTC) so that "today", calendar
days and upcoming classes use the student's local time.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from skillforge.auth.deps import Student
from skillforge.db.models import Subject, TimetableEntry
from skillforge.learner import diagnostic, insights, recommend, review
from skillforge.learner import state as learner_state
from skillforge.learner.evidence import utcnow
from skillforge.teacher import store

router = APIRouter(prefix="/learner")

TzOffset = Query(default=0, ge=-14 * 60, le=14 * 60)


def local_now(tz_offset: int) -> datetime:
    return utcnow() - timedelta(minutes=tz_offset)


def timetable_for(s, user_id: int) -> list[dict]:
    names = {x.id: x.name for x in s.scalars(select(Subject))}
    rows = s.scalars(select(TimetableEntry).where(TimetableEntry.user_id == user_id)).all()
    return [
        {
            "id": e.id,
            "day_of_week": e.day_of_week,
            "start_time": e.start_time.strftime("%H:%M"),
            "end_time": e.end_time.strftime("%H:%M"),
            "subject_id": e.subject_id,
            "subject_name": names.get(e.subject_id, e.subject_id),
            "room": e.room,
            "faculty": e.faculty,
        }
        for e in rows
    ]


def context(request: Request, user_id: int, tz_offset: int):
    """(learner state, recommendation context) for one student."""
    db = request.app.state.db
    active = store.active_session(db, user_id)
    with db.session() as s:
        state = learner_state.build(s, user_id)
        ctx = recommend.Context(
            local_now=local_now(tz_offset),
            active_session=active,
            diagnostic_status=diagnostic.status(s, user_id),
            timetable=timetable_for(s, user_id),
        )
    return state, ctx


def upcoming_with_preparation(state, ctx) -> list[dict]:
    out = []
    for cls in recommend.upcoming_classes(ctx.timetable, ctx.local_now):
        prep = recommend.prepare_for_class(state, cls)
        out.append(
            {
                **cls,
                "preparation": prep.to_dict() if prep else None,
                "note": None
                if prep
                else "No question bank for this subject yet, so there is no preparation recommendation.",
            }
        )
    return out


@router.get("/overview")
def overview(request: Request, user: Student, tz_offset: int = TzOffset) -> dict:
    state, ctx = context(request, user.id, tz_offset)
    recs = [r.to_dict() for r in recommend.recommend(state, ctx, limit=5)]
    assessed = state.assessed()
    weakest = min(assessed, key=lambda c: (c.status != "needs_review", c.p_known or 0), default=None)
    improved = [
        c
        for c in assessed
        if c.attempts >= insights.MIN_ATTEMPTS_FOR_TREND
        and c.first_p_before is not None
        and c.p_known is not None
        and c.p_known - c.first_p_before >= 0.05
    ]
    improved.sort(key=lambda c: -(c.p_known - c.first_p_before))
    today = ctx.local_now.date()
    with request.app.state.db.session() as s:
        level = insights.activity_level(s, user.id)
        today_activity = insights.activity(s, user.id, today, today, tz_offset)["days"]
    progress = store.progress_overview(request.app.state.db, user.id)
    return {
        "has_evidence": state.has_evidence(),
        "diagnostic_status": ctx.diagnostic_status,
        "overall": state.overall(),
        "recommendations": recs,
        "next_up": recs[0] if recs else None,
        "weakest_concept": weakest.to_dict() if weakest else None,
        "improved_concept": (
            {**improved[0].to_dict(), "from": improved[0].first_p_before} if improved else None
        ),
        "upcoming_classes": upcoming_with_preparation(state, ctx),
        "today": today_activity[0] if today_activity else None,
        "activity_level": level,
        "active_session": ctx.active_session,
        "recent_sessions": progress["recent_sessions"][:4],
        "subjects": progress["subjects"],
        "sessions_completed": progress["sessions_completed"],
    }


@router.get("/state")
def learner_state_view(request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        state = learner_state.build(s, user.id)
    subjects = []
    for subj in store.curriculum.subjects():
        topics = []
        for tid in store.curriculum.assessable_in_subject(subj["id"]):
            _, topic = store.curriculum.get_topic(tid)
            topics.append(
                {
                    "id": tid,
                    "title": topic["title"],
                    "unit_number": topic["unit_number"],
                    "unit_title": topic["unit_title"],
                    **state.topic_summary(tid),
                    "concepts": [c.to_dict() for c in state.by_topic(tid)],
                }
            )
        subjects.append(
            {
                "id": subj["id"],
                "name": subj["name"],
                "short_name": subj["short_name"],
                "code": subj["code"],
                **state.subject_summary(subj["id"]),
                "topics": topics,
            }
        )
    return {
        "overall": state.overall(),
        "subjects": subjects,
        "method": "Estimates are the mean BKT knowledge estimate over concepts with evidence; coverage "
        "is the share of concepts with at least one graded answer.",
    }


@router.get("/recommendations")
def recommendations(request: Request, user: Student, tz_offset: int = TzOffset) -> dict:
    state, ctx = context(request, user.id, tz_offset)
    return {"recommendations": [r.to_dict() for r in recommend.recommend(state, ctx, limit=10)]}


@router.get("/trends")
def trends(
    request: Request, user: Student, tz_offset: int = TzOffset, weeks: int = Query(default=8, ge=2, le=26)
) -> dict:
    with request.app.state.db.session() as s:
        return insights.trends(s, user.id, local_now(tz_offset).date(), weeks, tz_offset)


@router.get("/activity")
def activity(request: Request, user: Student, start: date, end: date, tz_offset: int = TzOffset) -> dict:
    if end < start or (end - start).days > 400:
        raise HTTPException(status_code=400, detail="Choose a date range of up to 400 days.")
    with request.app.state.db.session() as s:
        result = insights.activity(s, user.id, start, end, tz_offset)
        result["timetable"] = timetable_for(s, user.id)
    return result


@router.get("/ptm")
def ptm(request: Request, user: Student, tz_offset: int = TzOffset) -> dict:
    state, ctx = context(request, user.id, tz_offset)
    recs = [r.to_dict() for r in recommend.recommend(state, ctx, limit=5)]
    upcoming = recommend.upcoming_classes(ctx.timetable, ctx.local_now)
    with request.app.state.db.session() as s:
        report = insights.ptm_report(s, state, upcoming, recs, tz_offset)
        report["trends"] = insights.trends(s, user.id, ctx.local_now.date(), 8, tz_offset)["weeks"]
    report["student"] = {"name": user.name, "student_id": user.student_id}
    return report


@router.get("/review")
def performance_review(request: Request, user: Student, tz_offset: int = TzOffset) -> dict:
    """The full Student Performance Review (PTM mode) for the signed-in student."""
    state, ctx = context(request, user.id, tz_offset)
    recs = [r.to_dict() for r in recommend.recommend(state, ctx, limit=6)]
    upcoming = recommend.upcoming_classes(ctx.timetable, ctx.local_now)
    student = {"name": user.name, "student_id": user.student_id, "email": user.email}
    with request.app.state.db.session() as s:
        return review.performance_review(s, student, state, upcoming, recs, tz_offset)


# --- Onboarding diagnostic ------------------------------------------------------------------


class DiagnosticAnswer(BaseModel):
    question_id: str = Field(max_length=48)
    choice: int | None = None  # None = skipped
    response_ms: int | None = Field(default=None, ge=0)


def _owned_diagnostic(s, user_id: int):
    d = diagnostic.latest(s, user_id)
    if d is None:
        raise HTTPException(status_code=404, detail="No diagnostic yet.")
    return d


@router.get("/diagnostic")
def get_diagnostic(request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        d = diagnostic.latest(s, user.id)
        return {
            "status": diagnostic.status(s, user.id),
            "diagnostic": diagnostic.view(d) if d else None,
            "question_count": len(diagnostic.choose_questions()),
        }


@router.post("/diagnostic/start")
def start_diagnostic(request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        try:
            d = diagnostic.start(s, user.id)
        except diagnostic.DiagnosticError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        s.commit()
        return diagnostic.view(d)


@router.post("/diagnostic/answer")
def answer_diagnostic(body: DiagnosticAnswer, request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        d = _owned_diagnostic(s, user.id)
        try:
            diagnostic.answer(s, user.id, d, body.question_id, body.choice, body.response_ms)
        except diagnostic.DiagnosticError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        s.commit()
        return diagnostic.view(d)


@router.post("/diagnostic/skip")
def skip_diagnostic(request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        diagnostic.preference(s, user.id).diagnostic_skipped = True
        s.commit()
        return {"status": diagnostic.status(s, user.id)}
