from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.contact import Contact
from app.models.interaction import Interaction
from app.models.user import User
from app.providers.contact_enrichment_providers.registry import get_provider
from app.schemas.contact import (
    ContactCreate,
    ContactRead,
    ContactUpdate,
    EmailEnrichmentResponse,
)
from app.schemas.interaction import InteractionCreate, InteractionRead
from app.services.contact_enrichment import enrich_contact_email

router = APIRouter(prefix="/contacts", tags=["contacts"])


def _get_owned_or_404(session: Session, contact_id: int, user: User) -> Contact:
    contact = session.get(Contact, contact_id)
    if contact is None or contact.user_id != user.id:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.get("", response_model=list[ContactRead])
async def list_contacts(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[Contact]:
    return session.exec(select(Contact).where(Contact.user_id == current_user.id)).all()


@router.get("/follow-ups", response_model=list[ContactRead])
async def list_follow_ups(
    days_ahead: int = 7,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[Contact]:
    """Contacts with a follow-up due now or within `days_ahead` days,
    overdue ones first (most overdue first), then soonest-upcoming."""
    horizon = datetime.now(timezone.utc) + timedelta(days=days_ahead)

    contacts = session.exec(
        select(Contact)
        .where(Contact.user_id == current_user.id)
        .where(Contact.next_follow_up_at.is_not(None))
        .where(Contact.next_follow_up_at <= horizon)
        .order_by(Contact.next_follow_up_at.asc())
    ).all()
    return contacts


@router.post("", response_model=ContactRead, status_code=201)
async def create_contact(
    payload: ContactCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Contact:
    contact = Contact(user_id=current_user.id, **payload.model_dump())
    session.add(contact)
    session.commit()
    session.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactRead)
async def get_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Contact:
    return _get_owned_or_404(session, contact_id, current_user)


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: int,
    payload: ContactUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Contact:
    contact = _get_owned_or_404(session, contact_id, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    contact.updated_at = datetime.now(timezone.utc)
    session.add(contact)
    session.commit()
    session.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    contact = _get_owned_or_404(session, contact_id, current_user)
    session.delete(contact)
    session.commit()


@router.post("/{contact_id}/enrich-email", response_model=EmailEnrichmentResponse)
async def enrich_email(
    contact_id: int,
    provider_name: str = "hunter",
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> EmailEnrichmentResponse:
    """Looks up a likely professional email for this contact via a
    third-party data provider (Hunter.io by default) - opt-in, requires
    the user's own API key configured, and never overwrites an email the
    user already entered. See services/contact_enrichment.py for why this
    calls an external provider rather than scraping LinkedIn directly."""
    contact = _get_owned_or_404(session, contact_id, current_user)
    provider = get_provider(provider_name)
    result = await enrich_contact_email(session, contact, provider)
    session.refresh(contact)
    return EmailEnrichmentResponse(
        contact=contact, found=result.found, confidence=result.confidence
    )


@router.get("/{contact_id}/interactions", response_model=list[InteractionRead])
async def list_interactions(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[Interaction]:
    _get_owned_or_404(session, contact_id, current_user)  # 404 if not yours
    return session.exec(
        select(Interaction)
        .where(Interaction.contact_id == contact_id)
        .order_by(Interaction.occurred_at.desc())
    ).all()


@router.post("/{contact_id}/interactions", response_model=InteractionRead, status_code=201)
async def create_interaction(
    contact_id: int,
    payload: InteractionCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Interaction:
    _get_owned_or_404(session, contact_id, current_user)
    data = payload.model_dump()
    if data.get("occurred_at") is None:
        data["occurred_at"] = datetime.now(timezone.utc)

    interaction = Interaction(contact_id=contact_id, **data)
    session.add(interaction)
    session.commit()
    session.refresh(interaction)
    return interaction
