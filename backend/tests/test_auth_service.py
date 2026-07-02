import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.services.auth_service import (
    AuthError,
    authenticate_user,
    issue_tokens,
    refresh_access_token,
    register_user,
    revoke_refresh_token,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_register_user_hashes_password(session):
    user = register_user(session, "Jane Doe", "jane@example.com", "hunter2")
    assert user.password_hash != "hunter2"
    assert len(user.password_hash) > 20


def test_register_user_rejects_duplicate_email(session):
    register_user(session, "Jane Doe", "jane@example.com", "hunter2")
    with pytest.raises(AuthError):
        register_user(session, "Someone Else", "jane@example.com", "different")


def test_authenticate_user_success(session):
    register_user(session, "Jane Doe", "jane@example.com", "hunter2")
    user = authenticate_user(session, "jane@example.com", "hunter2")
    assert user.email == "jane@example.com"


def test_authenticate_user_wrong_password(session):
    register_user(session, "Jane Doe", "jane@example.com", "hunter2")
    with pytest.raises(AuthError):
        authenticate_user(session, "jane@example.com", "wrong")


def test_authenticate_user_unknown_email(session):
    with pytest.raises(AuthError):
        authenticate_user(session, "nobody@example.com", "anything")


def test_issue_tokens_creates_refresh_token_row(session):
    from sqlmodel import select

    from app.models.refresh_token import RefreshToken

    user = register_user(session, "Jane Doe", "jane@example.com", "hunter2")
    access_token, refresh_token = issue_tokens(session, user)

    assert access_token
    assert refresh_token

    stored = session.exec(select(RefreshToken).where(RefreshToken.user_id == user.id)).all()
    assert len(stored) == 1
    assert stored[0].revoked is False


def test_refresh_access_token_succeeds_with_valid_token(session):
    user = register_user(session, "Jane Doe", "jane@example.com", "hunter2")
    _, refresh_token = issue_tokens(session, user)

    new_access_token = refresh_access_token(session, refresh_token)
    assert new_access_token


def test_refresh_access_token_fails_after_revocation(session):
    user = register_user(session, "Jane Doe", "jane@example.com", "hunter2")
    _, refresh_token = issue_tokens(session, user)

    revoke_refresh_token(session, refresh_token)

    with pytest.raises(AuthError):
        refresh_access_token(session, refresh_token)


def test_revoke_unknown_token_does_not_raise(session):
    # Logout should always succeed from the client's perspective, even for
    # a garbage/already-expired token.
    revoke_refresh_token(session, "not-a-real-token")
