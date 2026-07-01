"""Central registry of available JobProvider implementations.

Milestone 2 will add real providers here (Greenhouse, Lever, Ashby, RSS...).
"""
from app.providers.job_providers.base import JobProvider
from app.providers.job_providers.stub_provider import StubJobProvider

_REGISTRY: dict[str, JobProvider] = {
    "stub": StubJobProvider(),
}


def get_provider(name: str) -> JobProvider:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown job provider: {name}") from exc


def list_providers() -> list[str]:
    return list(_REGISTRY.keys())
