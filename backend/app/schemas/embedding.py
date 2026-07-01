from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.job import JobRead


class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 20
    provider_name: str | None = None  # defaults to Settings.embedding_default_provider


class SemanticSearchResult(BaseModel):
    job: JobRead
    score: float


class SavedSearchCreate(BaseModel):
    name: str
    query_text: str
    provider_name: str | None = None


class SavedSearchRead(BaseModel):
    id: int
    user_id: int
    name: str
    query_text: str
    embedding_provider: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
