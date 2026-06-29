ADMIN_EMAIL = "admin@nexthire.com"
ADMIN_PASSWORD = "Admin@12345"


def admin_headers(client):
    res = client.post("/api/v1/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_requires_admin(client, auth_headers):
    res = client.get("/api/v1/admin/summary", headers=auth_headers)
    assert res.status_code == 403


def test_seeded_admin_can_read_summary(client):
    res = client.get("/api/v1/admin/summary", headers=admin_headers(client))
    assert res.status_code == 200
    assert "total_users" in res.json()


def test_admin_can_list_users(client):
    res = client.get("/api/v1/admin/users", headers=admin_headers(client))
    assert res.status_code == 200
    assert any(user["email"] == ADMIN_EMAIL for user in res.json())


def test_admin_can_add_featured_job(client):
    res = client.post(
        "/api/v1/admin/jobs",
        json={"title": "Featured Frontend Engineer", "company": "NextHire", "location": "Remote"},
        headers=admin_headers(client),
    )
    assert res.status_code == 200
    jobs = client.get("/api/v1/admin/jobs", headers=admin_headers(client))
    assert any(job["title"] == "Featured Frontend Engineer" for job in jobs.json())
