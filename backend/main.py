from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.routers import auth, jobs, search, saved_jobs, stats, notes

app = FastAPI(
    title="NextHire API",
    description="Job Search & Career Platform API",
    version="1.0.0"
)

# -----------------------
# CORS (IMPORTANT)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",  # frontend
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# ROUTES
# -----------------------
app.include_router(auth.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(saved_jobs.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")

# -----------------------
# HEALTH CHECK
# -----------------------
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "NextHire API"
    }