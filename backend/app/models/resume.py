from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Resume(SQLModel, table=True):
    """A resume version. Immutable once created — edits create a new row with
    `parent_version_id` pointing at the prior version, enabling rollback/diff.
    """

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    label: str  # e.g. "Base resume", "Tailored - Acme SWE role"
    content: str  # markdown or structured JSON, format TBD in Milestone 4
    tailored_for_job_id: int | None = Field(default=None, foreign_key="job.id")

    parent_version_id: int | None = Field(default=None, foreign_key="resume.id")
    version_number: int = 1

    created_at: datetime = Field(default_factory=utcnow)
