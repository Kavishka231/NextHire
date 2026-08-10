from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Optional

from schemas.validation import optional_email, optional_http_url, optional_iso_date, validate_salary_range


class CompanyJobCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    company: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)
    role_overview: str = Field(default="", max_length=10_000)
    company_description: str = Field(default="", max_length=10_000)
    salary_min: Optional[int] = Field(default=None, gt=0, le=1_000_000_000)
    salary_max: Optional[int] = Field(default=None, gt=0, le=1_000_000_000)
    category: str = Field(default="", max_length=100)
    employment_type: str = Field(default="", max_length=100)
    work_style: str = Field(default="", max_length=100)
    experience_level: str = Field(default="", max_length=100)
    requirements: str = Field(default="", max_length=10_000)
    responsibilities: str = Field(default="", max_length=10_000)
    additional_qualifications: str = Field(default="", max_length=10_000)
    schedule_expectations: str = Field(default="", max_length=5000)
    benefits: str = Field(default="", max_length=5000)
    application_email: str = Field(default="", max_length=320)
    application_url: str = Field(default="", max_length=2048)
    application_instructions: str = Field(default="", max_length=5000)
    deadline: str = Field(default="", max_length=10)

    @field_validator("application_email")
    @classmethod
    def valid_application_email(cls, value: str):
        return optional_email(value) or ""

    @field_validator("application_url")
    @classmethod
    def valid_application_url(cls, value: str):
        return optional_http_url(value) or ""

    @field_validator("deadline")
    @classmethod
    def valid_deadline(cls, value: str):
        return optional_iso_date(value) or ""

    @model_validator(mode="after")
    def valid_salary_range(self):
        validate_salary_range(self.salary_min, self.salary_max)
        return self


class CompanyJobUpdate(CompanyJobCreate):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
