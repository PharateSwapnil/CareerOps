from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    headline: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None


class UserProfileRead(BaseModel):
    id: int
    full_name: str
    email: str
    headline: str | None
    phone: str | None
    linkedin_url: str | None
    portfolio_url: str | None
    base_resume_text: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
