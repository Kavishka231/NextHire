from app.config import settings
from services.email_service import _send
from tasks.celery_app import celery_app


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
