from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeCreate, ResumeDiff, ResumeRead
from app.services.resume_export import render_resume_pdf
from app.services.resume_versioning import (
    ResumeNotFoundError,
    create_new_version,
    diff_versions,
    get_version_history,
    rollback_to_version,
)

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _get_owned_or_404(session: Session, resume_id: int, user: User) -> Resume:
    resume = session.get(Resume, resume_id)
    if resume is None or resume.user_id != user.id:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.get("", response_model=list[ResumeRead])
async def list_resumes(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[Resume]:
    """Lists only the latest version of each resume chain, so callers see
    one row per resume rather than every historical version. Use
    /resumes/{id}/history to see a chain's full version list."""
    all_resumes = session.exec(select(Resume).where(Resume.user_id == current_user.id)).all()

    parent_ids = {r.parent_version_id for r in all_resumes if r.parent_version_id is not None}
    latest_only = [r for r in all_resumes if r.id not in parent_ids]
    return latest_only


@router.post("", response_model=ResumeRead, status_code=201)
async def create_resume(
    payload: ResumeCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Resume:
    """Creates a brand-new resume chain (version 1, no parent)."""
    resume = Resume(
        user_id=current_user.id,
        label=payload.label,
        content=payload.content,
        tailored_for_job_id=payload.tailored_for_job_id,
        parent_version_id=None,
        version_number=1,
    )
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return resume


@router.get("/{resume_id}", response_model=ResumeRead)
async def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Resume:
    return _get_owned_or_404(session, resume_id, current_user)


@router.get("/{resume_id}/export.pdf")
async def export_resume_pdf(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    """Renders this resume version as a real PDF document, for downloading
    or for the browser-assisted application autofill (Milestone 8) to
    upload to a resume-upload field - closing the gap where autofill was
    uploading raw .txt content, which most ATS forms reject."""
    resume = _get_owned_or_404(session, resume_id, current_user)
    pdf_bytes = render_resume_pdf(resume.label, resume.content)
    filename = f"{resume.label.replace(' ', '_')}_v{resume.version_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{resume_id}/versions", response_model=ResumeRead, status_code=201)
async def create_version(
    resume_id: int,
    payload: ResumeCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Resume:
    """Creates a new version extending the chain from `resume_id`."""
    _get_owned_or_404(session, resume_id, current_user)  # ownership check
    try:
        return create_new_version(
            session,
            parent_id=resume_id,
            content=payload.content,
            label=payload.label,
            tailored_for_job_id=payload.tailored_for_job_id,
        )
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{resume_id}/history", response_model=list[ResumeRead])
async def get_history(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[Resume]:
    """Returns every version in the same chain as `resume_id`, oldest first."""
    _get_owned_or_404(session, resume_id, current_user)  # ownership check
    try:
        return get_version_history(session, resume_id)
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{from_id}/diff/{to_id}", response_model=ResumeDiff)
async def get_diff(
    from_id: int,
    to_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ResumeDiff:
    _get_owned_or_404(session, from_id, current_user)  # ownership check
    _get_owned_or_404(session, to_id, current_user)
    try:
        diff_text = diff_versions(session, from_id, to_id)
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResumeDiff(from_version_id=from_id, to_version_id=to_id, diff=diff_text)


@router.post("/{resume_id}/rollback", response_model=ResumeRead, status_code=201)
async def rollback(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Resume:
    """Creates a new version at the head of the chain with `resume_id`'s
    content - i.e. "revert to this version" without mutating history."""
    _get_owned_or_404(session, resume_id, current_user)  # ownership check
    try:
        return rollback_to_version(session, resume_id)
    except ResumeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
