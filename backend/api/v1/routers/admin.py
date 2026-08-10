from datetime import datetime, timedelta, timezone
import logging
import socket
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
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
from schemas.admin import (
    AdminFeaturedJobCreate,
    AdminJobUpdate,
    AdminPasswordResetRequest,
    AdminRole,
    AdminUserSecurityUpdate,
    CompanyApprovalRequest,
    ProfileModerationRequest,
)
from schemas.pagination import PaginationParams, paginated_response, pagination_params
from schemas.validation import validate_salary_range
from services.admin_audit_service import record_admin_audit
from services.auth_service import AuthService
from core.rate_limit import rate_limit
from services.notification_service import create_notification
from tasks.email_task import send_admin_email, send_broadcast_email

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


class AdminEmailRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20_000)


def _aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_active_super_admin(user: User, *, is_active=None, banned_until=None) -> bool:
    active = user.is_active if is_active is None else is_active
    ban = user.banned_until if banned_until is None else banned_until
    return bool(
        user.is_admin
        and user.admin_role == "super_admin"
        and active
        and (_aware_utc(ban) is None or _aware_utc(ban) <= datetime.now(timezone.utc))
    )


def _protect_last_active_super_admin(
    db: Session,
    target: User,
    *,
    is_active=None,
    banned_until=None,
    deleting: bool = False,
) -> None:
    if not target.is_admin or target.admin_role != "super_admin":
        return
    super_admins = (
        db.query(User)
        .filter(
            User.is_admin.is_(True),
            User.admin_role == "super_admin",
        )
        .order_by(User.id)
        .with_for_update()
        .populate_existing()
        .all()
    )
    locked_target = next((user for user in super_admins if user.id == target.id), target)
    if not _is_active_super_admin(locked_target):
        return
    remains_active = False if deleting else _is_active_super_admin(
        locked_target,
        is_active=is_active,
        banned_until=banned_until,
    )
    if remains_active:
        return
    if not any(
        _is_active_super_admin(user)
        for user in super_admins
        if user.id != locked_target.id
    ):
        raise HTTPException(status_code=409, detail="The final active super-admin cannot be disabled")


def _require_user_management_permission(actor: User, target: User) -> None:
    if target.is_admin and actor.admin_role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super-admins can modify administrator accounts")


def _record_privileged_change(
    db: Session,
    actor: User,
    action: str,
    resource_type: str,
    *,
    resource_id=None,
    target_user_id=None,
    details=None,
) -> None:
    record_admin_audit(
        db,
        actor,
        action,
        resource_type,
        resource_id=resource_id,
        target_user_id=target_user_id,
        details=details,
    )
    logger.info("Admin security operation", extra={
        "event": "admin_security_operation",
        "action": action,
        "actor_user_id": actor.id,
        "target_user_id": target_user_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
    })


def _user_payload(user: User, saved_count: int, applied_count: int) -> dict:
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


def _user_row(db: Session, user: User) -> dict:
    saved_count = db.query(SavedJob).filter(SavedJob.user_id == user.id).count()
    applied_count = db.query(SavedJob).filter(
        SavedJob.user_id == user.id,
        SavedJob.status == "applied",
    ).count()
    return _user_payload(user, saved_count, applied_count)


