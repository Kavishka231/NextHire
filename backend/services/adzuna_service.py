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

    title = raw.get("title", "Unknown Title")
    description = raw.get("description", "")
    location_text = location.get("display_name", "")
    contract_time = raw.get("contract_time", "")
    return {
        "external_id":   raw.get("id", ""),
        "title":         title,
        "company":       company.get("display_name", ""),
        "location":      location_text,
        "description":   description,
        "role_overview": _role_overview(title, company.get("display_name", ""), location_text, description),
        "experience_level": _experience_level(title),
        "company_description": "",
        "salary_min":    raw.get("salary_min"),
        "salary_max":    raw.get("salary_max"),
        "salary_is_predicted": raw.get("salary_is_predicted", "0") == "1",
        "url":           raw.get("redirect_url", ""),
        "category":      category.get("label", ""),
        "contract_type": raw.get("contract_type", ""),
        "contract_time": contract_time,
        "created":       raw.get("created", ""),
    }


def _experience_level(title: str) -> str:
    lowered = title.lower()
    if any(word in lowered for word in ["senior", "lead", "principal", "staff"]):
        return "Senior"
    if any(word in lowered for word in ["junior", "graduate", "intern", "entry"]):
        return "Entry level"
    if any(word in lowered for word in ["manager", "head", "director"]):
        return "Leadership"
    return "Mid level"


def _role_overview(title: str, company: str, location: str, description: str) -> str:
    clean = " ".join(str(description or "").replace("\n", " ").split())
    if len(clean) > 180:
        return clean[:700]
    company_name = company or "The hiring company"
    place = f" in {location}" if location else ""
    return (
        f"{company_name} is hiring a {title}{place} to help the team deliver reliable, high-quality work. "
        "The role involves understanding business needs, collaborating with colleagues, communicating progress, "
        "and taking ownership of practical outcomes from planning through delivery."
    )


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
        return _mock_results(keywords, location, page, results_per_page, salary_min, salary_max, full_time)

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

def _mock_results(
    keywords: str,
    location: str,
    page: int,
    per_page: int,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    full_time: Optional[bool] = None,
) -> dict:
    mock_jobs = [
        {
            "external_id": f"mock-{i}",
            "title": title,
            "company": company,
            "location": loc,
            "description": f"We are looking for an experienced {title} to join our growing team. "
                           "You will work on exciting projects with modern technologies. "
                           "Remote-friendly, competitive salary, and great benefits.",
            "role_overview": f"{company} needs a {title} to help design, build, and improve business-critical products for customers.",
            "company_description": f"{company} is a growing technology company focused on practical digital products and strong engineering culture.",
            "experience_level": _experience_level(title),
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
            ("Senior Python Developer",       "TechCorp Ltd",        "London, UK",        70000, 90000,  "IT Jobs",               "full_time"),
            ("React Frontend Engineer",       "StartupXYZ",          "Remote",            55000, 75000,  "IT Jobs",               "full_time"),
            ("Data Analyst",                  "DataInsights Co",     "Manchester, UK",    42000, 62000,  "Data & Analytics",      "full_time"),
            ("Product Manager",               "InnovateTech",        "Bristol, UK",       55000, 70000,  "Product Management",    "full_time"),
            ("UX Product Designer",           "Creative Agency",     "Birmingham, UK",    40000, 55000,  "Design & Creative",     "full_time"),
            ("Brand Marketing Manager",       "BrightLabs",          "London, UK",        43000, 61000,  "Marketing Jobs",        "full_time"),
            ("Content Marketing Specialist",  "Northstar Media",     "Remote",            32000, 48000,  "Marketing Jobs",        "part_time"),
            ("Customer Success Associate",    "CareDesk",            "Remote",            28000, 39000,  "Customer Service",      "full_time"),
            ("Customer Support Lead",         "Helpwise",            "Leeds, UK",         34000, 47000,  "Customer Service",      "full_time"),
            ("Human Resources Coordinator",   "PeopleFirst",         "London, UK",        31000, 45000,  "HR Jobs",               "full_time"),
            ("Recruitment Partner",           "TalentBridge",        "Manchester, UK",    36000, 52000,  "HR Jobs",               "part_time"),
            ("Project Manager",               "DeliveryWorks",       "Bristol, UK",       50000, 68000,  "Project Management",    "full_time"),
            ("Agile Delivery Manager",        "FlowStudio",          "Remote",            58000, 76000,  "Project Management",    "full_time"),
            ("Business Development Manager",  "MarketLane",          "London, UK",        45000, 70000,  "Business Development",  "full_time"),
            ("Partnerships Executive",        "GrowthPoint",         "Remote",            35000, 52000,  "Business Development",  "part_time"),
            ("Sales Development Representative", "RevenueStack",      "London, UK",        30000, 46000,  "Sales Jobs",            "full_time"),
            ("Account Executive",             "PipelineHQ",          "Manchester, UK",    42000, 65000,  "Sales Jobs",            "full_time"),
            ("Education Teaching Assistant",  "LearnWell Academy",   "Birmingham, UK",    24000, 32000,  "Teaching & Education",  "part_time"),
            ("Education Experience Designer", "EduCraft",            "Remote",            38000, 56000,  "Teaching & Education",  "full_time"),
            ("Graphic Designer",              "PixelForge",          "Leeds, UK",         30000, 46000,  "Design & Creative",     "full_time"),
            ("Accounts Assistant",            "LedgerLane",          "London, UK",        28000, 38000,  "Accounting & Finance",  "full_time"),
            ("Finance Analyst",               "ClearBooks",          "Remote",            39000, 56000,  "Accounting & Finance",  "full_time"),
            ("Healthcare Coordinator",        "CareNorth",           "Birmingham, UK",    30000, 43000,  "Healthcare & Nursing",  "full_time"),
            ("Clinic Operations Assistant",   "WellPath",            "Manchester, UK",    26000, 36000,  "Healthcare & Nursing",  "part_time"),
            ("Graduate Operations Associate", "LaunchPad",           "London, UK",        27000, 35000,  "Graduate Jobs",        "full_time"),
            ("Junior Business Analyst",       "FirstStep Consulting","Remote",            30000, 42000,  "Graduate Jobs",        "full_time"),
        ], 1)
    ]

    if keywords:
        tokens = [token for token in keywords.lower().replace("&", " ").split() if len(token) > 1]
        mock_jobs = [
            job for job in mock_jobs
            if any(
                token in " ".join([
                    job["title"],
                    job["company"],
                    job["category"],
                    job["description"],
                ]).lower()
                for token in tokens
            )
        ]

    if location:
        loc = location.lower()
        mock_jobs = [job for job in mock_jobs if loc in job["location"].lower()]

    if salary_min:
        mock_jobs = [job for job in mock_jobs if (job["salary_max"] or 0) >= salary_min]

    if salary_max:
        mock_jobs = [job for job in mock_jobs if (job["salary_min"] or 0) <= salary_max]

    if full_time is True:
        mock_jobs = [job for job in mock_jobs if job["contract_time"] == "full_time"]
    elif full_time is False:
        mock_jobs = [job for job in mock_jobs if job["contract_time"] == "part_time"]

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
        {"tag": "teaching-jobs",        "label": "Teaching & Education"},
        {"tag": "design-creative",      "label": "Design & Creative"},
        {"tag": "customer-service",     "label": "Customer Service"},
        {"tag": "project-management",   "label": "Project Management"},
        {"tag": "business-development", "label": "Business Development"},
        {"tag": "legal-jobs",           "label": "Legal Jobs"},
        {"tag": "hr-jobs",              "label": "HR Jobs"},
    ]
