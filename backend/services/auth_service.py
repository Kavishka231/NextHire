from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.models.user import User
from backend.core.security import hash_password, verify_password, create_access_token
from backend.schemas.auth import RegisterRequest, LoginRequest


class AuthService:

    @staticmethod
    def register(db: Session, data: RegisterRequest):
        existing_user = db.query(User).filter(User.email == data.email).first()

        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            name=data.name,
            email=data.email,
            password_hash=hash_password(data.password)
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return {"message": "User created successfully"}

    @staticmethod
    def login(db: Session, data: LoginRequest):
        user = db.query(User).filter(User.email == data.email).first()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token({"user_id": user.id, "email": user.email})

        return {
            "access_token": token,
            "token_type": "bearer"
        }