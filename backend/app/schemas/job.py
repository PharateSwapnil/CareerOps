"""Pydantic I/O schemas for jobs — decoupled from the ORM model so provider
adapters and API responses don't leak SQLModel internals."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobSearchQuery(BaseModel):
    keywords: list[str] = []
    location: str | None = None
    remote_only: bool = False
    limit: int = 25


class NormalizedJob(BaseModel):
    """The common shape every JobProvider must map its raw response into."""

    title: str
    company_name: str
    location: str | None = None
    remote: bool = False
    description: str | None = None
    url: str
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    source_provider: str
    raw_source_id: str
    posted_at: datetime | None = None


class JobRead(BaseModel):
    id: int
    title: str
    company_name: str
    location: str | None
    remote: bool
    url: str
    source_provider: str
    posted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
