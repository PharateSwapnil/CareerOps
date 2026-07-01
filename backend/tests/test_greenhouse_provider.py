import httpx
import pytest

from app.providers.job_providers.greenhouse_provider import GreenhouseJobProvider
from app.schemas.job import JobSearchQuery

SAMPLE_RESPONSE = {
    "jobs": [
        {
            "id": 1001,
            "title": "Senior Backend Engineer",
            "updated_at": "2026-01-14T10:55:28-05:00",
            "location": {"name": "Remote - US"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/1001",
            "content": "<p>Build <b>great</b> things.</p>",
        },
        {
            "id": 1002,
            "title": "Product Designer",
            "updated_at": "2026-01-10T09:00:00-05:00",
            "location": {"name": "New York, NY"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/1002",
            "content": "<p>Design things.</p>",
        },
    ]
}


class _MockTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_RESPONSE, request=request)


@pytest.mark.asyncio
async def test_greenhouse_fetch_and_normalize():
    client = httpx.AsyncClient(transport=_MockTransport())
    provider = GreenhouseJobProvider(client=client)

    jobs = await provider.fetch_jobs(JobSearchQuery(board_tokens=["acme"]))

    assert len(jobs) == 2
    titles = {j.title for j in jobs}
    assert titles == {"Senior Backend Engineer", "Product Designer"}

    backend_job = next(j for j in jobs if j.title == "Senior Backend Engineer")
    assert backend_job.remote is True
    assert backend_job.source_provider == "greenhouse"
    assert backend_job.raw_source_id == "1001"
    assert "<b>" not in (backend_job.description or "")

    await client.aclose()


@pytest.mark.asyncio
async def test_greenhouse_keyword_filter():
    client = httpx.AsyncClient(transport=_MockTransport())
    provider = GreenhouseJobProvider(client=client)

    jobs = await provider.fetch_jobs(
        JobSearchQuery(board_tokens=["acme"], keywords=["designer"])
    )

    assert len(jobs) == 1
    assert jobs[0].title == "Product Designer"

    await client.aclose()


@pytest.mark.asyncio
async def test_greenhouse_remote_only_filter():
    client = httpx.AsyncClient(transport=_MockTransport())
    provider = GreenhouseJobProvider(client=client)

    jobs = await provider.fetch_jobs(
        JobSearchQuery(board_tokens=["acme"], remote_only=True)
    )

    assert len(jobs) == 1
    assert jobs[0].title == "Senior Backend Engineer"

    await client.aclose()
