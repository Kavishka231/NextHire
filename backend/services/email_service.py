import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


def _send(to_email: str, subject: str, html_body: str):
    """Low-level SMTP send. Raises on failure."""
    if not settings.EMAIL_ENABLED:
        raise RuntimeError("Email delivery is disabled")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(
        settings.MAIL_SERVER,
        settings.MAIL_PORT,
        timeout=settings.MAIL_TIMEOUT_SECONDS,
    ) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        server.sendmail(settings.MAIL_FROM, to_email, msg.as_string())
