import pytest


def test_get_profile_returns_authenticated_user(client):
    response = client.get("/api/v1/me")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "test-user@example.com"


def test_update_profile(client):
    response = client.patch(
        "/api/v1/me",
        json={
            "full_name": "Jane Doe",
            "phone": "555-1234",
            "linkedin_url": "https://linkedin.com/in/janedoe",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Jane Doe"
    assert body["phone"] == "555-1234"
    assert body["linkedin_url"] == "https://linkedin.com/in/janedoe"


def test_profile_persists_across_requests(client):
    client.patch("/api/v1/me", json={"portfolio_url": "https://example.dev"})
    response = client.get("/api/v1/me")
    assert response.json()["portfolio_url"] == "https://example.dev"
