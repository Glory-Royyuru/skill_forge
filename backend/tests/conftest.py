from __future__ import annotations

import os
import tempfile

# `skillforge.api.app` builds a module-level app on import, which migrates and
# seeds whatever DATABASE_URL points at. Point it at a throwaway file so the
# test suite never touches the developer's ./skillforge.db.
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(tempfile.mkdtemp(prefix='sf-tests-'), 'import.db')}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from skillforge.db.database import Database  # noqa: E402

DEFAULT_PASSWORD = "forge2024x"


@pytest.fixture()
def db(tmp_path):
    """A fresh, isolated SQLite-backed Database for one test."""
    database = Database(f"sqlite:///{tmp_path / 'test.db'}")
    database.init()
    yield database
    database.engine.dispose()


@pytest.fixture()
def app(tmp_path):
    """The real API on an isolated database, with the console email sender
    (nothing is sent; messages land in `app.state.email_sender.outbox`)."""
    from skillforge.api.app import create_app
    from skillforge.auth.email import ConsoleEmailSender

    application = create_app(
        database_url=f"sqlite:///{tmp_path / 'api.db'}", email_sender=ConsoleEmailSender()
    )
    yield application
    application.state.db.engine.dispose()


def latest_link(app, email: str, kind: str) -> str:
    for message in reversed(app.state.email_sender.outbox):
        if message.to == email and message.kind == kind:
            return message.link
    raise AssertionError(f"no {kind} email for {email}")


def token_from(link: str) -> str:
    return link.split("token=", 1)[1]


@pytest.fixture()
def make_student(app):
    """Register, verify and sign in a student; returns their own TestClient
    (each client has its own cookie jar, so several students can coexist)."""

    def _make(email: str = "asha@example.com", name: str = "Asha Rao", password: str = DEFAULT_PASSWORD):
        client = TestClient(app)
        r = client.post(
            "/api/auth/register",
            json={
                "name": name,
                "email": email,
                "password": password,
                "confirm_password": password,
            },
        )
        assert r.status_code == 201, r.text
        token = token_from(latest_link(app, email, "verify_email"))
        assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 200
        assert client.post("/api/auth/login", json={"email": email, "password": password}).status_code == 200
        return client

    return _make
