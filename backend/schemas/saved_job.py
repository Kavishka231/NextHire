from typing import Optional
from pydantic import BaseModel, model_validator


class SavedJobCreate(BaseModel):
    job_id: Optional[int] = None
    external_id: Optional[str] = None

    @model_validator(mode="after")
    def has_job_reference(self):
        if self.job_id is None and not self.external_id:
            raise ValueError("job_id or external_id is required")
        return self


class SavedJobStatusUpdate(BaseModel):
    status: str

    @model_validator(mode="after")
    def valid_status(self):
        allowed = {"saved", "applied", "interview", "offer", "rejected"}
        if self.status not in allowed:
            raise ValueError("Invalid status")
        return self


class SavedJobResponse(BaseModel):
    id: int
    external_id: str
    job_id: int
    status: str

    class Config:
        from_attributes = True
