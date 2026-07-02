import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.application import Application
from app.models.automation_session import ApplicationAutomationSession, AutomationStatus
from app.models.job import Job
from app.schemas.automation import AutomationSessionRead, AutomationSessionStart
from app.services.browser_automation import session_manager
from app.services.browser_automation.playwright_driver import (
    BrowserAutomationSession,
    PlaywrightNotAvailableError,
)
from app.services.browser_automation.profile_builder import build_applicant_profile

router = APIRouter(prefix="/automation", tags=["automation"])

_STATUS_MAP = {
    "paused_captcha": AutomationStatus.PAUSED_CAPTCHA,
    "paused_auth": AutomationStatus.PAUSED_AUTH,
    "paused_unknown_field": AutomationStatus.PAUSED_UNKNOWN_FIELD,
    "awaiting_submit": AutomationStatus.AWAITING_SUBMIT,
}


def _get_or_404(session: Session, session_id: int) -> ApplicationAutomationSession:
    row = session.get(ApplicationAutomationSession, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Automation session not found")
    return row


@router.get("/sessions", response_model=list[AutomationSessionRead])
async def list_sessions(
    session: Session = Depends(get_session),
) -> list[ApplicationAutomationSession]:
    return session.exec(select(ApplicationAutomationSession)).all()


@router.get("/sessions/{session_id}", response_model=AutomationSessionRead)
async def get_session_status(
    session_id: int, session: Session = Depends(get_session)
) -> ApplicationAutomationSession:
    return _get_or_404(session, session_id)


@router.post("/sessions", response_model=AutomationSessionRead, status_code=201)
async def start_session(
    payload: AutomationSessionStart, session: Session = Depends(get_session)
) -> ApplicationAutomationSession:
    """Launches a real, visible browser and begins autofilling the
    application form. Requires `playwright install chromium` to have been
    run - if the browser binary isn't available, returns 503 with a clear
    explanation rather than a bare crash.
    """
    application = session.get(Application, payload.application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    job = session.get(Job, application.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found for this application")

    row = ApplicationAutomationSession(
        application_id=application.id, status=AutomationStatus.RUNNING
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    profile = build_applicant_profile(session, application)
    live_session = BrowserAutomationSession(row.id, job.url, profile)

    try:
        status_str, detail = await live_session.start()
    except PlaywrightNotAvailableError as exc:
        row.status = AutomationStatus.ERROR
        row.error_message = str(exc)
        row.updated_at = datetime.now(timezone.utc)
        session.add(row)
        session.commit()
        session.refresh(row)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    session_manager.register(row.id, live_session)
    _apply_status(row, status_str, detail, live_session)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.post("/sessions/{session_id}/resume", response_model=AutomationSessionRead)
async def resume_session(
    session_id: int, session: Session = Depends(get_session)
) -> ApplicationAutomationSession:
    """Call after manually handling a pause (solving the CAPTCHA, logging
    in, or filling the field yourself) in the visible browser window."""
    row = _get_or_404(session, session_id)
    live_session = session_manager.get(session_id)
    if live_session is None:
        raise HTTPException(
            status_code=409,
            detail="No active browser session found (it may have been closed or the "
            "server restarted) - start a new session instead.",
        )

    status_str, detail = await live_session.resume()
    _apply_status(row, status_str, detail, live_session)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/sessions/{session_id}", status_code=204)
async def close_session(session_id: int, session: Session = Depends(get_session)) -> None:
    row = _get_or_404(session, session_id)
    live_session = session_manager.get(session_id)
    if live_session is not None:
        await live_session.close()
        session_manager.remove(session_id)

    row.status = AutomationStatus.CLOSED
    row.closed_at = datetime.now(timezone.utc)
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()


def _apply_status(
    row: ApplicationAutomationSession,
    status_str: str,
    detail: str | None,
    live_session: BrowserAutomationSession,
) -> None:
    row.status = _STATUS_MAP.get(status_str, AutomationStatus.ERROR)
    row.pause_reason = detail
    row.filled_fields = json.dumps(
        [{"field_label": label, "value_preview": preview} for label, preview in live_session.filled_fields]
    )
    row.updated_at = datetime.now(timezone.utc)
