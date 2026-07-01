from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApplicationStatus(str, Enum):
    SAVED = "saved"
    APPLIED = "applied"
    PHONE_SCREEN = "phone_screen"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Application(SQLModel, table=True):
    """Tracks the full lifecycle of a user's application to a job."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    job_id: int = Field(foreign_key="job.id", index=True)
    resume_id: int | None = Field(default=None, foreign_key="resume.id")

    status: ApplicationStatus = Field(default=ApplicationStatus.SAVED, index=True)
    recruiter_contact_id: int | None = Field(default=None, foreign_key="contact.id")

    notes: str | None = None
    next_follow_up_at: datetime | None = None

    applied_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
