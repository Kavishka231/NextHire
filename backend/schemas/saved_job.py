from pydantic import BaseModel


class SavedJobCreate(BaseModel):
    external_id: str


class SavedJobResponse(BaseModel):
    id: int
    external_id: str
    job_id: int
    status: str

    class Config:
        from_attributes = True
