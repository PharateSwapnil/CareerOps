import httpx
import pytest

from app.providers.llm_providers.anthropic_provider import AnthropicLLMProvider
from app.providers.llm_providers.base import LLMProviderError
from app.providers.llm_providers.groq_provider import GroqLLMProvider
from app.schemas.llm import LLMMessage, LLMRequest


class _FakeSettings:
    anthropic_api_key = "test-anthropic-key"
    groq_api_key = "test-groq-key"


def _mock_transport(payload: dict) -> httpx.AsyncBaseTransport:
    class _Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload, request=request)

    return _Transport()


ANTHROPIC_RESPONSE = {
    "id": "msg_123",
    "model": "claude-sonnet-5",
    "role": "assistant",
    "content": [{"type": "text", "text": "Here is your optimized resume."}],
}


@pytest.mark.asyncio
async def test_anthropic_provider_success(monkeypatch):
    monkeypatch.setattr(
        "app.providers.llm_providers.anthropic_provider.get_settings",
        lambda: _FakeSettings(),
    )
    client = httpx.AsyncClient(transport=_mock_transport(ANTHROPIC_RESPONSE))
    provider = AnthropicLLMProvider(client=client)

    result = await provider.complete(
        LLMRequest(messages=[LLMMessage(role="user", content="Help me")])
    )

    assert result.content == "Here is your optimized resume."
    assert result.provider == "claude"
    assert result.model == "claude-sonnet-5"

    await client.aclose()


@pytest.mark.asyncio
async def test_anthropic_provider_missing_key(monkeypatch):
    class _NoKeySettings:
        anthropic_api_key = None

    monkeypatch.setattr(
        "app.providers.llm_providers.anthropic_provider.get_settings",
        lambda: _NoKeySettings(),
    )
    provider = AnthropicLLMProvider()

    with pytest.raises(LLMProviderError):
        await provider.complete(
            LLMRequest(messages=[LLMMessage(role="user", content="Help me")])
        )


GROQ_RESPONSE = {
    "model": "openai/gpt-oss-120b",
    "choices": [{"message": {"role": "assistant", "content": "Here is your cover letter."}}],
}


@pytest.mark.asyncio
async def test_groq_provider_success(monkeypatch):
    monkeypatch.setattr(
        "app.providers.llm_providers.groq_provider.get_settings",
        lambda: _FakeSettings(),
    )
    client = httpx.AsyncClient(transport=_mock_transport(GROQ_RESPONSE))
    provider = GroqLLMProvider(client=client)

    result = await provider.complete(
        LLMRequest(messages=[LLMMessage(role="user", content="Help me")])
    )

    assert result.content == "Here is your cover letter."
    assert result.provider == "groq"
    assert result.model == "openai/gpt-oss-120b"

    await client.aclose()


@pytest.mark.asyncio
async def test_groq_provider_missing_key(monkeypatch):
    class _NoKeySettings:
        groq_api_key = None

    monkeypatch.setattr(
        "app.providers.llm_providers.groq_provider.get_settings",
        lambda: _NoKeySettings(),
    )
    provider = GroqLLMProvider()

    with pytest.raises(LLMProviderError):
        await provider.complete(
            LLMRequest(messages=[LLMMessage(role="user", content="Help me")])
        )
