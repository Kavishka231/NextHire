from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db, get_current_user
from backend.schemas.saved_job import SavedJobCreate
from backend.services.saved_job_service import SavedJobService

router = APIRouter(
    prefix="/saved-jobs",
    tags=["Saved Jobs"]
)


@router.post("/")
def save_job(
    data: SavedJobCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return SavedJobService.save_job(
        db,
        current_user.id,
        data.job_id
    )


@router.get("/")
def get_saved_jobs(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return SavedJobService.get_saved_jobs(
        db,
        current_user.id
    )


@router.delete("/{job_id}")
def delete_saved_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return SavedJobService.delete_saved_job(
        db,
        current_user.id,
        job_id
    )