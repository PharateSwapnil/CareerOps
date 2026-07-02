"""ContactEnrichmentProvider backed by Hunter.io's Email Finder API.

Docs: https://hunter.io/api-documentation/v2#email-finder
Endpoint: GET https://api.hunter.io/v2/email-finder?domain=...&first_name=...&last_name=...&api_key=...

WHY THIS EXISTS AS A KEYED API INTEGRATION, NOT A SCRAPER: this project
was asked to scrape LinkedIn's People section for HR/recruiter contact
emails and phone numbers directly. That was declined - LinkedIn doesn't
actually expose personal emails/phones on profiles, so a "LinkedIn
scraper" for this purpose would really mean either violating LinkedIn's
anti-automation terms for something it doesn't even provide, or
aggregating data from many other sources the way Hunter/Apollo/similar
services do - which is a compliance-heavy data business, not a script to
bolt onto a personal project. Hunter.io already does that aggregation
legitimately, under its own terms and data-source agreements. Using their
API with the user's own key keeps CareerOps++ out of the business of
harvesting personal contact data itself.

Only finds a work email given a name + company domain - no phone numbers,
no other personal data, and it requires the user's own paid/free-tier API
key (nothing works without one, and the feature degrades to "not found"
rather than erroring if unconfigured, same pattern as Adzuna/Voyage).
"""
import httpx

from app.core.config import get_settings
from app.providers.contact_enrichment_providers.base import (
    ContactEnrichmentProviderError,
    EmailLookupResult,
)

HUNTER_EMAIL_FINDER_URL = "https://api.hunter.io/v2/email-finder"


class HunterEmailProvider:
    name = "hunter"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def find_email(
        self, first_name: str, last_name: str, domain: str
    ) -> EmailLookupResult:
        settings = get_settings()
        if not settings.hunter_api_key:
            return EmailLookupResult(found=False)

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=15.0)

        try:
            resp = await client.get(
                HUNTER_EMAIL_FINDER_URL,
                params={
                    "domain": domain,
                    "first_name": first_name,
                    "last_name": last_name,
                    "api_key": settings.hunter_api_key,
                },
            )
            if resp.status_code == 404:
                return EmailLookupResult(found=False)
            resp.raise_for_status()
            data = resp.json().get("data", {})

            email = data.get("email")
            if not email:
                return EmailLookupResult(found=False)

            return EmailLookupResult(found=True, email=email, confidence=data.get("score"))
        except httpx.HTTPError as exc:
            raise ContactEnrichmentProviderError(f"Hunter lookup failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()
