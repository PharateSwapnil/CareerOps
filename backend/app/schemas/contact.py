from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.contact import ContactRelationship


class ContactCreate(BaseModel):
    full_name: str
    relationship: ContactRelationship = ContactRelationship.OTHER
    company_id: int | None = None
    email: str | None = None
    linkedin_url: str | None = None
    notes: str | None = None
    next_follow_up_at: datetime | None = None


class ContactUpdate(BaseModel):
    full_name: str | None = None
    relationship: ContactRelationship | None = None
    company_id: int | None = None
    email: str | None = None
    linkedin_url: str | None = None
    notes: str | None = None
    next_follow_up_at: datetime | None = None


class ContactRead(BaseModel):
    id: int
    user_id: int
    full_name: str
    relationship: ContactRelationship
    company_id: int | None
    email: str | None
    linkedin_url: str | None
    notes: str | None
    next_follow_up_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailEnrichmentResponse(BaseModel):
    contact: ContactRead
    found: bool
    confidence: int | None = None
