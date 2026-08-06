from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import secrets

from app.config import settings
from models.password_reset_token import PasswordResetToken
from models.user import User
from models.refresh_token import RefreshToken
from core.security import hash_password, verify_password, create_access_token, create_refresh_token
from schemas.auth import RegisterRequest, LoginRequest
from services.notification_service import notify_admins
from tasks.email_task import send_password_reset_email

logger = logging.getLogger(__name__)


def _token_response(access_token: str, refresh_token: str) -> dict:
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class AuthService:

    @staticmethod
    def create_refresh_session(user_id: int) -> RefreshToken:
        return RefreshToken(
            token=create_refresh_token(),
            user_id=user_id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

    @staticmethod
    def revoke_all_sessions(db: Session, user_id: int) -> None:
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked.is_(False),
        ).update({"is_revoked": True}, synchronize_session=False)

    @staticmethod
    def register(db: Session, data: RegisterRequest):
        existing_user = db.query(User).filter(User.email == data.email).first()

        if existing_user:
            logger.warning("User registration failed", extra={
                "event": "user_registration_failed",
                "reason": "duplicate_email",
                "outcome": "failure",
            })
            raise HTTPException(status_code=400, detail="User already exists")

        user = User(
            full_name=data.full_name,
            email=data.email,
            hashed_password=hash_password(data.password),
            account_type=data.account_type,
            company_name=data.company_name if data.account_type == "company" else None,
            company_website=data.company_website if data.account_type == "company" else None,
            company_description=data.company_description if data.account_type == "company" else None,
            company_status="pending" if data.account_type == "company" else "none",
            company_verified=False,
        )

        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("User registered", extra={
            "event": "user_registered",
            "user_id": user.id,
            "account_type": user.account_type,
            "company_name": user.company_name,
            "outcome": "success",
        })

        if user.account_type == "company":
            notify_admins(
                db,
                "New company registration",
                f"{user.company_name or user.full_name} is waiting for company approval.",
                "company_pending",
            )
            db.commit()

        return user

    @staticmethod
    def login(db: Session, data: LoginRequest):
        user = db.query(User).filter(User.email == data.email).first()

        if not user:
            logger.warning("Authentication failed", extra={
                "event": "login_failed", "reason": "invalid_credentials",
                "outcome": "failure",
            })
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not user.is_active:
            logger.warning("Authentication failed", extra={
                "event": "login_failed", "user_id": user.id, "reason": "inactive",
                "outcome": "failure",
            })
            raise HTTPException(status_code=403, detail="Account is deactivated")

        if user.banned_until and user.banned_until > datetime.now(timezone.utc):
            logger.warning("Authentication failed", extra={
                "event": "login_failed", "user_id": user.id, "reason": "banned",
                "outcome": "failure",
            })
            raise HTTPException(status_code=403, detail="Account is temporarily banned")

        if not verify_password(data.password, user.hashed_password):
            logger.warning("Authentication failed", extra={
                "event": "login_failed", "user_id": user.id, "reason": "invalid_credentials",
                "outcome": "failure",
            })
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token({"user_id": user.id, "email": user.email})
        refresh = AuthService.create_refresh_session(user.id)
        user.last_active_at = datetime.now(timezone.utc)
        db.add(refresh)
        db.commit()
        logger.info("User logged in", extra={
            "event": "login_success",
            "user_id": user.id,
            "account_type": user.account_type,
            "outcome": "success",
        })

        return _token_response(token, refresh.token)

    @staticmethod
    def refresh(db: Session, token: str):
        refresh = (
            db.query(RefreshToken)
            .filter(RefreshToken.token == token)
            .with_for_update()
            .first()
        )
        if not refresh:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        if refresh.is_revoked:
            logger.warning("Refresh token reuse rejected", extra={
                "event": "refresh_token_reuse", "user_id": refresh.user_id,
                "reason": "revoked",
                "outcome": "failure",
            })
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        now = datetime.now(timezone.utc)
        if _as_utc(refresh.expires_at) <= now:
            refresh.is_revoked = True
            db.commit()
            logger.warning("Expired refresh token rejected", extra={
                "event": "authentication_failure", "user_id": refresh.user_id,
                "reason": "expired_refresh_token",
                "outcome": "failure",
            })
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        user = db.query(User).filter(User.id == refresh.user_id).first()
        if (
            not user
            or not user.is_active
            or (user.banned_until and _as_utc(user.banned_until) > now)
        ):
            refresh.is_revoked = True
            db.commit()
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        refresh.is_revoked = True
        rotated_refresh = AuthService.create_refresh_session(user.id)
        db.add(rotated_refresh)
        db.commit()
        return _token_response(
            create_access_token({"user_id": user.id, "email": user.email}),
            rotated_refresh.token,
        )

    @staticmethod
    def logout(db: Session, token: str):
        refresh = db.query(RefreshToken).filter(RefreshToken.token == token).first()
        if refresh:
            refresh.is_revoked = True
            db.commit()
        return {"message": "Logged out"}

    @staticmethod
    def forgot_password(db: Session, email: str):
        user = db.query(User).filter(User.email == email).first()
        if user and user.is_active:
            now = datetime.now(timezone.utc)
            db.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            ).update({"used_at": now}, synchronize_session=False)

            raw_token = secrets.token_urlsafe(48)
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            db.add(PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=now + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES),
            ))
            db.commit()
            try:
                send_password_reset_email.delay(user.email, raw_token)
            except Exception:
                logger.exception("Failed to queue password reset email", extra={
                    "event": "email_queue_failure",
                    "reason": "password_reset",
                    "outcome": "failure",
                })
        return {"message": "If the email exists, password reset instructions were sent"}

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str):
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        reset_token = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
            )
            .first()
        )
        now = datetime.now(timezone.utc)
        if not reset_token:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        expires_at = reset_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            reset_token.used_at = now
            db.commit()
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        user = db.query(User).filter(User.id == reset_token.user_id).first()
        if not user or not user.is_active:
            reset_token.used_at = now
            db.commit()
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        user.hashed_password = hash_password(new_password)
        reset_token.used_at = now
        AuthService.revoke_all_sessions(db, user.id)
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != reset_token.id,
            PasswordResetToken.used_at.is_(None),
        ).update({"used_at": now}, synchronize_session=False)
        db.commit()
        return {"message": "Password reset successfully"}

    @staticmethod
    def change_password(db: Session, user: User, current_password: str, new_password: str):
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user.hashed_password = hash_password(new_password)
        AuthService.revoke_all_sessions(db, user.id)
        db.commit()
        return {"message": "Password changed"}
