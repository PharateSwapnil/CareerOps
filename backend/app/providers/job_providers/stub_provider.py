"""A fake job provider used for local dev/testing until real integrations
(Greenhouse, Lever, Ashby, RSS...) land in Milestone 2.

Demonstrates the JobProvider interface contributors should follow.
"""
from datetime import datetime, timezone

from app.schemas.job import JobSearchQuery, NormalizedJob


class StubJobProvider:
    name = "stub"

    async def fetch_jobs(self, query: JobSearchQuery) -> list[NormalizedJob]:
        keyword = query.keywords[0] if query.keywords else "Engineer"
        # Vary the id by keyword (not just a fixed "stub-1") so that fetching
        # with two different keywords in the same dev DB doesn't collide via
        # the source_provider+raw_source_id dedupe key and silently return
        # stale data from an earlier search.
        slug = keyword.lower().replace(" ", "-")
        return [
            NormalizedJob(
                title=f"Senior {keyword}",
                company_name="Example Corp",
                location=query.location or "Remote",
                remote=query.remote_only or True,
                description=f"A stub {keyword} posting used for local development.",
                url=f"https://example.com/jobs/{slug}",
                source_provider=self.name,
                raw_source_id=f"stub-{slug}",
                posted_at=datetime.now(timezone.utc),
            )
        ]
