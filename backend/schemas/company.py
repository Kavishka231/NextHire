from pydantic import BaseModel, ConfigDict, Field, field_validator

from schemas.validation import optional_http_url


class CompanyUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    company_website: str | None = Field(default=None, max_length=2048)
    company_description: str | None = Field(default=None, max_length=5000)

    @field_validator("company_website")
    @classmethod
    def valid_company_website(cls, value: str | None):
        return optional_http_url(value)


class CompanyResponse(BaseModel):
    account_type: str
    company_name: str | None = None
    company_website: str | None = None
    company_description: str | None = None
    company_status: str
    company_verified: bool
