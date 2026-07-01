"""JobProvider for Greenhouse's public Job Board API.

Docs: https://developers.greenhouse.io/job-board.html
Endpoint used: GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true

This endpoint is public (no auth required) and returns every published posting
for a given company's board — it does not support server-side keyword search,
so keyword/location/remote filtering happens client-side after fetching.
"""
import re

import httpx

from app.providers.job_providers.base import JobProviderError
from app.schemas.job import JobSearchQuery, NormalizedJob

GREENHOUSE_BOARDS_BASE = "https://boards-api.greenhouse.io/v1/boards"

# A handful of real, public Greenhouse boards used as a sane default when the
# caller doesn't specify board_tokens, so the provider is usable out of the box.
DEFAULT_BOARD_TOKENS = ["stripe", "airbnb", "asana"]

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html: str | None) -> str | None:
    if not html:
        return None
    return _TAG_RE.sub(" ", html).strip()


class GreenhouseJobProvider:
    name = "greenhouse"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_jobs(self, query: JobSearchQuery) -> list[NormalizedJob]:
        board_tokens = query.board_tokens or DEFAULT_BOARD_TOKENS
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=15.0)

        try:
            results: list[NormalizedJob] = []
            for token in board_tokens:
                try:
                    resp = await client.get(
                        f"{GREENHOUSE_BOARDS_BASE}/{token}/jobs",
                        params={"content": "true"},
                    )
                    resp.raise_for_status()
                except httpx.HTTPError:
                    # One bad/unknown board token shouldn't fail the whole fetch.
                    continue

                data = resp.json()
                for raw in data.get("jobs", []):
                    results.append(self._normalize(raw, board_token=token))

            return self._apply_filters(results, query)
        except httpx.HTTPError as exc:
            raise JobProviderError(f"Greenhouse fetch failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

    def _normalize(self, raw: dict, board_token: str) -> NormalizedJob:
        location = (raw.get("location") or {}).get("name")
        remote = bool(location and "remote" in location.lower())
        return NormalizedJob(
            title=raw["title"],
            company_name=board_token,  # Greenhouse job payloads don't include a
            # display company name; the board token is the best identifier
            # available without a second API call.
            location=location,
            remote=remote,
            description=_strip_html(raw.get("content")),
            url=raw.get("absolute_url", ""),
            source_provider=self.name,
            raw_source_id=str(raw["id"]),
            posted_at=raw.get("updated_at"),
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
