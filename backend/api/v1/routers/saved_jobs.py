from fastapi import APIRouter, Depends
from backend.schemas.saved_job import SavedJobCreate
from backend.services.saved_job_service import SavedJobService
from backend.core.dependencies import get_current_user

router = APIRouter(prefix="/saved-jobs", tags=["Saved Jobs"])

@router.post("/")
def save_job(data: SavedJobCreate, user=Depends(get_current_user)):
    return SavedJobService.save_job(user.id, data)

@router.get("/")
def get_saved_jobs(user=Depends(get_current_user)):
    return SavedJobService.get_saved_jobs(user.id)

@router.delete("/{job_id}")
def delete_saved_job(job_id: int, user=Depends(get_current_user)):
    return SavedJobService.delete_saved_job(user.id, job_id)