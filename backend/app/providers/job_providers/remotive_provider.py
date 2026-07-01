"""JobProvider for Remotive's public remote-jobs API.

Docs: https://remotive.com/api/remote-jobs
Public, no auth required, supports ?search= and ?category= server-side, so
this provider can push keyword filtering to the API instead of doing it
entirely client-side.

Response shape:
    {"job-count": N, "jobs": [{"id", "url", "title", "company_name",
        "category", "job_type", "publication_date",
        "candidate_required_location", "salary", "tags", "description"}]}
"""
from datetime import datetime

import httpx

from app.providers.job_providers.base import JobProviderError
from app.schemas.job import JobSearchQuery, NormalizedJob

REMOTIVE_JOBS_URL = "https://remotive.com/api/remote-jobs"


class RemotiveJobProvider:
    name = "remotive"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_jobs(self, query: JobSearchQuery) -> list[NormalizedJob]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=15.0)

        try:
            params = {}
            if query.keywords:
                # Remotive's `search` param does a substring match server-side;
                # we only send the first keyword and refine the rest client-side.
                params["search"] = query.keywords[0]
            if query.limit:
                params["limit"] = query.limit

            resp = await client.get(REMOTIVE_JOBS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            normalized = [self._normalize(raw) for raw in data.get("jobs", [])]
            return self._apply_filters(normalized, query)
        except httpx.HTTPError as exc:
            raise JobProviderError(f"Remotive fetch failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

    def _normalize(self, raw: dict) -> NormalizedJob:
        location = raw.get("candidate_required_location")
        return NormalizedJob(
            title=raw.get("title", ""),
            company_name=raw.get("company_name", "Unknown"),
            location=location,
            remote=True,  # Remotive is a remote-only job board
            description=raw.get("description"),
            url=raw.get("url", ""),
            source_provider=self.name,
            raw_source_id=str(raw.get("id", "")),
            posted_at=self._parse_date(raw.get("publication_date")),
        )

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _apply_filters(
        self, jobs: list[NormalizedJob], query: JobSearchQuery
    ) -> list[NormalizedJob]:
        filtered = jobs

        # Extra client-side pass for keywords beyond the first (already sent
        # server-side) so a multi-keyword query still narrows results.
        if len(query.keywords) > 1:
            keywords_lower = [k.lower() for k in query.keywords[1:]]
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
