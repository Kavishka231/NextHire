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


def test_metrics_expose_http_runtime_and_dependency_series(client):
    client.get("/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "nexthire_http_requests_total" in body
    assert 'route="/health"' in body
    assert "nexthire_http_request_duration_seconds_bucket" in body
    assert "nexthire_database_up 1.0" in body
    assert "nexthire_redis_up" in body
    assert "nexthire_celery_queue_depth" in body
    assert "nexthire_celery_task_failures_total" in body
    assert "nexthire_application_uptime_seconds" in body


def test_metrics_do_not_use_raw_resource_ids_as_route_labels(client):
    client.get("/api/v1/jobs/987654321")
    response = client.get("/metrics")

    metric_lines = [
        line for line in response.text.splitlines()
        if line.startswith("nexthire_http_requests_total")
    ]
    assert any('route="/api/v1/jobs/{job_id}"' in line for line in metric_lines)
    assert all('route="/api/v1/jobs/987654321"' not in line for line in metric_lines)
