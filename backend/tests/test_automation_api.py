import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _create_application(client) -> int:
    job_resp = client.post(
        "/api/v1/jobs/fetch?provider_name=stub", json={"keywords": ["Engineer"]}
    )
    job_id = job_resp.json()[0]["id"]
    app_resp = client.post("/api/v1/applications", json={"job_id": job_id})
    return app_resp.json()["id"]


def test_start_session_without_browser_binary_returns_503(client):
    """In this dev sandbox (and in any environment where `playwright
    install chromium` hasn't been run), starting a session should fail
    loudly and clearly - not silently hang or 500. This test exercises the
    REAL code path, not a mock: playwright IS installed as a package here,
    but the Chromium binary genuinely isn't available."""
    application_id = _create_application(client)

    response = client.post("/api/v1/automation/sessions", json={"application_id": application_id})

    assert response.status_code == 503
    assert "chromium" in response.json()["detail"].lower() or "browser" in response.json()["detail"].lower()


def test_start_session_records_error_status_in_audit_log(client):
    application_id = _create_application(client)
    client.post("/api/v1/automation/sessions", json={"application_id": application_id})

    list_response = client.get("/api/v1/automation/sessions")
    assert list_response.status_code == 200
    sessions = list_response.json()
    assert len(sessions) >= 1
    assert sessions[-1]["status"] == "error"
    assert sessions[-1]["error_message"] is not None


def test_start_session_missing_application_404s(client):
    response = client.post("/api/v1/automation/sessions", json={"application_id": 999999})
    assert response.status_code == 404


def test_resume_without_active_session_returns_409(client):
    application_id = _create_application(client)
    # This will 503 (no browser), so no live session gets registered.
    client.post("/api/v1/automation/sessions", json={"application_id": application_id})

    # Get the session id that WAS created (with error status) to test resume against.
    sessions = client.get("/api/v1/automation/sessions").json()
    session_id = sessions[-1]["id"]

    resume_response = client.post(f"/api/v1/automation/sessions/{session_id}/resume")
    assert resume_response.status_code == 409


def test_get_missing_session_404s(client):
    response = client.get("/api/v1/automation/sessions/999999")
    assert response.status_code == 404


def test_close_session(client):
    application_id = _create_application(client)
    client.post("/api/v1/automation/sessions", json={"application_id": application_id})
    sessions = client.get("/api/v1/automation/sessions").json()
    session_id = sessions[-1]["id"]

    close_response = client.delete(f"/api/v1/automation/sessions/{session_id}")
    assert close_response.status_code == 204

    status_response = client.get(f"/api/v1/automation/sessions/{session_id}")
    assert status_response.json()["status"] == "closed"
