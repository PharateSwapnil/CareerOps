from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InteractionType(str, Enum):
    MESSAGE = "message"
    CALL = "call"
    MEETING = "meeting"
    EMAIL = "email"
    NOTE = "note"


class Interaction(SQLModel, table=True):
    """A logged touch-point with a Contact — the CRM's activity history."""

    id: int | None = Field(default=None, primary_key=True)
    contact_id: int = Field(foreign_key="contact.id", index=True)

    type: InteractionType = InteractionType.NOTE
    summary: str
    occurred_at: datetime = Field(default_factory=utcnow)

    created_at: datetime = Field(default_factory=utcnow)
