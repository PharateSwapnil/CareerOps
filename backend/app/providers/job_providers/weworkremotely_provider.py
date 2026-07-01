"""JobProvider for We Work Remotely's public RSS feeds.

WWR doesn't have a JSON API — it publishes per-category RSS feeds, e.g.
https://weworkremotely.com/categories/remote-programming-jobs.rss
Item titles are formatted as "Company: Job Title".
"""
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import httpx

from app.providers.job_providers.base import JobProviderError
from app.schemas.job import JobSearchQuery, NormalizedJob

WWR_RSS_BASE = "https://weworkremotely.com/categories"

DEFAULT_CATEGORIES = [
    "remote-programming-jobs",
    "remote-design-jobs",
    "remote-product-jobs",
]

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html: str | None) -> str | None:
    if not html:
        return None
    return _TAG_RE.sub(" ", html).strip()


class WeWorkRemotelyJobProvider:
    name = "weworkremotely"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_jobs(self, query: JobSearchQuery) -> list[NormalizedJob]:
        # Reuse board_tokens as an override for which RSS categories to pull.
        categories = query.board_tokens or DEFAULT_CATEGORIES
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=15.0)

        try:
            results: list[NormalizedJob] = []
            for category in categories:
                try:
                    resp = await client.get(f"{WWR_RSS_BASE}/{category}.rss")
                    resp.raise_for_status()
                except httpx.HTTPError:
                    continue

                results.extend(self._parse_rss(resp.text))

            return self._apply_filters(results, query)
        except httpx.HTTPError as exc:
            raise JobProviderError(f"WeWorkRemotely fetch failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

    def _parse_rss(self, xml_text: str) -> list[NormalizedJob]:
        jobs: list[NormalizedJob] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return jobs

        for item in root.findall(".//item"):
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            pubdate_el = item.find("pubDate")
            guid_el = item.find("guid")

            raw_title = (title_el.text or "").strip() if title_el is not None else ""
            company, _, job_title = raw_title.partition(": ")
            if not job_title:
                job_title, company = company, "Unknown"

            posted_at = None
            if pubdate_el is not None and pubdate_el.text:
                try:
                    posted_at = parsedate_to_datetime(pubdate_el.text.strip())
                except (TypeError, ValueError):
                    posted_at = None

            jobs.append(
                NormalizedJob(
                    title=job_title or raw_title,
                    company_name=company or "Unknown",
                    location=None,
                    remote=True,
                    description=_strip_html(desc_el.text if desc_el is not None else None),
                    url=(link_el.text or "").strip() if link_el is not None else "",
                    source_provider=self.name,
                    raw_source_id=(
                        (guid_el.text or link_el.text or raw_title).strip()
                        if (guid_el is not None or link_el is not None)
                        else raw_title
                    ),
                    posted_at=posted_at,
                )
            )
        return jobs

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
