from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeCreate(BaseModel):
    label: str
    content: str
    tailored_for_job_id: int | None = None


class ResumeRead(BaseModel):
    id: int
    user_id: int
    label: str
    content: str
    tailored_for_job_id: int | None
    parent_version_id: int | None
    version_number: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeDiff(BaseModel):
    from_version_id: int
    to_version_id: int
    diff: str  # unified diff format
