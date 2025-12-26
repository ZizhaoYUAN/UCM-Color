"""Password hashing helpers."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
from typing import Tuple

_ITERATIONS = 390_000
_ALGORITHM = "sha256"
_SALT_BYTES = 16


def _split(hash_value: str) -> Tuple[bytes, bytes]:
    try:
        salt_b64, digest_b64 = hash_value.split(":", 1)
    except ValueError as exc:  # pragma: no cover - invalid hash input
        raise ValueError("Invalid stored hash format") from exc
    return base64.b64decode(salt_b64), base64.b64decode(digest_b64)


def hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash for *password*."""

    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(_ALGORITHM, password.encode("utf-8"), salt, _ITERATIONS)
    return f"{base64.b64encode(salt).decode()}:{base64.b64encode(digest).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify *password* against the stored hash."""

    salt, digest = _split(stored_hash)
    check = hashlib.pbkdf2_hmac(_ALGORITHM, password.encode("utf-8"), salt, _ITERATIONS)
    return hmac.compare_digest(digest, check)


def sign_session(value: str, secret_key: str) -> str:
    """Return an HMAC signed session token for *value*."""

    signature = hmac.new(secret_key.encode(), value.encode(), hashlib.sha256).digest()
    encoded = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{value}.{encoded}"


def verify_session(token: str, secret_key: str) -> str | None:
    """Validate and return the username from a signed session token."""

    try:
        value, signature = token.rsplit(".", 1)
    except ValueError:
        return None

    padding = "=" * (-len(signature) % 4)
    try:
        provided = base64.urlsafe_b64decode(signature + padding)
    except (binascii.Error, ValueError):  # pragma: no cover - invalid base64
        return None

    expected = hmac.new(secret_key.encode(), value.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, provided):
        return None
    return value
