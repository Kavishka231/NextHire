from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.routers import auth, jobs, search, saved_jobs, stats, notes

app = FastAPI(
    title="NextHire API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(saved_jobs.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}