import pytest
from pydantic import ValidationError

from app.config import Settings


VALID_PRODUCTION_SETTINGS = {
    "ENVIRONMENT": "production",
    "SECRET_KEY": "a-strong-random-production-secret-key-with-64-characters-123456789",
    "DATABASE_URL": "postgresql://nexthire:strong-database-password@db:5432/nexthire",
    "PUBLIC_APP_URL": "https://jobs.example.com",
    "CORS_ORIGINS": "https://jobs.example.com,https://admin.example.com",
    "REFRESH_COOKIE_SECURE": True,
    "EMAIL_ENABLED": False,
    "SEED_ADMIN": False,
}


def production_settings(**overrides):
    return Settings(_env_file=None, **{**VALID_PRODUCTION_SETTINGS, **overrides})


def test_safe_production_settings_are_accepted():
    settings = production_settings()
    assert settings.ENVIRONMENT == "production"


@pytest.mark.parametrize("public_url", [
    "http://jobs.example.com",
    "https://user:password@jobs.example.com",
    "https://jobs.example.com/path",
])
def test_production_rejects_non_origin_public_urls(public_url):
    with pytest.raises(ValidationError, match="PUBLIC_APP_URL must be an HTTPS origin"):
        production_settings(PUBLIC_APP_URL=public_url)


@pytest.mark.parametrize("origins", [
    "*",
    "",
    "http://jobs.example.com",
    "https://jobs.example.com/path",
    "https://jobs.example.com,*",
])
def test_production_rejects_unsafe_cors_origins(origins):
    with pytest.raises(ValidationError, match="CORS"):
        production_settings(CORS_ORIGINS=origins)


def test_rejects_unsupported_jwt_algorithm():
    with pytest.raises(ValidationError, match="ALGORITHM must be HS256"):
        production_settings(ALGORITHM="none")


@pytest.mark.parametrize("cookie_name", ["", "bad cookie", "bad;cookie", "x" * 129])
def test_rejects_invalid_cookie_names(cookie_name):
    with pytest.raises(ValidationError, match="valid cookie name"):
        production_settings(REFRESH_COOKIE_NAME=cookie_name)


@pytest.mark.parametrize(("field", "value", "message"), [
    ("ACCESS_TOKEN_EXPIRE_MINUTES", 0, "ACCESS_TOKEN_EXPIRE_MINUTES"),
    ("ACCESS_TOKEN_EXPIRE_MINUTES", 1441, "ACCESS_TOKEN_EXPIRE_MINUTES"),
    ("REFRESH_TOKEN_EXPIRE_DAYS", 0, "REFRESH_TOKEN_EXPIRE_DAYS"),
    ("REFRESH_TOKEN_EXPIRE_DAYS", 366, "REFRESH_TOKEN_EXPIRE_DAYS"),
    ("RESET_TOKEN_EXPIRE_MINUTES", 0, "RESET_TOKEN_EXPIRE_MINUTES"),
    ("RESET_TOKEN_EXPIRE_MINUTES", 1441, "RESET_TOKEN_EXPIRE_MINUTES"),
])
def test_rejects_invalid_token_expiry_values(field, value, message):
    with pytest.raises(ValidationError, match=message):
        production_settings(**{field: value})


@pytest.mark.parametrize("database_url", [
    "postgresql://nexthire:replace-me@db:5432/nexthire",
    "postgresql://nexthire:password@db:5432/nexthire",
    "postgresql://nexthire@db:5432/nexthire",
    "mysql://nexthire:strong-password@db:3306/nexthire",
])
def test_production_rejects_placeholder_or_unsupported_database_credentials(database_url):
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        production_settings(DATABASE_URL=database_url)


def test_production_rejects_placeholder_secret_key():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        production_settings(
            SECRET_KEY="replace-with-a-random-secret-at-least-32-characters-long"
        )


def test_disabled_email_does_not_require_smtp_credentials():
    settings = production_settings(
        EMAIL_ENABLED=False,
        MAIL_USERNAME="",
        MAIL_PASSWORD="",
    )
    assert settings.EMAIL_ENABLED is False


@pytest.mark.parametrize("overrides", [
    {"MAIL_USERNAME": ""},
    {"MAIL_USERNAME": "replace-me"},
    {"MAIL_PASSWORD": ""},
    {"MAIL_PASSWORD": "replace-me"},
    {"MAIL_SERVER": ""},
    {"MAIL_SERVER": "smtp://mail.example.com"},
    {"MAIL_FROM_NAME": ""},
])
def test_enabled_production_email_requires_safe_smtp_settings(overrides):
    values = {
        "EMAIL_ENABLED": True,
        "MAIL_USERNAME": "smtp-user",
        "MAIL_PASSWORD": "strong-smtp-password",
        "MAIL_SERVER": "smtp.example.com",
        "MAIL_FROM": "noreply@example.com",
        "MAIL_FROM_NAME": "NextHire",
        **overrides,
    }
    with pytest.raises(ValidationError, match="email configuration"):
        production_settings(**values)


def test_enabled_production_email_requires_valid_sender():
    with pytest.raises(ValidationError, match="MAIL_FROM"):
        production_settings(
            EMAIL_ENABLED=True,
            MAIL_USERNAME="smtp-user",
            MAIL_PASSWORD="strong-smtp-password",
            MAIL_SERVER="smtp.example.com",
            MAIL_FROM="not-an-email",
        )


@pytest.mark.parametrize(("field", "value", "message"), [
    ("MAIL_PORT", 0, "MAIL_PORT"),
    ("MAIL_PORT", 65536, "MAIL_PORT"),
    ("MAIL_TIMEOUT_SECONDS", 0, "MAIL_TIMEOUT_SECONDS"),
])
def test_rejects_invalid_smtp_numeric_settings(field, value, message):
    with pytest.raises(ValidationError, match=message):
        production_settings(
            EMAIL_ENABLED=True,
            MAIL_USERNAME="smtp-user",
            MAIL_PASSWORD="strong-smtp-password",
            MAIL_SERVER="smtp.example.com",
            MAIL_FROM="noreply@example.com",
            **{field: value},
        )
