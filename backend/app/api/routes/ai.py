from fastapi import APIRouter, HTTPException

from app.schemas.llm import (
    AIAssistResponse,
    CoverLetterRequest,
    LLMRequest,
    LLMResponse,
    NetworkingMessageRequest,
    ResumeOptimizeRequest,
)
from app.services.ai_prompts import (
    build_cover_letter_request,
    build_networking_message_request,
    build_resume_optimize_request,
)
from app.services.llm_orchestrator import AllProvidersFailedError, complete_with_fallback

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/complete", response_model=LLMResponse)
async def complete(request: LLMRequest) -> LLMResponse:
    """Low-level passthrough to the LLM fallback orchestrator. Prefer the
    higher-level /resume-optimize and /cover-letter endpoints for career
    features; this exists for direct/experimental use."""
    try:
        return await complete_with_fallback(request)
    except AllProvidersFailedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/resume-optimize", response_model=AIAssistResponse)
async def resume_optimize(payload: ResumeOptimizeRequest) -> AIAssistResponse:
    llm_request = build_resume_optimize_request(payload)
    try:
        result = await complete_with_fallback(llm_request)
    except AllProvidersFailedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AIAssistResponse(
        content=result.content, provider=result.provider, model=result.model
    )


@router.post("/cover-letter", response_model=AIAssistResponse)
async def cover_letter(payload: CoverLetterRequest) -> AIAssistResponse:
    llm_request = build_cover_letter_request(payload)
    try:
        result = await complete_with_fallback(llm_request)
    except AllProvidersFailedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AIAssistResponse(
        content=result.content, provider=result.provider, model=result.model
    )


@router.post("/networking-message", response_model=AIAssistResponse)
async def networking_message(payload: NetworkingMessageRequest) -> AIAssistResponse:
    llm_request = build_networking_message_request(payload)
    try:
        result = await complete_with_fallback(llm_request)
    except AllProvidersFailedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AIAssistResponse(
        content=result.content, provider=result.provider, model=result.model
    )
