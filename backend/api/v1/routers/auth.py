from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
)
from services.auth_service import AuthService
from core.dependencies import get_current_user, get_db
from core.rate_limit import rate_limit
from app.config import settings
from models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(
        "register",
        settings.REGISTER_RATE_LIMIT_PER_MINUTE,
    ))],
)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return AuthService.register(db, data)


@router.post("/login", dependencies=[Depends(rate_limit(
    "login",
    settings.AUTH_RATE_LIMIT_PER_MINUTE,
))])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return AuthService.login(db, data)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/refresh", dependencies=[Depends(rate_limit(
    "refresh",
    settings.AUTH_RATE_LIMIT_PER_MINUTE,
))])
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    return AuthService.refresh(db, data.refresh_token)


@router.post("/logout")
def logout(data: RefreshRequest, db: Session = Depends(get_db)):
    return AuthService.logout(db, data.refresh_token)


@router.post("/forgot-password", dependencies=[Depends(rate_limit(
    "forgot-password",
    settings.REGISTER_RATE_LIMIT_PER_MINUTE,
))])
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    return AuthService.forgot_password(db, data.email)


@router.post("/reset-password", dependencies=[Depends(rate_limit(
    "reset-password",
    settings.AUTH_RATE_LIMIT_PER_MINUTE,
))])
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    return AuthService.reset_password(db, data.token, data.new_password)


@router.put("/change-password")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AuthService.change_password(db, current_user, data.current_password, data.new_password)
