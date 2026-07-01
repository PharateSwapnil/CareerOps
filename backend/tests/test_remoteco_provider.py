import httpx
import pytest

from app.providers.job_providers.remoteco_provider import RemoteCoJobProvider
from app.schemas.job import JobSearchQuery

# Synthetic HTML modeled on the structure observed on remote.co/remote-jobs
# (job-details link -> ul of tags -> h4 company -> location text).
REMOTE_CO_HTML = """
<html><body>
<div class="job-card">
  <h3><a href="/job-details/senior-associate-product-compliance-123">Senior Associate, Product Compliance</a></h3>
  <ul>
    <li>Hybrid Remote Work</li>
    <li>Full-Time</li>
    <li>$101,000 - $140,000 Annually</li>
  </ul>
  <h4>Chime Financial, Inc.</h4>
  <div>Hybrid Remote in Chicago, IL, New York, NY</div>
</div>
<div class="job-card">
  <h3><a href="/job-details/senior-financial-partnerships-manager-456">Senior Financial Partnerships Manager</a></h3>
  <ul>
    <li>100% Remote Work</li>
    <li>Full-Time</li>
  </ul>
  <h4>Mercury Banking</h4>
  <div>Remote, US National</div>
</div>
<div class="job-card">
  <h3><a href="/job-details/note-taker-789">Note Taker</a></h3>
  <ul>
    <li>No Remote Work</li>
    <li>Part-Time</li>
  </ul>
  <h4>City Colleges of Chicago</h4>
  <div>Chicago, IL</div>
</div>
</body></html>
"""


def _mock_transport() -> httpx.AsyncBaseTransport:
    class _Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text=REMOTE_CO_HTML, request=request)

    return _Transport()


@pytest.mark.asyncio
async def test_remoteco_parses_job_cards():
    client = httpx.AsyncClient(transport=_mock_transport())
    provider = RemoteCoJobProvider(client=client)

    jobs = await provider.fetch_jobs(JobSearchQuery())

    assert len(jobs) == 3
    titles = {j.title for j in jobs}
    assert "Senior Associate, Product Compliance" in titles
    assert all(j.source_provider == "remoteco" for j in jobs)

    await client.aclose()


@pytest.mark.asyncio
async def test_remoteco_remote_only_filter():
    client = httpx.AsyncClient(transport=_mock_transport())
    provider = RemoteCoJobProvider(client=client)

    jobs = await provider.fetch_jobs(JobSearchQuery(remote_only=True))

    # "No Remote Work" listing should be excluded; hybrid/100% remote kept.
    assert len(jobs) == 2
    assert all(j.remote for j in jobs)

    await client.aclose()


@pytest.mark.asyncio
async def test_remoteco_company_and_location_extraction():
    client = httpx.AsyncClient(transport=_mock_transport())
    provider = RemoteCoJobProvider(client=client)

    jobs = await provider.fetch_jobs(JobSearchQuery())
    mercury_job = next(j for j in jobs if "Financial Partnerships" in j.title)

    assert mercury_job.company_name == "Mercury Banking"
    assert mercury_job.location == "Remote, US National"

    await client.aclose()
