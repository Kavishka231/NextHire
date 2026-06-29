from sqlalchemy.orm import Session
from models.job import Job


def upsert_jobs(db: Session, jobs: list[dict]) -> list[Job]:
    """
    Save Adzuna results to the local DB so saved_jobs can reference them.
    Uses upsert logic: insert if not exists, update if exists.
    """
    saved = []
    for j in jobs:
        existing = db.query(Job).filter(Job.external_id == j["external_id"]).first()
        if existing:
            # Update fields in case they changed
            existing.title       = j["title"]
            existing.company     = j["company"]
            existing.location    = j["location"]
            existing.description = j["description"]
            existing.salary_min  = j.get("salary_min")
            existing.salary_max  = j.get("salary_max")
            existing.url         = j["url"]
            saved.append(existing)
        else:
            new_job = Job(
                external_id  = j["external_id"],
                title        = j["title"],
                company      = j.get("company", ""),
                location     = j.get("location", ""),
                description  = j.get("description", ""),
                salary_min   = j.get("salary_min"),
                salary_max   = j.get("salary_max"),
                url          = j.get("url", ""),
            )
            db.add(new_job)
            saved.append(new_job)

    db.commit()
    for job in saved:
        db.refresh(job)
    return saved


def get_job_by_external_id(db: Session, external_id: str) -> Job | None:
    return db.query(Job).filter(Job.external_id == external_id).first()
