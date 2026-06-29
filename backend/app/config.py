from pydantic_settings import BaseSettings
from pathlib import Path

# Resolves:  backend/app/config.py → backend/app → backend → NextHire (root)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────
    APP_NAME: str = "NextHire"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database ─────────────────────────────────
    DATABASE_URL: str

    # ── Redis / Celery ───────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Email ────────────────────────────────────
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = "noreply@nexthire.com"
    MAIL_FROM_NAME: str = "NextHire"
    MAIL_SERVER: str = "smtp.mailtrap.io"
    MAIL_PORT: int = 587

    # ── Adzuna ───────────────────────────────────
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""

    # Local development admin seed. Override these in .env before deploying.
    ADMIN_EMAIL: str = "admin@nexthire.com"
    ADMIN_PASSWORD: str = "Admin@12345"
    ADMIN_FULL_NAME: str = "NextHire Admin"

    class Config:
        env_file = str(ROOT_DIR / ".env")   # ← reads from NextHire/.env
        env_file_encoding = "utf-8"


settings = Settings()
