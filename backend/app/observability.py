import json
import logging
import re
import sys
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
}

SENSITIVE_TEXT = re.compile(
    r"(?i)(bearer\s+)[^\s]+|"
    r"((?:authorization|password|token|refresh_token|reset_token|mail_password|smtp_password)"
    r"\s*[=:]\s*)[^\s&,]+|"
    r"([?&]token=)[^&\s]+"
)


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
