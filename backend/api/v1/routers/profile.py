from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.dependencies import get_current_user, get_db
from models.user import User
from schemas.profile import ProfileResponse, ProfileUpdate
from services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me", response_model=ProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = ProfileService.get_or_create(db, current_user)
    return ProfileService.to_response(profile, current_user)


@router.put("/me", response_model=ProfileResponse)
def update_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = ProfileService.update(db, current_user, data)
    return ProfileService.to_response(profile, current_user)
