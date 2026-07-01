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


class ResumeOptimizeRequest(BaseModel):
    resume_text: str
    job_description: str


class CoverLetterRequest(BaseModel):
    resume_text: str
    job_description: str
    company_name: str | None = None
    tone: str = "professional"  # e.g. "professional", "enthusiastic", "concise"


class NetworkingMessageRequest(BaseModel):
    contact_name: str
    contact_relationship: str  # e.g. "recruiter", "hiring_manager", "referral", "peer"
    purpose: str  # e.g. "cold outreach for a referral", "follow-up after no response"
    context: str | None = None  # e.g. shared background, the role/company, prior conversation
    tone: str = "professional"
    channel: str = "linkedin"  # "linkedin", "email", "twitter" - affects length/formality


class AIAssistResponse(BaseModel):
    content: str
    provider: str
    model: str | None = None
