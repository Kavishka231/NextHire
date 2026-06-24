
from fastapi import APIRouter, Depends
from backend.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/")
def get_jobs():
    return JobService.get_all_jobs()

@router.get("/{job_id}")
def get_job(job_id: int):
    return JobService.get_job(job_id)