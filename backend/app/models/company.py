from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Company(SQLModel, table=True):
    """Normalized company record, enrichable with AI-generated intelligence."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    website: str | None = None
    size: str | None = None  # e.g. "51-200"
    funding_stage: str | None = None
    industry: str | None = None
    tech_stack: str | None = None  # comma-separated for now
    culture_summary: str | None = None  # AI-generated
    reputation_summary: str | None = None  # AI-generated
    salary_insights: str | None = None  # AI-generated / aggregated

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
