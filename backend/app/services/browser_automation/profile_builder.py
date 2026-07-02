"""Builds the ApplicantProfile that gets autofilled into a real application
form, from data the user already has in CareerOps++ (never fetched or
invented elsewhere).

KNOWN GAP: resumes in this app are stored as plain text/markdown
(`Resume.content` - see Milestone 4), and there's no PDF/DOCX rendering
pipeline yet. Most ATS resume-upload fields expect a PDF or Word document,
not a .txt file, so writing the raw text to a temp file and uploading it
will often be rejected by the real form. This is flagged here rather than
silently shipped as if it worked - a resume export pipeline (Milestone 4
follow-up, or part of a docx-export feature) is a prerequisite for this
part of Milestone 8 to be genuinely useful, not just structurally complete.
"""
import tempfile

from sqlmodel import Session

from app.models.application import Application
from app.models.resume import Resume
from app.models.user import User
from app.services.browser_automation.field_classifier import ApplicantProfile


def build_applicant_profile(session: Session, application: Application) -> ApplicantProfile:
    user = session.get(User, application.user_id)
    if user is None:
        raise ValueError(f"User {application.user_id} not found for application")

    resume_file_path = None
    cover_letter_text = None
    if application.resume_id:
        resume = session.get(Resume, application.resume_id)
        if resume is not None:
            # See module docstring: this is a .txt file, not a real
            # resume document format most ATS forms expect.
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, prefix="careerops_resume_"
            )
            tmp.write(resume.content)
            tmp.close()
            resume_file_path = tmp.name

    return ApplicantProfile(
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        linkedin_url=user.linkedin_url,
        portfolio_url=user.portfolio_url,
        resume_file_path=resume_file_path,
        cover_letter_text=cover_letter_text,
    )
