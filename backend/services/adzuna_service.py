import httpx
from typing import Optional
from app.config import settings

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"


def _build_params(
    keywords: str,
    location: str = "",
    page: int = 1,
    results_per_page: int = 20,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    full_time: Optional[bool] = None,
    sort_by: str = "relevance",       # relevance | date | salary
    country: str = "gb",
) -> dict:
    params = {
        "app_id":           settings.ADZUNA_APP_ID,
        "app_key":          settings.ADZUNA_APP_KEY,
        "results_per_page": results_per_page,
        "what":             keywords,
        "content-type":     "application/json",
        "sort_by":          sort_by,
    }
    if location:
        params["where"] = location
    if salary_min:
        params["salary_min"] = salary_min
    if salary_max:
        params["salary_max"] = salary_max
    if full_time is True:
        params["full_time"] = 1
    elif full_time is False:
        params["part_time"] = 1
    return params


def _parse_job(raw: dict) -> dict:
    """Normalize a raw Adzuna job object into our internal shape."""
    company  = raw.get("company", {})
    location = raw.get("location", {})
    category = raw.get("category", {})

    return {
        "external_id":   raw.get("id", ""),
        "title":         raw.get("title", "Unknown Title"),
        "company":       company.get("display_name", ""),
        "location":      location.get("display_name", ""),
        "description":   raw.get("description", ""),
        "salary_min":    raw.get("salary_min"),
        "salary_max":    raw.get("salary_max"),
        "salary_is_predicted": raw.get("salary_is_predicted", "0") == "1",
        "url":           raw.get("redirect_url", ""),
        "category":      category.get("label", ""),
        "contract_type": raw.get("contract_type", ""),
        "contract_time": raw.get("contract_time", ""),
        "created":       raw.get("created", ""),
    }


async def search_jobs(
    keywords: str,
    location: str = "",
    page: int = 1,
    results_per_page: int = 20,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    full_time: Optional[bool] = None,
    sort_by: str = "relevance",
    country: str = "gb",
) -> dict:
    """
    Search Adzuna for jobs. Returns:
      { total, page, results_per_page, jobs: [...] }
    Falls back to mock data if API keys are not configured.
    """
    if not settings.ADZUNA_APP_ID or settings.ADZUNA_APP_ID == "your_adzuna_app_id":
        return _mock_results(keywords, location, page, results_per_page)

    url    = f"{ADZUNA_BASE}/{country}/search/{page}"
    params = _build_params(
        keywords, location, page, results_per_page,
        salary_min, salary_max, full_time, sort_by, country,
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(url, params=params)
        res.raise_for_status()
        data = res.json()

    jobs = [_parse_job(j) for j in data.get("results", [])]
    return {
        "total":            data.get("count", 0),
        "page":             page,
        "results_per_page": results_per_page,
        "jobs":             jobs,
    }


async def get_job_categories(country: str = "gb") -> list:
    """Return available job categories from Adzuna."""
    if not settings.ADZUNA_APP_ID or settings.ADZUNA_APP_ID == "your_adzuna_app_id":
        return _mock_categories()

    url    = f"{ADZUNA_BASE}/{country}/categories"
    params = {"app_id": settings.ADZUNA_APP_ID, "app_key": settings.ADZUNA_APP_KEY}

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(url, params=params)
        res.raise_for_status()
        data = res.json()

    return [
        {"tag": c.get("tag", ""), "label": c.get("label", "")}
        for c in data.get("results", [])
    ]


# ── Mock data (used when no API keys set) ────────────────────────────────────

def _mock_results(keywords: str, location: str, page: int, per_page: int) -> dict:
    mock_jobs = [
        {
            "external_id": f"mock-{i}",
            "title": title,
            "company": company,
            "location": loc,
            "description": f"We are looking for an experienced {title} to join our growing team. "
                           "You will work on exciting projects with modern technologies. "
                           "Remote-friendly, competitive salary, and great benefits.",
            "salary_min": sal_min,
            "salary_max": sal_max,
            "salary_is_predicted": False,
            "url": "#",
            "category": cat,
            "contract_type": "permanent",
            "contract_time": ct,
            "created": "2024-06-01T09:00:00Z",
        }
        for i, (title, company, loc, sal_min, sal_max, cat, ct) in enumerate([
            ("Senior Python Developer",    "TechCorp Ltd",       "London, UK",        70000, 90000,  "IT Jobs",       "full_time"),
            ("React Frontend Engineer",    "StartupXYZ",         "Remote",            55000, 75000,  "IT Jobs",       "full_time"),
            ("Data Scientist",             "DataInsights Co",    "Manchester, UK",    60000, 80000,  "IT Jobs",       "full_time"),
            ("DevOps Engineer",            "CloudSystems Inc",   "Edinburgh, UK",     65000, 85000,  "IT Jobs",       "full_time"),
            ("Product Manager",            "InnovateTech",       "Bristol, UK",       55000, 70000,  "IT Jobs",       "full_time"),
            ("UX/UI Designer",             "Creative Agency",    "Birmingham, UK",    40000, 55000,  "IT Jobs",       "full_time"),
            ("Machine Learning Engineer",  "AI Ventures",        "Cambridge, UK",     75000, 100000, "IT Jobs",       "full_time"),
            ("Backend Engineer (Node.js)", "FinTech Solutions",  "London, UK",        60000, 80000,  "IT Jobs",       "full_time"),
            ("Cloud Architect",            "Enterprise Corp",    "Remote",            85000, 110000, "IT Jobs",       "full_time"),
            ("Full Stack Developer",       "Digital Agency",     "Leeds, UK",         45000, 65000,  "IT Jobs",       "full_time"),
        ], 1)
    ]
    # filter by keyword loosely
    if keywords:
        kw = keywords.lower()
        mock_jobs = [j for j in mock_jobs if kw in j["title"].lower() or kw in j["description"].lower()] or mock_jobs

    start = (page - 1) * per_page
    return {
        "total":            len(mock_jobs),
        "page":             page,
        "results_per_page": per_page,
        "jobs":             mock_jobs[start:start + per_page],
    }


def _mock_categories() -> list:
    return [
        {"tag": "it-jobs",              "label": "IT Jobs"},
        {"tag": "engineering-jobs",     "label": "Engineering Jobs"},
        {"tag": "accounting-finance",   "label": "Accounting & Finance"},
        {"tag": "healthcare-nursing",   "label": "Healthcare & Nursing"},
        {"tag": "sales-jobs",           "label": "Sales Jobs"},
        {"tag": "marketing-jobs",       "label": "Marketing Jobs"},
        {"tag": "graduate-jobs",        "label": "Graduate Jobs"},
        {"tag": "teaching-jobs",        "label": "Teaching Jobs"},
        {"tag": "legal-jobs",           "label": "Legal Jobs"},
        {"tag": "hr-jobs",              "label": "HR Jobs"},
    ]
