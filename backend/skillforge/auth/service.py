"""Account workflows: registration, email verification, login sessions,
password reset. API routes call these; they own no HTTP concerns beyond
raising `AuthError` with a status code.

Timestamps are compared as naive UTC because SQLite drops timezone info.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from skillforge.auth import security
from skillforge.auth.email import EmailSender, reset_email, verification_email
from skillforge.core.settings import Settings
from skillforge.db.models import AuthSession, EmailVerificationToken, PasswordResetToken, User

_STUDENT_ID_RE = re.compile(r"^[A-Za-z0-9]{4,32}$")


class AuthError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _naive(dt: datetime) -> datetime:
    return dt.astimezone(UTC).replace(tzinfo=None) if dt.tzinfo else dt


def _link(settings: Settings, route: str, token: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/#/{route}?token={token}"


# --- Registration and verification ---------------------------------------------


def register(
    db: Session,
    settings: Settings,
    sender: EmailSender,
    *,
    name: str,
    email: str,
    password: str,
    confirm_password: str,
    student_id: str | None = None,
) -> User:
    name = " ".join(name.split())
    email = security.normalize_email(email)
    student_id = (student_id or "").strip().upper() or None

    if not 1 <= len(name) <= 120:
        raise AuthError(400, "invalid_name", "Enter your name (up to 120 characters).")
    if err := security.email_error(email):
        raise AuthError(400, "invalid_email", err)
    if student_id is not None and not _STUDENT_ID_RE.match(student_id):
        raise AuthError(400, "invalid_student_id", "Registration ID must be 4–32 letters or digits.")
    if password != confirm_password:
        raise AuthError(400, "password_mismatch", "Passwords do not match.")
    if err := security.password_error(password, email):
        raise AuthError(400, "weak_password", err)
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise AuthError(409, "email_taken", "An account with this email already exists.")
    if student_id and db.scalar(select(User.id).where(User.student_id == student_id)) is not None:
        raise AuthError(409, "student_id_taken", "An account with this registration ID already exists.")

    user = User(name=name, email=email, student_id=student_id,
                password_hash=security.hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    send_verification(db, settings, sender, user)
    return user


def send_verification(db: Session, settings: Settings, sender: EmailSender, user: User) -> None:
    now = utcnow()
    # Only the newest link works: retire any outstanding ones.
    db.execute(
        update(EmailVerificationToken)
        .where(EmailVerificationToken.user_id == user.id, EmailVerificationToken.used_at.is_(None))
        .values(used_at=now)
    )
    token = security.new_token()
    db.add(EmailVerificationToken(
        user_id=user.id, token_hash=security.hash_token(token),
        expires_at=now + timedelta(hours=settings.verification_token_ttl_hours),
    ))
    db.commit()
    sender.send(verification_email(user.email, user.name, _link(settings, "verify-email", token),
                                   settings.verification_token_ttl_hours))


def resend_verification(db: Session, settings: Settings, sender: EmailSender, email: str) -> None:
    """Silently does nothing for unknown or already-verified emails."""
    user = db.scalar(select(User).where(User.email == security.normalize_email(email)))
    if user is not None and not user.is_verified:
        send_verification(db, settings, sender, user)


def _consume(db: Session, model, token: str):
    """Look up a single-use token row; mark it used. Raises on invalid,
    already-used or expired tokens."""
    row = db.scalar(select(model).where(model.token_hash == security.hash_token(token)))
    if row is None or row.used_at is not None:
        raise AuthError(400, "invalid_token", "This link is invalid or has already been used.")
    now = utcnow()
    if _naive(row.expires_at) <= now:
        raise AuthError(400, "expired_token", "This link has expired. Request a new one.")
    row.used_at = now
    return row


def verify_email(db: Session, token: str) -> User:
    row = _consume(db, EmailVerificationToken, token)
    user = db.get(User, row.user_id)
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()
    db.commit()
    return user


# --- Login sessions ----------------------------------------------------------


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == security.normalize_email(email)))
    if user is None:
        security.verify_password(password, security.DUMMY_PASSWORD_HASH)  # equalize timing
        raise AuthError(401, "invalid_credentials", "Incorrect email or password.")
    if not security.verify_password(password, user.password_hash):
        raise AuthError(401, "invalid_credentials", "Incorrect email or password.")
    if not user.is_verified:
        raise AuthError(403, "email_not_verified",
                        "Verify your email address before signing in. We can send a new link.")
    return user


def create_session(db: Session, settings: Settings, user: User) -> str:
    token = security.new_token()
    db.add(AuthSession(
        user_id=user.id, token_hash=security.hash_token(token),
        expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
    ))
    db.commit()
    return token


def user_for_session(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == security.hash_token(token)))
    if row is None or row.revoked_at is not None or _naive(row.expires_at) <= utcnow():
        return None
    user = db.get(User, row.user_id)
    return user if user is not None and user.is_verified else None


def revoke_session(db: Session, token: str | None) -> None:
    if not token:
        return
    db.execute(
        update(AuthSession)
        .where(AuthSession.token_hash == security.hash_token(token), AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    db.commit()


# --- Password reset ------------------------------------------------------------


def request_password_reset(db: Session, settings: Settings, sender: EmailSender, email: str) -> None:
    """Sends a reset link if the account exists. The caller must respond
    identically either way, so the response never reveals whether an email is
    registered."""
    user = db.scalar(select(User).where(User.email == security.normalize_email(email)))
    if user is None:
        return
    now = utcnow()
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    token = security.new_token()
    db.add(PasswordResetToken(
        user_id=user.id, token_hash=security.hash_token(token),
        expires_at=now + timedelta(minutes=settings.reset_token_ttl_minutes),
    ))
    db.commit()
    sender.send(reset_email(user.email, user.name, _link(settings, "reset-password", token),
                            settings.reset_token_ttl_minutes))


def reset_password(db: Session, token: str, password: str, confirm_password: str) -> User:
    if password != confirm_password:
        raise AuthError(400, "password_mismatch", "Passwords do not match.")
    token_hash = security.hash_token(token)
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    user = db.get(User, row.user_id) if row is not None else None
    if err := security.password_error(password, user.email if user else ""):
        raise AuthError(400, "weak_password", err)
    row = _consume(db, PasswordResetToken, token)
    user = db.get(User, row.user_id)
    user.password_hash = security.hash_password(password)
    # Completing a reset proves control of the mailbox.
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()
    # Sign out everywhere: any existing session may belong to whoever knew the old password.
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    db.commit()
    return user
