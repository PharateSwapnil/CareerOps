"""State machine for Application.status transitions.

Keeps transition rules in one place so the API layer doesn't need to know
the pipeline shape, and so the same rules could later back a kanban-style
drag-and-drop UI without duplicating validation logic.
"""
from app.models.application import ApplicationStatus

# Map of current status -> set of statuses it's allowed to move to.
# REJECTED and WITHDRAWN are terminal (no outgoing transitions).
ALLOWED_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.SAVED: {
        ApplicationStatus.APPLIED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.APPLIED: {
        ApplicationStatus.PHONE_SCREEN,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.PHONE_SCREEN: {
        ApplicationStatus.INTERVIEWING,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.INTERVIEWING: {
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.OFFER: {
        ApplicationStatus.REJECTED,  # offer declined by the candidate, or rescinded
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.WITHDRAWN: set(),
}


class InvalidTransitionError(Exception):
    def __init__(self, current: ApplicationStatus, target: ApplicationStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition Application from {current} to {target}")


def validate_transition(current: ApplicationStatus, target: ApplicationStatus) -> None:
    """Raises InvalidTransitionError if the transition isn't allowed.
    A no-op transition (current == target) is always allowed."""
    if current == target:
        return
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise InvalidTransitionError(current, target)
