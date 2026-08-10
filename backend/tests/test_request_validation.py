import pytest
from pydantic import ValidationError

from schemas.application import ApplicationCreate
from schemas.auth import RegisterRequest
from schemas.company import CompanyUpdate
from schemas.job import CompanyJobCreate
from schemas.note import CreateNoteRequest
from schemas.profile import ProfileUpdate
from schemas.saved_job import SavedJobCreate
from tests.test_admin import admin_headers
from tests.test_company_jobs import company_headers, register_company


@pytest.mark.parametrize(("model", "payload"), [
    (RegisterRequest, {
        "email": "person@example.com",
        "full_name": "x" * 151,
        "password": "password123",
    }),
    (RegisterRequest, {
        "email": "company@example.com",
        "full_name": "Company Owner",
        "password": "password123",
        "account_type": "company",
        "company_name": "x" * 201,
    }),
    (CompanyJobCreate, {"title": "x" * 201}),
    (CompanyJobCreate, {"title": "Engineer", "location": "x" * 201}),
    (ApplicationCreate, {"external_id": "job-1", "applicant_name": "x" * 151}),
    (ApplicationCreate, {"external_id": "job-1", "location": "x" * 201}),
])
def test_names_titles_companies_and_locations_are_bounded(model, payload):
    with pytest.raises(ValidationError):
        model(**payload)


@pytest.mark.parametrize(("model", "payload"), [
    (CompanyJobCreate, {"title": "Engineer", "description": "x" * 5001}),
    (ApplicationCreate, {"external_id": "job-1", "cover_letter": "x" * 10_001}),
    (ApplicationCreate, {"external_id": "job-1", "extra_details": "x" * 5001}),
    (CreateNoteRequest, {"saved_job_id": 1, "content": "x" * 5001}),
    (ProfileUpdate, {"bio": "x" * 5001}),
])
def test_descriptions_letters_notes_and_biography_are_bounded(model, payload):
    with pytest.raises(ValidationError):
        model(**payload)


def test_profile_short_lists_are_bounded():
    with pytest.raises(ValidationError):
        ProfileUpdate(preferred_locations=[f"Location {index}" for index in range(26)])
    with pytest.raises(ValidationError):
        ProfileUpdate(industries=["x" * 101])


@pytest.mark.parametrize("skills", [
    [{"name": f"Skill {index}"} for index in range(26)],
    [{f"field_{index}": "value" for index in range(21)}],
    [{"name": "x" * 2001}],
    [{"one": {"two": {"three": {"four": "too deep"}}}}],
])
def test_profile_nested_collections_are_bounded(skills):
    with pytest.raises(ValidationError):
        ProfileUpdate(skills=skills)


@pytest.mark.parametrize(("model", "payload"), [
    (CompanyJobCreate, {"title": "Engineer", "salary_min": 0}),
    (CompanyJobCreate, {"title": "Engineer", "salary_min": 100, "salary_max": 99}),
    (ProfileUpdate, {"expected_salary_min": -1}),
    (ProfileUpdate, {"expected_salary_min": 100, "expected_salary_max": 99}),
])
def test_salaries_are_positive_and_ordered(model, payload):
    with pytest.raises(ValidationError):
        model(**payload)


@pytest.mark.parametrize(("model", "payload"), [
    (CompanyUpdate, {"company_website": "not-a-url"}),
    (RegisterRequest, {
        "email": "company@example.com",
        "full_name": "Company Owner",
        "password": "password123",
        "company_website": "ftp://example.com",
    }),
    (CompanyJobCreate, {"title": "Engineer", "application_url": "javascript:alert(1)"}),
    (ApplicationCreate, {"external_id": "job-1", "resume_url": "data:application/pdf;base64,AAAA"}),
    (ProfileUpdate, {"portfolio_url": "https://user:password@example.com"}),
    (ProfileUpdate, {"portfolio_url": "https://example.com/bad path"}),
])
def test_application_company_and_profile_urls_require_safe_http_urls(model, payload):
    with pytest.raises(ValidationError):
        model(**payload)


@pytest.mark.parametrize("deadline", ["tomorrow", "2026-02-30", "10/08/2026"])
def test_job_deadline_requires_iso_calendar_date(deadline):
    with pytest.raises(ValidationError):
        CompanyJobCreate(title="Engineer", deadline=deadline)


def test_valid_urls_dates_and_salary_ranges_are_accepted():
    job = CompanyJobCreate(
        title="Engineer",
        salary_min=80_000,
        salary_max=120_000,
        application_url="https://jobs.example.com/apply",
        deadline="2026-12-31",
    )
    profile = ProfileUpdate(
        portfolio_url="https://portfolio.example.com",
        expected_salary_min=80_000,
        expected_salary_max=120_000,
    )
    assert job.deadline == "2026-12-31"
    assert profile.portfolio_url == "https://portfolio.example.com"


def test_saved_job_reference_is_positive_and_bounded():
    with pytest.raises(ValidationError):
        SavedJobCreate(job_id=0)
    with pytest.raises(ValidationError):
        SavedJobCreate(external_id="x" * 256)


@pytest.mark.parametrize("params", [
    {"keywords": "developer", "page": 0},
    {"keywords": "developer", "page": 1001},
    {"keywords": "developer", "results_per_page": 0},
    {"keywords": "developer", "results_per_page": 51},
    {"keywords": "developer", "salary_min": 0},
    {"keywords": "developer", "salary_min": 100, "salary_max": 99},
    {"keywords": "developer", "sort_by": "newest"},
    {"keywords": "developer", "country": "lk"},
    {"keywords": "x" * 101},
    {"keywords": "developer", "location": "x" * 101},
    {"keywords": "   "},
])
def test_search_query_parameters_are_bounded(client, params):
    response = client.get("/api/v1/search/jobs", params=params)
    assert response.status_code == 422


def test_search_accepts_supported_country_sort_and_page_size(client):
    response = client.get("/api/v1/search/jobs", params={
        "keywords": "developer",
        "country": "us",
        "sort_by": "date",
        "page": 1,
        "results_per_page": 50,
    })
    assert response.status_code == 200
    assert response.json()["results_per_page"] == 50


def test_categories_reject_unsupported_country(client):
    response = client.get("/api/v1/search/categories", params={"country": "lk"})
    assert response.status_code == 422


def test_profile_partial_salary_update_checks_stored_counterpart(client, auth_headers):
    initial = client.put("/api/v1/profile/me", json={
        "expected_salary_min": 80_000,
        "expected_salary_max": 120_000,
    }, headers=auth_headers)
    invalid_partial = client.put("/api/v1/profile/me", json={
        "expected_salary_min": 130_000,
    }, headers=auth_headers)

    assert initial.status_code == 200
    assert invalid_partial.status_code == 422


def test_job_partial_salary_update_checks_stored_counterpart(client):
    company = register_company(client)
    pending = client.get("/api/v1/admin/companies/pending", headers=admin_headers(client)).json()
    company_id = next(user["id"] for user in pending if user["email"] == company["email"])
    client.patch(
        f"/api/v1/admin/companies/{company_id}/approval",
        json={"approved": True},
        headers=admin_headers(client),
    )
    headers = company_headers(client, company)
    job = client.post("/api/v1/jobs/company", json={
        "title": "Salary Validation Engineer",
        "salary_min": 80_000,
        "salary_max": 120_000,
    }, headers=headers).json()

    invalid_partial = client.put(
        f"/api/v1/jobs/company/{job['id']}",
        json={"salary_min": 130_000},
        headers=headers,
    )

    assert invalid_partial.status_code == 422
