"""Every professional-email lookup source implements this Protocol.

Deliberately scoped to email lookup only - not phone numbers, not any
other personal data, and never scraping a social platform directly. See
providers/contact_enrichment_providers/hunter_provider.py's docstring for
why this exists as a keyed third-party API integration rather than an
in-house scraper.
"""
from typing import Protocol

from pydantic import BaseModel


class EmailLookupResult(BaseModel):
    found: bool
    email: str | None = None
    confidence: int | None = None  # 0-100, provider's own confidence score


class ContactEnrichmentProvider(Protocol):
    name: str

    async def find_email(
        self, first_name: str, last_name: str, domain: str
    ) -> EmailLookupResult:
        """Look up a likely professional email for someone at `domain`.
        Returns found=False (not an exception) when nothing matches."""
        ...


class ContactEnrichmentProviderError(Exception):
    """Raised only for actual failures (network error, malformed response) -
    not for "no email found", which is EmailLookupResult(found=False)."""
