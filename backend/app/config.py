from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


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
        if self.ENVIRONMENT.lower() == "production":
            if len(self.SECRET_KEY) < 32 or "change-me" in self.SECRET_KEY:
                raise ValueError("Production SECRET_KEY must be a strong value of at least 32 characters")
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError("Production DATABASE_URL must use a managed database")
            if not self.REFRESH_COOKIE_SECURE:
                raise ValueError("Production refresh cookies must be secure")
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
