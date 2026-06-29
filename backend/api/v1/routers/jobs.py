from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from core.dependencies import get_current_user
from models.job import Job
from models.user import User
from schemas.job import CompanyJobCreate, CompanyJobUpdate
from services.notification_service import notify_admins

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/")
def get_jobs(db: Session = Depends(get_db)):
    return db.query(Job).filter(Job.is_active.is_(True)).all()


def serialize_job(job: Job):
    poster = job.poster
    return {
        "id": job.id,
        "external_id": job.external_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "description": job.description,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "url": job.url,
        "category": job.category,
        "is_featured": job.is_featured,
        "source": job.source,
        "employment_type": job.employment_type,
        "work_style": job.work_style,
        "experience_level": job.experience_level,
        "requirements": job.requirements,
        "responsibilities": job.responsibilities,
        "benefits": job.benefits,
        "application_email": job.application_email,
        "application_url": job.application_url or job.url,
        "application_instructions": job.application_instructions,
        "deadline": job.deadline,
        "created_at": job.created_at,
        "poster_id": job.posted_by_user_id,
        "company_verified": bool(poster and poster.company_verified),
    }


@router.get("/external/{external_id}")
def get_job_by_external_id(external_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.external_id == external_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return serialize_job(job)


def require_approved_company(user: User):
    if user.account_type != "company":
        raise HTTPException(status_code=403, detail="Only company accounts can post jobs")
    if user.company_status != "approved" or not user.company_verified:
        raise HTTPException(status_code=403, detail="Company account is pending admin approval")


@router.get("/company/mine")
def my_company_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_approved_company(current_user)
    jobs = db.query(Job).filter(Job.posted_by_user_id == current_user.id).order_by(Job.created_at.desc()).all()
    return [serialize_job(job) for job in jobs]


@router.post("/company")
def create_company_job(
    data: CompanyJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_approved_company(current_user)
    job = Job(
        external_id=f"company-{current_user.id}-{int(__import__('time').time())}",
        title=data.title,
        company=data.company or current_user.company_name or current_user.full_name,
        location=data.location,
        description=data.description,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        category=data.category,
        source="company",
        posted_by_user_id=current_user.id,
        employment_type=data.employment_type,
        work_style=data.work_style,
        experience_level=data.experience_level,
        requirements=data.requirements,
        responsibilities=data.responsibilities,
        benefits=data.benefits,
        application_email=data.application_email,
        application_url=data.application_url,
        application_instructions=data.application_instructions,
        deadline=data.deadline,
        is_active=True,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    notify_admins(
        db,
        "New company job post",
        f"{job.company or current_user.company_name} posted {job.title}.",
        "job_post",
    )
    db.commit()
    return serialize_job(job)


@router.put("/company/{job_id}")
def update_company_job(
    job_id: int,
    data: CompanyJobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not current_user.is_admin and job.posted_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own job posts")
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return serialize_job(job)


@router.delete("/company/{job_id}")
def delete_company_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not current_user.is_admin and job.posted_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own job posts")
    db.delete(job)
    db.commit()
    return {"message": "Job post deleted"}


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return serialize_job(job)
