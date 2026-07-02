from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.schemas.user import UserProfileRead, UserProfileUpdate
from app.services.default_user import get_or_create_default_user

router = APIRouter(prefix="/me", tags=["profile"])


@router.get("", response_model=UserProfileRead)
async def get_profile(session: Session = Depends(get_session)) -> User:
    return get_or_create_default_user(session)


@router.patch("", response_model=UserProfileRead)
async def update_profile(
    payload: UserProfileUpdate, session: Session = Depends(get_session)
) -> User:
    user = get_or_create_default_user(session)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    user.updated_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
