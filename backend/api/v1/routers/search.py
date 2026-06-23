from fastapi import APIRouter, Query
from backend.services.adzuna_service import AdzunaService

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/")
def search_jobs(query: str = Query(...)):
    return AdzunaService.search_jobs(query)