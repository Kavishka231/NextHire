from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.schemas.auth import RegisterRequest, LoginRequest
from backend.services.auth_service import AuthService
from backend.core.dependencies import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return AuthService.register(db, data)

@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return AuthService.login(db, data)