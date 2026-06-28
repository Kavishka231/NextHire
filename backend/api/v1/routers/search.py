from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from core.dependencies import get_current_user
from models.job import Job
from services.adzuna_service import (
    search_jobs as adzuna_search_jobs,
    get_job_categories,
)

router = APIRouter(prefix="/search", tags=["Search"])


def _cache_jobs(db: Session, jobs: list[dict]) -> None:
    for item in jobs:
        external_id = item.get("external_id")
        if not external_id:
            continue

        job = db.query(Job).filter(Job.external_id == external_id).first()
        if not job:
            job = Job(external_id=external_id)
            db.add(job)

        job.title = item.get("title") or "Unknown Title"
        job.company = item.get("company") or ""
        job.location = item.get("location") or ""
        job.description = item.get("description") or ""
        job.salary_min = item.get("salary_min")
        job.salary_max = item.get("salary_max")
        job.url = item.get("url") or ""

    db.commit()


@router.get("/jobs")
async def search_jobs(
    keywords: str = Query(..., min_length=1),
    location: str = "",
    page: int = 1,
    results_per_page: int = 20,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    full_time: Optional[bool] = None,
    sort_by: str = "relevance",
    country: str = "gb",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = await adzuna_search_jobs(
        keywords=keywords,
        location=location,
        page=page,
        results_per_page=results_per_page,
        salary_min=salary_min,
        salary_max=salary_max,
        full_time=full_time,
        sort_by=sort_by,
        country=country,
    )
    _cache_jobs(db, data["jobs"])
    return data


@router.get("/categories")
async def categories(
    country: str = "gb",
    current_user=Depends(get_current_user),
):
    return await get_job_categories(country)


@router.get("/")
async def search(query: str = Query(...), current_user=Depends(get_current_user)):
    return await adzuna_search_jobs(keywords=query)
