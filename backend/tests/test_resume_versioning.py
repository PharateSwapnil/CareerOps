import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models.resume import Resume
from app.models.user import User
from app.services.resume_versioning import (
    ResumeNotFoundError,
    create_new_version,
    diff_versions,
    get_version_history,
    rollback_to_version,
)


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


def test_create_version_increments_version_number(session, user):
    v1 = Resume(user_id=user.id, label="Base", content="v1 content", version_number=1)
    session.add(v1)
    session.commit()
    session.refresh(v1)

    v2 = create_new_version(session, parent_id=v1.id, content="v2 content")

    assert v2.version_number == 2
    assert v2.parent_version_id == v1.id
    assert v2.label == "Base"  # inherited from parent


def test_get_version_history_returns_full_chain_oldest_first(session, user):
    v1 = Resume(user_id=user.id, label="Base", content="v1", version_number=1)
    session.add(v1)
    session.commit()
    session.refresh(v1)

    v2 = create_new_version(session, parent_id=v1.id, content="v2")
    v3 = create_new_version(session, parent_id=v2.id, content="v3")

    history = get_version_history(session, v3.id)

    assert [r.version_number for r in history] == [1, 2, 3]
    assert history[0].id == v1.id
    assert history[-1].id == v3.id


def test_history_lookup_works_from_any_version_in_chain(session, user):
    v1 = Resume(user_id=user.id, label="Base", content="v1", version_number=1)
    session.add(v1)
    session.commit()
    session.refresh(v1)
    v2 = create_new_version(session, parent_id=v1.id, content="v2")
    create_new_version(session, parent_id=v2.id, content="v3")

    # Looking up history from the middle version should still return all 3.
    history = get_version_history(session, v2.id)
    assert len(history) == 3


def test_rollback_creates_new_head_version_with_old_content(session, user):
    v1 = Resume(user_id=user.id, label="Base", content="original content", version_number=1)
    session.add(v1)
    session.commit()
    session.refresh(v1)
    v2 = create_new_version(session, parent_id=v1.id, content="changed content")

    rolled_back = rollback_to_version(session, v1.id)

    assert rolled_back.content == "original content"
    assert rolled_back.version_number == 3  # new head, not overwriting v1 or v2
    assert rolled_back.parent_version_id == v2.id

    # v1 and v2 remain unmodified (immutability).
    session.refresh(v1)
    session.refresh(v2)
    assert v1.content == "original content"
    assert v2.content == "changed content"


def test_diff_versions_produces_unified_diff(session, user):
    v1 = Resume(user_id=user.id, label="Base", content="line1\nline2\n", version_number=1)
    session.add(v1)
    session.commit()
    session.refresh(v1)
    v2 = create_new_version(session, parent_id=v1.id, content="line1\nline2 changed\n")

    diff_text = diff_versions(session, v1.id, v2.id)

    assert "-line2" in diff_text
    assert "+line2 changed" in diff_text


def test_not_found_raises_resume_not_found_error(session):
    with pytest.raises(ResumeNotFoundError):
        get_version_history(session, 999)
