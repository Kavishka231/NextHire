from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from core.dependencies import get_current_user
from models.user import User
from schemas.stats import StatsResponse
from services.stats_service import get_stats

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("", response_model=StatsResponse)
def stats(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Return full stats for the current user's job search."""
    return get_stats(db, current_user)
