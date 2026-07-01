from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.contact import Contact
from app.models.interaction import Interaction
from app.schemas.contact import ContactCreate, ContactRead, ContactUpdate
from app.schemas.interaction import InteractionCreate, InteractionRead
from app.services.default_user import get_or_create_default_user

router = APIRouter(prefix="/contacts", tags=["contacts"])


def _get_or_404(session: Session, contact_id: int) -> Contact:
    contact = session.get(Contact, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.get("", response_model=list[ContactRead])
async def list_contacts(session: Session = Depends(get_session)) -> list[Contact]:
    user = get_or_create_default_user(session)
    return session.exec(select(Contact).where(Contact.user_id == user.id)).all()


@router.get("/follow-ups", response_model=list[ContactRead])
async def list_follow_ups(
    days_ahead: int = 7, session: Session = Depends(get_session)
) -> list[Contact]:
    """Contacts with a follow-up due now or within `days_ahead` days,
    overdue ones first (most overdue first), then soonest-upcoming."""
    user = get_or_create_default_user(session)
    horizon = datetime.now(timezone.utc) + timedelta(days=days_ahead)

    contacts = session.exec(
        select(Contact)
        .where(Contact.user_id == user.id)
        .where(Contact.next_follow_up_at.is_not(None))
        .where(Contact.next_follow_up_at <= horizon)
        .order_by(Contact.next_follow_up_at.asc())
    ).all()
    return contacts


@router.post("", response_model=ContactRead, status_code=201)
async def create_contact(
    payload: ContactCreate, session: Session = Depends(get_session)
) -> Contact:
    user = get_or_create_default_user(session)
    contact = Contact(user_id=user.id, **payload.model_dump())
    session.add(contact)
    session.commit()
    session.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactRead)
async def get_contact(contact_id: int, session: Session = Depends(get_session)) -> Contact:
    return _get_or_404(session, contact_id)


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(
    contact_id: int, payload: ContactUpdate, session: Session = Depends(get_session)
) -> Contact:
    contact = _get_or_404(session, contact_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    contact.updated_at = datetime.now(timezone.utc)
    session.add(contact)
    session.commit()
    session.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(contact_id: int, session: Session = Depends(get_session)) -> None:
    contact = _get_or_404(session, contact_id)
    session.delete(contact)
    session.commit()


@router.get("/{contact_id}/interactions", response_model=list[InteractionRead])
async def list_interactions(
    contact_id: int, session: Session = Depends(get_session)
) -> list[Interaction]:
    _get_or_404(session, contact_id)  # 404 if the contact doesn't exist
    return session.exec(
        select(Interaction)
        .where(Interaction.contact_id == contact_id)
        .order_by(Interaction.occurred_at.desc())
    ).all()


@router.post("/{contact_id}/interactions", response_model=InteractionRead, status_code=201)
async def create_interaction(
    contact_id: int, payload: InteractionCreate, session: Session = Depends(get_session)
) -> Interaction:
    _get_or_404(session, contact_id)
    data = payload.model_dump()
    if data.get("occurred_at") is None:
        data["occurred_at"] = datetime.now(timezone.utc)

    interaction = Interaction(contact_id=contact_id, **data)
    session.add(interaction)
    session.commit()
    session.refresh(interaction)
    return interaction
