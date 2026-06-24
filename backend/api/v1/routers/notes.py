from fastapi import APIRouter, Depends
from backend.services.note_service import NoteService
from backend.core.dependencies import get_current_user
from backend.schemas.note import NoteCreate

router = APIRouter(prefix="/notes", tags=["Notes"])

@router.post("/")
def create_note(data: NoteCreate, user=Depends(get_current_user)):
    return NoteService.create_note(user.id, data)

@router.get("/")
def get_notes(user=Depends(get_current_user)):
    return NoteService.get_notes(user.id)