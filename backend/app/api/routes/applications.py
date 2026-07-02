from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.application import Application, ApplicationStatus
from app.models.job import Job
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationStatusUpdate,
    ApplicationUpdate,
)
from app.services.application_state_machine import InvalidTransitionError, validate_transition

router = APIRouter(prefix="/applications", tags=["applications"])


def _get_owned_or_404(session: Session, application_id: int, user: User) -> Application:
    # 404 (not 403) for both "doesn't exist" and "exists but isn't yours" -
    # a 403 would confirm the id is valid and belongs to someone else,
    # leaking information about other users' data.
    application = session.get(Application, application_id)
    if application is None or application.user_id != user.id:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.get("", response_model=list[ApplicationRead])
async def list_applications(
    status: ApplicationStatus | None = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[Application]:
    query = select(Application).where(Application.user_id == current_user.id)
    if status is not None:
        query = query.where(Application.status == status)
    return session.exec(query).all()


@router.post("", response_model=ApplicationRead, status_code=201)
async def create_application(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Application:
    job = session.get(Job, payload.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    application = Application(
        user_id=current_user.id,
        job_id=payload.job_id,
        resume_id=payload.resume_id,
        status=payload.status,
        notes=payload.notes,
        next_follow_up_at=payload.next_follow_up_at,
        applied_at=datetime.now(timezone.utc) if payload.status == ApplicationStatus.APPLIED else None,
    )
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Application:
    return _get_owned_or_404(session, application_id, current_user)


@router.patch("/{application_id}", response_model=ApplicationRead)
async def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Application:
    application = _get_owned_or_404(session, application_id, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(application, field, value)
    application.updated_at = datetime.now(timezone.utc)

    session.add(application)
    session.commit()
    session.refresh(application)
    return application


@router.patch("/{application_id}/status", response_model=ApplicationRead)
async def update_application_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Application:
    application = _get_owned_or_404(session, application_id, current_user)

    try:
        validate_transition(application.status, payload.status)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    application.status = payload.status
    if payload.status == ApplicationStatus.APPLIED and application.applied_at is None:
        application.applied_at = datetime.now(timezone.utc)
    application.updated_at = datetime.now(timezone.utc)

    session.add(application)
    session.commit()
    session.refresh(application)
    return application


@router.delete("/{application_id}", status_code=204)
async def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    application = _get_owned_or_404(session, application_id, current_user)
    session.delete(application)
    session.commit()
