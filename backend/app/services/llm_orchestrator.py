"""Fallback orchestrator: tries LLM providers in a configured priority order,
moving to the next on failure (missing key, HTTP error, timeout) rather than
failing the whole request. This is what makes CareerOps++'s AI features
resilient to any single provider being down or unconfigured.
"""
import asyncio
import logging

from app.core.config import get_settings
from app.providers.llm_providers.base import LLMProviderError
from app.providers.llm_providers.registry import get_provider
from app.schemas.llm import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30.0


class AllProvidersFailedError(Exception):
    """Raised when every provider in the priority order failed."""

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors
        summary = "; ".join(f"{name}: {msg}" for name, msg in errors.items())
        super().__init__(f"All LLM providers failed - {summary}")


async def complete_with_fallback(
    request: LLMRequest,
    priority: list[str] | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> LLMResponse:
    """Try each provider in `priority` (defaults to Settings.llm_provider_priority)
    in order, returning the first successful response. Raises
    AllProvidersFailedError if every provider fails."""
    settings = get_settings()
    order = priority or settings.llm_provider_priority

    errors: dict[str, str] = {}
    for name in order:
        try:
            provider = get_provider(name)
        except ValueError:
            errors[name] = "not registered"
            continue

        try:
            return await asyncio.wait_for(
                provider.complete(request), timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            errors[name] = f"timed out after {timeout_seconds}s"
            logger.warning("LLM provider %s timed out, trying next", name)
        except LLMProviderError as exc:
            errors[name] = str(exc)
            logger.warning("LLM provider %s failed: %s, trying next", name, exc)

    raise AllProvidersFailedError(errors)
