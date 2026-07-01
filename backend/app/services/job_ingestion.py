"""Shared job-ingestion logic: fetch from a provider, normalize, dedupe, persist.

Used by both the synchronous POST /jobs/fetch endpoint and the background
POST /jobs/ingest endpoint, so the dedupe rule (source_provider +
raw_source_id) only lives in one place.
"""
import logging

from sqlmodel import Session, select

from app.db.session import engine
from app.models.job import Job
from app.providers.job_providers.base import JobProvider
from app.schemas.job import JobSearchQuery

logger = logging.getLogger(__name__)


async def ingest_jobs(
    provider: JobProvider, query: JobSearchQuery, session: Session
) -> list[Job]:
    """Fetch postings from `provider`, dedupe against existing rows, persist
    new ones, and return the full set (existing + newly created) matching
    the query."""
    normalized_jobs = await provider.fetch_jobs(query)

    saved: list[Job] = []
    for nj in normalized_jobs:
        existing = session.exec(
            select(Job).where(
                Job.source_provider == nj.source_provider,
                Job.raw_source_id == nj.raw_source_id,
            )
        ).first()
        if existing:
            saved.append(existing)
            continue

        job = Job(**nj.model_dump())
        session.add(job)
        session.commit()
        session.refresh(job)
        saved.append(job)

    return saved


async def ingest_jobs_background(provider: JobProvider, query: JobSearchQuery) -> None:
    """Entry point for FastAPI BackgroundTasks: opens its own DB session since
    the request-scoped session is closed by the time a background task runs."""
    with Session(engine) as session:
        try:
            jobs = await ingest_jobs(provider, query, session)
            logger.info(
                "Background ingestion via %s completed: %d jobs", provider.name, len(jobs)
            )
        except Exception:
            logger.exception("Background ingestion via %s failed", provider.name)
