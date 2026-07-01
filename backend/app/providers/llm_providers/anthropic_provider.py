"""LLMProvider for Anthropic's Claude API.

Docs: https://docs.claude.com/en/api/messages
Endpoint: POST https://api.anthropic.com/v1/messages
Auth: x-api-key header + anthropic-version header (not Bearer auth).

Reads ANTHROPIC_API_KEY from Settings. Raises LLMProviderError (rather than
returning a degraded response) when the key is missing or the request fails,
so the fallback orchestrator can move on to the next configured provider.
"""
import httpx

from app.core.config import get_settings
from app.providers.llm_providers.base import LLMProviderError
from app.schemas.llm import LLMRequest, LLMResponse

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5"


class AnthropicLLMProvider:
    name = "claude"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def complete(self, request: LLMRequest) -> LLMResponse:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise LLMProviderError("ANTHROPIC_API_KEY is not configured")

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0)

        try:
            # Anthropic's Messages API takes system prompts separately from
            # the message list; pull any "system" role messages out.
            system_parts = [m.content for m in request.messages if m.role == "system"]
            chat_messages = [
                {"role": m.role, "content": m.content}
                for m in request.messages
                if m.role != "system"
            ]

            payload = {
                "model": DEFAULT_MODEL,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "messages": chat_messages,
            }
            if system_parts:
                payload["system"] = "\n\n".join(system_parts)

            resp = await client.post(
                ANTHROPIC_MESSAGES_URL,
                json=payload,
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            text_blocks = [
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type") == "text"
            ]

            return LLMResponse(
                content="".join(text_blocks),
                provider=self.name,
                model=data.get("model", DEFAULT_MODEL),
            )
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Claude request failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()
