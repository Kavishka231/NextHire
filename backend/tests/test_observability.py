import json
import logging

from app.observability import JsonFormatter, _before_send


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
    record.password = "must-never-appear"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "authentication_failure"
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
