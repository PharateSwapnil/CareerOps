from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.interaction import InteractionType


class InteractionCreate(BaseModel):
    type: InteractionType = InteractionType.NOTE
    summary: str
    occurred_at: datetime | None = None  # defaults to now if omitted


class InteractionRead(BaseModel):
    id: int
    contact_id: int
    type: InteractionType
    summary: str
    occurred_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
