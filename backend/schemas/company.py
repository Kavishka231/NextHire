from pydantic import BaseModel


class CompanyUpdate(BaseModel):
    company_name: str | None = None
    company_website: str | None = None
    company_description: str | None = None


class CompanyResponse(BaseModel):
    account_type: str
    company_name: str | None = None
    company_website: str | None = None
    company_description: str | None = None
    company_status: str
    company_verified: bool
