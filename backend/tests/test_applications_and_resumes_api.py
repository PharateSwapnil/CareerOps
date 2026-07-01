import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _create_job(client) -> int:
    response = client.post(
        "/api/v1/jobs/fetch?provider_name=stub",
        json={"keywords": ["Engineer"]},
    )
    return response.json()[0]["id"]


def test_create_and_list_applications(client):
    job_id = _create_job(client)

    response = client.post("/api/v1/applications", json={"job_id": job_id})
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "saved"
    assert body["job_id"] == job_id

    list_response = client.get("/api/v1/applications")
    assert list_response.status_code == 200
    assert any(a["id"] == body["id"] for a in list_response.json())


def test_create_application_with_missing_job_404s(client):
    response = client.post("/api/v1/applications", json={"job_id": 999999})
    assert response.status_code == 404


def test_status_transition_success(client):
    job_id = _create_job(client)
    app_resp = client.post("/api/v1/applications", json={"job_id": job_id})
    app_id = app_resp.json()["id"]

    response = client.patch(
        f"/api/v1/applications/{app_id}/status", json={"status": "applied"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "applied"
    assert body["applied_at"] is not None


def test_status_transition_rejects_invalid_skip(client):
    job_id = _create_job(client)
    app_resp = client.post("/api/v1/applications", json={"job_id": job_id})
    app_id = app_resp.json()["id"]

    # SAVED -> INTERVIEWING is not a legal transition.
    response = client.patch(
        f"/api/v1/applications/{app_id}/status", json={"status": "interviewing"}
    )
    assert response.status_code == 409


def test_update_application_notes(client):
    job_id = _create_job(client)
    app_resp = client.post("/api/v1/applications", json={"job_id": job_id})
    app_id = app_resp.json()["id"]

    response = client.patch(
        f"/api/v1/applications/{app_id}", json={"notes": "Great referral from Jane"}
    )
    assert response.status_code == 200
    assert response.json()["notes"] == "Great referral from Jane"


def test_delete_application(client):
    job_id = _create_job(client)
    app_resp = client.post("/api/v1/applications", json={"job_id": job_id})
    app_id = app_resp.json()["id"]

    delete_response = client.delete(f"/api/v1/applications/{app_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/applications/{app_id}")
    assert get_response.status_code == 404


def test_resume_create_and_versioning_flow(client):
    create_resp = client.post(
        "/api/v1/resumes", json={"label": "Base resume", "content": "v1 text"}
    )
    assert create_resp.status_code == 201
    resume_id = create_resp.json()["id"]
    assert create_resp.json()["version_number"] == 1

    version_resp = client.post(
        f"/api/v1/resumes/{resume_id}/versions",
        json={"label": "Base resume", "content": "v2 text"},
    )
    assert version_resp.status_code == 201
    v2 = version_resp.json()
    assert v2["version_number"] == 2
    assert v2["parent_version_id"] == resume_id

    history_resp = client.get(f"/api/v1/resumes/{resume_id}/history")
    assert history_resp.status_code == 200
    versions = history_resp.json()
    assert [v["version_number"] for v in versions] == [1, 2]

    diff_resp = client.get(f"/api/v1/resumes/{resume_id}/diff/{v2['id']}")
    assert diff_resp.status_code == 200
    assert "v1 text" in diff_resp.json()["diff"] or "v2 text" in diff_resp.json()["diff"]

    rollback_resp = client.post(f"/api/v1/resumes/{resume_id}/rollback")
    assert rollback_resp.status_code == 201
    rolled_back = rollback_resp.json()
    assert rolled_back["content"] == "v1 text"
    assert rolled_back["version_number"] == 3


def test_resume_list_returns_only_latest_versions(client):
    create_resp = client.post(
        "/api/v1/resumes", json={"label": "Chain A", "content": "a-v1"}
    )
    resume_id = create_resp.json()["id"]
    client.post(
        f"/api/v1/resumes/{resume_id}/versions",
        json={"label": "Chain A", "content": "a-v2"},
    )

    list_resp = client.get("/api/v1/resumes")
    assert list_resp.status_code == 200
    labels_and_versions = [(r["label"], r["version_number"]) for r in list_resp.json()]
    # Only the latest version of "Chain A" (v2) should appear, not v1.
    chain_a_versions = [v for label, v in labels_and_versions if label == "Chain A"]
    assert chain_a_versions == [2]
