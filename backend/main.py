import logging
import time
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from sqlalchemy import text
from app.config import settings
from app.database import engine, get_db
from api.v1.routers import auth, search, jobs, saved_jobs, notes, stats, profile, admin, notifications, company, applications
from services.admin_seed import ensure_default_admin
from app.observability import (
    configure_logging,
    configure_sentry,
    reset_request_context,
    set_request_context,
    user_id_context,
)

configure_logging()
configure_sentry()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(application: FastAPI):
    if settings.SEED_ADMIN:
        db_provider = application.dependency_overrides.get(get_db, get_db)
        db_gen = db_provider()
        db = next(db_gen)
        try:
            ensure_default_admin(db)
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="NextHire — Job tracking platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _header_id(value: str | None) -> str:
    if not value:
        return str(uuid4())
    try:
        return str(UUID(value))
    except ValueError:
        return str(uuid4())


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = _header_id(request.headers.get("X-Request-ID"))
    correlation_id = _header_id(request.headers.get("X-Correlation-ID"))
    request_token, correlation_token = set_request_context(request_id, correlation_id)
    started_at = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        response_time_ms = round((time.perf_counter() - started_at) * 1000, 2)
        status_code = response.status_code if response else 500
        logger.info(
            "HTTP request completed",
            extra={
                "event": "http_request_completed",
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "response_time_ms": response_time_ms,
            },
        )
        if response:
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id
        user_id_context.set(None)
        reset_request_context(request_token, correlation_token)

app.include_router(auth.router,       prefix="/api/v1")
app.include_router(search.router,     prefix="/api/v1")
app.include_router(jobs.router,       prefix="/api/v1")
app.include_router(saved_jobs.router, prefix="/api/v1")
app.include_router(notes.router,      prefix="/api/v1")
app.include_router(stats.router,      prefix="/api/v1")
app.include_router(profile.router,    prefix="/api/v1")
app.include_router(admin.router,      prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(company.router,    prefix="/api/v1")
app.include_router(applications.router, prefix="/api/v1")


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logger.exception(
        "Unexpected API error",
        extra={
            "event": "unexpected_api_error",
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
            "exception_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/ready", tags=["Health"])
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    redis_client = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    redis_client.ping()
    return {"status": "ready", "database": "ok", "redis": "ok"}
