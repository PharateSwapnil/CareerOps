"""Company intelligence: linking jobs to Company records, inferring a tech
stack from a company's own job postings (data we've already ingested - the
cheapest and most directly relevant "public data aggregation" available),
fetching external public data (Wikipedia), and orchestrating AI-generated
summaries on top of those signals.
"""
import logging

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.company import Company
from app.models.job import Job
from app.providers.company_data_providers.base import (
    CompanyDataProvider,
    CompanyDataProviderError,
    CompanyDataResult,
)
from app.services.ai_prompts import build_company_culture_request, build_company_reputation_request
from app.services.llm_orchestrator import AllProvidersFailedError, complete_with_fallback

logger = logging.getLogger(__name__)

# A curated list of common technology keywords to match against job
# descriptions. Not exhaustive, and case-insensitive substring matching on
# free text will always have some false positives/negatives (e.g. "Go" is
# common as a regular word) - this is a heuristic signal, not a guarantee.
TECH_KEYWORDS = [
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Golang", "Rust",
    "Ruby", "PHP", "C++", "C#", "Kotlin", "Swift", "Scala",
    "React", "Vue", "Angular", "Next.js", "Node.js", "Django", "Flask",
    "FastAPI", "Spring", "Rails",
    "AWS", "GCP", "Azure", "Kubernetes", "Docker", "Terraform",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Snowflake", "Databricks",
    "Kafka", "Spark", "Airflow", "GraphQL", "gRPC",
]


def get_or_create_company(session: Session, name: str) -> Company:
    """Dedupes case-insensitively on name. Job postings from different
    providers often format company names slightly differently, but exact
    dedupe is still far better than none - fuzzy matching is a documented
    follow-up, not attempted here to avoid merging two different
    similarly-named companies incorrectly."""
    normalized = name.strip()
    existing = session.exec(
        select(Company).where(Company.name.ilike(normalized))
    ).first()
    if existing:
        return existing

    company = Company(name=normalized)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


async def _safe_fetch_public_data(data_provider: CompanyDataProvider, company_name: str):
    """A provider failure (network error, malformed response) degrades to
    "no public data found" rather than propagating - consistent with how
    every other external-dependency failure in this codebase (embedding,
    LLM providers) is handled: log it, don't let it break the feature."""
    try:
        return await data_provider.fetch(company_name)
    except CompanyDataProviderError:
        logger.exception(
            "Public data provider %s failed for %s, continuing without it",
            data_provider.name,
            company_name,
        )
        return CompanyDataResult(found=False)


def infer_tech_stack_from_jobs(session: Session, company_id: int) -> list[str]:
    """Scans this company's own ingested job descriptions for known tech
    keywords. Purely local - no network call, always available."""
    jobs = session.exec(select(Job).where(Job.company_id == company_id)).all()
    combined_text = " ".join(
        f"{job.title} {job.description or ''}" for job in jobs
    ).lower()

    found = [kw for kw in TECH_KEYWORDS if kw.lower() in combined_text]
    return found


async def enrich_company(
    session: Session,
    company: Company,
    data_provider: CompanyDataProvider,
) -> Company:
    """Runs the full enrichment pipeline: fetch public data, infer tech
    stack from our own job postings, generate AI summaries grounded in
    those signals, and persist the result onto `company`.

    Deliberately does NOT generate `salary_insights` - doing so via an LLM
    with no real salary data source would mean fabricating numbers, which
    is exactly the kind of hallucination that could mislead someone's real
    career/compensation decisions. That field stays null until a real
    salary data source is integrated.
    """
    public_data = await _safe_fetch_public_data(data_provider, company.name)
    tech_stack = infer_tech_stack_from_jobs(session, company.id)
    job_count = len(
        session.exec(select(Job).where(Job.company_id == company.id)).all()
    )

    wiki_extract = public_data.summary_extract if public_data.found else None

    culture_request = build_company_culture_request(
        company.name, wiki_extract, tech_stack, job_count
    )
    reputation_request = build_company_reputation_request(company.name, wiki_extract)

    try:
        culture_result = await complete_with_fallback(culture_request)
        company.culture_summary = culture_result.content
    except AllProvidersFailedError:
        company.culture_summary = None

    try:
        reputation_result = await complete_with_fallback(reputation_request)
        company.reputation_summary = reputation_result.content
    except AllProvidersFailedError:
        company.reputation_summary = None

    if tech_stack:
        company.tech_stack = ", ".join(tech_stack)

    company.updated_at = datetime.now(timezone.utc)
    session.add(company)
    session.commit()
    session.refresh(company)
    return company
