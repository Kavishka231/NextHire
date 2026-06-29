from datetime import datetime, timedelta
import socket
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from core.dependencies import require_admin, require_admin_role
from core.security import hash_password
from models.job import Job
from models.note import Note
from models.profile import UserProfile
from models.saved_job import SavedJob
from models.search_log import SearchLog
from models.user import User
from schemas.auth import RegisterRequest
from services.notification_service import create_notification

router = APIRouter(prefix="/admin", tags=["Admin"])


def _user_row(db: Session, user: User) -> dict:
    saved_count = db.query(SavedJob).filter(SavedJob.user_id == user.id).count()
    applied_count = db.query(SavedJob).filter(SavedJob.user_id == user.id, SavedJob.status == "applied").count()
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "join_date": user.created_at,
        "last_active": user.last_active_at,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "is_admin": user.is_admin,
        "admin_role": user.admin_role,
        "account_type": user.account_type,
        "company_name": user.company_name,
        "company_status": user.company_status,
        "company_verified": user.company_verified,
        "banned_until": user.banned_until,
        "saved_jobs": saved_count,
        "applied_jobs": applied_count,
    }


@router.get("/summary")
def summary(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)
    return {
        "total_users": db.query(User).count(),
        "new_users_week": db.query(User).filter(User.created_at >= week_ago).count(),
        "new_users_month": db.query(User).filter(User.created_at >= month_ago).count(),
        "total_jobs": db.query(Job).count(),
        "total_searches": db.query(SearchLog).count(),
        "total_saved": db.query(SavedJob).count(),
        "total_applications": db.query(SavedJob).filter(SavedJob.status != "saved").count(),
        "active_users": db.query(User).filter(User.is_active.is_(True)).count(),
    }


@router.get("/users")
def list_users(
    q: str = "",
    status: str = "all",
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = db.query(User)
    if q:
        like = f"%{q}%"
        query = query.filter((User.email.ilike(like)) | (User.full_name.ilike(like)))
    if status == "active":
        query = query.filter(User.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(User.is_active.is_(False))
    return [_user_row(db, user) for user in query.order_by(User.created_at.desc()).all()]


@router.get("/companies/pending")
def pending_companies(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    users = (
        db.query(User)
        .filter(User.account_type == "company", User.company_status == "pending")
        .order_by(User.created_at.desc())
        .all()
    )
    return [_user_row(db, user) for user in users]


@router.patch("/companies/{user_id}/approval")
def approve_company(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin", "moderator")),
):
    user = db.query(User).filter(User.id == user_id, User.account_type == "company").first()
    if not user:
        raise HTTPException(status_code=404, detail="Company account not found")
    approved = bool(payload.get("approved"))
    user.company_status = "approved" if approved else "rejected"
    user.company_verified = approved
    create_notification(
        db,
        user.id,
        "Company approved" if approved else "Company rejected",
        "Your company can now post jobs on NextHire." if approved else "Your company verification request was rejected by admin.",
        "company_approval",
    )
    db.commit()
    return _user_row(db, user)


@router.get("/users/{user_id}")
def user_detail(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    return {"user": _user_row(db, user), "profile": profile}


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin", "moderator")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field in ["is_active", "is_verified"]:
        if field in payload:
            setattr(user, field, bool(payload[field]))
    if "banned_until" in payload:
        user.banned_until = datetime.fromisoformat(payload["banned_until"]) if payload["banned_until"] else None
    db.commit()
    db.refresh(user)
    return _user_row(db, user)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin")),
):
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin")),
):
    new_password = payload.get("new_password")
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = hash_password(new_password)
    db.commit()
    return {"message": "Password reset"}


@router.post("/admins")
def create_admin(
    payload: RegisterRequest,
    role: str = Query("moderator", pattern="^(super_admin|moderator|analyst)$"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin")),
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="User already exists")
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_verified=True,
        is_admin=True,
        admin_role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_row(db, user)


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = (
        db.query(
            Job,
            func.count(SavedJob.id).label("saved_count"),
            func.sum(case((SavedJob.status != "saved", 1), else_=0)).label("application_count"),
        )
        .outerjoin(SavedJob, SavedJob.job_id == Job.id)
        .group_by(Job.id)
        .order_by(Job.created_at.desc())
        .all()
    )
    return [
        {
            "id": job.id,
            "external_id": job.external_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "url": job.url,
            "category": job.category,
            "is_featured": job.is_featured,
            "saved_count": saved_count or 0,
            "application_count": application_count or 0,
        }
        for job, saved_count, application_count in rows
    ]


@router.post("/jobs")
def add_featured_job(
    payload: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin", "moderator")),
):
    title = payload.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="Job title is required")
    job = Job(
        external_id=payload.get("external_id") or f"manual-{int(datetime.utcnow().timestamp())}",
        title=title,
        company=payload.get("company") or "",
        location=payload.get("location") or "",
        description=payload.get("description") or "",
        salary_min=payload.get("salary_min"),
        salary_max=payload.get("salary_max"),
        url=payload.get("url") or "",
        category=payload.get("category") or "featured",
        is_featured=True,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"id": job.id, "message": "Featured job added"}


@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin_role("super_admin", "moderator"))):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"message": "Job deleted"}


