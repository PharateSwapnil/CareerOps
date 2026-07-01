"""Every LLM backend integration implements this Protocol.

Milestone 3 adds a fallback orchestrator that tries providers in priority order
and moves to the next one on LLMProviderError/timeout.
"""
from typing import Protocol

from app.schemas.llm import LLMRequest, LLMResponse


class LLMProvider(Protocol):
    name: str

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Run a completion. Raise LLMProviderError on failure."""
        ...


class LLMProviderError(Exception):
    """Raised by a provider when it fails to produce a completion."""
