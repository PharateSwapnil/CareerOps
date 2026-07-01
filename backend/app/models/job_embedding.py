from datetime import datetime, timezone

from sqlmodel import Field, SQLModel, UniqueConstraint


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobEmbedding(SQLModel, table=True):
    """Stores one embedding vector per (job, provider) pair. Re-embedding a
    job with the same provider overwrites its row rather than piling up
    duplicates - `services/embeddings.py` handles the upsert. Keeping
    provider as part of the identity (rather than one fixed column on Job)
    lets a job carry both a cheap local embedding and a higher-quality
    neural one side by side without a schema migration.
    """

    __table_args__ = (UniqueConstraint("job_id", "provider", name="uq_job_embedding_provider"),)

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", index=True)
    provider: str = Field(index=True)  # e.g. "hashing", "voyage"
    model: str  # e.g. "hashing-v1", "voyage-4-lite"
    dimension: int
    vector: str  # JSON-encoded list[float]

    created_at: datetime = Field(default_factory=utcnow)
