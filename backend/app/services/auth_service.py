"""Registration, login, token refresh, and logout logic. Kept separate
from route wiring (api/routes/auth.py) so it's independently testable.
"""
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User


class AuthError(Exception):
    """Raised for any auth failure (bad credentials, email already
    registered, invalid/expired/revoked token) - routes map this to an
    appropriate 4xx, never a 500."""


def register_user(session: Session, full_name: str, email: str, password: str) -> User:
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        raise AuthError("An account with this email already exists")

    user = User(full_name=full_name, email=email, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate_user(session: Session, email: str, password: str) -> User:
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None or not verify_password(password, user.password_hash):
        # Deliberately the same error for "no such user" and "wrong
        # password" - distinguishing them lets an attacker enumerate
        # registered emails.
        raise AuthError("Incorrect email or password")
    return user


def issue_tokens(session: Session, user: User) -> tuple[str, str]:
    """Returns (access_token, refresh_token) and persists the refresh
    token's jti so it can later be revoked."""
    access_token = create_access_token(user.id)
    refresh_token, jti, expires_at = create_refresh_token(user.id)

    session.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at))
    session.commit()

    return access_token, refresh_token


def refresh_access_token(session: Session, refresh_token: str) -> str:
    """Validates a refresh token (signature, expiry, not revoked) and
    issues a new access token. Does NOT rotate the refresh token itself in
    this first pass - see ROADMAP.md for the refresh-token-rotation
    follow-up note."""
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise AuthError(str(exc)) from exc

    jti = payload.get("jti")
    stored = session.exec(select(RefreshToken).where(RefreshToken.jti == jti)).first()
    if stored is None or stored.revoked:
        raise AuthError("Refresh token has been revoked or is unknown")
    # stored.expires_at comes back naive after a SQLite round-trip (SQLite
    # has no native timezone-aware datetime type), even though it was
    # written as UTC - so compare against a naive UTC "now" rather than a
    # timezone-aware one, which would otherwise raise TypeError.
    if stored.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise AuthError("Refresh token has expired")

    user_id = int(payload["sub"])
    return create_access_token(user_id)


def revoke_refresh_token(session: Session, refresh_token: str) -> None:
    """Logout: marks the refresh token revoked so it can no longer be used
    to mint new access tokens, even though the JWT itself remains
    cryptographically valid until it naturally expires."""
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except TokenError:
        # Already invalid/expired - nothing to revoke, and logout should
        # succeed either way from the client's perspective.
        return

    jti = payload.get("jti")
    stored = session.exec(select(RefreshToken).where(RefreshToken.jti == jti)).first()
    if stored is not None:
        stored.revoked = True
        session.add(stored)
        session.commit()
