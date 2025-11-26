"""Password hashing helpers."""

from __future__ import annotations

import base64
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
