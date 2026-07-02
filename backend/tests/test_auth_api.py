import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import session as db_session
from app.main import app


@pytest.fixture()
def raw_client(monkeypatch):
    """Unlike the `client` fixture in conftest.py, this one does NOT
    auto-register a user or set an Authorization header - needed for tests
    that exercise registration/login themselves, or that need two separate
    users to test cross-user isolation."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[db_session.get_session] = override_get_session
    monkeypatch.setattr(db_session, "engine", engine)

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    engine.dispose()


def test_register_returns_tokens(raw_client):
    response = raw_client.post(
        "/api/v1/auth/register",
        json={"full_name": "Jane Doe", "email": "jane@example.com", "password": "hunter2"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_register_duplicate_email_rejected(raw_client):
    payload = {"full_name": "Jane Doe", "email": "jane@example.com", "password": "hunter2"}
    raw_client.post("/api/v1/auth/register", json=payload)
    response = raw_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


def test_login_with_correct_credentials(raw_client):
    raw_client.post(
        "/api/v1/auth/register",
        json={"full_name": "Jane Doe", "email": "jane@example.com", "password": "hunter2"},
    )
    response = raw_client.post(
        "/api/v1/auth/login", json={"email": "jane@example.com", "password": "hunter2"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_wrong_password_rejected(raw_client):
    raw_client.post(
        "/api/v1/auth/register",
        json={"full_name": "Jane Doe", "email": "jane@example.com", "password": "hunter2"},
    )
    response = raw_client.post(
        "/api/v1/auth/login", json={"email": "jane@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_with_unknown_email_rejected(raw_client):
    response = raw_client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )
    assert response.status_code == 401


def test_protected_endpoint_requires_auth(raw_client):
    response = raw_client.get("/api/v1/applications")
    assert response.status_code == 401


def test_protected_endpoint_rejects_garbage_token(raw_client):
    response = raw_client.get(
        "/api/v1/applications", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_protected_endpoint_works_with_valid_token(raw_client):
    register_resp = raw_client.post(
        "/api/v1/auth/register",
        json={"full_name": "Jane Doe", "email": "jane@example.com", "password": "hunter2"},
    )
    token = register_resp.json()["access_token"]
    response = raw_client.get(
        "/api/v1/applications", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_refresh_token_issues_new_access_token(raw_client):
    register_resp = raw_client.post(
        "/api/v1/auth/register",
        json={"full_name": "Jane Doe", "email": "jane@example.com", "password": "hunter2"},
    )
    refresh_token = register_resp.json()["refresh_token"]

    response = raw_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_logout_revokes_refresh_token(raw_client):
    register_resp = raw_client.post(
        "/api/v1/auth/register",
        json={"full_name": "Jane Doe", "email": "jane@example.com", "password": "hunter2"},
    )
    refresh_token = register_resp.json()["refresh_token"]

    logout_resp = raw_client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 204

    # The refresh token should no longer work after logout.
    refresh_resp = raw_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401


def test_users_cannot_see_each_others_applications(raw_client):
    """The core promise of multi-user auth: user A's data must be
    completely invisible to user B, including by direct ID lookup."""
    user_a = raw_client.post(
        "/api/v1/auth/register",
        json={"full_name": "User A", "email": "a@example.com", "password": "passwordA"},
    ).json()
    user_b = raw_client.post(
        "/api/v1/auth/register",
        json={"full_name": "User B", "email": "b@example.com", "password": "passwordB"},
    ).json()

    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}

    job_resp = raw_client.post(
        "/api/v1/jobs/fetch?provider_name=stub", json={"keywords": ["Engineer"]}, headers=headers_a
    )
    job_id = job_resp.json()[0]["id"]

    app_resp = raw_client.post(
        "/api/v1/applications", json={"job_id": job_id}, headers=headers_a
    )
    assert app_resp.status_code == 201
    application_id = app_resp.json()["id"]

    # User A can see it.
    get_as_a = raw_client.get(f"/api/v1/applications/{application_id}", headers=headers_a)
    assert get_as_a.status_code == 200

    # User B gets a 404, not a 403 - the app shouldn't even confirm the id exists.
    get_as_b = raw_client.get(f"/api/v1/applications/{application_id}", headers=headers_b)
    assert get_as_b.status_code == 404

    # User B's own application list is empty - A's application doesn't leak in.
    list_as_b = raw_client.get("/api/v1/applications", headers=headers_b)
    assert list_as_b.json() == []

    # User B can't delete user A's application either.
    delete_as_b = raw_client.delete(f"/api/v1/applications/{application_id}", headers=headers_b)
    assert delete_as_b.status_code == 404


def test_users_cannot_see_each_others_contacts(raw_client):
    user_a = raw_client.post(
        "/api/v1/auth/register",
        json={"full_name": "User A", "email": "a2@example.com", "password": "passwordA"},
    ).json()
    user_b = raw_client.post(
        "/api/v1/auth/register",
        json={"full_name": "User B", "email": "b2@example.com", "password": "passwordB"},
    ).json()

    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}

    contact_resp = raw_client.post(
        "/api/v1/contacts", json={"full_name": "Some Recruiter"}, headers=headers_a
    )
    contact_id = contact_resp.json()["id"]

    get_as_b = raw_client.get(f"/api/v1/contacts/{contact_id}", headers=headers_b)
    assert get_as_b.status_code == 404


def test_profile_is_per_user(raw_client):
    user_a = raw_client.post(
        "/api/v1/auth/register",
        json={"full_name": "User A", "email": "a3@example.com", "password": "passwordA"},
    ).json()
    user_b = raw_client.post(
        "/api/v1/auth/register",
        json={"full_name": "User B", "email": "b3@example.com", "password": "passwordB"},
    ).json()

    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}

    raw_client.patch("/api/v1/me", json={"phone": "111-1111"}, headers=headers_a)

    profile_a = raw_client.get("/api/v1/me", headers=headers_a).json()
    profile_b = raw_client.get("/api/v1/me", headers=headers_b).json()

    assert profile_a["phone"] == "111-1111"
    assert profile_b["phone"] is None
