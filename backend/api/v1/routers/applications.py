import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from core.dependencies import get_current_user
from models.application import JobApplication
from models.job import Job
from models.user import User
from schemas.application import ApplicationCreate, ApplicationResponse, ApplicationStatusUpdate
from services.notification_service import create_notification
from services.profile_service import ProfileService

router = APIRouter(prefix="/applications", tags=["Applications"])
logger = logging.getLogger(__name__)


def serialize_application(application: JobApplication) -> dict:
    job = application.job
    return {
        "id": application.id,
        "job_id": application.job_id,
        "external_id": job.external_id,
        "job_title": job.title,
        "company": job.company or "",
        "applicant_name": application.applicant_name,
        "applicant_email": application.applicant_email,
        "applicant_phone": application.applicant_phone,
        "headline": application.headline,
        "location": application.location,
        "linkedin_url": application.linkedin_url,
        "github_url": application.github_url,
        "portfolio_url": application.portfolio_url,
        "resume_url": application.resume_url,
        "cover_letter": application.cover_letter,
        "extra_details": application.extra_details,
        "use_profile": application.use_profile,
        "status": application.status,
        "created_at": application.created_at,
    }


@router.post("", response_model=ApplicationResponse)
def submit_application(
    data: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.external_id == data.external_id, Job.is_active.is_(True)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = ProfileService.get_or_create(db, current_user)
    application = JobApplication(
        job_id=job.id,
        applicant_user_id=current_user.id,
        applicant_name=(data.applicant_name or current_user.full_name).strip(),
        applicant_email=str(data.applicant_email or current_user.email),
        applicant_phone=data.applicant_phone or profile.phone,
        headline=data.headline or profile.headline,
        location=data.location or profile.location,
        linkedin_url=data.linkedin_url or profile.linkedin_url,
        github_url=data.github_url or profile.github_url,
        portfolio_url=data.portfolio_url or profile.portfolio_url,
        resume_url=data.resume_url or profile.resume_url,
        cover_letter=data.cover_letter,
        extra_details=data.extra_details,
        use_profile=data.use_profile,
    )
    db.add(application)
    if job.posted_by_user_id:
        create_notification(
            db,
            job.posted_by_user_id,
            "New job application",
            f"{application.applicant_name} applied for {job.title}.",
            "job_application",
        )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="You have already applied for this job",
        ) from exc
    db.refresh(application)
    logger.info("Application submitted", extra={
        "event": "application_submitted",
        "application_id": application.id,
        "job_id": job.id,
        "job_title": job.title,
        "actor_user_id": current_user.id,
        "outcome": "success",
    })
    return serialize_application(application)


@router.get("/company", response_model=list[ApplicationResponse])
def company_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.account_type != "company" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only companies can review applications")
    query = db.query(JobApplication).join(Job)
    if not current_user.is_admin:
        query = query.filter(Job.posted_by_user_id == current_user.id)
    applications = query.order_by(JobApplication.created_at.desc()).all()
    return [serialize_application(application) for application in applications]


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
def update_application_status(
    application_id: int,
    data: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if not current_user.is_admin and application.job.posted_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only review applications for your jobs")
    application.status = data.status
    if application.applicant_user_id:
        create_notification(
            db,
            application.applicant_user_id,
            "Application status updated",
            f"{application.job.title} is now marked as {data.status}.",
            "application_status",
        )
    db.commit()
    db.refresh(application)
    return serialize_application(application)
