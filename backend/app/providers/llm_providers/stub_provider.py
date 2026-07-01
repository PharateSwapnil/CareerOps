"""A fake LLM provider used for local dev/testing until real integrations
(Claude, Groq, OpenRouter, Gemini...) land in Milestone 3.

Demonstrates the LLMProvider interface contributors should follow.
"""
from app.schemas.llm import LLMRequest, LLMResponse


class StubLLMProvider:
    name = "stub"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        last_user_msg = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        )
        return LLMResponse(
            content=f"[stub response] You said: {last_user_msg[:200]}",
            provider=self.name,
            model="stub-model",
        )
