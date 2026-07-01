"""Core semantic search logic: turning a Job into embeddable text, storing
embeddings (upserting per job+provider), and running in-process cosine
similarity search over stored vectors.

Deliberately NOT using a vector database or a SQLite extension (sqlite-vss
etc.) - per the roadmap's own guidance to "start with a simple in-process
index." For a personal job-search tool's scale (hundreds to low thousands of
postings), a linear scan with cosine similarity in Python is fast enough and
avoids the fragility of loadable SQLite extensions across platforms/Python
builds. If the corpus grows large enough for this to matter, swapping in a
real vector index is a contained change - only this module's search function
would need to change, not the API or storage schema.
"""
import json
import math

from sqlmodel import Session, select

from app.models.job import Job
from app.models.job_embedding import JobEmbedding
from app.providers.embedding_providers.base import EmbeddingProvider


def job_to_embedding_text(job: Job) -> str:
    """Builds the text that gets embedded for a job - title and description
    carry the most semantic signal; company/location add useful context."""
    parts = [job.title, job.company_name]
    if job.location:
        parts.append(job.location)
    if job.description:
        parts.append(job.description)
    return "\n".join(parts)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vector dimension mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def embed_and_store_job(
    session: Session, job: Job, provider: EmbeddingProvider
) -> JobEmbedding:
    """Embeds `job` with `provider` and upserts its JobEmbedding row (one
    row per job+provider - re-embedding overwrites rather than duplicates)."""
    text = job_to_embedding_text(job)
    vectors = await provider.embed([text], input_type="document")
    vector = vectors[0]

    existing = session.exec(
        select(JobEmbedding).where(
            JobEmbedding.job_id == job.id, JobEmbedding.provider == provider.name
        )
    ).first()

    if existing:
        existing.model = provider.model
        existing.dimension = provider.dimension
        existing.vector = json.dumps(vector)
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    embedding = JobEmbedding(
        job_id=job.id,
        provider=provider.name,
        model=provider.model,
        dimension=provider.dimension,
        vector=json.dumps(vector),
    )
    session.add(embedding)
    session.commit()
    session.refresh(embedding)
    return embedding


def _load_embeddings_for_provider(
    session: Session, provider_name: str
) -> list[tuple[int, list[float]]]:
    rows = session.exec(
        select(JobEmbedding).where(JobEmbedding.provider == provider_name)
    ).all()
    return [(row.job_id, json.loads(row.vector)) for row in rows]


async def semantic_search_jobs(
    session: Session,
    query: str,
    provider: EmbeddingProvider,
    limit: int = 20,
) -> list[tuple[Job, float]]:
    """Embeds `query` and returns the top `limit` jobs by cosine similarity,
    highest first, alongside their similarity score."""
    query_vectors = await provider.embed([query], input_type="query")
    query_vector = query_vectors[0]

    stored = _load_embeddings_for_provider(session, provider.name)
    scored = [(job_id, cosine_similarity(query_vector, vec)) for job_id, vec in stored]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    results: list[tuple[Job, float]] = []
    for job_id, score in scored[:limit]:
        job = session.get(Job, job_id)
        if job is not None:
            results.append((job, score))
    return results


def match_saved_search(
    session: Session, vector: list[float], provider_name: str, limit: int = 20
) -> list[tuple[Job, float]]:
    """Matches a pre-computed embedding vector (e.g. from a SavedSearch)
    against stored job embeddings, without re-embedding anything."""
    stored = _load_embeddings_for_provider(session, provider_name)
    scored = [(job_id, cosine_similarity(vector, vec)) for job_id, vec in stored]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    results: list[tuple[Job, float]] = []
    for job_id, score in scored[:limit]:
        job = session.get(Job, job_id)
        if job is not None:
            results.append((job, score))
    return results


def find_similar_jobs(
    session: Session, job_id: int, provider_name: str, limit: int = 10
) -> list[tuple[Job, float]]:
    """Finds jobs most similar to `job_id`'s own embedding, excluding itself."""
    target_embedding = session.exec(
        select(JobEmbedding).where(
            JobEmbedding.job_id == job_id, JobEmbedding.provider == provider_name
        )
    ).first()
    if target_embedding is None:
        return []

    target_vector = json.loads(target_embedding.vector)
    stored = _load_embeddings_for_provider(session, provider_name)

    scored = [
        (jid, cosine_similarity(target_vector, vec))
        for jid, vec in stored
        if jid != job_id
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    results: list[tuple[Job, float]] = []
    for jid, score in scored[:limit]:
        job = session.get(Job, jid)
        if job is not None:
            results.append((job, score))
    return results
