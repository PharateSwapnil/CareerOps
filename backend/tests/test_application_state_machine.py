import pytest

from app.models.application import ApplicationStatus
from app.services.application_state_machine import InvalidTransitionError, validate_transition


def test_valid_forward_transitions():
    validate_transition(ApplicationStatus.SAVED, ApplicationStatus.APPLIED)
    validate_transition(ApplicationStatus.APPLIED, ApplicationStatus.PHONE_SCREEN)
    validate_transition(ApplicationStatus.PHONE_SCREEN, ApplicationStatus.INTERVIEWING)
    validate_transition(ApplicationStatus.INTERVIEWING, ApplicationStatus.OFFER)


def test_same_status_is_noop():
    validate_transition(ApplicationStatus.APPLIED, ApplicationStatus.APPLIED)


def test_rejection_allowed_from_any_active_stage():
    for status in [
        ApplicationStatus.APPLIED,
        ApplicationStatus.PHONE_SCREEN,
        ApplicationStatus.INTERVIEWING,
        ApplicationStatus.OFFER,
    ]:
        validate_transition(status, ApplicationStatus.REJECTED)


def test_cannot_skip_stages():
    with pytest.raises(InvalidTransitionError):
        validate_transition(ApplicationStatus.SAVED, ApplicationStatus.INTERVIEWING)


def test_terminal_statuses_have_no_outgoing_transitions():
    with pytest.raises(InvalidTransitionError):
        validate_transition(ApplicationStatus.REJECTED, ApplicationStatus.APPLIED)
    with pytest.raises(InvalidTransitionError):
        validate_transition(ApplicationStatus.WITHDRAWN, ApplicationStatus.SAVED)


def test_cannot_go_backward():
    with pytest.raises(InvalidTransitionError):
        validate_transition(ApplicationStatus.INTERVIEWING, ApplicationStatus.APPLIED)
