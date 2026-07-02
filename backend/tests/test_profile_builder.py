import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models.application import Application
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.services.browser_automation.profile_builder import build_applicant_profile


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_build_applicant_profile_generates_real_pdf_not_txt(session):
    user = User(full_name="Jane Doe", email="jane@example.com", phone="555-1234")
    session.add(user)
    session.commit()
    session.refresh(user)

    resume = Resume(user_id=user.id, label="Base Resume", content="Senior Engineer\n\n- Built APIs")
    session.add(resume)
    session.commit()
    session.refresh(resume)

    job = Job(
        title="Engineer",
        company_name="Acme",
        url="https://example.com",
        source_provider="test",
        raw_source_id="1",
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    application = Application(user_id=user.id, job_id=job.id, resume_id=resume.id)
    session.add(application)
    session.commit()
    session.refresh(application)

    profile = build_applicant_profile(session, application)

    assert profile.resume_file_path is not None
    assert profile.resume_file_path.endswith(".pdf")

    with open(profile.resume_file_path, "rb") as f:
        content = f.read()
    assert content[:4] == b"%PDF"


def test_build_applicant_profile_without_resume_has_no_file_path(session):
    user = User(full_name="Jane Doe", email="jane@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    job = Job(
        title="Engineer",
        company_name="Acme",
        url="https://example.com",
        source_provider="test",
        raw_source_id="2",
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    application = Application(user_id=user.id, job_id=job.id, resume_id=None)
    session.add(application)
    session.commit()
    session.refresh(application)

    profile = build_applicant_profile(session, application)

    assert profile.resume_file_path is None
