from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """Local user profile. CareerOps++ starts single-user/local-first;
    multi-user support is a later milestone."""

    id: int | None = Field(default=None, primary_key=True)
    full_name: str
    email: str = Field(index=True, unique=True)

    # Free-text / JSON-ish fields kept simple for Milestone 1; may move to
    # dedicated normalized tables (Skill, Goal) in a later milestone.
    headline: str | None = None
    skills: str | None = None  # comma-separated for now
    career_goals: str | None = None
    preferences: str | None = None  # JSON-encoded string

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
