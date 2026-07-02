from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.automation_session import AutomationStatus


class AutomationSessionStart(BaseModel):
    application_id: int


class AutomationSessionRead(BaseModel):
    id: int
    application_id: int
    status: AutomationStatus
    pause_reason: str | None
    filled_fields: str | None  # JSON-encoded list, parsed by the frontend
    error_message: str | None
    started_at: datetime
    updated_at: datetime
    closed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
