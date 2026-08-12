import time

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from redis import Redis
from sqlalchemy import text
from starlette.routing import Match

from app.config import settings
from app.database import engine


STARTED_AT = time.time()
CELERY_FAILURE_KEY = "nexthire:metrics:celery_task_failures_total"

HTTP_REQUESTS = Counter(
    "nexthire_http_requests_total",
    "Completed HTTP requests.",
    ["method", "route", "status"],
)
HTTP_DURATION = Histogram(
    "nexthire_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
HTTP_IN_PROGRESS = Gauge(
    "nexthire_http_requests_in_progress",
    "HTTP requests currently executing.",
    ["method"],
)
DATABASE_UP = Gauge("nexthire_database_up", "Whether PostgreSQL is reachable (1/0).")
REDIS_UP = Gauge("nexthire_redis_up", "Whether Redis is reachable (1/0).")
CELERY_QUEUE_DEPTH = Gauge(
    "nexthire_celery_queue_depth", "Messages waiting in the default Celery queue."
)
CELERY_TASK_FAILURES = Gauge(
    "nexthire_celery_task_failures_total",
    "Celery task failures persisted in Redis across worker processes.",
)
DB_POOL_CHECKED_OUT = Gauge(
    "nexthire_database_pool_checked_out", "Database connections currently checked out."
)
DB_POOL_SIZE = Gauge("nexthire_database_pool_size", "Configured database pool size.")
APP_UPTIME = Gauge("nexthire_application_uptime_seconds", "API process uptime in seconds.")
APP_INFO = Gauge("nexthire_application_info", "Application build information.", ["release", "environment"])
APP_INFO.labels(settings.APP_RELEASE or "unknown", settings.ENVIRONMENT).set(1)


def route_label(request) -> str:
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    path_regex = getattr(route, "path_regex", None)
    if template and path_regex:
        raw_path = request.url.path
        for index, character in enumerate(raw_path):
            if character == "/" and path_regex.fullmatch(raw_path[index:]):
                return raw_path[:index] + template
    for candidate in request.app.routes:
        match, _ = candidate.matches(request.scope)
        if match == Match.FULL:
            return getattr(candidate, "path", "unmatched")
    return "unmatched"


def record_request(method: str, route: str, status: int, duration: float) -> None:
    HTTP_REQUESTS.labels(method, route, str(status)).inc()
    HTTP_DURATION.labels(method, route).observe(duration)


def refresh_runtime_metrics() -> None:
    APP_UPTIME.set(max(0, time.time() - STARTED_AT))
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        DATABASE_UP.set(1)
    except Exception:
        DATABASE_UP.set(0)

    pool = engine.pool
    if hasattr(pool, "checkedout"):
        checked_out = pool.checkedout
        DB_POOL_CHECKED_OUT.set(checked_out() if callable(checked_out) else checked_out)
    if hasattr(pool, "size"):
        pool_size = pool.size
        DB_POOL_SIZE.set(pool_size() if callable(pool_size) else pool_size)

    try:
        redis_client = Redis.from_url(
            settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1
        )
        redis_client.ping()
        REDIS_UP.set(1)
        CELERY_QUEUE_DEPTH.set(redis_client.llen("celery"))
        CELERY_TASK_FAILURES.set(int(redis_client.get(CELERY_FAILURE_KEY) or 0))
    except Exception:
        REDIS_UP.set(0)
        CELERY_QUEUE_DEPTH.set(0)


def metrics_payload() -> bytes:
    refresh_runtime_metrics()
    return generate_latest()
