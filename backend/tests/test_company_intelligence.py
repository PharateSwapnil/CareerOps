import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models.company import Company
from app.models.job import Job
from app.providers.company_data_providers.base import CompanyDataResult
from app.services.company_intelligence import (
    enrich_company,
    get_or_create_company,
    infer_tech_stack_from_jobs,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


class _FakeDataProvider:
    name = "fake"

    def __init__(self, result: CompanyDataResult) -> None:
        self._result = result

    async def fetch(self, company_name: str) -> CompanyDataResult:
        return self._result


def test_get_or_create_company_dedupes_case_insensitively(session):
    c1 = get_or_create_company(session, "Acme Corp")
    c2 = get_or_create_company(session, "acme corp")
    c3 = get_or_create_company(session, "ACME CORP")

    assert c1.id == c2.id == c3.id


def test_get_or_create_company_creates_distinct_companies(session):
    c1 = get_or_create_company(session, "Acme Corp")
    c2 = get_or_create_company(session, "Widget Inc")

    assert c1.id != c2.id


def test_infer_tech_stack_from_jobs_matches_known_keywords(session):
    company = get_or_create_company(session, "Acme Corp")
    job = Job(
        title="Senior Python Engineer",
        company_name="Acme Corp",
        company_id=company.id,
        description="We use Python, Kubernetes, and PostgreSQL heavily.",
        url="https://example.com",
        source_provider="test",
        raw_source_id="1",
    )
    session.add(job)
    session.commit()

    tech_stack = infer_tech_stack_from_jobs(session, company.id)

    assert "Python" in tech_stack
    assert "Kubernetes" in tech_stack
    assert "PostgreSQL" in tech_stack
    assert "Ruby" not in tech_stack


def test_infer_tech_stack_returns_empty_for_no_jobs(session):
    company = get_or_create_company(session, "Empty Corp")
    assert infer_tech_stack_from_jobs(session, company.id) == []


@pytest.mark.asyncio
async def test_enrich_company_does_not_set_salary_insights(session, monkeypatch):
    """Guards against ever silently starting to fabricate salary numbers -
    salary_insights should stay untouched until a real data source exists."""
    company = get_or_create_company(session, "Acme Corp")
    data_provider = _FakeDataProvider(
        CompanyDataResult(found=True, summary_extract="Acme Corp is a widget maker.")
    )

    async def fake_complete(request, *args, **kwargs):
        from app.schemas.llm import LLMResponse

        return LLMResponse(content="A fabricated-free summary.", provider="stub")

    monkeypatch.setattr(
        "app.services.company_intelligence.complete_with_fallback", fake_complete
    )

    result = await enrich_company(session, company, data_provider)

    assert result.salary_insights is None
    assert result.culture_summary == "A fabricated-free summary."
    assert result.reputation_summary == "A fabricated-free summary."


@pytest.mark.asyncio
async def test_enrich_company_handles_not_found_public_data(session, monkeypatch):
    company = get_or_create_company(session, "Totally Obscure LLC")
    data_provider = _FakeDataProvider(CompanyDataResult(found=False))

    async def fake_complete(request, *args, **kwargs):
        from app.schemas.llm import LLMResponse

        return LLMResponse(content="Limited public information available.", provider="stub")

    monkeypatch.setattr(
        "app.services.company_intelligence.complete_with_fallback", fake_complete
    )

    result = await enrich_company(session, company, data_provider)

    assert result.culture_summary is not None  # still gets a summary, just grounded in less
