"""Builds LLMRequest prompts for the career-assistant AI features
(resume optimization, cover letter drafting). Kept separate from the routes
so prompt engineering can be iterated on without touching API wiring, and so
it's testable without spinning up FastAPI.
"""
from app.schemas.llm import (
    CoverLetterRequest,
    LLMMessage,
    LLMRequest,
    NetworkingMessageRequest,
    ResumeOptimizeRequest,
)

RESUME_OPTIMIZE_SYSTEM_PROMPT = (
    "You are an expert resume writer and ATS (Applicant Tracking System) "
    "optimization specialist. Given a candidate's resume and a target job "
    "description, suggest specific, actionable edits that better align the "
    "resume with the role - emphasizing relevant experience, mirroring key "
    "terminology from the job description where truthful, and improving "
    "clarity and impact. Do not fabricate experience or skills the "
    "candidate doesn't have. Output the improved resume content directly, "
    "followed by a brief bullet list of what you changed and why."
)

COVER_LETTER_SYSTEM_PROMPT = (
    "You are an expert career coach writing cover letters. Given a "
    "candidate's resume and a target job description, write a compelling, "
    "concise cover letter (3-4 paragraphs) that connects the candidate's "
    "genuine experience to the role's requirements. Avoid generic "
    "filler phrases and do not fabricate experience. Match the requested "
    "tone."
)


NETWORKING_MESSAGE_SYSTEM_PROMPT = (
    "You are an expert at professional networking outreach. Given "
    "information about a contact, the purpose of reaching out, and "
    "optional context, draft a concise, genuine-sounding message - never "
    "generic or template-feeling. Avoid corporate jargon and overly "
    "salesy language. Keep the length and formality appropriate to the "
    "specified channel (LinkedIn messages should be short; emails can be "
    "slightly longer). The message should keep the recipient in control - "
    "it's a starting point for them to edit, not a final message to send "
    "verbatim without review. Output only the message text, no preamble "
    "or explanation."
)


COMPANY_CULTURE_SYSTEM_PROMPT = (
    "You are a career research assistant summarizing a company's engineering "
    "culture for a job seeker. You will be given factual signals gathered "
    "about the company (an encyclopedia extract, and/or a tech stack "
    "inferred from that company's own job postings). Base your summary "
    "ONLY on the signals provided. Do not invent specific facts, figures, "
    "funding amounts, headcounts, or claims you weren't given. If the "
    "provided signals are thin, say so explicitly rather than padding the "
    "summary with generic or fabricated detail. Write 2-4 sentences, "
    "neutral and factual in tone - not promotional copy."
)

COMPANY_REPUTATION_SYSTEM_PROMPT = (
    "You are a career research assistant summarizing what's publicly known "
    "about a company's reputation, for a job seeker doing due diligence. "
    "You will be given factual signals gathered about the company. Base "
    "your summary ONLY on the signals provided. Do not invent specific "
    "facts, ratings, controversies, or claims you weren't given - if the "
    "signals don't mention reputation-relevant information, say plainly "
    "that there isn't enough public information available rather than "
    "fabricating something plausible-sounding. Write 2-3 sentences, neutral "
    "and factual, not speculative."
)


def build_company_culture_request(
    company_name: str, wiki_extract: str | None, tech_stack: list[str], job_count: int
) -> LLMRequest:
    signals = [f"Company name: {company_name}"]
    if wiki_extract:
        signals.append(f"Encyclopedia extract: {wiki_extract}")
    if tech_stack:
        signals.append(f"Tech stack inferred from their own job postings: {', '.join(tech_stack)}")
    signals.append(f"Number of open job postings currently tracked: {job_count}")

    return LLMRequest(
        messages=[
            LLMMessage(role="system", content=COMPANY_CULTURE_SYSTEM_PROMPT),
            LLMMessage(role="user", content="\n".join(signals)),
        ],
        max_tokens=300,
        temperature=0.3,
    )


def build_company_reputation_request(
    company_name: str, wiki_extract: str | None
) -> LLMRequest:
    signals = [f"Company name: {company_name}"]
    if wiki_extract:
        signals.append(f"Encyclopedia extract: {wiki_extract}")
    else:
        signals.append("No encyclopedia extract was found for this company.")

    return LLMRequest(
        messages=[
            LLMMessage(role="system", content=COMPANY_REPUTATION_SYSTEM_PROMPT),
            LLMMessage(role="user", content="\n".join(signals)),
        ],
        max_tokens=250,
        temperature=0.3,
    )


def build_resume_optimize_request(payload: ResumeOptimizeRequest) -> LLMRequest:
    user_content = (
        f"Job description:\n{payload.job_description}\n\n"
        f"Current resume:\n{payload.resume_text}"
    )
    return LLMRequest(
        messages=[
            LLMMessage(role="system", content=RESUME_OPTIMIZE_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_content),
        ],
        max_tokens=2048,
        temperature=0.4,
    )


def build_cover_letter_request(payload: CoverLetterRequest) -> LLMRequest:
    company_line = f"Company: {payload.company_name}\n" if payload.company_name else ""
    user_content = (
        f"{company_line}"
        f"Tone: {payload.tone}\n\n"
        f"Job description:\n{payload.job_description}\n\n"
        f"Candidate's resume:\n{payload.resume_text}"
    )
    return LLMRequest(
        messages=[
            LLMMessage(role="system", content=COVER_LETTER_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_content),
        ],
        max_tokens=1024,
        temperature=0.6,
    )


def build_networking_message_request(payload: NetworkingMessageRequest) -> LLMRequest:
    context_line = f"Context: {payload.context}\n" if payload.context else ""
    user_content = (
        f"Contact: {payload.contact_name} ({payload.contact_relationship})\n"
        f"Channel: {payload.channel}\n"
        f"Tone: {payload.tone}\n"
        f"Purpose: {payload.purpose}\n"
        f"{context_line}"
    )
    return LLMRequest(
        messages=[
            LLMMessage(role="system", content=NETWORKING_MESSAGE_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_content),
        ],
        max_tokens=512,
        temperature=0.7,
    )
