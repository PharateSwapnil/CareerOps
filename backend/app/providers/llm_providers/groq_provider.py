"""LLMProvider for Groq's OpenAI-compatible chat completions API.

Docs: https://console.groq.com/docs/api-reference
Endpoint: POST https://api.groq.com/openai/v1/chat/completions
Auth: Bearer token.

Default model is openai/gpt-oss-120b — Groq deprecated llama-3.3-70b-versatile
and llama-3.1-8b-instant in June 2026 in favor of the GPT-OSS and Qwen3.6
lineup, so this intentionally does NOT use the older Llama model names still
found in a lot of older Groq examples online.

Reads GROQ_API_KEY from Settings. Raises LLMProviderError when the key is
missing or the request fails, so the fallback orchestrator can move on.
"""
import httpx

from app.core.config import get_settings
from app.providers.llm_providers.base import LLMProviderError
from app.schemas.llm import LLMRequest, LLMResponse

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"


class GroqLLMProvider:
    name = "groq"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def complete(self, request: LLMRequest) -> LLMResponse:
        settings = get_settings()
        if not settings.groq_api_key:
            raise LLMProviderError("GROQ_API_KEY is not configured")

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0)

        try:
            payload = {
                "model": DEFAULT_MODEL,
                "messages": [
                    {"role": m.role, "content": m.content} for m in request.messages
                ],
                "max_completion_tokens": request.max_tokens,
                "temperature": request.temperature,
            }

            resp = await client.post(
                GROQ_CHAT_COMPLETIONS_URL,
                json=payload,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

            choices = data.get("choices", [])
            content = choices[0]["message"]["content"] if choices else ""

            return LLMResponse(
                content=content,
                provider=self.name,
                model=data.get("model", DEFAULT_MODEL),
            )
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Groq request failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()
