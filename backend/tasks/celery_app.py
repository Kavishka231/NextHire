from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery = Celery(
    "nexthire",
    broker=REDIS_URL,
    backend=REDIS_URL
)

@celery.task
def test_task():
    return "Celery is working"