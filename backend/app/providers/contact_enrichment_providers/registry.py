"""Central registry of available ContactEnrichmentProvider implementations."""
from app.providers.contact_enrichment_providers.base import ContactEnrichmentProvider
from app.providers.contact_enrichment_providers.hunter_provider import HunterEmailProvider

_REGISTRY: dict[str, ContactEnrichmentProvider] = {
    "hunter": HunterEmailProvider(),
}


def get_provider(name: str) -> ContactEnrichmentProvider:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown contact enrichment provider: {name}") from exc


def list_providers() -> list[str]:
    return list(_REGISTRY.keys())
