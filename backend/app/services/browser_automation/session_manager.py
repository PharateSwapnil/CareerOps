"""In-memory registry mapping ApplicationAutomationSession.id -> the live
BrowserAutomationSession object holding the actual Playwright browser
handle. Playwright handles can't be serialized to the database, so this
process-local dict is the only place they exist - restarting the backend
loses any in-progress sessions (their DB rows would need a reconciliation
pass to mark them closed/error, not attempted here since this is a
single-process local-first app where that's an acceptable rough edge for a
first cut).
"""
from app.services.browser_automation.playwright_driver import BrowserAutomationSession

_ACTIVE_SESSIONS: dict[int, BrowserAutomationSession] = {}


def register(session_id: int, session: BrowserAutomationSession) -> None:
    _ACTIVE_SESSIONS[session_id] = session


def get(session_id: int) -> BrowserAutomationSession | None:
    return _ACTIVE_SESSIONS.get(session_id)


def remove(session_id: int) -> None:
    _ACTIVE_SESSIONS.pop(session_id, None)
