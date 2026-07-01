from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from models.job import Job
from models.search_log import SearchLog
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
        job.category = item.get("category") or ""
        job.source = item.get("source") or "adzuna"

    db.commit()


def _company_job_result(job: Job) -> dict:
    poster = job.poster
    return {
        "external_id": job.external_id,
        "title": job.title,
        "company": job.company or "",
        "location": job.location or "",
        "description": job.description or "",
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_is_predicted": False,
        "url": job.application_url or job.url or "",
        "category": job.category or "Company post",
        "contract_type": job.employment_type or "",
        "contract_time": job.employment_type or "",
        "created": str(job.created_at or ""),
        "source": job.source,
        "company_verified": bool(poster and poster.company_verified),
    }


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
    local_query = db.query(Job).filter(Job.source == "company", Job.is_active.is_(True))
    if keywords:
        like = f"%{keywords}%"
        local_query = local_query.filter(or_(Job.title.ilike(like), Job.description.ilike(like), Job.company.ilike(like)))
    if location:
        local_query = local_query.filter(Job.location.ilike(f"%{location}%"))
    local_jobs = [_company_job_result(job) for job in local_query.order_by(Job.created_at.desc()).limit(10).all()]
    data["jobs"] = local_jobs + data["jobs"]
    data["total"] = data.get("total", 0) + len(local_jobs)
    db.add(SearchLog(keywords=keywords, location=location, category=None))
    db.commit()
    return data


@router.get("/categories")
async def categories(
    country: str = "gb",
):
    return await get_job_categories(country)


@router.get("/")
async def search(query: str = Query(...)):
    return await adzuna_search_jobs(keywords=query)
