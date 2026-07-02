import pytest


def test_ai_complete_falls_back_to_stub(client):
    """With no ANTHROPIC_API_KEY/GROQ_API_KEY configured in the test env,
    the orchestrator should skip claude/groq and succeed via the stub
    provider rather than erroring."""
    response = client.post(
        "/api/v1/ai/complete",
        json={"messages": [{"role": "user", "content": "Hello there"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "stub"
    assert "Hello there" in body["content"]


def test_resume_optimize_returns_content(client):
    response = client.post(
        "/api/v1/ai/resume-optimize",
        json={
            "resume_text": "Experienced backend engineer, 5 years Python.",
            "job_description": "Looking for a senior Python backend engineer.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "stub"
    assert len(body["content"]) > 0


def test_cover_letter_returns_content(client):
    response = client.post(
        "/api/v1/ai/cover-letter",
        json={
            "resume_text": "Experienced backend engineer, 5 years Python.",
            "job_description": "Looking for a senior Python backend engineer.",
            "company_name": "Acme Corp",
            "tone": "enthusiastic",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "stub"
    assert len(body["content"]) > 0
