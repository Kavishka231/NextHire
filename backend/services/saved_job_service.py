import logging

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from models.saved_job import SavedJob
from models.job import Job


logger = logging.getLogger(__name__)


class SavedJobService:

    @staticmethod
    def save_job(db, user_id: int, job_id: int = None, external_id: str = None):
        if external_id and job_id is None:
            job = db.query(Job).filter(Job.external_id == external_id).first()
        else:
            job = db.query(Job).filter(Job.id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=404,
                detail="Job not found"
            )

        saved_job = SavedJob(
            user_id=user_id,
            job_id=job.id
        )

        db.add(saved_job)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Job already saved",
            ) from exc
        db.refresh(saved_job)
        logger.info("Saved job created", extra={
            "event": "saved_job_created",
            "saved_job_id": saved_job.id,
            "job_id": job.id,
            "job_title": job.title,
            "user_id": user_id,
            "outcome": "success",
        })

        return saved_job

    @staticmethod
    def get_saved_jobs(db, user_id: int):

        saved_jobs = (
            db.query(SavedJob)
            .filter(SavedJob.user_id == user_id)
            .all()
        )

        return saved_jobs

    @staticmethod
    def update_status(db, user_id: int, saved_job_id: int, status_value: str):
        # Similar to note ownership checks, but kept local for saved-job status semantics.
        saved_job = (
            db.query(SavedJob)
            .filter(SavedJob.id == saved_job_id, SavedJob.user_id == user_id)
            .first()
        )

        if not saved_job:
            raise HTTPException(status_code=404, detail="Saved job not found")

        saved_job.status = status_value
        db.commit()
        db.refresh(saved_job)
        return saved_job

    @staticmethod
    def delete_saved_job(db, user_id: int, job_id: int):

        # Similar to note ownership checks, but kept local because deletion uses job_id.
        saved_job = (
            db.query(SavedJob)
            .filter(
                SavedJob.user_id == user_id,
                SavedJob.job_id == job_id
            )
            .first()
        )

        if not saved_job:
            raise HTTPException(
                status_code=404,
                detail="Saved job not found"
            )

        db.delete(saved_job)
        db.commit()
        logger.info("Saved job deleted", extra={
            "event": "saved_job_deleted",
            "saved_job_id": saved_job.id,
            "job_id": job_id,
            "user_id": user_id,
            "outcome": "success",
        })

        return {
            "message": "Saved job removed"
        }
