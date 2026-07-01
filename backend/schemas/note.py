from pydantic import BaseModel, field_validator
from datetime import datetime


class CreateNoteRequest(BaseModel):
    saved_job_id: int
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Note content cannot be empty")
        return v.strip()


class UpdateNoteRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Note content cannot be empty")
        return v.strip()


class NoteResponse(BaseModel):
    id:           int
    saved_job_id: int
    content:      str
    created_at:   datetime

    class Config:
        from_attributes = True
