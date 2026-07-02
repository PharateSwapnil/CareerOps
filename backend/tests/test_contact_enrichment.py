import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models.company import Company
from app.models.contact import Contact
from app.models.user import User
from app.providers.contact_enrichment_providers.base import EmailLookupResult
from app.services.contact_enrichment import _extract_domain, _split_name, enrich_contact_email


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture()
def user(session):
    u = User(full_name="Test User", email="test@example.com")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


class _FakeProvider:
    name = "fake"

    def __init__(self, result: EmailLookupResult) -> None:
        self._result = result

    async def find_email(self, first_name, last_name, domain) -> EmailLookupResult:
        self.called_with = (first_name, last_name, domain)
        return self._result


def test_extract_domain_from_bare_domain():
    assert _extract_domain("stripe.com") == "stripe.com"


def test_extract_domain_from_full_url():
    assert _extract_domain("https://www.stripe.com/about") == "stripe.com"


def test_split_name_two_parts():
    assert _split_name("Jane Doe") == ("Jane", "Doe")


def test_split_name_multiple_parts_uses_first_and_last():
    assert _split_name("Jane Middle Doe") == ("Jane", "Doe")


def test_split_name_single_part():
    assert _split_name("Cher") == ("Cher", "Cher")


@pytest.mark.asyncio
async def test_enrich_contact_email_finds_and_fills(session, user):
    company = Company(name="Acme Corp", website="acme.com")
    session.add(company)
    session.commit()
    session.refresh(company)

    contact = Contact(user_id=user.id, full_name="Jane Doe", company_id=company.id)
    session.add(contact)
    session.commit()
    session.refresh(contact)

    provider = _FakeProvider(EmailLookupResult(found=True, email="jane@acme.com", confidence=90))
    result = await enrich_contact_email(session, contact, provider)

    assert result.found is True
    assert contact.email == "jane@acme.com"
    assert provider.called_with == ("Jane", "Doe", "acme.com")


@pytest.mark.asyncio
async def test_enrich_contact_email_never_overwrites_existing_email(session, user):
    company = Company(name="Acme Corp", website="acme.com")
    session.add(company)
    session.commit()
    session.refresh(company)

    contact = Contact(
        user_id=user.id, full_name="Jane Doe", company_id=company.id, email="already@set.com"
    )
    session.add(contact)
    session.commit()
    session.refresh(contact)

    provider = _FakeProvider(EmailLookupResult(found=True, email="wrong@acme.com", confidence=90))
    result = await enrich_contact_email(session, contact, provider)

    # Provider should never even be called since email is already set.
    assert not hasattr(provider, "called_with")
    assert contact.email == "already@set.com"


@pytest.mark.asyncio
async def test_enrich_contact_email_without_company_returns_not_found(session, user):
    contact = Contact(user_id=user.id, full_name="Jane Doe", company_id=None)
    session.add(contact)
    session.commit()
    session.refresh(contact)

    provider = _FakeProvider(EmailLookupResult(found=True, email="jane@acme.com"))
    result = await enrich_contact_email(session, contact, provider)

    assert result.found is False
    assert contact.email is None


@pytest.mark.asyncio
async def test_enrich_contact_email_company_without_website_returns_not_found(session, user):
    company = Company(name="No Website Corp")  # website left unset
    session.add(company)
    session.commit()
    session.refresh(company)

    contact = Contact(user_id=user.id, full_name="Jane Doe", company_id=company.id)
    session.add(contact)
    session.commit()
    session.refresh(contact)

    provider = _FakeProvider(EmailLookupResult(found=True, email="jane@acme.com"))
    result = await enrich_contact_email(session, contact, provider)

    assert result.found is False
