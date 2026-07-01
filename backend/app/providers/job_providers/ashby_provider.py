"""JobProvider for Ashby's public Job Board API.

Endpoint: GET https://api.ashbyhq.com/posting-api/job-board/{job_board_name}
(no auth). Like Greenhouse/Lever, per-organization — callers supply org
names via JobSearchQuery.board_tokens.

NOTE: field names below are based on Ashby's publicly documented posting-api
shape at the time this was written, but weren't verified against a live
response in this dev sandbox (network egress here doesn't reach
api.ashbyhq.com). The parsing is defensive (.get() with fallbacks) so a
missing/renamed field degrades gracefully rather than crashing — but treat
this provider as needing a real smoke test before relying on it in
production.
"""
import httpx

from app.providers.job_providers.base import JobProviderError
from app.schemas.job import JobSearchQuery, NormalizedJob

ASHBY_BASE = "https://api.ashbyhq.com/posting-api/job-board"

DEFAULT_ASHBY_ORGS = ["ashby"]


class AshbyJobProvider:
    name = "ashby"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_jobs(self, query: JobSearchQuery) -> list[NormalizedJob]:
        orgs = query.board_tokens or DEFAULT_ASHBY_ORGS
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=15.0)

        try:
            results: list[NormalizedJob] = []
            for org in orgs:
                try:
                    resp = await client.get(f"{ASHBY_BASE}/{org}")
                    resp.raise_for_status()
                except httpx.HTTPError:
                    continue

                data = resp.json()
                for raw in data.get("jobs", []):
                    results.append(self._normalize(raw, org=org))

            return self._apply_filters(results, query)
        except httpx.HTTPError as exc:
            raise JobProviderError(f"Ashby fetch failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

    def _normalize(self, raw: dict, org: str) -> NormalizedJob:
        location = raw.get("location") or raw.get("locationName")
        remote = bool(raw.get("isRemote")) or bool(
            location and "remote" in str(location).lower()
        )
        return NormalizedJob(
            title=raw.get("title", ""),
            company_name=org,
            location=location,
            remote=remote,
            description=raw.get("descriptionPlain") or raw.get("description"),
            url=raw.get("jobUrl") or raw.get("applyUrl", ""),
            source_provider=self.name,
            raw_source_id=str(raw.get("id", "")),
            posted_at=raw.get("publishedAt"),
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
        return filtered[: query.limit]
