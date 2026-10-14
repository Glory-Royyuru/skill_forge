from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from skillforge.auth import security
from skillforge.auth.service import utcnow
from skillforge.db.models import AuthSession, EmailVerificationToken, PasswordResetToken, User
from tests.conftest import DEFAULT_PASSWORD, latest_link, token_from

EMAIL = "asha@example.com"


def _register(client, **over):
    body = {
        "name": "Asha Rao",
        "email": EMAIL,
        "password": DEFAULT_PASSWORD,
        "confirm_password": DEFAULT_PASSWORD,
        **over,
    }
    return client.post("/api/auth/register", json=body)


def _code(r):
    return r.json()["detail"]["code"]


# --- Passwords and tokens ---------------------------------------------------------


def test_password_hash_is_salted_scrypt_and_verifies():
    h1, h2 = security.hash_password("forge2024x"), security.hash_password("forge2024x")
    assert h1 != h2 and h1.startswith("scrypt$") and "forge2024x" not in h1
    assert security.verify_password("forge2024x", h1)
    assert not security.verify_password("forge2024y", h1)
    assert not security.verify_password("x", "not-a-hash")


@pytest.mark.parametrize("pw", ["short1", "onlyletters", "12345678901", "aaaa1111"])
def test_weak_passwords_rejected(pw):
    assert security.password_error(pw) is not None


# --- Registration -----------------------------------------------------------------


def test_register_creates_unverified_account_and_sends_verification(app):
    client = TestClient(app)
    r = _register(client, email="  Asha@Example.COM ")
    assert r.status_code == 201
    body = r.json()
    assert body["email_delivery"] == "disabled" and "no email was sent" in body["delivery_note"]
    with app.state.db.session() as s:
        user = s.scalar(select(User))
        assert user.email == EMAIL  # normalized
        assert user.email_verified_at is None
        assert user.password_hash != DEFAULT_PASSWORD
        token_row = s.scalar(select(EmailVerificationToken))
    link = latest_link(app, EMAIL, "verify_email")
    assert link.startswith("http://localhost:5173/#/verify-email?token=")
    # Only the hash of the token is stored.
    assert token_row.token_hash == security.hash_token(token_from(link))
    assert token_from(link) not in token_row.token_hash


def test_register_rejects_duplicate_email_case_insensitively(app):
    client = TestClient(app)
    assert _register(client).status_code == 201
    r = _register(client, email="ASHA@example.com")
    assert r.status_code == 409 and _code(r) == "email_taken"


@pytest.mark.parametrize("email", ["not-an-email", "a@b", "a b@example.com", "@example.com"])
def test_register_rejects_invalid_email(app, email):
    r = _register(TestClient(app), email=email)
    assert r.status_code == 400 and _code(r) == "invalid_email"


def test_register_rejects_weak_or_mismatched_password(app):
    client = TestClient(app)
    r = _register(client, password="password", confirm_password="password")
    assert r.status_code == 400 and _code(r) == "weak_password"
    r = _register(client, confirm_password="different123")
    assert r.status_code == 400 and _code(r) == "password_mismatch"


def test_register_optional_student_id_validated_and_unique(app):
    client = TestClient(app)
    assert _register(client, student_id="22071a6601").status_code == 201
    r = _register(client, email="b@example.com", student_id="22071A6601")
    assert r.status_code == 409 and _code(r) == "student_id_taken"
    r = _register(client, email="c@example.com", student_id="bad id!")
    assert r.status_code == 400 and _code(r) == "invalid_student_id"


# --- Verification and login -----------------------------------------------------


def test_unverified_account_cannot_sign_in(app):
    client = TestClient(app)
    _register(client)
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": DEFAULT_PASSWORD})
    assert r.status_code == 403 and _code(r) == "email_not_verified"
    assert "sf_session" not in r.headers.get("set-cookie", "")


def test_verify_then_login_sets_httponly_session_cookie(app):
    client = TestClient(app)
    _register(client)
    token = token_from(latest_link(app, EMAIL, "verify_email"))
    assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 200
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": DEFAULT_PASSWORD})
    assert r.status_code == 200
    assert r.json()["user"] == {"id": 1, "name": "Asha Rao", "email": EMAIL, "student_id": None}
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    me = client.get("/api/auth/me").json()["user"]
    assert me["email"] == EMAIL and "password_hash" not in me


def test_verification_token_is_single_use(app):
    client = TestClient(app)
    _register(client)
    token = token_from(latest_link(app, EMAIL, "verify_email"))
    assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 200
    r = client.post("/api/auth/verify-email", json={"token": token})
    assert r.status_code == 400 and _code(r) == "invalid_token"


def test_expired_verification_token_rejected(app):
    client = TestClient(app)
    _register(client)
    token = token_from(latest_link(app, EMAIL, "verify_email"))
    with app.state.db.session() as s:
        s.execute(update(EmailVerificationToken).values(expires_at=utcnow() - timedelta(minutes=1)))
        s.commit()
    r = client.post("/api/auth/verify-email", json={"token": token})
    assert r.status_code == 400 and _code(r) == "expired_token"


