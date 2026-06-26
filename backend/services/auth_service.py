from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import uuid4

from models.user import User
from models.refresh_token import RefreshToken
from core.security import hash_password, verify_password, create_access_token
from schemas.auth import RegisterRequest, LoginRequest


class AuthService:

    @staticmethod
    def register(db: Session, data: RegisterRequest):
        existing_user = db.query(User).filter(User.email == data.email).first()

        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")

        user = User(
            full_name=data.full_name,
            email=data.email,
            hashed_password=hash_password(data.password)
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def login(db: Session, data: LoginRequest):
        user = db.query(User).filter(User.email == data.email).first()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not verify_password(data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token({"user_id": user.id, "email": user.email})
        refresh = RefreshToken(token=str(uuid4()), user_id=user.id)
        db.add(refresh)
        db.commit()

        return {
            "access_token": token,
            "refresh_token": refresh.token,
            "token_type": "bearer"
        }

    @staticmethod
    def refresh(db: Session, token: str):
        refresh = (
            db.query(RefreshToken)
            .filter(RefreshToken.token == token, RefreshToken.is_revoked.is_(False))
            .first()
        )
        if not refresh:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        user = db.query(User).filter(User.id == refresh.user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        return {
            "access_token": create_access_token({"user_id": user.id, "email": user.email}),
            "token_type": "bearer",
        }

    @staticmethod
    def logout(db: Session, token: str):
        refresh = db.query(RefreshToken).filter(RefreshToken.token == token).first()
        if refresh:
            refresh.is_revoked = True
            db.commit()
        return {"message": "Logged out"}

    @staticmethod
    def forgot_password():
        return {"message": "If the email exists, password reset instructions were sent"}

    @staticmethod
    def change_password(db: Session, user: User, current_password: str, new_password: str):
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        user.hashed_password = hash_password(new_password)
        db.commit()
        return {"message": "Password changed"}
