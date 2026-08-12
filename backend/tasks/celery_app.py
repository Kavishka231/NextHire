import logging

from celery import Celery
from celery.schedules import crontab
from celery.signals import task_failure
from app.config import settings
from app.observability import configure_logging, configure_sentry
from app.metrics import CELERY_FAILURE_KEY
from redis import Redis

configure_logging()
configure_sentry()
logger = logging.getLogger(__name__)

celery_app = Celery(
    "nexthire",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["tasks.reminder_task", "tasks.email_task", "tasks.token_cleanup_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        # Run daily at 09:00 UTC
        "send-daily-reminders": {
            "task":     "tasks.reminder_task.send_reminders",
            "schedule": 86400,   # every 24 h in seconds
        },
        "cleanup-refresh-tokens": {
            "task": "tasks.token_cleanup_task.cleanup_refresh_tokens",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)


@task_failure.connect
def log_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    try:
        Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1).incr(CELERY_FAILURE_KEY)
    except Exception:
        logger.exception("Could not persist Celery failure metric")
    logger.error(
        "Celery task failed",
        extra={
            "event": "celery_task_failure",
            "task_name": getattr(sender, "name", "unknown"),
            "task_id": task_id,
            "exception_type": type(exception).__name__ if exception else "unknown",
        },
    )
