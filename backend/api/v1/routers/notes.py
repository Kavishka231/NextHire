from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from core.dependencies import get_current_user
from models.user import User
from schemas.note import CreateNoteRequest, UpdateNoteRequest, NoteResponse
from schemas.auth import MessageResponse
from services.note_service import (
    create_note, get_notes_for_job, update_note, delete_note,
)

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def add_note(
    data:         CreateNoteRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Add a note to a saved job."""
    return create_note(db, current_user, data)


@router.get("/job/{saved_job_id}", response_model=list[NoteResponse])
def list_notes(
    saved_job_id: int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """List all notes for a specific saved job."""
    return get_notes_for_job(db, current_user, saved_job_id)


@router.put("/{note_id}", response_model=NoteResponse)
def edit_note(
    note_id:      int,
    data:         UpdateNoteRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Edit an existing note."""
    return update_note(db, current_user, note_id, data)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_note(
    note_id:      int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """Delete a note."""
    delete_note(db, current_user, note_id)
