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

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
