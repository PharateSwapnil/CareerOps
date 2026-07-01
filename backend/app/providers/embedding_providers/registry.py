"""Central registry of available EmbeddingProvider implementations."""
from app.providers.embedding_providers.base import EmbeddingProvider
from app.providers.embedding_providers.hashing_provider import HashingEmbeddingProvider
from app.providers.embedding_providers.voyage_provider import VoyageEmbeddingProvider

_REGISTRY: dict[str, EmbeddingProvider] = {
    "hashing": HashingEmbeddingProvider(),
    "voyage": VoyageEmbeddingProvider(),
}


def get_provider(name: str) -> EmbeddingProvider:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown embedding provider: {name}") from exc


def list_providers() -> list[str]:
    return list(_REGISTRY.keys())
