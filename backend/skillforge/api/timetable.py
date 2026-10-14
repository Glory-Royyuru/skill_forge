"""Student timetable: weekly class slots the student enters themselves.

All routes are scoped to the signed-in student; another student's entry id
returns 404. Entries record a `source` ("manual" here) so future importers
(PDF, image, Excel) can create rows through the same table and validation
(`validate_entry`).
"""

from __future__ import annotations

from datetime import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from skillforge.auth.deps import CurrentUser, Student
from skillforge.db.models import Subject, TimetableEntry

router = APIRouter(prefix="/timetable")

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class EntryBody(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    subject_id: str = Field(max_length=48)
    faculty: str | None = Field(default=None, max_length=120)
    room: str | None = Field(default=None, max_length=60)


def validate_entry(session, body: EntryBody) -> None:
    if body.end_time <= body.start_time:
        raise HTTPException(status_code=400, detail="End time must be after start time.")
    if session.get(Subject, body.subject_id) is None:
        raise HTTPException(status_code=400, detail="Unknown subject.")


def _clean(value: str | None) -> str | None:
    value = " ".join(value.split()) if value else ""
    return value or None


def _out(e: TimetableEntry, subject_names: dict[str, str]) -> dict:
    return {
        "id": e.id,
        "day_of_week": e.day_of_week,
        "day_name": DAY_NAMES[e.day_of_week],
        "start_time": e.start_time.strftime("%H:%M"),
        "end_time": e.end_time.strftime("%H:%M"),
        "subject_id": e.subject_id,
        "subject_name": subject_names.get(e.subject_id, e.subject_id),
        "faculty": e.faculty,
        "room": e.room,
        "source": e.source,
    }


def _subject_names(session) -> dict[str, str]:
    return {s.id: s.name for s in session.scalars(select(Subject))}


def _owned(session, user: CurrentUser, entry_id: int) -> TimetableEntry:
    entry = session.scalar(
        select(TimetableEntry).where(TimetableEntry.id == entry_id, TimetableEntry.user_id == user.id)
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Timetable entry not found.")
    return entry


@router.get("")
def list_entries(request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        rows = s.scalars(
            select(TimetableEntry)
            .where(TimetableEntry.user_id == user.id)
            .order_by(TimetableEntry.day_of_week, TimetableEntry.start_time)
        ).all()
        names = _subject_names(s)
        return {"entries": [_out(e, names) for e in rows]}


@router.post("", status_code=201)
def create_entry(body: EntryBody, request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        validate_entry(s, body)
        entry = TimetableEntry(
            user_id=user.id, day_of_week=body.day_of_week, start_time=body.start_time,
            end_time=body.end_time, subject_id=body.subject_id, faculty=_clean(body.faculty),
            room=_clean(body.room), source="manual",
        )
        s.add(entry)
        s.commit()
        s.refresh(entry)
        return _out(entry, _subject_names(s))


@router.put("/{entry_id}")
def update_entry(
    entry_id: int, body: EntryBody, request: Request, user: Student
) -> dict:
    with request.app.state.db.session() as s:
        entry = _owned(s, user, entry_id)
        validate_entry(s, body)
        entry.day_of_week = body.day_of_week
        entry.start_time = body.start_time
        entry.end_time = body.end_time
        entry.subject_id = body.subject_id
        entry.faculty = _clean(body.faculty)
        entry.room = _clean(body.room)
        s.commit()
        s.refresh(entry)
        return _out(entry, _subject_names(s))


@router.delete("/{entry_id}", status_code=204)
def delete_entry(entry_id: int, request: Request, user: Student) -> Response:
    with request.app.state.db.session() as s:
        s.delete(_owned(s, user, entry_id))
        s.commit()
    return Response(status_code=204)
