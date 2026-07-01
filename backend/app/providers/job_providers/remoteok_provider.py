"""JobProvider for RemoteOK's public JSON API.

Docs/endpoint: GET https://remoteok.com/api (no auth). Returns a JSON array
whose first element is a legal/attribution notice (not a job) — must be
skipped. RemoteOK's terms require crediting them and linking directly back
to the job's RemoteOK URL, which `NormalizedJob.url` already does.
"""
import httpx

from app.providers.job_providers.base import JobProviderError
from app.schemas.job import JobSearchQuery, NormalizedJob

REMOTEOK_URL = "https://remoteok.com/api"


class RemoteOKJobProvider:
    name = "remoteok"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_jobs(self, query: JobSearchQuery) -> list[NormalizedJob]:
        owns_client = self._client is None
        # RemoteOK blocks requests without a browser-like User-Agent.
        client = self._client or httpx.AsyncClient(
            timeout=15.0, headers={"User-Agent": "CareerOpsPlusPlus/0.1 (+job-search-tool)"}
        )

        try:
            resp = await client.get(REMOTEOK_URL)
            resp.raise_for_status()
            data = resp.json()

            # First entry is a legal notice dict without a "position" field.
            raw_jobs = [j for j in data if isinstance(j, dict) and "position" in j]
            normalized = [self._normalize(raw) for raw in raw_jobs]
            return self._apply_filters(normalized, query)
        except httpx.HTTPError as exc:
            raise JobProviderError(f"RemoteOK fetch failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

    def _normalize(self, raw: dict) -> NormalizedJob:
        return NormalizedJob(
            title=raw.get("position", ""),
            company_name=raw.get("company", "Unknown"),
            location=raw.get("location") or "Remote",
            remote=True,
            description=raw.get("description"),
            url=raw.get("url", f"https://remoteok.com/remote-jobs/{raw.get('id', '')}"),
            salary_min=raw.get("salary_min"),
            salary_max=raw.get("salary_max"),
            source_provider=self.name,
            raw_source_id=str(raw.get("id", raw.get("slug", ""))),
            posted_at=raw.get("date"),
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
        return filtered[: query.limit]
