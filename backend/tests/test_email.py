from unittest.mock import MagicMock, patch

from services.email_service import _send
from tasks.email_task import _admin_message_html, send_broadcast_email


def test_smtp_transport_uses_timeout_tls_and_login(monkeypatch):
    monkeypatch.setattr("services.email_service.settings.MAIL_USERNAME", "smtp-user")
    monkeypatch.setattr("services.email_service.settings.MAIL_PASSWORD", "smtp-password")
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    with patch("services.email_service.smtplib.SMTP", return_value=smtp) as smtp_factory:
        _send("user@example.com", "Subject", "<p>Body</p>")

    smtp_factory.assert_called_once()
    assert smtp_factory.call_args.kwargs["timeout"] > 0
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once()
    smtp.sendmail.assert_called_once()


def test_smtp_transport_skips_login_without_credentials(monkeypatch):
    monkeypatch.setattr("services.email_service.settings.MAIL_USERNAME", "")
    monkeypatch.setattr("services.email_service.settings.MAIL_PASSWORD", "")
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp

    with patch("services.email_service.smtplib.SMTP", return_value=smtp):
        _send("user@example.com", "Subject", "<p>Body</p>")

    smtp.login.assert_not_called()
    smtp.sendmail.assert_called_once()


def test_admin_email_body_is_html_escaped():
    rendered = _admin_message_html("<script>alert('x')</script>")
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_broadcast_continues_after_one_recipient_fails():
    with patch(
        "tasks.email_task._send",
        side_effect=[OSError("failed"), None],
    ):
        result = send_broadcast_email(
            ["first@example.com", "second@example.com"],
            "Subject",
            "Body",
        )
    assert result == {"sent": 1, "failed": 1}
