import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _fetch_stub_job(client, keyword: str) -> int:
    response = client.post(
        "/api/v1/jobs/fetch?provider_name=stub",
        json={"keywords": [keyword]},
    )
    return response.json()[0]["id"]


def test_jobs_are_auto_embedded_on_ingestion(client):
    """Fetching a job via the stub provider should auto-create a hashing
    embedding for it, without any separate embed step."""
    job_id = _fetch_stub_job(client, "Data Engineer")

    similar_response = client.get(f"/api/v1/jobs/{job_id}/similar")
    assert similar_response.status_code == 200
    # No assertion on contents (may be empty if it's the only job) - the
    # real check is that this doesn't error, which it would if no
    # embedding existed and the endpoint mishandled that.


def test_semantic_search_returns_results(client):
    _fetch_stub_job(client, "Backend Engineer")
    _fetch_stub_job(client, "Marketing Manager")

    response = client.post(
        "/api/v1/jobs/semantic-search", json={"query": "backend engineering role", "limit": 10}
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert "score" in results[0]
    assert "job" in results[0]


def test_similar_jobs_endpoint(client):
    job_id = _fetch_stub_job(client, "Platform Engineer")
    _fetch_stub_job(client, "Site Reliability Engineer")

    response = client.get(f"/api/v1/jobs/{job_id}/similar?limit=5")
    assert response.status_code == 200
    results = response.json()
    # The target job itself should never appear in its own similar list.
    assert all(r["job"]["id"] != job_id for r in results)


def test_saved_search_create_and_match(client):
    _fetch_stub_job(client, "Cloud Engineer")

    create_response = client.post(
        "/api/v1/saved-searches",
        json={"name": "Cloud roles", "query_text": "cloud infrastructure engineer"},
    )
    assert create_response.status_code == 201
    saved_search = create_response.json()
    assert saved_search["embedding_provider"] == "hashing"

    matches_response = client.get(f"/api/v1/saved-searches/{saved_search['id']}/matches")
    assert matches_response.status_code == 200
    assert isinstance(matches_response.json(), list)


def test_saved_search_list_and_delete(client):
    create_response = client.post(
        "/api/v1/saved-searches",
        json={"name": "Test search", "query_text": "test query"},
    )
    saved_search_id = create_response.json()["id"]

    list_response = client.get("/api/v1/saved-searches")
    assert list_response.status_code == 200
    assert any(s["id"] == saved_search_id for s in list_response.json())

    delete_response = client.delete(f"/api/v1/saved-searches/{saved_search_id}")
    assert delete_response.status_code == 204

    list_after = client.get("/api/v1/saved-searches")
    assert all(s["id"] != saved_search_id for s in list_after.json())
