"""Central registry of available LLMProvider implementations."""
from app.providers.llm_providers.anthropic_provider import AnthropicLLMProvider
from app.providers.llm_providers.base import LLMProvider
from app.providers.llm_providers.groq_provider import GroqLLMProvider
from app.providers.llm_providers.stub_provider import StubLLMProvider

_REGISTRY: dict[str, LLMProvider] = {
    "claude": AnthropicLLMProvider(),
    "groq": GroqLLMProvider(),
    "stub": StubLLMProvider(),
}


def get_provider(name: str) -> LLMProvider:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown LLM provider: {name}") from exc


def list_providers() -> list[str]:
    return list(_REGISTRY.keys())
