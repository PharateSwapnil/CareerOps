from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.company import Company
from app.models.job import Job
from app.providers.company_data_providers.registry import get_provider, list_providers
from app.schemas.company import CompanyEnrichRequest, CompanyRead, CompanyUpdate
from app.schemas.job import JobRead
from app.services.company_intelligence import enrich_company

router = APIRouter(prefix="/companies", tags=["companies"])


def _get_or_404(session: Session, company_id: int) -> Company:
    company = session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.get("", response_model=list[CompanyRead])
async def list_companies(session: Session = Depends(get_session)) -> list[Company]:
    return session.exec(select(Company)).all()


@router.get("/data-providers")
async def get_data_providers() -> list[str]:
    return list_providers()


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(company_id: int, session: Session = Depends(get_session)) -> Company:
    return _get_or_404(session, company_id)


@router.patch("/{company_id}", response_model=CompanyRead)
async def update_company(
    company_id: int, payload: CompanyUpdate, session: Session = Depends(get_session)
) -> Company:
    """Lets the user manually fill in details (most importantly `website`,
    which nothing auto-populates yet) that enrichment couldn't find on its
    own. Also needed so contact-email enrichment (services/contact_enrichment.py)
    has a domain to work with."""
    company = _get_or_404(session, company_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    company.updated_at = datetime.now(timezone.utc)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


@router.get("/{company_id}/jobs", response_model=list[JobRead])
async def get_company_jobs(
    company_id: int, session: Session = Depends(get_session)
) -> list[Job]:
    _get_or_404(session, company_id)
    return session.exec(select(Job).where(Job.company_id == company_id)).all()


@router.post("/{company_id}/enrich", response_model=CompanyRead)
async def enrich_company_endpoint(
    company_id: int,
    payload: CompanyEnrichRequest = CompanyEnrichRequest(),
    session: Session = Depends(get_session),
) -> Company:
    """Runs the full enrichment pipeline synchronously: public data lookup
    (Wikipedia by default) + tech-stack inference from this company's own
    ingested job postings + AI-generated culture/reputation summaries
    grounded in those signals. Can take a few seconds (network + LLM calls);
    there's no background variant yet since company enrichment is a
    one-off, user-initiated action rather than a bulk operation like job
    ingestion.
    """
    company = _get_or_404(session, company_id)
    data_provider = get_provider(payload.data_provider_name)
    return await enrich_company(session, company, data_provider)
