from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ContactRelationship(str, Enum):
    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    REFERRAL = "referral"
    COLD_OUTREACH = "cold_outreach"
    PEER = "peer"
    OTHER = "other"


class Contact(SQLModel, table=True):
    """A person in the user's networking CRM."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    full_name: str
    relationship: ContactRelationship = ContactRelationship.OTHER
    company_id: int | None = Field(default=None, foreign_key="company.id")
    email: str | None = None
    linkedin_url: str | None = None
    notes: str | None = None

    next_follow_up_at: datetime | None = None

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
