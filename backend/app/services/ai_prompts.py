"""Builds LLMRequest prompts for the career-assistant AI features
(resume optimization, cover letter drafting). Kept separate from the routes
so prompt engineering can be iterated on without touching API wiring, and so
it's testable without spinning up FastAPI.
"""
from app.schemas.llm import CoverLetterRequest, LLMMessage, LLMRequest, ResumeOptimizeRequest

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
