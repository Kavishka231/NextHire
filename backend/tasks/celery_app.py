from celery import Celery
from app.config import settings

celery_app = Celery(
    "nexthire",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["tasks.reminder_task"],
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
    },
)
