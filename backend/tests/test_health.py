import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    # Use as a context manager so FastAPI's lifespan (init_db) actually runs.
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_fetch_jobs_stub_provider(client):
    response = client.post(
        "/api/v1/jobs/fetch?provider_name=stub",
        json={"keywords": ["Data Engineer"], "location": "Remote"},
    )
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 1
    assert "Data Engineer" in jobs[0]["title"]


def test_list_jobs_after_fetch(client):
    client.post(
        "/api/v1/jobs/fetch?provider_name=stub",
        json={"keywords": ["Data Engineer"], "location": "Remote"},
    )
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
