from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.note import Note
from models.saved_job import SavedJob
from models.user import User
from schemas.note import CreateNoteRequest, UpdateNoteRequest


def _verify_saved_job(db: Session, user: User, saved_job_id: int) -> SavedJob:
    sj = db.query(SavedJob).filter(
        SavedJob.id == saved_job_id,
        SavedJob.user_id == user.id,
    ).first()
    if not sj:
        raise HTTPException(status_code=404, detail="Saved job not found")
    return sj


def _get_note(db: Session, user: User, note_id: int) -> Note:
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == user.id,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


def create_note(db: Session, user: User, data: CreateNoteRequest) -> Note:
    _verify_saved_job(db, user, data.saved_job_id)
    note = Note(
        user_id=user.id,
        saved_job_id=data.saved_job_id,
        content=data.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def get_notes_for_job(db: Session, user: User, saved_job_id: int) -> list[Note]:
    _verify_saved_job(db, user, saved_job_id)
    return (
        db.query(Note)
        .filter(Note.saved_job_id == saved_job_id, Note.user_id == user.id)
        .order_by(Note.created_at.desc())
        .all()
    )


def update_note(db: Session, user: User, note_id: int, data: UpdateNoteRequest) -> Note:
    note = _get_note(db, user, note_id)
    note.content = data.content
    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, user: User, note_id: int):
    note = _get_note(db, user, note_id)
    db.delete(note)
    db.commit()
