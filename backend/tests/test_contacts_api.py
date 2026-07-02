from datetime import datetime, timedelta, timezone

import pytest


def test_create_and_list_contacts(client):
    response = client.post(
        "/api/v1/contacts",
        json={"full_name": "Jane Recruiter", "relationship": "recruiter"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["full_name"] == "Jane Recruiter"
    assert body["relationship"] == "recruiter"

    list_response = client.get("/api/v1/contacts")
    assert list_response.status_code == 200
    assert any(c["id"] == body["id"] for c in list_response.json())


def test_get_missing_contact_404s(client):
    response = client.get("/api/v1/contacts/999999")
    assert response.status_code == 404


def test_update_contact(client):
    create_resp = client.post("/api/v1/contacts", json={"full_name": "Alex Peer"})
    contact_id = create_resp.json()["id"]

    update_resp = client.patch(
        f"/api/v1/contacts/{contact_id}", json={"notes": "Met at PyCon 2026"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["notes"] == "Met at PyCon 2026"


def test_delete_contact(client):
    create_resp = client.post("/api/v1/contacts", json={"full_name": "To Delete"})
    contact_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/api/v1/contacts/{contact_id}")
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/api/v1/contacts/{contact_id}")
    assert get_resp.status_code == 404


def test_create_and_list_interactions(client):
    create_resp = client.post("/api/v1/contacts", json={"full_name": "Sam Hiring Manager"})
    contact_id = create_resp.json()["id"]

    interaction_resp = client.post(
        f"/api/v1/contacts/{contact_id}/interactions",
        json={"type": "message", "summary": "Sent intro message on LinkedIn"},
    )
    assert interaction_resp.status_code == 201
    assert interaction_resp.json()["contact_id"] == contact_id

    list_resp = client.get(f"/api/v1/contacts/{contact_id}/interactions")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_interaction_on_missing_contact_404s(client):
    response = client.post(
        "/api/v1/contacts/999999/interactions",
        json={"type": "note", "summary": "test"},
    )
    assert response.status_code == 404


def test_follow_ups_returns_overdue_and_upcoming(client):
    now = datetime.now(timezone.utc)
    overdue_time = (now - timedelta(days=2)).isoformat()
    upcoming_time = (now + timedelta(days=3)).isoformat()
    far_future_time = (now + timedelta(days=30)).isoformat()

    client.post(
        "/api/v1/contacts",
        json={"full_name": "Overdue Contact", "next_follow_up_at": overdue_time},
    )
    client.post(
        "/api/v1/contacts",
        json={"full_name": "Upcoming Contact", "next_follow_up_at": upcoming_time},
    )
    client.post(
        "/api/v1/contacts",
        json={"full_name": "Far Future Contact", "next_follow_up_at": far_future_time},
    )
    client.post("/api/v1/contacts", json={"full_name": "No Follow-up Contact"})

    response = client.get("/api/v1/contacts/follow-ups?days_ahead=7")
    assert response.status_code == 200
    names = [c["full_name"] for c in response.json()]

    assert "Overdue Contact" in names
    assert "Upcoming Contact" in names
    assert "Far Future Contact" not in names
    assert "No Follow-up Contact" not in names
    # Overdue (earlier next_follow_up_at) should sort before upcoming.
    assert names.index("Overdue Contact") < names.index("Upcoming Contact")


def test_networking_message_endpoint_falls_back_to_stub(client):
    response = client.post(
        "/api/v1/ai/networking-message",
        json={
            "contact_name": "Jordan",
            "contact_relationship": "recruiter",
            "purpose": "follow up after a great phone screen",
            "channel": "linkedin",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "stub"
    assert len(body["content"]) > 0
