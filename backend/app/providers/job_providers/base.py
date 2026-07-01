"""Every job source integration implements this Protocol.

Adding a new provider (e.g. Lever, Ashby, a company career page scraper) means:
  1. Create providers/job_providers/<name>.py implementing JobProvider
  2. Register it in providers/job_providers/registry.py
No other code should need to change — routes and services depend only on this
interface, never on a concrete provider.
"""
from typing import Protocol

from app.schemas.job import JobSearchQuery, NormalizedJob


class JobProvider(Protocol):
    name: str

    async def fetch_jobs(self, query: JobSearchQuery) -> list[NormalizedJob]:
        """Fetch postings from this source and return them already normalized."""
        ...


class JobProviderError(Exception):
    """Raised by a provider when it fails to fetch/parse postings."""
