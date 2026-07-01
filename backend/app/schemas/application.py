from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.application import ApplicationStatus


class ApplicationCreate(BaseModel):
    job_id: int
    resume_id: int | None = None
    status: ApplicationStatus = ApplicationStatus.SAVED
    notes: str | None = None
    next_follow_up_at: datetime | None = None


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationUpdate(BaseModel):
    resume_id: int | None = None
    notes: str | None = None
    next_follow_up_at: datetime | None = None
    recruiter_contact_id: int | None = None


class ApplicationRead(BaseModel):
    id: int
    user_id: int
    job_id: int
    resume_id: int | None
    status: ApplicationStatus
    recruiter_contact_id: int | None
    notes: str | None
    next_follow_up_at: datetime | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
