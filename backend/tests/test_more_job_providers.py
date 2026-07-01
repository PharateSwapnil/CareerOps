import httpx
import pytest

from app.providers.job_providers.adzuna_provider import AdzunaJobProvider
from app.providers.job_providers.ashby_provider import AshbyJobProvider
from app.providers.job_providers.jobicy_provider import JobicyJobProvider
from app.providers.job_providers.lever_provider import LeverJobProvider
from app.providers.job_providers.remoteok_provider import RemoteOKJobProvider
from app.providers.job_providers.weworkremotely_provider import WeWorkRemotelyJobProvider
from app.schemas.job import JobSearchQuery


def _mock_transport(payload, content_type="json"):
    class _Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if content_type == "json":
                return httpx.Response(200, json=payload, request=request)
            return httpx.Response(200, text=payload, request=request)

    return _Transport()


REMOTEOK_RESPONSE = [
    {"legal": "By using this API you agree to..."},
    {
        "id": "111",
        "position": "Frontend Engineer",
        "company": "RemoteCo",
        "location": "Worldwide",
        "description": "Build UIs.",
        "url": "https://remoteok.com/remote-jobs/111",
        "date": "2026-01-01T00:00:00",
    },
]


@pytest.mark.asyncio
async def test_remoteok_skips_legal_notice_row():
    client = httpx.AsyncClient(transport=_mock_transport(REMOTEOK_RESPONSE))
    provider = RemoteOKJobProvider(client=client)

    jobs = await provider.fetch_jobs(JobSearchQuery())

    assert len(jobs) == 1
    assert jobs[0].title == "Frontend Engineer"
    assert jobs[0].remote is True

    await client.aclose()


LEVER_RESPONSE = [
    {
        "id": "abc123",
        "text": "Backend Engineer",
        "categories": {"location": "Remote - US", "team": "Engineering"},
        "descriptionPlain": "Work on infra.",
        "hostedUrl": "https://jobs.lever.co/acme/abc123",
        "createdAt": 1737000000000,
        "workplaceType": "remote",
    }
]


@pytest.mark.asyncio
async def test_lever_normalize():
    client = httpx.AsyncClient(transport=_mock_transport(LEVER_RESPONSE))
    provider = LeverJobProvider(client=client)

    jobs = await provider.fetch_jobs(JobSearchQuery(board_tokens=["acme"]))

    assert len(jobs) == 1
    assert jobs[0].title == "Backend Engineer"
    assert jobs[0].company_name == "acme"
    assert jobs[0].remote is True

    await client.aclose()


ASHBY_RESPONSE = {
    "jobs": [
        {
            "id": "j1",
            "title": "Platform Engineer",
            "location": "Remote",
            "isRemote": True,
            "descriptionPlain": "Own the platform.",
            "jobUrl": "https://jobs.ashbyhq.com/acme/j1",
            "publishedAt": "2026-01-01T00:00:00Z",
        }
    ]
}


@pytest.mark.asyncio
async def test_ashby_normalize():
    client = httpx.AsyncClient(transport=_mock_transport(ASHBY_RESPONSE))
    provider = AshbyJobProvider(client=client)

    jobs = await provider.fetch_jobs(JobSearchQuery(board_tokens=["acme"]))

    assert len(jobs) == 1
    assert jobs[0].title == "Platform Engineer"
    assert jobs[0].remote is True

    await client.aclose()


JOBICY_RESPONSE = {
    "jobs": [
        {
            "id": 42,
            "jobTitle": "DevOps Engineer",
            "companyName": "CloudCo",
            "jobGeo": "Europe",
            "jobExcerpt": "Manage our infra.",
            "url": "https://jobicy.com/jobs/42",
            "pubDate": "2026-01-01T00:00:00",
        }
    ]
}


@pytest.mark.asyncio
async def test_jobicy_all_remote():
    client = httpx.AsyncClient(transport=_mock_transport(JOBICY_RESPONSE))
    provider = JobicyJobProvider(client=client)

    jobs = await provider.fetch_jobs(JobSearchQuery())

    assert len(jobs) == 1
    assert jobs[0].remote is True
    assert jobs[0].title == "DevOps Engineer"

    await client.aclose()


WWR_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<item>
<title>Acme Corp: Senior Python Developer</title>
<link>https://weworkremotely.com/remote-jobs/acme-corp-senior-python-developer</link>
<description>&lt;p&gt;We need a Python developer.&lt;/p&gt;</description>
<pubDate>Thu, 01 Jan 2026 12:00:00 +0000</pubDate>
<guid>https://weworkremotely.com/remote-jobs/acme-corp-senior-python-developer</guid>
</item>
</channel>
</rss>"""


@pytest.mark.asyncio
async def test_weworkremotely_parses_rss():
    client = httpx.AsyncClient(transport=_mock_transport(WWR_RSS, content_type="text"))
    provider = WeWorkRemotelyJobProvider(client=client)

    jobs = await provider.fetch_jobs(JobSearchQuery(board_tokens=["remote-programming-jobs"]))

    assert len(jobs) == 1
    assert jobs[0].title == "Senior Python Developer"
    assert jobs[0].company_name == "Acme Corp"
    assert jobs[0].remote is True
    assert "Python developer" in (jobs[0].description or "")

    await client.aclose()


@pytest.mark.asyncio
async def test_adzuna_returns_empty_without_api_key():
    """Without ADZUNA_APP_ID/APP_KEY configured, the provider should return
    an empty list rather than error, so it's safe to leave in the registry."""
    provider = AdzunaJobProvider()
    jobs = await provider.fetch_jobs(JobSearchQuery(keywords=["engineer"]))
    assert jobs == []
