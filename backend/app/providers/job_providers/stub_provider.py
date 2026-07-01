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
        return [
            NormalizedJob(
                title=f"Senior {keyword}",
                company_name="Example Corp",
                location=query.location or "Remote",
                remote=query.remote_only or True,
                description=f"A stub {keyword} posting used for local development.",
                url="https://example.com/jobs/1",
                source_provider=self.name,
                raw_source_id="stub-1",
                posted_at=datetime.now(timezone.utc),
            )
        ]
