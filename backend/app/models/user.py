from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """A registered CareerOps++ account. Multi-user auth (Milestone 8
    follow-up) - every other user-owned model (Application, Resume,
    Contact, SavedSearch) is scoped to a specific User via user_id, and
    every route enforces that a user can only see/modify their own data.
    See core/security.py and api/routes/auth.py for the auth flow."""

    id: int | None = Field(default=None, primary_key=True)
    full_name: str
    email: str = Field(index=True, unique=True)
    password_hash: str

    # Free-text / JSON-ish fields kept simple for Milestone 1; may move to
    # dedicated normalized tables (Skill, Goal) in a later milestone.
    headline: str | None = None
    skills: str | None = None  # comma-separated for now
    career_goals: str | None = None
    preferences: str | None = None  # JSON-encoded string

    # Added in Milestone 8 for browser-assisted application autofill -
    # these are the only fields BrowserAutomationSession is allowed to type
    # into a real application form (see field_classifier.ApplicantProfile).
    phone: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None

    # Uploaded resume - raw text extracted from the user's own PDF.
    # Used to extract skills for smart job filtering, and as the source
    # for autofill's resume-upload field when no structured resume exists.
    base_resume_text: str | None = None

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
