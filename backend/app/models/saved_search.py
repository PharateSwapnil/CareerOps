from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SavedSearch(SQLModel, table=True):
    """A saved semantic search: a query the user wants to keep re-running
    against newly ingested jobs (e.g. as a future "new matches" alert
    feature). The query text's embedding is stored alongside it so matching
    doesn't require re-embedding on every read.
    """

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    name: str
    query_text: str

    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    embedding_vector: str  # JSON-encoded list[float]

    created_at: datetime = Field(default_factory=utcnow)
