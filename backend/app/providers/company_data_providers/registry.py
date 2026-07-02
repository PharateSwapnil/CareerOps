"""Central registry of available CompanyDataProvider implementations."""
from app.providers.company_data_providers.base import CompanyDataProvider
from app.providers.company_data_providers.wikipedia_provider import WikipediaCompanyProvider

_REGISTRY: dict[str, CompanyDataProvider] = {
    "wikipedia": WikipediaCompanyProvider(),
}


def get_provider(name: str) -> CompanyDataProvider:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown company data provider: {name}") from exc


def list_providers() -> list[str]:
    return list(_REGISTRY.keys())
