from enum import Enum


class ApplicationStatus(str, Enum):
    SUBMITTED = "submitted"
    REVIEWING = "reviewing"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    OFFERED = "offered"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


APPLICATION_STATUS_TRANSITIONS = {
    ApplicationStatus.SUBMITTED: frozenset({
        ApplicationStatus.REVIEWING,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }),
    ApplicationStatus.REVIEWING: frozenset({
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }),
    ApplicationStatus.SHORTLISTED: frozenset({
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }),
    ApplicationStatus.INTERVIEW: frozenset({
        ApplicationStatus.OFFERED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }),
    ApplicationStatus.OFFERED: frozenset({ApplicationStatus.WITHDRAWN}),
    ApplicationStatus.REJECTED: frozenset(),
    ApplicationStatus.WITHDRAWN: frozenset(),
}


def can_transition_application_status(current: str, requested: ApplicationStatus) -> bool:
    try:
        current_status = ApplicationStatus(current)
    except ValueError:
        return False
    return (
        requested == current_status
        or requested in APPLICATION_STATUS_TRANSITIONS[current_status]
    )
