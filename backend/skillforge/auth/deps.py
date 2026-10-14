"""FastAPI dependencies for authenticated routes.

`current_user` is the only way route code learns who is calling. Every
student-owned query must filter on `CurrentUser.id`; returning 404 (not 403)
for another student's resource avoids revealing that it exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from skillforge.auth import service


@dataclass(frozen=True)
class CurrentUser:
    id: int
    email: str
    name: str
    student_id: str | None


def public_user(user) -> dict:
    """The only user fields ever returned by the API."""
    return {"id": user.id, "name": user.name, "email": user.email, "student_id": user.student_id}


def current_user(request: Request) -> CurrentUser:
    settings = request.app.state.settings
    token = request.cookies.get(settings.session_cookie_name)
    with request.app.state.db.session() as db:
        user = service.user_for_session(db, token)
        if user is None:
            raise HTTPException(status_code=401, detail="Sign in to continue.")
        return CurrentUser(id=user.id, email=user.email, name=user.name, student_id=user.student_id)


# Route parameter type for "the signed-in, verified student":
#     def handler(user: Student): ...
Student = Annotated[CurrentUser, Depends(current_user)]
