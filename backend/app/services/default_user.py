"""CareerOps++ is local-first and single-user until real auth is built (see
ARCHITECTURE.md - "Auth beyond a single local user" is explicitly out of
scope for now). Rather than requiring every request to pass a user_id, this
helper gets-or-creates a single default local user so Milestone 4's
Application/Resume endpoints have something to attach records to.

This is a deliberate, temporary simplification - it should be replaced by
real user resolution (from an auth session) once Milestone 4's roadmap item
for auth is tackled. Grep for `get_or_create_default_user` when that
happens.
"""
from sqlmodel import Session, select

from app.models.user import User

DEFAULT_USER_EMAIL = "you@localhost"


def get_or_create_default_user(session: Session) -> User:
    existing = session.exec(select(User).where(User.email == DEFAULT_USER_EMAIL)).first()
    if existing:
        return existing

    user = User(full_name="Local User", email=DEFAULT_USER_EMAIL)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
