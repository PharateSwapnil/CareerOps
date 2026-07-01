"""JobProvider for Lever's public Postings API.

Docs: https://github.com/lever/postings-api
Endpoint: GET https://api.lever.co/v0/postings/{site}?mode=json (no auth).
Like Greenhouse, this is per-company (per "site"), so callers supply site
names via JobSearchQuery.board_tokens.
"""
import httpx

from app.providers.job_providers.base import JobProviderError
from app.schemas.job import JobSearchQuery, NormalizedJob

LEVER_POSTINGS_BASE = "https://api.lever.co/v0/postings"

DEFAULT_LEVER_SITES = ["netflix", "lever"]


class LeverJobProvider:
    name = "lever"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_jobs(self, query: JobSearchQuery) -> list[NormalizedJob]:
        sites = query.board_tokens or DEFAULT_LEVER_SITES
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=15.0)

        try:
            results: list[NormalizedJob] = []
            for site in sites:
                try:
                    resp = await client.get(
                        f"{LEVER_POSTINGS_BASE}/{site}", params={"mode": "json"}
                    )
                    resp.raise_for_status()
                except httpx.HTTPError:
                    continue

                for raw in resp.json():
                    results.append(self._normalize(raw, site=site))

            return self._apply_filters(results, query)
        except httpx.HTTPError as exc:
            raise JobProviderError(f"Lever fetch failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

    def _normalize(self, raw: dict, site: str) -> NormalizedJob:
        categories = raw.get("categories", {})
        location = categories.get("location")
        workplace_type = raw.get("workplaceType")
        remote = workplace_type == "remote" or bool(
            location and "remote" in location.lower()
        )

        posted_at = None
        created_at = raw.get("createdAt")
        if isinstance(created_at, (int, float)):
            from datetime import datetime, timezone

            posted_at = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)

        return NormalizedJob(
            title=raw.get("text", ""),
            company_name=site,
            location=location,
            remote=remote,
            description=raw.get("descriptionPlain"),
            url=raw.get("hostedUrl", raw.get("applyUrl", "")),
            source_provider=self.name,
            raw_source_id=str(raw.get("id", "")),
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
