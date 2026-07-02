"""Password hashing (bcrypt) and JWT access/refresh token creation +
validation.

If JWT_SECRET_KEY isn't set in the environment, a random one is generated
here at process startup - meaning every issued token becomes invalid the
next time the server restarts (everyone gets logged out). That's a
reasonable default for "just try the app," but it's flagged loudly (via
logger.warning, not silently) since anyone running this for real should
set a persistent secret. See SETUP.md.
"""
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
import jwt

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Generated once per process if not configured - see module docstring.
_FALLBACK_SECRET_KEY = secrets.token_hex(32)
_warned_about_fallback = False


def _get_secret_key() -> str:
    global _warned_about_fallback
    settings = get_settings()
    if settings.jwt_secret_key:
        return settings.jwt_secret_key
    if not _warned_about_fallback:
        logger.warning(
            "JWT_SECRET_KEY is not set - using a random per-process secret. "
            "All sessions will be invalidated on the next server restart. "
            "Set JWT_SECRET_KEY in your .env for persistent sessions."
        )
        _warned_about_fallback = True
    return _FALLBACK_SECRET_KEY


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed hash (shouldn't happen with our own data, but a
        # corrupted/foreign hash should fail closed, not raise a 500).
        return False


class TokenError(Exception):
    """Raised for any invalid/expired/malformed token - callers map this
    to a 401, not a 500."""


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    """Returns (raw_token, jti, expires_at). The raw token is what's sent
    to the client; `jti` (a random token id, not derived from the token
    itself) is what gets stored server-side in RefreshToken.token_hash so
    a specific token can be looked up and revoked on logout without ever
    storing the raw token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    jti = uuid.uuid4().hex

    payload = {"sub": str(user_id), "type": "refresh", "jti": jti, "iat": now, "exp": expires_at}
    raw_token = jwt.encode(payload, _get_secret_key(), algorithm=settings.jwt_algorithm)
    return raw_token, jti, expires_at


def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid token") from exc

    if payload.get("type") != expected_type:
        raise TokenError(f"Expected a {expected_type} token")

    return payload
