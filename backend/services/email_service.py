import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


def _send(to_email: str, subject: str, html_body: str):
    """Low-level SMTP send. Raises on failure."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
        server.starttls()
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        server.sendmail(settings.MAIL_FROM, to_email, msg.as_string())


def send_verification_email(to_email: str, full_name: str, token: str):
    # In production replace localhost with your real domain
    verify_url = f"http://localhost/verify-email?token={token}"
    subject    = "Verify your NextHire account"
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#2563eb">Welcome to NextHire, {full_name}!</h2>
      <p>Click the button below to verify your email address.</p>
      <a href="{verify_url}"
         style="display:inline-block;padding:12px 24px;background:#2563eb;
                color:#fff;text-decoration:none;border-radius:6px;margin:16px 0">
        Verify Email
      </a>
      <p style="color:#6b7280;font-size:13px">
        Link expires in 24 hours. If you didn't create an account, ignore this email.
      </p>
    </div>
    """
    try:
        _send(to_email, subject, body)
    except Exception as e:
        # Log but never crash the registration flow
        print(f"[email] Failed to send verification to {to_email}: {e}")


def send_password_reset_email(to_email: str, full_name: str, token: str):
    reset_url = f"http://localhost/reset-password?token={token}"
    subject   = "Reset your NextHire password"
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#2563eb">Password Reset</h2>
      <p>Hi {full_name}, we received a request to reset your password.</p>
      <a href="{reset_url}"
         style="display:inline-block;padding:12px 24px;background:#2563eb;
                color:#fff;text-decoration:none;border-radius:6px;margin:16px 0">
        Reset Password
      </a>
      <p style="color:#6b7280;font-size:13px">
        Link expires in 1 hour. If you didn't request this, ignore this email.
      </p>
    </div>
    """
    try:
        _send(to_email, subject, body)
    except Exception as e:
        print(f"[email] Failed to send reset to {to_email}: {e}")
