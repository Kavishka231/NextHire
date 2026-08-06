import json
import logging
from uuid import UUID

from app.observability import (
    JsonFormatter,
    _before_send,
    reset_request_context,
    reset_user_context,
    set_request_context,
    set_user_context,
)


def test_json_logging_redacts_secrets_and_ignores_unsafe_fields():
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="authorization=Bearer-secret password=hunter2 token=reset-value",
        args=(),
        exc_info=None,
    )
    record.event = "authentication_failure"
    record.job_id = 42
    record.account_type = "candidate"
    record.password = "must-never-appear"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "authentication_failure"
    assert payload["job_id"] == 42
    assert payload["account_type"] == "candidate"
    assert "Bearer-secret" not in payload["message"]
    assert "hunter2" not in payload["message"]
    assert "reset-value" not in payload["message"]
    assert "must-never-appear" not in json.dumps(payload)


def test_sentry_hook_removes_sensitive_request_data():
    event = {
        "request": {
            "url": "https://example.test/api/v1/auth/login",
            "headers": {"Authorization": "Bearer secret"},
            "cookies": {"nexthire_refresh": "secret"},
            "data": {"password": "secret"},
            "query_string": "token=secret",
        },
    }

    sanitized = _before_send(event, {})

    assert sanitized["request"] == {
        "url": "https://example.test/api/v1/auth/login",
    }


def test_json_logging_includes_request_context():
    request_token, correlation_token = set_request_context("request-123", "correlation-456")
    user_token = set_user_context(42)
    try:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="request completed",
            args=(),
            exc_info=None,
        )

        payload = json.loads(JsonFormatter().format(record))

        assert payload["request_id"] == "request-123"
        assert payload["correlation_id"] == "correlation-456"
        assert payload["user_id"] == 42
    finally:
        reset_user_context(user_token)
        reset_request_context(request_token, correlation_token)


def test_request_logging_adds_correlation_headers(client):
    response = client.get("/health", headers={
        "X-Request-ID": "not-a-uuid",
        "X-Correlation-ID": "not-a-uuid",
    })

    assert response.status_code == 200
    assert UUID(response.headers["X-Request-ID"])
    assert UUID(response.headers["X-Correlation-ID"])
