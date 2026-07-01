PROFILE_URL = "/api/v1/profile/me"


def test_profile_requires_auth(client):
    res = client.get(PROFILE_URL)
    assert res.status_code == 401


def test_profile_defaults(client, auth_headers):
    res = client.get(PROFILE_URL, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "test@example.com"
    assert body["full_name"] == "Test User"
    assert body["completeness"] < 100
    assert "Add skills" in body["missing_items"]


def test_update_profile_sections(client, auth_headers):
    payload = {
        "headline": "Frontend Developer with 2 years experience",
        "location": "Colombo, Sri Lanka",
        "bio": "I build polished SaaS interfaces and reliable APIs.",
        "open_to_work": True,
        "phone": "+94770000000",
        "github_url": "https://github.com/example",
        "desired_job_title": "Frontend Developer",
        "preferred_job_type": "full time",
        "preferred_work_style": "remote",
        "preferred_locations": ["Remote", "Colombo"],
        "expected_salary_min": 80000,
        "expected_salary_max": 140000,
        "industries": ["SaaS", "AI"],
        "resume_file_name": "resume.pdf",
        "resume_url": "https://example.com/resume.pdf",
        "resume_visible_to_recruiters": True,
        "work_experience": [
            {"title": "Frontend Developer", "company": "Acme", "start_date": "2024-01", "end_date": "current"}
        ],
        "education": [
            {"school": "Example University", "degree": "BSc Computer Science", "start_year": "2021", "end_year": "2025"}
        ],
        "skills": [
            {"name": "React", "level": "expert"},
            {"name": "SQL", "level": "intermediate"},
        ],
        "certifications": [{"name": "AWS Cloud Practitioner", "issuer": "AWS"}],
        "projects": [{"name": "NextHire", "stack": "FastAPI, HTML, CSS, JS"}],
        "languages": [{"name": "English", "proficiency": "fluent"}],
    }

    res = client.put(PROFILE_URL, json=payload, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["headline"] == payload["headline"]
    assert body["open_to_work"] is True
    assert body["skills"][0]["name"] == "React"
    assert body["completeness"] >= 80
