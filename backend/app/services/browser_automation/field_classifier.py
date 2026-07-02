"""Deciding what to do with a detected form field is pure decision logic
with no browser dependency - deliberately kept separate from
`playwright_driver.py` so it can be fully unit-tested without a real
browser (which this dev sandbox can't run - see that module's docstring).

Design principle: default to NOT filling. A false negative (pausing on a
field we could actually have filled) just costs the user a click to
resume. A false positive (confidently filling the wrong thing into a field
we misclassified) puts wrong data into a real application - a much worse
failure mode. Every classification here is deliberately conservative.
"""
from dataclasses import dataclass
from enum import Enum


class FieldCategory(str, Enum):
    FULL_NAME = "full_name"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    EMAIL = "email"
    PHONE = "phone"
    LINKEDIN_URL = "linkedin_url"
    PORTFOLIO_URL = "portfolio_url"
    RESUME_UPLOAD = "resume_upload"
    COVER_LETTER = "cover_letter"
    UNKNOWN = "unknown"


class PauseReason(str, Enum):
    AUTH = "auth"
    CAPTCHA = "captcha"
    UNKNOWN_REQUIRED_FIELD = "unknown_required_field"


@dataclass
class DetectedField:
    """What the Playwright driver reports about one form field it found on
    the page - deliberately just plain strings/bools, no Playwright types,
    so this stays testable without a browser."""

    label: str  # visible label text, or nearby placeholder/aria-label
    input_type: str  # "text", "email", "tel", "file", "password", "textarea", etc.
    name: str = ""  # the `name` or `id` HTML attribute, often more reliable than label
    required: bool = False


@dataclass
class ApplicantProfile:
    """The subset of a CareerOps++ user's own data that's safe to
    autofill into a job application form - all of it is information the
    user already entered into their own User/Resume records, never
    invented or fetched from elsewhere."""

    full_name: str
    email: str
    phone: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    resume_file_path: str | None = None
    cover_letter_text: str | None = None


@dataclass
class FillPlan:
    # (field, value_to_fill) pairs for fields we're confident about
    fills: list[tuple[DetectedField, str]]
    # None if nothing requires a pause; otherwise why we're stopping
    pause_reason: PauseReason | None
    pause_detail: str | None = None


# (category, keywords) - matched against a lowercased label+name string.
# Order matters: more specific patterns are checked before generic ones
# (e.g. "first name" before a bare "name" match).
_CATEGORY_KEYWORDS: list[tuple[FieldCategory, list[str]]] = [
    (FieldCategory.EMAIL, ["email", "e-mail"]),
    (FieldCategory.PHONE, ["phone", "mobile", "telephone"]),
    (FieldCategory.LINKEDIN_URL, ["linkedin"]),
    (FieldCategory.PORTFOLIO_URL, ["portfolio", "website", "github", "personal site"]),
    (FieldCategory.FIRST_NAME, ["first name", "firstname", "given name"]),
    (FieldCategory.LAST_NAME, ["last name", "lastname", "surname", "family name"]),
    (FieldCategory.FULL_NAME, ["full name", "your name", "candidate name"]),
    (FieldCategory.RESUME_UPLOAD, ["resume", "cv", "curriculum vitae"]),
    (FieldCategory.COVER_LETTER, ["cover letter", "coverletter"]),
]

_CAPTCHA_MARKERS = ["captcha", "hcaptcha", "recaptcha", "cf-turnstile"]
_AUTH_MARKERS = ["password", "sign in", "log in", "login", "sso"]


def classify_field(field: DetectedField) -> FieldCategory:
    haystack = f"{field.label} {field.name}".lower()

    if field.input_type == "password":
        # Handled as an auth signal at the page level, not filled here.
        return FieldCategory.UNKNOWN

    for category, keywords in _CATEGORY_KEYWORDS:
        if any(kw in haystack for kw in keywords):
            return category

    # A bare "name" match only counts if nothing more specific matched -
    # otherwise "first name" would also match here and get double-counted.
    if "name" in haystack:
        return FieldCategory.FULL_NAME

    return FieldCategory.UNKNOWN


def page_has_auth_signal(page_text: str) -> bool:
    lowered = page_text.lower()
    return any(marker in lowered for marker in _AUTH_MARKERS)


def page_has_captcha_signal(page_html: str) -> bool:
    lowered = page_html.lower()
    return any(marker in lowered for marker in _CAPTCHA_MARKERS)


def _value_for_category(category: FieldCategory, profile: ApplicantProfile) -> str | None:
    mapping = {
        FieldCategory.FULL_NAME: profile.full_name,
        FieldCategory.FIRST_NAME: profile.full_name.split(" ")[0] if profile.full_name else None,
        FieldCategory.LAST_NAME: (
            profile.full_name.split(" ")[-1]
            if profile.full_name and " " in profile.full_name
            else None
        ),
        FieldCategory.EMAIL: profile.email,
        FieldCategory.PHONE: profile.phone,
        FieldCategory.LINKEDIN_URL: profile.linkedin_url,
        FieldCategory.PORTFOLIO_URL: profile.portfolio_url,
        FieldCategory.COVER_LETTER: profile.cover_letter_text,
        # RESUME_UPLOAD is handled separately via set_input_files, not a
        # text value - deliberately excluded from this text-value mapping.
    }
    return mapping.get(category)


def build_fill_plan(fields: list[DetectedField], profile: ApplicantProfile) -> FillPlan:
    """Decides what to fill and whether a pause is needed. Stops at the
    first unfillable REQUIRED field rather than trying to fill everything
    else first - an incompletely-scanned form is safer to hand back to the
    user than one we've partially filled while still uncertain about it."""
    fills: list[tuple[DetectedField, str]] = []

    for field in fields:
        if field.input_type == "password":
            return FillPlan(fills=fills, pause_reason=PauseReason.AUTH, pause_detail=field.label)

        category = classify_field(field)

        if category == FieldCategory.RESUME_UPLOAD:
            if profile.resume_file_path:
                fills.append((field, profile.resume_file_path))
                continue
            if field.required:
                return FillPlan(
                    fills=fills,
                    pause_reason=PauseReason.UNKNOWN_REQUIRED_FIELD,
                    pause_detail=f"Resume upload field ('{field.label}') but no resume file is available",
                )
            continue

        value = _value_for_category(category, profile)
        if value:
            fills.append((field, value))
        elif field.required:
            return FillPlan(
                fills=fills,
                pause_reason=PauseReason.UNKNOWN_REQUIRED_FIELD,
                pause_detail=f"Required field '{field.label}' couldn't be confidently classified or has no data",
            )
        # Non-required unknown fields are silently skipped - pausing on
        # every optional field would make this unusably tedious.

    return FillPlan(fills=fills, pause_reason=None)
