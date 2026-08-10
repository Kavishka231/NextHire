from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from app.config import settings
from models.user import User
from tests.conftest import TestingSessionLocal

ADMIN_EMAIL = "admin@nexthire.com"
ADMIN_PASSWORD = "Admin@Test12345"


def admin_headers(client):
    res = client.post("/api/v1/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def token_version_for(user_id: int) -> int:
    db = TestingSessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).one().token_version
    finally:
        db.close()


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


def test_disabling_user_revokes_refresh_sessions(client):
    user = client.post("/api/v1/auth/register", json={
        "email": "disabled@example.com",
        "full_name": "Disabled User",
        "password": "password123",
    }).json()
    login = client.post("/api/v1/auth/login", json={
        "email": "disabled@example.com",
        "password": "password123",
    })
    user_refresh = login.cookies.get(settings.REFRESH_COOKIE_NAME)
    user_access = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.patch(
        f"/api/v1/admin/users/{user['id']}",
        json={"is_active": False},
        headers=admin_headers(client),
    )

    assert response.status_code == 200
    assert token_version_for(user["id"]) == 1
    assert client.get("/api/v1/auth/me", headers=user_access).status_code == 401
    client.cookies.set(settings.REFRESH_COOKIE_NAME, user_refresh)
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_banning_user_invalidates_existing_access_token(client):
    user = client.post("/api/v1/auth/register", json={
        "email": "banned@example.com",
        "full_name": "Banned User",
        "password": "password123",
    }).json()
    login = client.post("/api/v1/auth/login", json={
        "email": "banned@example.com",
        "password": "password123",
    })
    user_access = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.patch(
        f"/api/v1/admin/users/{user['id']}",
        json={"banned_until": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()},
        headers=admin_headers(client),
    )

    assert response.status_code == 200
    assert token_version_for(user["id"]) == 1
    assert client.get("/api/v1/auth/me", headers=user_access).status_code == 401


def test_admin_password_reset_revokes_refresh_sessions(client):
    user = client.post("/api/v1/auth/register", json={
        "email": "admin-reset@example.com",
        "full_name": "Admin Reset User",
        "password": "password123",
    }).json()
    login = client.post("/api/v1/auth/login", json={
        "email": "admin-reset@example.com",
        "password": "password123",
    })
    user_refresh = login.cookies.get(settings.REFRESH_COOKIE_NAME)
    user_access = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.post(
        f"/api/v1/admin/users/{user['id']}/reset-password",
        json={"new_password": "replacement-password"},
        headers=admin_headers(client),
    )

    assert response.status_code == 200
    assert token_version_for(user["id"]) == 1
    assert client.get("/api/v1/auth/me", headers=user_access).status_code == 401
    client.cookies.set(settings.REFRESH_COOKIE_NAME, user_refresh)
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_admin_can_add_featured_job(client):
    res = client.post(
        "/api/v1/admin/jobs",
        json={"title": "Featured Frontend Engineer", "company": "NextHire", "location": "Remote"},
        headers=admin_headers(client),
    )
    assert res.status_code == 200
    jobs = client.get("/api/v1/admin/jobs", headers=admin_headers(client))
    assert any(job["title"] == "Featured Frontend Engineer" for job in jobs.json())


def test_super_admin_can_queue_broadcast_to_active_users(client):
    client.post("/api/v1/auth/register", json={
        "email": "recipient@example.com",
        "full_name": "Recipient",
        "password": "password123",
    })
    with patch(
        "api.v1.routers.admin.send_broadcast_email.delay",
        return_value=SimpleNamespace(id="broadcast-task"),
    ) as queue:
        response = client.post(
            "/api/v1/admin/email/broadcast",
            json={"subject": "Product update", "body": "A useful update for all active users."},
            headers=admin_headers(client),
        )
    assert response.status_code == 200
    assert response.json()["task_id"] == "broadcast-task"
    assert response.json()["recipients"] == 2
    recipients, subject, body = queue.call_args.args
    assert set(recipients) == {ADMIN_EMAIL, "recipient@example.com"}
    assert subject == "Product update"
    assert body == "A useful update for all active users."


def test_admin_can_queue_email_for_active_user(client):
    registered = client.post("/api/v1/auth/register", json={
        "email": "one@example.com",
        "full_name": "One User",
        "password": "password123",
    }).json()
    with patch(
        "api.v1.routers.admin.send_admin_email.delay",
        return_value=SimpleNamespace(id="user-email-task"),
    ) as queue:
        response = client.post(
            f"/api/v1/admin/email/user/{registered['id']}",
            json={"subject": "Application update", "body": "Your application has an update."},
            headers=admin_headers(client),
        )
    assert response.status_code == 200
    assert response.json()["task_id"] == "user-email-task"
    queue.assert_called_once_with(
        "one@example.com",
        "Application update",
        "Your application has an update.",
    )


def test_email_endpoints_reject_invalid_payload_and_non_admin(client, auth_headers):
    invalid = client.post(
        "/api/v1/admin/email/broadcast",
        json={"subject": "", "body": ""},
        headers=admin_headers(client),
    )
    assert invalid.status_code == 422

    forbidden = client.post(
        "/api/v1/admin/email/broadcast",
        json={"subject": "Subject", "body": "Body"},
        headers=auth_headers,
    )
    assert forbidden.status_code == 403


def test_email_queue_failure_returns_service_unavailable(client):
    registered = client.post("/api/v1/auth/register", json={
        "email": "queue@example.com",
        "full_name": "Queue User",
        "password": "password123",
    }).json()
    with patch(
        "api.v1.routers.admin.send_admin_email.delay",
        side_effect=RuntimeError("queue unavailable"),
    ):
        response = client.post(
            f"/api/v1/admin/email/user/{registered['id']}",
            json={"subject": "Subject", "body": "Body"},
            headers=admin_headers(client),
        )
    assert response.status_code == 503
    assert response.json()["detail"] == "Email queue unavailable"
