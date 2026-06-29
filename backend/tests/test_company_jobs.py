from tests.test_admin import admin_headers


def register_company(client):
    payload = {
        "email": "hr@example.com",
        "full_name": "Hiring Manager",
        "password": "password123",
        "account_type": "company",
        "company_name": "Example Labs",
        "company_website": "https://example.com",
        "company_description": "Builds hiring software",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    return payload


def company_headers(client, payload):
    res = client.post("/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_company_registers_pending(client):
    company = register_company(client)
    users = client.get("/api/v1/admin/companies/pending", headers=admin_headers(client)).json()
    assert any(user["email"] == company["email"] and user["company_status"] == "pending" for user in users)
    notes = client.get("/api/v1/notifications", headers=admin_headers(client))
    assert notes.status_code == 200
    assert any(note["kind"] == "company_pending" for note in notes.json())


def test_pending_company_cannot_post_job(client):
    company = register_company(client)
    res = client.post(
        "/api/v1/jobs/company",
        json={"title": "Frontend Engineer", "description": "Build UI"},
        headers=company_headers(client, company),
    )
    assert res.status_code == 403


def test_admin_approves_company_and_company_posts_job(client):
    company = register_company(client)
    pending = client.get("/api/v1/admin/companies/pending", headers=admin_headers(client)).json()
    company_id = next(user["id"] for user in pending if user["email"] == company["email"])
    approval = client.patch(
        f"/api/v1/admin/companies/{company_id}/approval",
        json={"approved": True},
        headers=admin_headers(client),
    )
    assert approval.status_code == 200
    assert approval.json()["company_verified"] is True
    company_notes = client.get("/api/v1/notifications", headers=company_headers(client, company)).json()
    assert any(note["kind"] == "company_approval" for note in company_notes)

    created = client.post(
        "/api/v1/jobs/company",
        json={
            "title": "Frontend Engineer",
            "location": "Remote",
            "description": "Build polished UI",
            "application_email": "hr@example.com",
        },
        headers=company_headers(client, company),
    )
    assert created.status_code == 200
    body = created.json()
    assert body["source"] == "company"
    assert body["company_verified"] is True

    detail = client.get(f"/api/v1/jobs/external/{body['external_id']}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "Frontend Engineer"


def test_company_profile_update_sets_pending(client):
    company = register_company(client)
    pending = client.get("/api/v1/admin/companies/pending", headers=admin_headers(client)).json()
    company_id = next(user["id"] for user in pending if user["email"] == company["email"])
    client.patch(f"/api/v1/admin/companies/{company_id}/approval", json={"approved": True}, headers=admin_headers(client))

    res = client.put(
        "/api/v1/company/me",
        json={"company_name": "Renamed Labs", "company_website": "https://renamed.example"},
        headers=company_headers(client, company),
    )
    assert res.status_code == 200
    assert res.json()["company_status"] == "pending"
    assert res.json()["company_verified"] is False
