from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from pydantic import EmailStr, TypeAdapter, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
COOKIE_NAME_PATTERN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
EMAIL_ADAPTER = TypeAdapter(EmailStr)
PLACEHOLDER_VALUES = {
    "change-me",
    "changeme",
    "password",
    "replace-me",
    "secret",
    "your-password",
}


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        normalized in PLACEHOLDER_VALUES
        or normalized.startswith(("replace-", "replace_", "your-", "your_"))
        or "change-me" in normalized
    )


def _require_https_origin(value: str, label: str) -> None:
    parsed = urlsplit(value)
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError(f"Production {label} must be an HTTPS origin") from exc
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError(f"Production {label} must be an HTTPS origin")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "NextHire"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "development-only-secret-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_COOKIE_NAME: str = "nexthire_refresh"
    REFRESH_COOKIE_SECURE: bool = False
    RESET_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = "sqlite:///./nexthire.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0
    APP_RELEASE: str = ""
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT_SECONDS: int = 30
    DB_POOL_RECYCLE_SECONDS: int = 1800
    AUTH_RATE_LIMIT_PER_MINUTE: int = 10
    REGISTER_RATE_LIMIT_PER_MINUTE: int = 5
    EMAIL_RATE_LIMIT_PER_HOUR: int = 10
    PUBLIC_APP_URL: str = "http://localhost:5500"
    CORS_ORIGINS: str = "http://localhost:5500,http://127.0.0.1:5500"

    EMAIL_ENABLED: bool = False
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = "noreply@nexthire.com"
    MAIL_FROM_NAME: str = "NextHire"
    MAIL_SERVER: str = "smtp.mailtrap.io"
    MAIL_PORT: int = 587
    MAIL_TIMEOUT_SECONDS: int = 10
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""

    SEED_ADMIN: bool = False
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    ADMIN_FULL_NAME: str = "NextHire Admin"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_runtime(self):
        if self.ALGORITHM != "HS256":
            raise ValueError("ALGORITHM must be HS256")
        if (
            not self.REFRESH_COOKIE_NAME
            or len(self.REFRESH_COOKIE_NAME) > 128
            or not COOKIE_NAME_PATTERN.fullmatch(self.REFRESH_COOKIE_NAME)
        ):
            raise ValueError("REFRESH_COOKIE_NAME is not a valid cookie name")
        if not 1 <= self.ACCESS_TOKEN_EXPIRE_MINUTES <= 24 * 60:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 1440")
        if not 1 <= self.REFRESH_TOKEN_EXPIRE_DAYS <= 365:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be between 1 and 365")
        if not 1 <= self.RESET_TOKEN_EXPIRE_MINUTES <= 24 * 60:
            raise ValueError("RESET_TOKEN_EXPIRE_MINUTES must be between 1 and 1440")
        if self.ENVIRONMENT.lower() == "production":
            if len(self.SECRET_KEY) < 32 or _is_placeholder(self.SECRET_KEY):
                raise ValueError("Production SECRET_KEY must be a strong value of at least 32 characters")
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError("Production DATABASE_URL must use a managed database")
            database = urlsplit(self.DATABASE_URL)
            try:
                database.port
            except ValueError as exc:
                raise ValueError("Production DATABASE_URL contains an invalid port") from exc
            database_username = unquote(database.username or "")
            database_password = unquote(database.password or "")
            if (
                not database.scheme.startswith("postgresql")
                or not database.hostname
                or not database_username
                or _is_placeholder(database_username)
                or not database_password
                or _is_placeholder(database_password)
            ):
                raise ValueError(
                    "Production DATABASE_URL must use PostgreSQL with non-placeholder credentials"
                )
            if not self.REFRESH_COOKIE_SECURE:
                raise ValueError("Production refresh cookies must be secure")
            _require_https_origin(self.PUBLIC_APP_URL, "PUBLIC_APP_URL")
            origins = self.cors_origins
            if not origins or "*" in origins:
                raise ValueError("Production CORS_ORIGINS must not be empty or contain a wildcard")
            for origin in origins:
                _require_https_origin(origin, "CORS origin")
            if self.EMAIL_ENABLED:
                if not 1 <= self.MAIL_PORT <= 65535:
                    raise ValueError("MAIL_PORT must be between 1 and 65535")
                if self.MAIL_TIMEOUT_SECONDS < 1:
                    raise ValueError("MAIL_TIMEOUT_SECONDS must be positive")
                if (
                    not self.MAIL_USERNAME.strip()
                    or _is_placeholder(self.MAIL_USERNAME)
                    or not self.MAIL_PASSWORD
                    or _is_placeholder(self.MAIL_PASSWORD)
                    or not self.MAIL_SERVER.strip()
                    or _is_placeholder(self.MAIL_SERVER)
                    or "://" in self.MAIL_SERVER
                    or any(character.isspace() for character in self.MAIL_SERVER)
                    or not self.MAIL_FROM_NAME.strip()
                ):
                    raise ValueError("Production email configuration is incomplete or unsafe")
                try:
                    EMAIL_ADAPTER.validate_python(self.MAIL_FROM)
                except ValueError as exc:
                    raise ValueError("Production MAIL_FROM must be a valid email address") from exc
        if self.SEED_ADMIN and (not self.ADMIN_EMAIL or len(self.ADMIN_PASSWORD) < 12):
            raise ValueError("Admin bootstrap requires ADMIN_EMAIL and a password of at least 12 characters")
        if min(
            self.AUTH_RATE_LIMIT_PER_MINUTE,
            self.REGISTER_RATE_LIMIT_PER_MINUTE,
            self.EMAIL_RATE_LIMIT_PER_HOUR,
        ) < 1:
            raise ValueError("Rate limits must be positive integers")
        if self.DB_POOL_SIZE < 1 or self.DB_MAX_OVERFLOW < 0:
            raise ValueError("Database pool settings are invalid")
        if not 0 <= self.SENTRY_TRACES_SAMPLE_RATE <= 1:
            raise ValueError("Sentry traces sample rate must be between 0 and 1")
        return self


settings = Settings()
