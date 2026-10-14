"""Password hashing, opaque tokens, and input validation for accounts.

Passwords are hashed with scrypt (memory-hard KDF from the standard library,
so no extra dependency) using a per-password random salt. Session, email
verification and password-reset tokens are random 256-bit values; only their
SHA-256 digests are ever stored.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets

# scrypt cost parameters (N = 2**14, r = 8, p = 1 → ~16 MiB per hash), the
# interactive-login recommendation; stored in the hash so they can be raised
# later without invalidating existing passwords.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_KEY_BYTES = 32

PASSWORD_MIN = 8
PASSWORD_MAX = 128
_EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
                       r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    key = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_KEY_BYTES
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(key)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, key_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(key_b64)
        key = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(key, expected)


# A valid hash of a random password, used to spend the same time on logins
# for unknown emails as for known ones (no account enumeration via timing).
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


def new_token() -> str:
    """A URL-safe random token with 256 bits of entropy."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def email_error(email: str) -> str | None:
    if len(email) > 254 or not _EMAIL_RE.match(email):
        return "Enter a valid email address."
    return None


def password_error(password: str, email: str = "") -> str | None:
    """Return a human-readable reason the password is too weak, or None."""
    if len(password) < PASSWORD_MIN:
        return f"Password must be at least {PASSWORD_MIN} characters."
    if len(password) > PASSWORD_MAX:
        return f"Password must be at most {PASSWORD_MAX} characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one number."
    if email and password.lower() == email.lower():
        return "Password must not be the same as your email address."
    if len(set(password)) < 4:
        return "Password is too repetitive."
    return None
