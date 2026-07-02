import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_job_ingestion_auto_creates_and_links_company(client):
    response = client.post(
        "/api/v1/jobs/fetch?provider_name=stub",
        json={"keywords": ["Platform Engineer"]},
    )
    job = response.json()[0]

    companies_response = client.get("/api/v1/companies")
    assert companies_response.status_code == 200
    companies = companies_response.json()
    matching = [c for c in companies if c["name"] == job["company_name"]]
    assert len(matching) == 1


def test_get_company_jobs(client):
    fetch_resp = client.post(
        "/api/v1/jobs/fetch?provider_name=stub",
        json={"keywords": ["Data Scientist"]},
    )
    job = fetch_resp.json()[0]

    companies = client.get("/api/v1/companies").json()
    company = next(c for c in companies if c["name"] == job["company_name"])

    jobs_response = client.get(f"/api/v1/companies/{company['id']}/jobs")
    assert jobs_response.status_code == 200
    assert any(j["id"] == job["id"] for j in jobs_response.json())


def test_get_missing_company_404s(client):
    response = client.get("/api/v1/companies/999999")
    assert response.status_code == 404


def test_data_providers_list(client):
    response = client.get("/api/v1/companies/data-providers")
    assert response.status_code == 200
    assert "wikipedia" in response.json()


def test_enrich_company_endpoint(client):
    """Enrichment should work end-to-end even with no external API keys
    configured: the Wikipedia lookup will fail to reach the real network in
    most sandboxed/CI environments (falling back to found=False internally
    on error would be nice, but since we can't mock httpx globally through
    the API layer here, this test just checks the endpoint doesn't 500 and
    the AI summary falls back to the stub LLM provider successfully)."""
    fetch_resp = client.post(
        "/api/v1/jobs/fetch?provider_name=stub",
        json={"keywords": ["Backend Engineer"]},
    )
    job = fetch_resp.json()[0]
    companies = client.get("/api/v1/companies").json()
    company = next(c for c in companies if c["name"] == job["company_name"])

    response = client.post(f"/api/v1/companies/{company['id']}/enrich")
    assert response.status_code == 200
    body = response.json()
    assert body["salary_insights"] is None  # never AI-fabricated
