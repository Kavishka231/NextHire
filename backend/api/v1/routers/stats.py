from fastapi import APIRouter, Depends
from services.stats_service import StatsService
from core.dependencies import get_current_user


router = APIRouter(prefix="/stats", tags=["Stats"])

@router.get("/")
def get_stats(user=Depends(get_current_user)):
    return StatsService.get_dashboard_stats(user.id)