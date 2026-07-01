"""JobProvider for Jobicy's public remote-jobs API.

Endpoint: GET https://jobicy.com/api/v2/remote-jobs (no auth). Supports
?count=, ?tag=, ?geo=, ?industry= server-side.
"""
import httpx

from app.providers.job_providers.base import JobProviderError
from app.schemas.job import JobSearchQuery, NormalizedJob

JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"


class JobicyJobProvider:
    name = "jobicy"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_jobs(self, query: JobSearchQuery) -> list[NormalizedJob]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=15.0)

        try:
            params = {"count": max(query.limit, 20)}
            resp = await client.get(JOBICY_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            normalized = [self._normalize(raw) for raw in data.get("jobs", [])]
            return self._apply_filters(normalized, query)
        except httpx.HTTPError as exc:
            raise JobProviderError(f"Jobicy fetch failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

    def _normalize(self, raw: dict) -> NormalizedJob:
        return NormalizedJob(
            title=raw.get("jobTitle", ""),
            company_name=raw.get("companyName", "Unknown"),
            location=raw.get("jobGeo"),
            remote=True,  # Jobicy is a remote-only board
            description=raw.get("jobExcerpt") or raw.get("jobDescription"),
            url=raw.get("url", ""),
            salary_min=raw.get("annualSalaryMin"),
            salary_max=raw.get("annualSalaryMax"),
            source_provider=self.name,
            raw_source_id=str(raw.get("id", "")),
            posted_at=raw.get("pubDate"),
        )

    def _apply_filters(
        self, jobs: list[NormalizedJob], query: JobSearchQuery
    ) -> list[NormalizedJob]:
        filtered = jobs
        if query.keywords:
            keywords_lower = [k.lower() for k in query.keywords]
            filtered = [
                j
                for j in filtered
                if any(
                    kw in j.title.lower() or kw in (j.description or "").lower()
                    for kw in keywords_lower
                )
            ]
        if query.location:
            loc_lower = query.location.lower()
            filtered = [
                j for j in filtered if j.location and loc_lower in j.location.lower()
            ]
        return filtered[: query.limit]
