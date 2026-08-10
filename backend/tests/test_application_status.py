import pytest

from core.application_status import ApplicationStatus, can_transition_application_status


@pytest.mark.parametrize(("current", "requested"), [
    ("submitted", ApplicationStatus.REVIEWING),
    ("submitted", ApplicationStatus.REJECTED),
    ("submitted", ApplicationStatus.WITHDRAWN),
    ("reviewing", ApplicationStatus.SHORTLISTED),
    ("reviewing", ApplicationStatus.INTERVIEW),
    ("reviewing", ApplicationStatus.REJECTED),
    ("reviewing", ApplicationStatus.WITHDRAWN),
    ("shortlisted", ApplicationStatus.INTERVIEW),
    ("shortlisted", ApplicationStatus.REJECTED),
    ("shortlisted", ApplicationStatus.WITHDRAWN),
    ("interview", ApplicationStatus.OFFERED),
    ("interview", ApplicationStatus.REJECTED),
    ("interview", ApplicationStatus.WITHDRAWN),
    ("offered", ApplicationStatus.WITHDRAWN),
])
def test_allowed_application_status_transitions(current, requested):
    assert can_transition_application_status(current, requested)


@pytest.mark.parametrize("status", list(ApplicationStatus))
def test_repeating_application_status_is_idempotent(status):
    assert can_transition_application_status(status.value, status)


@pytest.mark.parametrize(("current", "requested"), [
    ("rejected", ApplicationStatus.SUBMITTED),
    ("withdrawn", ApplicationStatus.SUBMITTED),
    ("offered", ApplicationStatus.REVIEWING),
    ("interview", ApplicationStatus.SUBMITTED),
    ("shortlisted", ApplicationStatus.REVIEWING),
    ("unknown", ApplicationStatus.REVIEWING),
])
def test_forbidden_application_status_transitions(current, requested):
    assert not can_transition_application_status(current, requested)
