"""Profile and preferences: student/PTM mode and theme.

PTM mode is a presentation of the student's OWN record (no other account can
read it). Themes are a presentation-layer setting: "auto" picks a seasonal
decoration by date on the client; "none" turns decorations off.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from skillforge.auth.deps import Student, public_user
from skillforge.learner import diagnostic

router = APIRouter(prefix="/profile")

MODES = ("student", "ptm")
THEMES = ("auto", "none", "christmas", "diwali", "halloween", "newyear")


class PreferencesBody(BaseModel):
    mode: str | None = None
    theme: str | None = None


def _prefs(pref) -> dict:
    return {"mode": pref.mode, "theme": pref.theme, "diagnostic_skipped": pref.diagnostic_skipped}


@router.get("")
def get_profile(request: Request, user: Student) -> dict:
    with request.app.state.db.session() as s:
        pref = diagnostic.preference(s, user.id)
        s.commit()
        return {"user": public_user(user), "preferences": _prefs(pref), "modes": MODES, "themes": THEMES}


@router.put("/preferences")
def update_preferences(body: PreferencesBody, request: Request, user: Student) -> dict:
    from fastapi import HTTPException

    if body.mode is not None and body.mode not in MODES:
        raise HTTPException(status_code=400, detail="Unknown mode.")
    if body.theme is not None and body.theme not in THEMES:
        raise HTTPException(status_code=400, detail="Unknown theme.")
    with request.app.state.db.session() as s:
        pref = diagnostic.preference(s, user.id)
        if body.mode is not None:
            pref.mode = body.mode
        if body.theme is not None:
            pref.theme = body.theme
        s.commit()
        return {"preferences": _prefs(pref)}
