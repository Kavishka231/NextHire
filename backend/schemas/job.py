from pydantic import BaseModel
from typing import Optional


class JobSearchParams(BaseModel):
    keywords:        str
    location:        str           = ""
    page:            int           = 1
    results_per_page: int          = 20
    salary_min:      Optional[int] = None
    salary_max:      Optional[int] = None
    full_time:       Optional[bool]= None
    sort_by:         str           = "relevance"   # relevance | date | salary
    country:         str           = "gb"


class JobResult(BaseModel):
    external_id:         str
    title:               str
    company:             str           = ""
    location:            str           = ""
    description:         str           = ""
    salary_min:          Optional[int] = None
    salary_max:          Optional[int] = None
    salary_is_predicted: bool          = False
    url:                 str           = ""
    category:            str           = ""
    contract_type:       str           = ""
    contract_time:       str           = ""
    created:             str           = ""


class JobSearchResponse(BaseModel):
    total:            int
    page:             int
    results_per_page: int
    jobs:             list[JobResult]


class JobCategory(BaseModel):
    tag:   str
    label: str


class JobDB(BaseModel):
    id:          int
    external_id: str
    title:       str
    company:     str           = ""
    location:    str           = ""
    salary_min:  Optional[int] = None
    salary_max:  Optional[int] = None
    url:         str           = ""
    source:      str           = "adzuna"
    is_featured: bool          = False
    company_verified: bool     = False

    class Config:
        from_attributes = True


class CompanyJobCreate(BaseModel):
    title: str
    company: str = ""
    location: str = ""
    description: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    category: str = ""
    employment_type: str = ""
    work_style: str = ""
    experience_level: str = ""
    requirements: str = ""
    responsibilities: str = ""
    benefits: str = ""
    application_email: str = ""
    application_url: str = ""
    application_instructions: str = ""
    deadline: str = ""


class CompanyJobUpdate(CompanyJobCreate):
    title: Optional[str] = None
