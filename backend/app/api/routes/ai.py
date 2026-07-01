from fastapi import APIRouter

from app.providers.llm_providers.stub_provider import StubLLMProvider
from app.schemas.llm import LLMRequest, LLMResponse

router = APIRouter(prefix="/ai", tags=["ai"])

# Milestone 3 replaces this with a provider-fallback orchestrator selecting
# from Claude/Groq/OpenRouter/Gemini based on configured priority.
_provider = StubLLMProvider()


@router.post("/complete", response_model=LLMResponse)
async def complete(request: LLMRequest) -> LLMResponse:
    return await _provider.complete(request)