def test_resend_verification_invalidates_previous_link(app):
    client = TestClient(app)
    _register(client)
    old = token_from(latest_link(app, EMAIL, "verify_email"))
    assert client.post("/api/auth/resend-verification", json={"email": EMAIL}).status_code == 200
    new = token_from(latest_link(app, EMAIL, "verify_email"))
    assert new != old
    assert client.post("/api/auth/verify-email", json={"token": old}).status_code == 400
    assert client.post("/api/auth/verify-email", json={"token": new}).status_code == 200


def test_resend_for_unknown_email_gives_same_response(app):
    client = TestClient(app)
    _register(client)
    known = client.post("/api/auth/resend-verification", json={"email": EMAIL}).json()
    unknown = client.post("/api/auth/resend-verification", json={"email": "nobody@example.com"}).json()
    assert known == unknown


def test_login_failures(make_student, app):
    make_student()
    client = TestClient(app)
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": "wrongpass1"})
    assert r.status_code == 401 and _code(r) == "invalid_credentials"
    r2 = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrongpass1"})
    assert r2.status_code == 401 and r2.json() == r.json()  # no account enumeration


def test_login_is_throttled_after_repeated_failures(make_student, app):
    make_student()
    client = TestClient(app)
    for _ in range(8):
        client.post("/api/auth/login", json={"email": EMAIL, "password": "wrongpass1"})
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": DEFAULT_PASSWORD})
    assert r.status_code == 429


def test_logout_revokes_session_server_side(make_student, app):
    client = make_student()
    cookie = client.cookies.get("sf_session")
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").json()["user"] is None
    # Replaying the old cookie no longer works: the session is revoked in the DB.
    replay = TestClient(app)
    replay.cookies.set("sf_session", cookie)
    assert replay.get("/api/auth/me").json()["user"] is None
    with app.state.db.session() as s:
        assert s.scalar(select(AuthSession)).revoked_at is not None


def test_expired_session_rejected(make_student, app):
    client = make_student()
    with app.state.db.session() as s:
        s.execute(update(AuthSession).values(expires_at=utcnow() - timedelta(seconds=1)))
        s.commit()
    assert client.get("/api/auth/me").json()["user"] is None


# --- Password reset ---------------------------------------------------------------


def test_forgot_password_does_not_reveal_whether_email_exists(make_student, app):
    make_student()
    client = TestClient(app)
    a = client.post("/api/auth/forgot-password", json={"email": EMAIL})
    b = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert a.status_code == b.status_code == 200
    assert a.json() == b.json()
    assert not [m for m in app.state.email_sender.outbox if m.to == "nobody@example.com"]


def test_password_reset_flow_changes_password_and_signs_out_everywhere(make_student, app):
    signed_in = make_student()
    client = TestClient(app)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    token = token_from(latest_link(app, EMAIL, "reset_password"))
    r = client.post(
        "/api/auth/reset-password",
        json={"token": token, "password": "newforge2025", "confirm_password": "newforge2025"},
    )
    assert r.status_code == 200
    assert signed_in.get("/api/auth/me").json()["user"] is None  # old session revoked
    assert (
        client.post("/api/auth/login", json={"email": EMAIL, "password": DEFAULT_PASSWORD}).status_code == 401
    )
    assert (
        client.post("/api/auth/login", json={"email": EMAIL, "password": "newforge2025"}).status_code == 200
    )
    # Single use.
    r = client.post(
        "/api/auth/reset-password",
        json={"token": token, "password": "another2025x", "confirm_password": "another2025x"},
    )
    assert r.status_code == 400 and _code(r) == "invalid_token"


def test_expired_reset_token_rejected(make_student, app):
    make_student()
    client = TestClient(app)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    token = token_from(latest_link(app, EMAIL, "reset_password"))
    with app.state.db.session() as s:
        s.execute(update(PasswordResetToken).values(expires_at=utcnow() - timedelta(minutes=1)))
        s.commit()
    r = client.post(
        "/api/auth/reset-password",
        json={"token": token, "password": "newforge2025", "confirm_password": "newforge2025"},
    )
    assert r.status_code == 400 and _code(r) == "expired_token"


def test_reset_rejects_weak_password(make_student, app):
    make_student()
    client = TestClient(app)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    token = token_from(latest_link(app, EMAIL, "reset_password"))
    r = client.post(
        "/api/auth/reset-password", json={"token": token, "password": "weak", "confirm_password": "weak"}
    )
    assert r.status_code == 400 and _code(r) == "weak_password"


# --- Development outbox and cross-site protection -------------------------------------


def test_dev_outbox_only_in_development_console_mode(app, monkeypatch):
    client = TestClient(app)
    _register(client)
    r = client.get("/api/dev/outbox", params={"email": EMAIL})
    assert r.status_code == 200 and r.json()["emails"][0]["kind"] == "verify_email"
    monkeypatch.setattr(app.state.settings, "app_env", "production")
    assert client.get("/api/dev/outbox", params={"email": EMAIL}).status_code == 404


def test_cross_site_write_refused(app):
    client = TestClient(app)
    r = client.post(
        "/api/auth/login", json={"email": EMAIL, "password": "x"}, headers={"Origin": "https://evil.example"}
    )
    assert r.status_code == 403
    ok = client.post(
        "/api/auth/login", json={"email": EMAIL, "password": "x"}, headers={"Origin": "http://localhost:5173"}
    )
    assert ok.status_code == 401
