from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AutomationStatus(str, Enum):
    RUNNING = "running"
    PAUSED_AUTH = "paused_auth"  # login/auth page detected
    PAUSED_CAPTCHA = "paused_captcha"  # CAPTCHA detected
    PAUSED_UNKNOWN_FIELD = "paused_unknown_field"  # a required field we can't confidently fill
    AWAITING_SUBMIT = "awaiting_submit"  # form filled; human must click Submit themselves
    CLOSED = "closed"
    ERROR = "error"


class ApplicationAutomationSession(SQLModel, table=True):
    """Audit log for a browser-assisted application session. The live
    Playwright browser handle itself is NOT stored here (can't be
    serialized to a DB row) - it lives in-process in
    services/browser_automation/session_manager.py's in-memory registry,
    keyed by this row's id. This table exists so the user has a durable
    history of what automation did, even after the browser session ends.
    """

    id: int | None = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id", index=True)

    status: AutomationStatus = Field(default=AutomationStatus.RUNNING)
    pause_reason: str | None = None  # human-readable detail for the current pause

    # JSON-encoded list of {"field_label": ..., "value_preview": ...} for
    # transparency - the user can see exactly what was auto-filled, since
    # they never get to review before it's typed into the real form.
    filled_fields: str | None = None

    error_message: str | None = None

    started_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    closed_at: datetime | None = None
