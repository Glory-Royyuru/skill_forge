"""Outgoing email: a small sender interface with two implementations.

- `ConsoleEmailSender` (default, development): does NOT send anything. It
  writes the message, including its link, to the server log and keeps it in
  an in-memory outbox that tests and the development-only
  `GET /api/dev/outbox` endpoint can read. API responses say plainly that
  delivery is disabled, so nothing claims an email was sent when it wasn't.
- `SMTPEmailSender`: delivers through any SMTP server configured with the
  `SMTP_*` environment variables (credentials never live in source).
"""

from __future__ import annotations

import logging
import smtplib
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage as MimeMessage
from typing import Protocol

from skillforge.core.settings import Settings

logger = logging.getLogger("skillforge.email")


@dataclass
class OutgoingEmail:
    to: str
    subject: str
    text: str
    kind: str  # "verify_email" | "reset_password"
    link: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EmailSender(Protocol):
    # True when messages actually leave the server.
    delivers: bool

    def send(self, message: OutgoingEmail) -> None: ...


class ConsoleEmailSender:
    delivers = False

    def __init__(self, keep: int = 50):
        self.outbox: deque[OutgoingEmail] = deque(maxlen=keep)

    def send(self, message: OutgoingEmail) -> None:
        self.outbox.append(message)
        logger.warning(
            "EMAIL NOT SENT (EMAIL_BACKEND=console). To: %s | Subject: %s | Link: %s",
            message.to, message.subject, message.link,
        )


class SMTPEmailSender:
    delivers = True

    def __init__(self, settings: Settings):
        if not settings.smtp_host:
            raise ValueError("EMAIL_BACKEND=smtp requires SMTP_HOST")
        self.settings = settings

    def send(self, message: OutgoingEmail) -> None:
        s = self.settings
        mime = MimeMessage()
        mime["From"] = s.smtp_from
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.text)
        if s.smtp_ssl:
            server: smtplib.SMTP = smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, timeout=s.smtp_timeout_seconds)
        else:
            server = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=s.smtp_timeout_seconds)
        with server:
            if s.smtp_starttls and not s.smtp_ssl:
                server.starttls()
            if s.smtp_username:
                server.login(s.smtp_username, s.smtp_password or "")
            server.send_message(mime)


def build_email_sender(settings: Settings) -> EmailSender:
    backend = settings.email_backend.lower()
    if backend == "console":
        return ConsoleEmailSender()
    if backend == "smtp":
        return SMTPEmailSender(settings)
    raise ValueError(f"Unknown EMAIL_BACKEND {settings.email_backend!r} (use 'console' or 'smtp')")


def verification_email(to: str, name: str, link: str, ttl_hours: int) -> OutgoingEmail:
    text = (
        f"Hi {name},\n\n"
        "Welcome to SkillForge. Confirm your email address to activate your account:\n\n"
        f"{link}\n\n"
        f"This link expires in {ttl_hours} hours and can be used once. If you did not create an account, "
        "you can ignore this email.\n"
    )
    return OutgoingEmail(to=to, subject="Verify your SkillForge email", text=text, kind="verify_email",
                         link=link)


def reset_email(to: str, name: str, link: str, ttl_minutes: int) -> OutgoingEmail:
    text = (
        f"Hi {name},\n\n"
        "Someone (hopefully you) asked to reset your SkillForge password. Choose a new password here:\n\n"
        f"{link}\n\n"
        f"This link expires in {ttl_minutes} minutes and can be used once. If you did not ask for this, "
        "you can ignore this email; your password will not change.\n"
    )
    return OutgoingEmail(to=to, subject="Reset your SkillForge password", text=text, kind="reset_password",
                         link=link)
