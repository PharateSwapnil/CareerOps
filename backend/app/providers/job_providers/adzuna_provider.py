"""JobProvider for Adzuna's public job search API.

Docs: https://developer.adzuna.com/
Endpoint: GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}
Requires a free app_id + app_key (register at developer.adzuna.com) — this
provider reads them from Settings and returns an empty list if they're not
configured, rather than raising, so a missing key doesn't break app startup
or a multi-provider search.

This is the reference implementation for the "needs a free API key" tier —
Reed, Jooble, Careerjet, and USAJobs follow the same shape (config-driven
key, empty-list fallback when unset) and are queued as fast-follows.
"""
import httpx

from app.core.config import get_settings
from app.providers.job_providers.base import JobProviderError
from app.schemas.job import JobSearchQuery, NormalizedJob

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"
DEFAULT_COUNTRY = "us"


class AdzunaJobProvider:
    name = "adzuna"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_jobs(self, query: JobSearchQuery) -> list[NormalizedJob]:
        settings = get_settings()
        if not settings.adzuna_app_id or not settings.adzuna_app_key:
            # No key configured — return nothing rather than erroring, so
            # this provider can sit in the registry without breaking
            # multi-provider fetches for users who haven't set it up.
            return []

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=15.0)

        try:
            params = {
                "app_id": settings.adzuna_app_id,
                "app_key": settings.adzuna_app_key,
                "results_per_page": query.limit,
                "what": " ".join(query.keywords) if query.keywords else None,
                "where": query.location,
            }
            params = {k: v for k, v in params.items() if v is not None}

            country = (query.board_tokens[0] if query.board_tokens else DEFAULT_COUNTRY)
            resp = await client.get(f"{ADZUNA_BASE}/{country}/search/1", params=params)
            resp.raise_for_status()
            data = resp.json()

            normalized = [self._normalize(raw) for raw in data.get("results", [])]
            return self._apply_filters(normalized, query)
        except httpx.HTTPError as exc:
            raise JobProviderError(f"Adzuna fetch failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

    def _normalize(self, raw: dict) -> NormalizedJob:
        location = (raw.get("location") or {}).get("display_name")
        company = (raw.get("company") or {}).get("display_name", "Unknown")
        return NormalizedJob(
            title=raw.get("title", ""),
            company_name=company,
            location=location,
            remote=bool(location and "remote" in location.lower()),
            description=raw.get("description"),
            url=raw.get("redirect_url", ""),
            salary_min=raw.get("salary_min"),
            salary_max=raw.get("salary_max"),
            salary_currency=raw.get("salary_currency"),
            source_provider=self.name,
            raw_source_id=str(raw.get("id", "")),
            posted_at=raw.get("created"),
        )

    def _apply_filters(
        self, jobs: list[NormalizedJob], query: JobSearchQuery
    ) -> list[NormalizedJob]:
        # Adzuna already filters server-side on `what`/`where`; this is just
        # a safety net for remote_only, which Adzuna doesn't support directly.
        filtered = jobs
        if query.remote_only:
            filtered = [j for j in filtered if j.remote]
        return filtered[: query.limit]
