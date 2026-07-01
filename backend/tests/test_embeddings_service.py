import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models.job import Job
from app.providers.embedding_providers.hashing_provider import HashingEmbeddingProvider
from app.services.embeddings import (
    embed_and_store_job,
    find_similar_jobs,
    job_to_embedding_text,
    semantic_search_jobs,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture()
def provider():
    return HashingEmbeddingProvider()


def _make_job(session, title, description, source_id) -> Job:
    job = Job(
        title=title,
        company_name="Acme",
        description=description,
        url="https://example.com/job",
        source_provider="test",
        raw_source_id=source_id,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def test_job_to_embedding_text_includes_key_fields():
    job = Job(
        title="Backend Engineer",
        company_name="Acme",
        location="Remote",
        description="Build APIs",
        url="https://x",
        source_provider="test",
        raw_source_id="1",
    )
    text = job_to_embedding_text(job)
    assert "Backend Engineer" in text
    assert "Acme" in text
    assert "Remote" in text
    assert "Build APIs" in text


@pytest.mark.asyncio
async def test_embed_and_store_job_upserts_not_duplicates(session, provider):
    job = _make_job(session, "Backend Engineer", "Python and Go", "1")

    first = await embed_and_store_job(session, job, provider)
    second = await embed_and_store_job(session, job, provider)

    assert first.id == second.id  # same row, updated in place


@pytest.mark.asyncio
async def test_semantic_search_ranks_relevant_job_higher(session, provider):
    relevant = _make_job(
        session, "Senior Python Backend Engineer", "Django, PostgreSQL, AWS", "1"
    )
    irrelevant = _make_job(
        session, "Marketing Coordinator", "Social media and content calendars", "2"
    )
    await embed_and_store_job(session, relevant, provider)
    await embed_and_store_job(session, irrelevant, provider)

    results = await semantic_search_jobs(session, "python backend developer", provider, limit=10)

    assert len(results) == 2
    top_job, top_score = results[0]
    assert top_job.id == relevant.id


@pytest.mark.asyncio
async def test_find_similar_jobs_excludes_self(session, provider):
    job1 = _make_job(session, "Backend Engineer", "Python APIs", "1")
    job2 = _make_job(session, "Senior Backend Engineer", "Python APIs and microservices", "2")
    await embed_and_store_job(session, job1, provider)
    await embed_and_store_job(session, job2, provider)

    results = find_similar_jobs(session, job1.id, provider.name, limit=10)

    assert all(job.id != job1.id for job, _ in results)
    assert any(job.id == job2.id for job, _ in results)


def test_find_similar_jobs_returns_empty_without_embedding(session, provider):
    job = _make_job(session, "Backend Engineer", "Python", "1")
    results = find_similar_jobs(session, job.id, provider.name, limit=10)
    assert results == []
