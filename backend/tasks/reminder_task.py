from tasks.celery_app import celery_app
from app.database import SessionLocal
from models.user import User
from models.saved_job import SavedJob
from models.job import Job
from services.email_service import _send
from datetime import datetime, timedelta, timezone


@celery_app.task(name="tasks.reminder_task.send_reminders")
def send_reminders():
    """
    Daily task: email users who have jobs stuck in 'applied'
    for more than 7 days with no status change.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        stale_jobs = (
            db.query(SavedJob, Job, User)
            .join(Job,  SavedJob.job_id  == Job.id)
            .join(User, SavedJob.user_id == User.id)
            .filter(
                SavedJob.status == "applied",
                SavedJob.created_at <= cutoff,
                User.is_active == True,
            )
            .all()
        )

        # Group by user
        by_user: dict[int, list] = {}
        for sj, job, user in stale_jobs:
            by_user.setdefault(user.id, {"user": user, "jobs": []})
            by_user[user.id]["jobs"].append(job)

        for data in by_user.values():
            user = data["user"]
            jobs = data["jobs"]
            _send_reminder(user, jobs)

        return f"Sent reminders to {len(by_user)} users"
    finally:
        db.close()


def _send_reminder(user, jobs):
    job_list_html = "".join(
        f"<li style='margin-bottom:6px'><strong>{j.title}</strong>"
        f"{' at ' + j.company if j.company else ''}</li>"
        for j in jobs
    )
    subject = f"⏰ {len(jobs)} application(s) need a follow-up — NextHire"
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;color:#0f172a">
      <div style="background:linear-gradient(135deg,#1e293b,#1e1b4b);padding:32px;border-radius:12px 12px 0 0">
        <h2 style="color:white;margin:0;font-size:22px">Time to follow up, {user.full_name.split()[0]}!</h2>
      </div>
      <div style="background:#f8fafc;padding:28px;border-radius:0 0 12px 12px;border:1px solid #e2e8f0">
        <p style="color:#334155;margin-bottom:16px">
          You applied to <strong>{len(jobs)} job(s)</strong> more than a week ago
          and haven't heard back. Now's a great time to follow up:
        </p>
        <ul style="color:#334155;padding-left:20px;margin-bottom:20px">
          {job_list_html}
        </ul>
        <a href="http://localhost/jobs.html"
           style="display:inline-block;padding:12px 24px;background:#2563eb;color:white;
                  text-decoration:none;border-radius:8px;font-weight:600">
          View my board →
        </a>
        <p style="color:#94a3b8;font-size:12px;margin-top:20px">
          You're receiving this because you have an active NextHire account.
        </p>
      </div>
    </div>
    """
    try:
        _send(user.email, subject, body)
    except Exception as e:
        print(f"[reminder] Failed to email {user.email}: {e}")
