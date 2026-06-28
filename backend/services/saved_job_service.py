from fastapi import HTTPException

from models.saved_job import SavedJob
from models.job import Job


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

        existing = (
            db.query(SavedJob)
            .filter(
                SavedJob.user_id == user_id,
                SavedJob.job_id == job.id
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Job already saved"
            )

        saved_job = SavedJob(
            user_id=user_id,
            job_id=job.id
        )

        db.add(saved_job)
        db.commit()
        db.refresh(saved_job)

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

        return {
            "message": "Saved job removed"
        }