@router.get("/summary")
def summary(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
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
    q: str = Query(default="", max_length=100),
    status: str = Query(default="all", pattern="^(all|active|inactive)$"),
    pagination: PaginationParams = Depends(pagination_params),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    conditions = []
    if q:
        like = f"%{q}%"
        conditions.append((User.email.ilike(like)) | (User.full_name.ilike(like)))
    if status == "active":
        conditions.append(User.is_active.is_(True))
    elif status == "inactive":
        conditions.append(User.is_active.is_(False))
    total = db.query(func.count(User.id)).filter(*conditions).scalar() or 0
    rows = (
        db.query(
            User,
            func.count(SavedJob.id).label("saved_count"),
            func.sum(case((SavedJob.status == "applied", 1), else_=0)).label("applied_count"),
        )
        .outerjoin(SavedJob, SavedJob.user_id == User.id)
        .filter(*conditions)
        .group_by(User.id)
        .order_by(User.created_at.desc(), User.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
    )
    items = [
        _user_payload(user, saved_count or 0, applied_count or 0)
        for user, saved_count, applied_count in rows
    ]
    return paginated_response(items, total, pagination)


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
    payload: CompanyApprovalRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin", "moderator")),
):
    user = db.query(User).filter(User.id == user_id, User.account_type == "company").first()
    if not user:
        raise HTTPException(status_code=404, detail="Company account not found")
    approved = payload.approved
    user.company_status = "approved" if approved else "rejected"
    user.company_verified = approved
    create_notification(
        db,
        user.id,
        "Company approved" if approved else "Company rejected",
        "Your company can now post jobs on NextHire." if approved else "Your company verification request was rejected by admin.",
        "company_approval",
    )
    _record_privileged_change(
        db,
        admin,
        "approve_company" if approved else "reject_company",
        "user",
        resource_id=user.id,
        target_user_id=user.id,
        details={"approved": approved},
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
    payload: AdminUserSecurityUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin", "moderator")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _require_user_management_permission(admin, user)
    changes = payload.model_dump(exclude_unset=True)
    proposed_active = changes.get("is_active", user.is_active)
    proposed_ban = changes.get("banned_until", user.banned_until)
    _protect_last_active_super_admin(
        db,
        user,
        is_active=proposed_active,
        banned_until=proposed_ban,
    )
    invalidate_sessions = False
    for field in ["is_active", "is_verified"]:
        if field in changes:
            new_value = changes[field]
            if getattr(user, field) != new_value:
                setattr(user, field, new_value)
                if field == "is_verified" or not new_value:
                    invalidate_sessions = True
    if "banned_until" in changes:
        new_banned_until = changes["banned_until"]
        if _aware_utc(new_banned_until) != _aware_utc(user.banned_until):
            user.banned_until = new_banned_until
            if new_banned_until:
                if _aware_utc(new_banned_until) > datetime.now(timezone.utc):
                    invalidate_sessions = True
    if invalidate_sessions:
        AuthService.invalidate_user_sessions(db, user)
    _record_privileged_change(
        db,
        admin,
        "update_user_security",
        "user",
        resource_id=user.id,
        target_user_id=user.id,
        details={"fields": sorted(changes)},
    )
    db.commit()
    db.refresh(user)
    return _user_row(db, user)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _protect_last_active_super_admin(db, user, deleting=True)
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account")
    _record_privileged_change(
        db,
        admin,
        "delete_user",
        "user",
        resource_id=user.id,
        target_user_id=user.id,
        details={"was_admin": user.is_admin, "admin_role": user.admin_role},
    )
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    payload: AdminPasswordResetRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = hash_password(payload.new_password)
    AuthService.invalidate_user_sessions(db, user)
    _record_privileged_change(
        db,
        admin,
        "reset_user_password",
        "user",
        resource_id=user.id,
        target_user_id=user.id,
    )
    db.commit()
    return {"message": "Password reset"}


@router.post("/admins")
def create_admin(
    payload: RegisterRequest,
    role: AdminRole = Query("moderator"),
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
    db.flush()
    _record_privileged_change(
        db,
        admin,
        "create_admin",
        "user",
        resource_id=user.id,
        target_user_id=user.id,
        details={"admin_role": role},
    )
    db.commit()
    db.refresh(user)
    return _user_row(db, user)


@router.get("/jobs")
def list_jobs(
    pagination: PaginationParams = Depends(pagination_params),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    total = db.query(func.count(Job.id)).scalar() or 0
    rows = (
        db.query(
            Job,
            func.count(SavedJob.id).label("saved_count"),
            func.sum(case((SavedJob.status != "saved", 1), else_=0)).label("application_count"),
        )
        .outerjoin(SavedJob, SavedJob.job_id == Job.id)
        .group_by(Job.id)
        .order_by(Job.created_at.desc(), Job.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
    )
    items = [
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
    return paginated_response(items, total, pagination)


@router.post("/jobs")
def add_featured_job(
    payload: AdminFeaturedJobCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin", "moderator")),
):
    job = Job(
        external_id=payload.external_id or f"manual-{int(datetime.now(timezone.utc).timestamp())}",
        title=payload.title,
        company=payload.company,
        location=payload.location,
        description=payload.description,
        salary_min=payload.salary_min,
        salary_max=payload.salary_max,
        url=payload.url,
        category=payload.category,
        is_featured=True,
    )
    db.add(job)
    db.flush()
    _record_privileged_change(
        db,
        admin,
        "create_featured_job",
        "job",
        resource_id=job.id,
        details={"title": job.title},
    )
    db.commit()
    db.refresh(job)
    return {"id": job.id, "message": "Featured job added"}


@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin_role("super_admin", "moderator"))):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    _record_privileged_change(
        db,
        admin,
        "delete_job",
        "job",
        resource_id=job.id,
        details={"title": job.title},
    )
    db.delete(job)
    db.commit()
    return {"message": "Job deleted"}


@router.patch("/jobs/{job_id}")
def update_job(
    job_id: int,
    payload: AdminJobUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin", "moderator")),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    changes = payload.model_dump(exclude_unset=True)
    try:
        validate_salary_range(
            changes.get("salary_min", job.salary_min),
            changes.get("salary_max", job.salary_max),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    for field, value in changes.items():
        setattr(job, field, value)
    _record_privileged_change(
        db,
        admin,
        "update_job",
        "job",
        resource_id=job.id,
        details={"fields": sorted(changes)},
    )
    db.commit()
    db.refresh(job)
    return {"message": "Job updated", "id": job.id}


@router.get("/moderation/notes")
def list_notes(
    pagination: PaginationParams = Depends(pagination_params),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin", "moderator")),
):
    query = db.query(Note, User).join(User, Note.user_id == User.id)
    total = db.query(func.count(Note.id)).scalar() or 0
    notes = (
        query.order_by(Note.created_at.desc(), Note.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
    )
    items = [
        {"id": note.id, "content": note.content, "created_at": note.created_at, "user_email": user.email}
        for note, user in notes
    ]
    return paginated_response(items, total, pagination)


@router.delete("/moderation/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin_role("super_admin", "moderator"))):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    _record_privileged_change(
        db,
        admin,
        "delete_note",
        "note",
        resource_id=note.id,
        target_user_id=note.user_id,
    )
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
def moderate_profile(
    profile_id: int,
    payload: ProfileModerationRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin", "moderator")),
):
    profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    for field in ["avatar_url", "headline", "bio"]:
        if getattr(payload, f"clear_{field}"):
            setattr(profile, field, None)
    cleared_fields = [
        field for field in ["avatar_url", "headline", "bio"]
        if getattr(payload, f"clear_{field}")
    ]
    _record_privileged_change(
        db,
        admin,
        "moderate_profile",
        "profile",
        resource_id=profile.id,
        target_user_id=profile.user_id,
        details={"cleared_fields": cleared_fields},
    )
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


@router.post("/email/broadcast", dependencies=[Depends(rate_limit(
    "admin-email-broadcast",
    settings.EMAIL_RATE_LIMIT_PER_HOUR,
    3600,
))])
def broadcast_email(
    payload: AdminEmailRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin")),
):
    recipients = [
        email for (email,) in
        db.query(User.email).filter(User.is_active.is_(True)).all()
    ]
    if not recipients:
        raise HTTPException(status_code=400, detail="No active recipients")
    try:
        task = send_broadcast_email.delay(recipients, payload.subject.strip(), payload.body.strip())
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Email queue unavailable") from exc
    _record_privileged_change(
        db,
        admin,
        "queue_broadcast_email",
        "email",
        details={"recipient_count": len(recipients), "subject": payload.subject.strip()},
    )
    db.commit()
    return {
        "message": "Broadcast queued",
        "subject": payload.subject.strip(),
        "recipients": len(recipients),
        "task_id": task.id,
    }


@router.post("/email/user/{user_id}", dependencies=[Depends(rate_limit(
    "admin-email-user",
    settings.EMAIL_RATE_LIMIT_PER_HOUR,
    3600,
))])
def email_user(
    user_id: int,
    payload: AdminEmailRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_role("super_admin", "moderator")),
):
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Active user not found")
    try:
        task = send_admin_email.delay(user.email, payload.subject.strip(), payload.body.strip())
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Email queue unavailable") from exc
    _record_privileged_change(
        db,
        admin,
        "queue_user_email",
        "email",
        target_user_id=user.id,
        resource_id=user.id,
        details={"subject": payload.subject.strip()},
    )
    db.commit()
    return {
        "message": "Email queued",
        "user_id": user.id,
        "subject": payload.subject.strip(),
        "task_id": task.id,
    }


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
