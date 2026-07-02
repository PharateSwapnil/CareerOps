"""Shared pytest fixtures.

Fixes a known gap flagged since Milestone 4: API-level tests using
TestClient(app) were previously sharing the persistent dev SQLite file
(backend/data/careerops.db) across the whole test run, because
app.db.session.engine is created once at import time bound to
Settings.database_url. That meant data inserted by one test file could
leak into another - which is exactly how the Milestone 4 stub-provider
raw_source_id bug was discovered.

The `client` fixture here gives every test its own fresh, isolated
in-memory SQLite database. Two separate things need to point at it:
1. FastAPI's `get_session` dependency, overridden via
   `app.dependency_overrides` (covers every normal request-handling path).
2. `services/job_ingestion.py`'s background-task path
   (`ingest_jobs_background`), which does NOT go through FastAPI's
   dependency injection at all - it opens its own `Session(db_session.engine)`
   directly, so dependency_overrides alone doesn't reach it. That module
   was updated to read `db_session.engine` dynamically (rather than
   binding the name at import time) specifically so this fixture can
   monkeypatch it too.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import session as db_session
from app.main import app


@pytest.fixture()
def client(monkeypatch):
    # StaticPool keeps a single connection alive for the lifetime of this
    # in-memory engine, since ":memory:" SQLite databases are otherwise
    # per-connection and would vanish between requests.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[db_session.get_session] = override_get_session
    monkeypatch.setattr(db_session, "engine", engine)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()

