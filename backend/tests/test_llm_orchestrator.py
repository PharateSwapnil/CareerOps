import pytest

from app.providers.llm_providers.base import LLMProviderError
from app.schemas.llm import LLMMessage, LLMRequest, LLMResponse
from app.services.llm_orchestrator import AllProvidersFailedError, complete_with_fallback


class _AlwaysFailsProvider:
    name = "always_fails"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise LLMProviderError("simulated failure")


class _AlwaysSucceedsProvider:
    name = "always_succeeds"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(content="ok", provider=self.name, model="fake-model")


class _SlowProvider:
    name = "slow"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        import asyncio

        await asyncio.sleep(10)
        return LLMResponse(content="too slow", provider=self.name)


def _patch_registry(monkeypatch, providers: dict):
    monkeypatch.setattr(
        "app.services.llm_orchestrator.get_provider",
        lambda name: providers[name],
    )


@pytest.mark.asyncio
async def test_orchestrator_uses_first_successful_provider(monkeypatch):
    providers = {
        "a": _AlwaysFailsProvider(),
        "b": _AlwaysSucceedsProvider(),
    }
    _patch_registry(monkeypatch, providers)

    result = await complete_with_fallback(
        LLMRequest(messages=[LLMMessage(role="user", content="hi")]),
        priority=["a", "b"],
    )

    assert result.content == "ok"
    assert result.provider == "always_succeeds"


@pytest.mark.asyncio
async def test_orchestrator_raises_when_all_fail(monkeypatch):
    providers = {
        "a": _AlwaysFailsProvider(),
        "b": _AlwaysFailsProvider(),
    }
    _patch_registry(monkeypatch, providers)

    with pytest.raises(AllProvidersFailedError) as exc_info:
        await complete_with_fallback(
            LLMRequest(messages=[LLMMessage(role="user", content="hi")]),
            priority=["a", "b"],
        )

    assert "a" in exc_info.value.errors
    assert "b" in exc_info.value.errors


@pytest.mark.asyncio
async def test_orchestrator_falls_back_on_timeout(monkeypatch):
    providers = {
        "slow": _SlowProvider(),
        "fast": _AlwaysSucceedsProvider(),
    }
    _patch_registry(monkeypatch, providers)

    result = await complete_with_fallback(
        LLMRequest(messages=[LLMMessage(role="user", content="hi")]),
        priority=["slow", "fast"],
        timeout_seconds=0.05,
    )

    assert result.provider == "always_succeeds"
