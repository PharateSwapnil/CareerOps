"""Resume version-chain logic: creating new versions, walking a chain's
history, diffing two versions, and rolling back to an older version by
creating a new version with the old content (keeping every row immutable).

Chain structure: each Resume optionally points at `parent_version_id`. A
chain's root is the version with `parent_version_id is None`. This module
doesn't assume the chain is a simple linked list end-to-end in the DB
schema - it discovers membership by walking parent pointers - so it works
correctly even after a rollback creates a new branch tip.
"""
import difflib

from sqlmodel import Session, select

from app.models.resume import Resume


class ResumeNotFoundError(Exception):
    pass


def _find_root_id(session: Session, resume: Resume) -> int:
    current = resume
    while current.parent_version_id is not None:
        parent = session.get(Resume, current.parent_version_id)
        if parent is None:
            break
        current = parent
    return current.id


def get_version_history(session: Session, resume_id: int) -> list[Resume]:
    """Returns every version in the same chain as `resume_id`, oldest first."""
    target = session.get(Resume, resume_id)
    if target is None:
        raise ResumeNotFoundError(f"Resume {resume_id} not found")

    root_id = _find_root_id(session, target)
    candidates = session.exec(
        select(Resume).where(Resume.user_id == target.user_id)
    ).all()
    chain = [r for r in candidates if _find_root_id(session, r) == root_id]
    chain.sort(key=lambda r: r.version_number)
    return chain


def create_new_version(
    session: Session,
    parent_id: int,
    content: str,
    label: str | None = None,
    tailored_for_job_id: int | None = None,
) -> Resume:
    """Creates a new version extending the chain from `parent_id`."""
    parent = session.get(Resume, parent_id)
    if parent is None:
        raise ResumeNotFoundError(f"Resume {parent_id} not found")

    new_version = Resume(
        user_id=parent.user_id,
        label=label or parent.label,
        content=content,
        tailored_for_job_id=(
            tailored_for_job_id if tailored_for_job_id is not None else parent.tailored_for_job_id
        ),
        parent_version_id=parent.id,
        version_number=parent.version_number + 1,
    )
    session.add(new_version)
    session.commit()
    session.refresh(new_version)
    return new_version


def rollback_to_version(session: Session, resume_id: int) -> Resume:
    """Creates a new version at the head of the chain whose content matches
    `resume_id`'s content - i.e. "revert to this version" without deleting
    or mutating any existing row."""
    target = session.get(Resume, resume_id)
    if target is None:
        raise ResumeNotFoundError(f"Resume {resume_id} not found")

    chain = get_version_history(session, resume_id)
    latest = max(chain, key=lambda r: r.version_number)

    return create_new_version(
        session,
        parent_id=latest.id,
        content=target.content,
        label=target.label,
        tailored_for_job_id=target.tailored_for_job_id,
    )


def diff_versions(session: Session, from_id: int, to_id: int) -> str:
    from_resume = session.get(Resume, from_id)
    to_resume = session.get(Resume, to_id)
    if from_resume is None or to_resume is None:
        raise ResumeNotFoundError("One or both resume versions not found")

    diff_lines = difflib.unified_diff(
        from_resume.content.splitlines(keepends=True),
        to_resume.content.splitlines(keepends=True),
        fromfile=f"v{from_resume.version_number}",
        tofile=f"v{to_resume.version_number}",
    )
    return "".join(diff_lines)
