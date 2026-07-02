from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RefreshToken(SQLModel, table=True):
    """Tracks issued refresh tokens so logout/revocation actually works -
    a pure stateless-JWT scheme has no way to invalidate a token before its
    natural expiry, which means "logout" would be purely cosmetic (the
    token would still work if stolen/leaked).

    Stores `jti` (a random token identifier embedded in the JWT payload,
    generated in core/security.py) rather than the raw refresh token
    itself. This still lets the server revoke a specific token on logout,
    but a leak of this table doesn't hand out usable bearer credentials -
    the jti alone can't be used to authenticate without a valid JWT
    signature, which isn't derivable from it.
    """

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    jti: str = Field(index=True, unique=True)
    expires_at: datetime
    revoked: bool = False
    created_at: datetime = Field(default_factory=utcnow)
