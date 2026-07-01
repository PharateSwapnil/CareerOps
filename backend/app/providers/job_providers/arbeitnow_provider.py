"""JobProvider for Arbeitnow's public Job Board API.

Docs: https://www.arbeitnow.com/api/job-board-api
Public, no auth required. Response shape (JSON:API-ish):
    {"data": [{"slug", "company_name", "title", "description", "remote",
               "url", "tags", "job_types", "location", "created_at"}],
     "links": {...}, "meta": {...}}

No server-side keyword search — filtering happens client-side, same pattern
as the Greenhouse provider.
"""
from datetime import datetime, timezone

import httpx

from app.providers.job_providers.base import JobProviderError
from app.schemas.job import JobSearchQuery, NormalizedJob

ARBEITNOW_JOBS_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowJobProvider:
    name = "arbeitnow"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_jobs(self, query: JobSearchQuery) -> list[NormalizedJob]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=15.0)

        try:
            params = {}
            if query.remote_only:
                params["remote"] = "true"

            resp = await client.get(ARBEITNOW_JOBS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            raw_jobs = data.get("data", data if isinstance(data, list) else [])
            normalized = [self._normalize(raw) for raw in raw_jobs]
            return self._apply_filters(normalized, query)
        except httpx.HTTPError as exc:
            raise JobProviderError(f"Arbeitnow fetch failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

    def _normalize(self, raw: dict) -> NormalizedJob:
        created_at = raw.get("created_at")
        posted_at = None
        if isinstance(created_at, (int, float)):
            posted_at = datetime.fromtimestamp(created_at, tz=timezone.utc)

        return NormalizedJob(
            title=raw.get("title", ""),
            company_name=raw.get("company_name", "Unknown"),
            location=raw.get("location"),
            remote=bool(raw.get("remote", False)),
            description=raw.get("description"),
            url=raw.get("url", ""),
            source_provider=self.name,
            raw_source_id=str(raw.get("slug", raw.get("url", ""))),
            posted_at=posted_at,
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

        if query.remote_only:
            filtered = [j for j in filtered if j.remote]

        if query.location:
            loc_lower = query.location.lower()
            filtered = [
                j for j in filtered if j.location and loc_lower in j.location.lower()
            ]

        return filtered[: query.limit]
