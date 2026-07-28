from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
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


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="lax",
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="lax",
        path="/api/v1/auth",
    )


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
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    tokens = AuthService.login(db, data)
    _set_refresh_cookie(response, tokens.pop("refresh_token"))
    return tokens


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/refresh", dependencies=[Depends(rate_limit(
    "refresh",
    settings.AUTH_RATE_LIMIT_PER_MINUTE,
))])
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    tokens = AuthService.refresh(db, refresh_token)
    _set_refresh_cookie(response, tokens.pop("refresh_token"))
    return tokens


@router.post("/logout")
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    if refresh_token:
        AuthService.logout(db, refresh_token)
    _clear_refresh_cookie(response)
    return {"message": "Logged out"}


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
