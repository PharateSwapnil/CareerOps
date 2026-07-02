"""Builds the ApplicantProfile that gets autofilled into a real application
form, from data the user already has in CareerOps++ (never fetched or
invented elsewhere).

Resume handling: renders the resume's stored content to a real PDF via
services/resume_export.py and writes it to a temp file for upload. This
used to write raw markdown/plain text to a .txt file, which most ATS
resume-upload fields reject outright - closed as part of Milestone 8
follow-up work. The PDF is plain/unstyled (see resume_export.py's
docstring) - readable and acceptable to upload fields, but not a designed
resume template.
"""
import tempfile

from sqlmodel import Session

from app.models.application import Application
from app.models.resume import Resume
from app.models.user import User
from app.services.browser_automation.field_classifier import ApplicantProfile
from app.services.resume_export import render_resume_pdf


def build_applicant_profile(session: Session, application: Application) -> ApplicantProfile:
    user = session.get(User, application.user_id)
    if user is None:
        raise ValueError(f"User {application.user_id} not found for application")

    resume_file_path = None
    cover_letter_text = None
    if application.resume_id:
        resume = session.get(Resume, application.resume_id)
        if resume is not None:
            pdf_bytes = render_resume_pdf(resume.label, resume.content)
            tmp = tempfile.NamedTemporaryFile(
                mode="wb", suffix=".pdf", delete=False, prefix="careerops_resume_"
            )
            tmp.write(pdf_bytes)
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
