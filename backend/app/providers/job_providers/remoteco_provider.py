"""JobProvider that scrapes Remote.co's public, server-rendered job listing
pages (no login wall, no JS-rendering requirement, no anti-bot challenge
observed — unlike Wellfound or NoDesk, see notes below).

Remote.co has no public API, so this anchors on the one structural element
that's very unlikely to change: job detail links follow a stable
`/job-details/{slug}` URL pattern. Extraction walks outward from each such
link to pick up the nearby company name, location, and remote-type text
rather than depending on exact CSS class names, which are far more likely to
shift between deploys.

CAVEAT: written against markdown-rendered page content (via web fetch during
development), not raw HTML source, so exact DOM nesting is inferred rather
than confirmed. The extraction is deliberately tolerant (falls back to "" /
None rather than raising) so a shifted layout degrades gracefully instead of
crashing — but this should get a live smoke test before being relied on.

Two sibling sources requested alongside this one were intentionally NOT
built the same way:
- Wellfound: protected by active anti-bot measures (DataDome); scraping
  around that would mean defeating a platform's bot protection, which this
  project treats as off-limits regardless of framing.
- NoDesk: job listings are loaded client-side via JavaScript after page
  load, so a plain HTTP GET (no browser engine) returns an empty listing —
  it needs headless-browser infrastructure (Playwright), which belongs with
  Milestone 8's browser automation work, not this scraper pattern.
"""
import re

import httpx
from bs4 import BeautifulSoup

from app.providers.job_providers.base import JobProviderError
from app.schemas.job import JobSearchQuery, NormalizedJob

REMOTE_CO_JOBS_URL = "https://remote.co/remote-jobs"
JOB_LINK_PATTERN = re.compile(r"/job-details/")


class RemoteCoJobProvider:
    name = "remoteco"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_jobs(self, query: JobSearchQuery) -> list[NormalizedJob]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=15.0, headers={"User-Agent": "Mozilla/5.0 (compatible; CareerOpsPlusPlus/0.1)"}
        )

        try:
            resp = await client.get(REMOTE_CO_JOBS_URL)
            resp.raise_for_status()
            jobs = self._parse_html(resp.text)
            return self._apply_filters(jobs, query)
        except httpx.HTTPError as exc:
            raise JobProviderError(f"Remote.co fetch failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

    def _parse_html(self, html: str) -> list[NormalizedJob]:
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[NormalizedJob] = []
        seen_urls: set[str] = set()

        for link in soup.find_all("a", href=JOB_LINK_PATTERN):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or not href or href in seen_urls:
                continue
            seen_urls.add(href)

            url = href if href.startswith("http") else f"https://remote.co{href}"

            # Walk up to a reasonably-sized container and look for nearby
            # metadata rather than assuming an exact tag/class.
            container = link.find_parent(["li", "div", "article"]) or link.parent
            company = "Unknown"
            location = None
            remote_label = None

            if container is not None:
                h4 = container.find_next("h4")
                if h4 is not None:
                    company = h4.get_text(strip=True) or "Unknown"
                    location_el = h4.find_next(["div", "p", "span"])
                    if location_el is not None:
                        loc_text = location_el.get_text(strip=True)
                        if loc_text and len(loc_text) < 150:
                            location = loc_text

                for li in container.find_all("li"):
                    li_text = li.get_text(strip=True)
                    if "remote" in li_text.lower():
                        remote_label = li_text
                        break

            remote = bool(remote_label) and "no remote" not in (remote_label or "").lower()

            jobs.append(
                NormalizedJob(
                    title=title,
                    company_name=company,
                    location=location,
                    remote=remote,
                    description=None,  # full description requires a second
                    # page fetch per job; deferred to keep listing fetch fast.
                    url=url,
                    source_provider=self.name,
                    raw_source_id=href.rstrip("/").rsplit("/", 1)[-1],
                    posted_at=None,
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
                j for j in filtered if any(kw in j.title.lower() for kw in keywords_lower)
            ]
        if query.remote_only:
            filtered = [j for j in filtered if j.remote]
        return filtered[: query.limit]
