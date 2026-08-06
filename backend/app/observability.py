import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.config import settings


SAFE_LOG_FIELDS = {
    "event",
    "action",
    "actor_user_id",
    "target_user_id",
    "user_id",
    "job_id",
    "job_title",
    "company_name",
    "application_id",
    "saved_job_id",
    "account_type",
    "reason",
    "outcome",
    "task_name",
    "task_id",
    "exception_type",
    "method",
    "path",
    "status_code",
    "sent",
    "failed",
    "request_id",
    "correlation_id",
    "response_time_ms",
}

SENSITIVE_TEXT = re.compile(
    r"(?i)(bearer\s+)[^\s]+|"
    r"((?:authorization|password|token|refresh_token|reset_token|mail_password|smtp_password)"
    r"\s*[=:]\s*)[^\s&,]+|"
    r"([?&]token=)[^&\s]+"
)

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_context: ContextVar[str | None] = ContextVar("correlation_id", default=None)
user_id_context: ContextVar[int | str | None] = ContextVar("user_id", default=None)


def set_request_context(request_id: str, correlation_id: str):
    request_token = request_id_context.set(request_id)
    correlation_token = correlation_id_context.set(correlation_id)
    return request_token, correlation_token


def reset_request_context(request_token, correlation_token) -> None:
    request_id_context.reset(request_token)
    correlation_id_context.reset(correlation_token)


def set_user_context(user_id: int | str):
    return user_id_context.set(user_id)


def reset_user_context(user_token) -> None:
    user_id_context.reset(user_token)


def redact_text(value: str) -> str:
    return SENSITIVE_TEXT.sub(
        lambda match: f"{next(group for group in match.groups() if group)}[REDACTED]",
        value,
    )


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        context_fields = {
            "request_id": request_id_context.get(),
            "correlation_id": correlation_id_context.get(),
            "user_id": user_id_context.get(),
        }
        for field, value in context_fields.items():
            if value is not None and field not in payload:
                payload[field] = value
        for field in SAFE_LOG_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.LOG_LEVEL.upper())


def _before_send(event, hint):
    request = event.get("request")
    if request:
        request.pop("headers", None)
        request.pop("cookies", None)
        request.pop("data", None)
        request.pop("query_string", None)
    return event


def configure_sentry() -> None:
    if not settings.SENTRY_DSN:
        return
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.APP_RELEASE or None,
        send_default_pii=False,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        before_send=_before_send,
        integrations=[FastApiIntegration(), CeleryIntegration()],
    )
