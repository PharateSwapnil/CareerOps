from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyRead(BaseModel):
    id: int
    name: str
    website: str | None
    size: str | None
    funding_stage: str | None
    industry: str | None
    tech_stack: str | None
    culture_summary: str | None
    reputation_summary: str | None
    salary_insights: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyEnrichRequest(BaseModel):
    data_provider_name: str = "wikipedia"
