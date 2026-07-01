"""Every embedding backend implements this Protocol.

Adding a new provider (a different neural embedding API, or a local model
via sentence-transformers) means implementing this interface and registering
it in registry.py - nothing else needs to change, following the same
plugin pattern as JobProvider and LLMProvider.
"""
from typing import Protocol


class EmbeddingProvider(Protocol):
    name: str
    model: str
    dimension: int

    async def embed(self, texts: list[str], input_type: str = "document") -> list[list[float]]:
        """Embed a batch of texts. `input_type` distinguishes queries from
        documents for providers that use different prompting for each
        (Voyage does; providers that don't care can ignore it)."""
        ...


class EmbeddingProviderError(Exception):
    """Raised by a provider when it fails to produce embeddings."""
