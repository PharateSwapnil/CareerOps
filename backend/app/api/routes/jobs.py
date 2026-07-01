from fastapi import APIRouter, BackgroundTasks, Depends
from sqlmodel import Session, select

from app.core.config import get_settings
from app.db.session import get_session
from app.models.job import Job
from app.providers.embedding_providers.registry import get_provider as get_embedding_provider
from app.providers.job_providers.registry import get_provider, list_providers
from app.schemas.job import JobRead, JobSearchQuery
from app.schemas.embedding import SemanticSearchRequest, SemanticSearchResult
from app.services.embeddings import find_similar_jobs, semantic_search_jobs
from app.services.job_ingestion import ingest_jobs, ingest_jobs_background

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
async def list_jobs(session: Session = Depends(get_session)) -> list[Job]:
    return session.exec(select(Job)).all()


@router.get("/providers")
async def get_providers() -> list[str]:
    return list_providers()


@router.post("/semantic-search", response_model=list[SemanticSearchResult])
async def semantic_search(
    payload: SemanticSearchRequest, session: Session = Depends(get_session)
) -> list[SemanticSearchResult]:
    """Finds jobs by meaning rather than exact keyword match. Quality
    depends on the configured embedding provider - see
    Settings.embedding_default_provider and providers/embedding_providers/
    for the tradeoffs between the free local "hashing" provider and the
    neural "voyage" provider."""
    settings = get_settings()
    provider_name = payload.provider_name or settings.embedding_default_provider
    provider = get_embedding_provider(provider_name)

    results = await semantic_search_jobs(session, payload.query, provider, payload.limit)
    return [SemanticSearchResult(job=job, score=score) for job, score in results]


@router.get("/{job_id}/similar", response_model=list[SemanticSearchResult])
async def similar_jobs(
    job_id: int,
    limit: int = 10,
    provider_name: str | None = None,
    session: Session = Depends(get_session),
) -> list[SemanticSearchResult]:
    """Finds jobs similar to `job_id` using its stored embedding."""
    settings = get_settings()
    resolved_provider = provider_name or settings.embedding_default_provider

    results = find_similar_jobs(session, job_id, resolved_provider, limit)
    return [SemanticSearchResult(job=job, score=score) for job, score in results]


@router.post("/fetch", response_model=list[JobRead])
async def fetch_jobs(
    query: JobSearchQuery,
    provider_name: str = "stub",
    session: Session = Depends(get_session),
) -> list[Job]:
    """Fetch jobs from a provider synchronously and return them once persisted.

    Best for small/fast providers (or the stub) where the caller wants results
    immediately. For larger fetches (e.g. many Greenhouse board tokens), prefer
    POST /jobs/ingest which runs in the background.
    """
    provider = get_provider(provider_name)
    return await ingest_jobs(provider, query, session)


@router.post("/ingest", status_code=202)
async def ingest_jobs_endpoint(
    background_tasks: BackgroundTasks,
    query: JobSearchQuery,
    provider_name: str = "greenhouse",
) -> dict[str, str]:
    """Kick off a job fetch in the background and return immediately.

    The client should poll GET /jobs afterward to see newly ingested postings.
    """
    provider = get_provider(provider_name)
    background_tasks.add_task(ingest_jobs_background, provider, query)
    return {"status": "accepted", "provider": provider_name}
