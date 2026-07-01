from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.job import Job
from app.providers.job_providers.registry import get_provider
from app.schemas.job import JobRead, JobSearchQuery

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
async def list_jobs(session: Session = Depends(get_session)) -> list[Job]:
    return session.exec(select(Job)).all()


@router.post("/fetch", response_model=list[JobRead])
async def fetch_jobs(
    query: JobSearchQuery,
    provider_name: str = "stub",
    session: Session = Depends(get_session),
) -> list[Job]:
    """Fetch jobs from a provider, normalize + dedupe, and persist them."""
    provider = get_provider(provider_name)
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
