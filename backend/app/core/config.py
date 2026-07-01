"""Application settings, loaded from environment variables (.env supported).

Local-first by default: the database lives in a SQLite file on disk unless
DATABASE_URL is overridden.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CareerOps++"
    api_v1_prefix: str = "/api/v1"
    debug: bool = True

    # Local-first storage: default to a SQLite file under backend/data/
    database_url: str = "sqlite:///./data/careerops.db"

    # LLM provider API keys (all optional; providers that lack a key are skipped
    # by the fallback orchestrator introduced in Milestone 3).
    anthropic_api_key: str | None = None
    groq_api_key: str | None = None
    openrouter_api_key: str | None = None
    gemini_api_key: str | None = None

    # Job provider API keys for sources that require registration (all
    # optional; a provider without its key configured returns no results
    # rather than erroring, so it's safe to leave these blank).
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None

    # Embedding provider for semantic search (Milestone 5). "hashing" is a
    # zero-dependency, zero-API-key local fallback (lexical/n-gram overlap,
    # not true neural semantics) that's used by default so search works out
    # of the box. Set to "voyage" + configure VOYAGE_API_KEY for real neural
    # embeddings with cross-terminology semantic matching.
    embedding_default_provider: str = "hashing"
    voyage_api_key: str | None = None

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Order in which the LLM fallback orchestrator (Milestone 3) tries
    # providers. "stub" is included last by default so /ai endpoints still
    # work end-to-end in local dev without any API keys configured.
    llm_provider_priority: list[str] = ["claude", "groq", "stub"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
