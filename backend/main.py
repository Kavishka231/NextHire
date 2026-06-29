from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import get_db
from api.v1.routers import auth, search, jobs, saved_jobs, notes, stats, profile, admin, notifications, company
from services.admin_seed import ensure_default_admin

app = FastAPI(
    title=settings.APP_NAME,
    description="NextHire — Job tracking platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:5500",
        "http://127.0.0.1",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.on_event("startup")
def seed_admin_account():
    db_provider = app.dependency_overrides.get(get_db, get_db)
    db_gen = db_provider()
    db = next(db_gen)
    try:
        ensure_default_admin(db)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "app": settings.APP_NAME}
