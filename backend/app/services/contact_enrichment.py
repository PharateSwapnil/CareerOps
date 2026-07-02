"""Orchestrates finding a professional email for a Contact: splits their
name, looks up their linked Company's domain, calls a
ContactEnrichmentProvider, and safely updates Contact.email (never
overwriting an email the user already entered themselves).
"""
from urllib.parse import urlparse

from sqlmodel import Session

from app.models.company import Company
from app.models.contact import Contact
from app.providers.contact_enrichment_providers.base import (
    ContactEnrichmentProvider,
    ContactEnrichmentProviderError,
    EmailLookupResult,
)


def _extract_domain(website: str) -> str:
    """Company.website might be stored as a bare domain or a full URL -
    normalize either into just the domain Hunter's API expects."""
    if "://" not in website:
        website = f"https://{website}"
    return urlparse(website).netloc.removeprefix("www.")


def _split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(" ")
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[0], parts[-1]


async def enrich_contact_email(
    session: Session, contact: Contact, provider: ContactEnrichmentProvider
) -> EmailLookupResult:
    """Attempts to find and fill in `contact.email`. Returns the lookup
    result regardless of outcome (found or not) so the caller/UI can show
    what happened rather than silently doing nothing.

    Deliberately does NOT overwrite an email the user already entered -
    enrichment only fills a gap, never replaces user-provided data.
    """
    if contact.email:
        return EmailLookupResult(found=True, email=contact.email, confidence=None)

    if not contact.company_id:
        return EmailLookupResult(found=False)

    company = session.get(Company, contact.company_id)
    if company is None or not company.website:
        return EmailLookupResult(found=False)

    domain = _extract_domain(company.website)
    first_name, last_name = _split_name(contact.full_name)

    try:
        result = await provider.find_email(first_name, last_name, domain)
    except ContactEnrichmentProviderError:
        return EmailLookupResult(found=False)

    if result.found and result.email:
        contact.email = result.email
        session.add(contact)
        session.commit()
        session.refresh(contact)

    return result
