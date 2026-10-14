"""Account endpoints: register, verify email, login/logout, current user,
password reset, and (development only) the unsent-email outbox.

Sessions are opaque random tokens in an HttpOnly, SameSite=Lax cookie; the
database stores only their hashes, so logout really revokes them.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from skillforge.auth import service
from skillforge.auth.deps import public_user
from skillforge.auth.service import AuthError

router = APIRouter(prefix="/auth")
dev_router = APIRouter(prefix="/dev")

# Failed-login throttle (per normalized email, per process): after
# LOGIN_MAX_FAILURES failures within LOGIN_WINDOW_SECONDS, further attempts
# are refused until the window passes.
LOGIN_MAX_FAILURES = 8
LOGIN_WINDOW_SECONDS = 15 * 60

GENERIC_EMAIL_MESSAGE = "If an account exists for that email, we've sent it a link."


class RegisterBody(BaseModel):
    name: str = Field(max_length=200)
    email: str = Field(max_length=320)
    password: str = Field(max_length=256)
    confirm_password: str = Field(max_length=256)
    student_id: str | None = Field(default=None, max_length=64)


class LoginBody(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=256)


class EmailBody(BaseModel):
    email: str = Field(max_length=320)


class TokenBody(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class ResetBody(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(max_length=256)
    confirm_password: str = Field(max_length=256)


def _fail(e: AuthError) -> HTTPException:
    return HTTPException(status_code=e.status, detail={"code": e.code, "message": e.message})


def _delivery(request: Request) -> dict:
    sender = request.app.state.email_sender
    if sender.delivers:
        return {"email_delivery": "sent"}
    return {
        "email_delivery": "disabled",
        "delivery_note": "Email delivery is not configured on this server (development mode), so no email "
        "was sent. The link was written to the server log.",
        "dev_outbox": request.app.state.settings.dev_outbox_enabled,
    }


def _failures(request: Request) -> dict[str, deque]:
    state = request.app.state
    if not hasattr(state, "login_failures"):
        state.login_failures = defaultdict(deque)
    return state.login_failures


@router.post("/register", status_code=201)
def register(body: RegisterBody, request: Request) -> dict:
    with request.app.state.db.session() as db:
        try:
            service.register(
                db, request.app.state.settings, request.app.state.email_sender,
                name=body.name, email=body.email, password=body.password,
                confirm_password=body.confirm_password, student_id=body.student_id,
            )
        except AuthError as e:
            raise _fail(e) from e
    return {"message": "Account created. Check your email for a verification link.", **_delivery(request)}


@router.post("/verify-email")
def verify_email(body: TokenBody, request: Request) -> dict:
    with request.app.state.db.session() as db:
        try:
            service.verify_email(db, body.token)
        except AuthError as e:
            raise _fail(e) from e
    return {"message": "Email verified. You can sign in now."}


@router.post("/resend-verification")
def resend_verification(body: EmailBody, request: Request) -> dict:
    with request.app.state.db.session() as db:
        service.resend_verification(
            db, request.app.state.settings, request.app.state.email_sender, body.email
        )
    return {"message": GENERIC_EMAIL_MESSAGE, **_delivery(request)}


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response) -> dict:
    settings = request.app.state.settings
    key = body.email.strip().lower()
    failures = _failures(request)[key]
    now = time.monotonic()
    while failures and now - failures[0] > LOGIN_WINDOW_SECONDS:
        failures.popleft()
    if len(failures) >= LOGIN_MAX_FAILURES:
        raise HTTPException(status_code=429, detail={
            "code": "too_many_attempts",
            "message": "Too many failed sign-in attempts. Try again in a few minutes.",
        })
    with request.app.state.db.session() as db:
        try:
            user = service.authenticate(db, body.email, body.password)
        except AuthError as e:
            if e.code == "invalid_credentials":
                failures.append(now)
            raise _fail(e) from e
        failures.clear()
        token = service.create_session(db, settings, user)
        out = public_user(user)
    response.set_cookie(
        settings.session_cookie_name, token, max_age=settings.session_ttl_hours * 3600,
        httponly=True, secure=settings.session_cookie_secure, samesite="lax", path="/",
    )
    return {"user": out}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    settings = request.app.state.settings
    with request.app.state.db.session() as db:
        service.revoke_session(db, request.cookies.get(settings.session_cookie_name))
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"message": "Signed out."}


@router.get("/me")
def me(request: Request) -> dict:
    """The signed-in student, or `{"user": null}` when signed out (a normal
    state for this endpoint, so it is not an error)."""
    settings = request.app.state.settings
    with request.app.state.db.session() as db:
        user = service.user_for_session(db, request.cookies.get(settings.session_cookie_name))
        return {"user": public_user(user) if user else None}


@router.post("/forgot-password")
def forgot_password(body: EmailBody, request: Request) -> dict:
    with request.app.state.db.session() as db:
        service.request_password_reset(
            db, request.app.state.settings, request.app.state.email_sender, body.email
        )
    # Identical response whether or not the account exists.
    return {"message": GENERIC_EMAIL_MESSAGE, **_delivery(request)}


@router.post("/reset-password")
def reset_password(body: ResetBody, request: Request) -> dict:
    with request.app.state.db.session() as db:
        try:
            service.reset_password(db, body.token, body.password, body.confirm_password)
        except AuthError as e:
            raise _fail(e) from e
    return {"message": "Password updated. Sign in with your new password."}


@dev_router.get("/outbox")
def dev_outbox(request: Request, email: str) -> dict:
    """Unsent emails for one address, for local development without SMTP.

    Exists only when APP_ENV=development, EMAIL_BACKEND=console and
    DEV_EMAIL_OUTBOX is on, and only answers requests from this machine."""
    settings = request.app.state.settings
    client = request.client.host if request.client else ""
    if not settings.dev_outbox_enabled or client not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(status_code=404, detail="Not Found")
    target = email.strip().lower()
    items = [m for m in request.app.state.email_sender.outbox if m.to == target]
    return {
        "emails": [
            {"kind": m.kind, "subject": m.subject, "link": m.link, "created_at": m.created_at.isoformat()}
            for m in reversed(items)
        ]
    }
