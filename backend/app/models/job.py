from datetime import datetime, timezone

from sqlmodel import Field, SQLModel, UniqueConstraint


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(SQLModel, table=True):
    """A job posting, normalized regardless of which provider it came from.

    `source_provider` + `raw_source_id` together uniquely identify a posting so
    duplicate ingestion from multiple providers can be detected.
    """

    __table_args__ = (UniqueConstraint("source_provider", "raw_source_id", name="uq_job_source"),)

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    company_id: int | None = Field(default=None, foreign_key="company.id")
    company_name: str  # denormalized for cases where Company enrichment hasn't run yet

    location: str | None = None
    remote: bool = False
    description: str | None = None
    url: str
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None

    source_provider: str = Field(index=True)  # e.g. "greenhouse", "lever", "rss"
    raw_source_id: str = Field(index=True)  # provider's native job id

    posted_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=utcnow)
    created_at: datetime = Field(default_factory=utcnow)
