from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.dependencies import get_db, get_current_user
from schemas.saved_job import SavedJobCreate, SavedJobResponse
from services.saved_job_service import SavedJobService

router = APIRouter(
    prefix="/saved-jobs",
    tags=["Saved Jobs"]
)


@router.post("", response_model=SavedJobResponse)
def save_job(
    data: SavedJobCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return SavedJobService.save_job(
        db,
        current_user.id,
        data.external_id
    )


@router.get("", response_model=list[SavedJobResponse])
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


@router.patch("/{saved_job_id}/status", response_model=SavedJobResponse)
def update_saved_job_status(
    saved_job_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return SavedJobService.update_status(db, current_user.id, saved_job_id, data["status"])
