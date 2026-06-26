from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from core.dependencies import get_current_user
from services.adzuna_service import get_job_categories, search_jobs
from services.job_service import upsert_jobs

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/jobs")
async def search(
    keywords: str = Query(...),
    location: str = "",
    page: int = 1,
    results_per_page: int = 20,
    salary_min: int | None = None,
    salary_max: int | None = None,
    full_time: bool | None = None,
    sort_by: str = "relevance",
    country: str = "gb",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    results = await search_jobs(
        keywords, location, page, results_per_page,
        salary_min, salary_max, full_time, sort_by, country,
    )
    upsert_jobs(db, results["jobs"])
    return results


@router.get("/categories")
async def categories(current_user=Depends(get_current_user)):
    return await get_job_categories()
