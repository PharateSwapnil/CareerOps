"""Every public company-data source implements this Protocol.

Milestone 7 ships one real provider (Wikipedia). Adding another (Crunchbase,
a company's own careers page, GitHub org info, etc.) means implementing this
interface and registering it - same plugin pattern as job/LLM/embedding
providers.
"""
from typing import Protocol

from pydantic import BaseModel


class CompanyDataResult(BaseModel):
    found: bool
    summary_extract: str | None = None  # raw factual text, not AI-generated
    source_url: str | None = None


class CompanyDataProvider(Protocol):
    name: str

    async def fetch(self, company_name: str) -> CompanyDataResult:
        """Look up public data for `company_name`. Returns found=False
        (not an exception) when nothing matches - a missing lookup is a
        normal, expected outcome for an obscure or misspelled company name,
        not an error condition."""
        ...


class CompanyDataProviderError(Exception):
    """Raised only for actual failures (network error, malformed response) -
    not for "no data found", which is CompanyDataResult(found=False)."""
