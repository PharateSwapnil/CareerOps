"""Pydantic I/O schemas for LLM provider requests/responses."""
from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str


class LLMRequest(BaseModel):
    messages: list[LLMMessage]
    max_tokens: int = 1024
    temperature: float = 0.7


class LLMResponse(BaseModel):
    content: str
    provider: str
    model: str | None = None
