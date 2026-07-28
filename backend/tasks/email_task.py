from html import escape
import logging
import smtplib

from app.config import settings
from services.email_service import _send
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _admin_message_html(body: str) -> str:
    safe_body = "<br>".join(escape(body).splitlines())
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;color:#0f172a">
      <div style="background:#1e293b;padding:24px;border-radius:12px 12px 0 0">
        <h2 style="color:white;margin:0">NextHire</h2>
      </div>
      <div style="background:#f8fafc;padding:24px;border:1px solid #e2e8f0">
        <p>{safe_body}</p>
      </div>
    </div>
    """


@celery_app.task(
    name="tasks.email_task.send_password_reset_email",
    autoretry_for=(OSError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_password_reset_email(to_email: str, reset_token: str) -> None:
    reset_url = f"{settings.PUBLIC_APP_URL.rstrip('/')}/reset-password.html?token={reset_token}"
    subject = "Reset your NextHire password"
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;color:#0f172a">
      <h2>Reset your NextHire password</h2>
      <p>This link expires in {settings.RESET_TOKEN_EXPIRE_MINUTES} minutes and can be used once.</p>
      <p><a href="{reset_url}">Choose a new password</a></p>
      <p>If you did not request this change, you can ignore this email.</p>
    </div>
    """
    _send(to_email, subject, body)


@celery_app.task(
    name="tasks.email_task.send_admin_email",
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_admin_email(to_email: str, subject: str, body: str) -> None:
    _send(to_email, subject, _admin_message_html(body))


@celery_app.task(name="tasks.email_task.send_broadcast_email")
def send_broadcast_email(recipients: list[str], subject: str, body: str) -> dict:
    sent = 0
    failed = 0
    html_body = _admin_message_html(body)
    for recipient in recipients:
        try:
            _send(recipient, subject, html_body)
            sent += 1
        except (OSError, smtplib.SMTPException):
            failed += 1
            logger.exception("Broadcast email delivery failed", extra={
                "event": "email_delivery_failure",
                "reason": "broadcast_recipient",
            })
    logger.info("Broadcast email completed", extra={
        "event": "email_broadcast_complete",
        "sent": sent,
        "failed": failed,
    })
    return {"sent": sent, "failed": failed}
