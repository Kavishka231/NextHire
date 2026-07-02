from pydantic import BaseModel
from typing import Optional


class CompanyJobCreate(BaseModel):
    title: str
    company: str = ""
    location: str = ""
    description: str = ""
    role_overview: str = ""
    company_description: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    category: str = ""
    employment_type: str = ""
    work_style: str = ""
    experience_level: str = ""
    requirements: str = ""
    responsibilities: str = ""
    additional_qualifications: str = ""
    schedule_expectations: str = ""
    benefits: str = ""
    application_email: str = ""
    application_url: str = ""
    application_instructions: str = ""
    deadline: str = ""


class CompanyJobUpdate(CompanyJobCreate):
    title: Optional[str] = None
