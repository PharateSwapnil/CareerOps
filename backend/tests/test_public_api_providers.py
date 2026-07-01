import httpx
import pytest

from app.providers.job_providers.arbeitnow_provider import ArbeitnowJobProvider
from app.providers.job_providers.remotive_provider import RemotiveJobProvider
from app.schemas.job import JobSearchQuery

ARBEITNOW_RESPONSE = {
    "data": [
        {
            "slug": "senior-backend-engineer-acme",
            "company_name": "Acme GmbH",
            "title": "Senior Backend Engineer",
            "description": "Build APIs in Berlin or remote.",
            "remote": True,
            "url": "https://www.arbeitnow.com/jobs/senior-backend-engineer-acme",
            "tags": ["python", "backend"],
            "job_types": ["Full-time"],
            "location": "Berlin, Germany",
            "created_at": 1737000000,
        },
        {
            "slug": "office-manager-acme",
            "company_name": "Acme GmbH",
            "title": "Office Manager",
            "description": "On-site role in Munich.",
            "remote": False,
            "url": "https://www.arbeitnow.com/jobs/office-manager-acme",
            "tags": ["admin"],
            "job_types": ["Full-time"],
            "location": "Munich, Germany",
            "created_at": 1737000000,
        },
    ],
    "links": {},
    "meta": {},
}

REMOTIVE_RESPONSE = {
    "job-count": 2,
    "jobs": [
        {
            "id": 555,
            "url": "https://remotive.com/remote-jobs/555",
            "title": "Data Engineer",
            "company_name": "RemoteCo",
            "category": "Software Development",
            "job_type": "full_time",
            "publication_date": "2026-01-15T12:00:00",
            "candidate_required_location": "Worldwide",
            "salary": "",
            "tags": ["python", "sql"],
            "description": "Work on our data platform.",
        },
        {
            "id": 556,
            "url": "https://remotive.com/remote-jobs/556",
            "title": "Sales Rep",
            "company_name": "RemoteCo",
            "category": "Sales",
            "job_type": "full_time",
            "publication_date": "2026-01-14T12:00:00",
            "candidate_required_location": "USA",
            "salary": "",
            "tags": [],
            "description": "Sell our product.",
        },
    ],
}


def _mock_transport(payload: dict) -> httpx.AsyncBaseTransport:
    class _Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload, request=request)

    return _Transport()


@pytest.mark.asyncio
async def test_arbeitnow_normalize_and_remote_filter():
    client = httpx.AsyncClient(transport=_mock_transport(ARBEITNOW_RESPONSE))
    provider = ArbeitnowJobProvider(client=client)

    jobs = await provider.fetch_jobs(JobSearchQuery(remote_only=True))

    assert len(jobs) == 1
    assert jobs[0].title == "Senior Backend Engineer"
    assert jobs[0].source_provider == "arbeitnow"
    assert jobs[0].raw_source_id == "senior-backend-engineer-acme"

    await client.aclose()


@pytest.mark.asyncio
async def test_arbeitnow_keyword_filter():
    client = httpx.AsyncClient(transport=_mock_transport(ARBEITNOW_RESPONSE))
    provider = ArbeitnowJobProvider(client=client)

    jobs = await provider.fetch_jobs(JobSearchQuery(keywords=["office"]))

    assert len(jobs) == 1
    assert jobs[0].title == "Office Manager"

    await client.aclose()


@pytest.mark.asyncio
async def test_remotive_normalize_all_remote():
    client = httpx.AsyncClient(transport=_mock_transport(REMOTIVE_RESPONSE))
    provider = RemotiveJobProvider(client=client)

    jobs = await provider.fetch_jobs(JobSearchQuery())

    assert len(jobs) == 2
    assert all(j.remote is True for j in jobs)
    assert all(j.source_provider == "remotive" for j in jobs)

    await client.aclose()


@pytest.mark.asyncio
async def test_remotive_location_filter():
    client = httpx.AsyncClient(transport=_mock_transport(REMOTIVE_RESPONSE))
    provider = RemotiveJobProvider(client=client)

    jobs = await provider.fetch_jobs(JobSearchQuery(location="USA"))

    assert len(jobs) == 1
    assert jobs[0].title == "Sales Rep"

    await client.aclose()
