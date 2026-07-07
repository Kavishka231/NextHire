from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.job import Job
from models.saved_job import SavedJob
from models.user import User

COLUMN_META = [
    {"status": "saved", "label": "Saved", "color": "#64748b"},
    {"status": "applied", "label": "Applied", "color": "#2563eb"},
    {"status": "interview", "label": "Interview", "color": "#7c3aed"},
    {"status": "offer", "label": "Offer", "color": "#16a34a"},
    {"status": "rejected", "label": "Rejected", "color": "#dc2626"},
]

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def get_stats(db: Session, user: User) -> dict:
    saved_jobs = _get_saved_jobs(db, user)
    counts = _count_statuses(saved_jobs)
    rates = _calculate_rates(counts)
    salary_averages = _get_salary_averages(db, user)

    return {
        "total_saved": counts.get("saved", 0),
        "total_applied": counts.get("applied", 0),
        "total_interviews": counts.get("interview", 0),
        "total_offers": counts.get("offer", 0),
        "total_rejected": counts.get("rejected", 0),
        "response_rate": rates["response_rate"],
        "offer_rate": rates["offer_rate"],
        "status_counts": _build_status_counts(counts),
        "weekly_activity": _build_weekly_activity(saved_jobs),
        "top_companies": _get_top_companies(db, user),
        "avg_salary_min": salary_averages["avg_salary_min"],
        "avg_salary_max": salary_averages["avg_salary_max"],
    }


def _get_saved_jobs(db: Session, user: User) -> list[SavedJob]:
    return (
        db.query(SavedJob)
        .filter(SavedJob.user_id == user.id)
        .all()
    )


def _count_statuses(saved_jobs: list[SavedJob]) -> defaultdict:
    counts = defaultdict(int)
    for saved_job in saved_jobs:
        counts[saved_job.status] += 1
    return counts


def _calculate_rates(counts: defaultdict) -> dict:
    total_applied = counts.get("applied", 0)
    total_interviews = counts.get("interview", 0)
    total_offers = counts.get("offer", 0)
    return {
        "response_rate": round((total_interviews / total_applied * 100), 1) if total_applied else 0.0,
        "offer_rate": round((total_offers / total_applied * 100), 1) if total_applied else 0.0,
    }

def _build_status_counts(counts: defaultdict) -> list[dict]:
    return [
        {**meta, "count": counts.get(meta["status"], 0)}
        for meta in COLUMN_META
    ]


def _build_weekly_activity(saved_jobs: list[SavedJob]) -> list[dict]:
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    daily = defaultdict(int)

    for saved_job in saved_jobs:
        created = saved_job.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created >= week_ago:
            daily[DAY_LABELS[created.weekday()]] += 1

    return [
        {"week": day, "count": daily.get(day, 0)}
        for day in DAY_LABELS
    ]


def _get_top_companies(db: Session, user: User) -> list[dict]:
    company_rows = (
        db.query(Job.company, func.count(SavedJob.id).label("cnt"))
        .join(SavedJob, SavedJob.job_id == Job.id)
        .filter(SavedJob.user_id == user.id, Job.company != "")
        .group_by(Job.company)
        .order_by(func.count(SavedJob.id).desc())
        .limit(5)
        .all()
    )
    return [{"company": row.company, "count": row.cnt} for row in company_rows]


def _get_salary_averages(db: Session, user: User) -> dict:
    salary_rows = (
        db.query(Job.salary_min, Job.salary_max)
        .join(SavedJob, SavedJob.job_id == Job.id)
        .filter(
            SavedJob.user_id == user.id,
            Job.salary_min.isnot(None),
            Job.salary_max.isnot(None),
        )
        .all()
    )
    avg_min = round(sum(row.salary_min for row in salary_rows) / len(salary_rows)) if salary_rows else None
    avg_max = round(sum(row.salary_max for row in salary_rows) / len(salary_rows)) if salary_rows else None

    return {
        "avg_salary_min": avg_min,
        "avg_salary_max": avg_max,
    }


class StatsService:
    @staticmethod
    def get_dashboard_stats(db: Session, user: User) -> dict:
        return get_stats(db, user)