@router.patch("/jobs/{job_id}")
def update_job(
    job_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin", "moderator")),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    allowed = {
        "title", "company", "location", "description", "salary_min", "salary_max",
        "category", "is_featured", "is_active", "application_email", "application_url",
        "application_instructions",
    }
    for field, value in payload.items():
        if field in allowed:
            setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return {"message": "Job updated", "id": job.id}


@router.get("/moderation/notes")
def list_notes(db: Session = Depends(get_db), admin: User = Depends(require_admin_role("super_admin", "moderator"))):
    notes = db.query(Note, User).join(User, Note.user_id == User.id).order_by(Note.created_at.desc()).limit(200).all()
    return [
        {"id": note.id, "content": note.content, "created_at": note.created_at, "user_email": user.email}
        for note, user in notes
    ]


@router.delete("/moderation/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin_role("super_admin", "moderator"))):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return {"message": "Note deleted"}


@router.get("/moderation/profiles")
def list_profiles(db: Session = Depends(get_db), admin: User = Depends(require_admin_role("super_admin", "moderator"))):
    profiles = db.query(UserProfile, User).join(User, UserProfile.user_id == User.id).order_by(UserProfile.updated_at.desc()).limit(200).all()
    return [
        {
            "profile": {
                "id": profile.id,
                "avatar_url": profile.avatar_url,
                "headline": profile.headline,
                "bio": profile.bio,
                "location": profile.location,
                "updated_at": profile.updated_at,
            },
            "user": _user_row(db, user),
        }
        for profile, user in profiles
    ]


@router.patch("/moderation/profiles/{profile_id}")
def moderate_profile(profile_id: int, payload: dict, db: Session = Depends(get_db), admin: User = Depends(require_admin_role("super_admin", "moderator"))):
    profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    for field in ["avatar_url", "headline", "bio"]:
        if payload.get(f"clear_{field}"):
            setattr(profile, field, None)
    db.commit()
    return {"message": "Profile moderated"}


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    status_counts = dict(db.query(SavedJob.status, func.count(SavedJob.id)).group_by(SavedJob.status).all())
    top_keywords = db.query(SearchLog.keywords, func.count(SearchLog.id)).group_by(SearchLog.keywords).order_by(func.count(SearchLog.id).desc()).limit(8).all()
    top_locations = db.query(SearchLog.location, func.count(SearchLog.id)).filter(SearchLog.location != "").group_by(SearchLog.location).order_by(func.count(SearchLog.id).desc()).limit(8).all()
    top_categories = db.query(Job.category, func.count(Job.id)).filter(Job.category != None).group_by(Job.category).order_by(func.count(Job.id).desc()).limit(8).all()
    return {
        "status_counts": status_counts,
        "top_keywords": [{"label": k, "count": c} for k, c in top_keywords],
        "top_locations": [{"label": k, "count": c} for k, c in top_locations],
        "top_categories": [{"label": k, "count": c} for k, c in top_categories],
        "conversion_funnel": {
            "saved": status_counts.get("saved", 0),
            "applied": status_counts.get("applied", 0),
            "interview": status_counts.get("interview", 0),
            "offer": status_counts.get("offer", 0),
        },
    }


@router.post("/email/broadcast")
def broadcast_email(payload: dict, admin: User = Depends(require_admin_role("super_admin"))):
    return {"message": "Broadcast queued", "subject": payload.get("subject", ""), "recipients": "all users"}


@router.post("/email/user/{user_id}")
def email_user(user_id: int, payload: dict, admin: User = Depends(require_admin_role("super_admin", "moderator"))):
    return {"message": "Email queued", "user_id": user_id, "subject": payload.get("subject", "")}


@router.get("/email/reminder-preview")
def reminder_preview(admin: User = Depends(require_admin)):
    return {
        "subject": "Applications need a follow-up - NextHire",
        "html": "<h2>Time to follow up</h2><p>You have applications waiting for your next move.</p>",
        "daily_reminders_enabled": True,
    }


@router.get("/health")
def admin_health(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    db_ok = bool(db.execute(text("SELECT 1")).scalar())
    parsed = urlparse(settings.REDIS_URL)
    redis_ok = False
    try:
        with socket.create_connection((parsed.hostname or "localhost", parsed.port or 6379), timeout=1):
            redis_ok = True
    except OSError:
        redis_ok = False
    return {
        "database": "connected" if db_ok else "down",
        "redis": "connected" if redis_ok else "down",
        "celery_worker": "check worker container logs",
        "api_response_times": [],
        "api_requests_today": None,
    }
