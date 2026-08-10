from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from sqlalchemy import event
from app.config import settings
from models.admin_audit_log import AdminAuditLog
from models.user import User
from tests.conftest import TestingSessionLocal, engine

ADMIN_EMAIL = "admin@nexthire.com"
ADMIN_PASSWORD = "Admin@Test12345"


def admin_headers(client):
    res = client.post("/api/v1/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_admin_headers(client, email: str, role: str):
    response = client.post(
        f"/api/v1/admin/admins?role={role}",
        json={
            "email": email,
            "full_name": f"{role} account",
            "password": "Admin@Test12345",
        },
        headers=admin_headers(client),
    )
    assert response.status_code == 200
    login = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Admin@Test12345",
    })
    assert login.status_code == 200
    return response.json(), {"Authorization": f"Bearer {login.json()['access_token']}"}


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
    body = res.json()
    assert set(body) == {"items", "page", "page_size", "total"}
    assert any(user["email"] == ADMIN_EMAIL for user in body["items"])


def test_admin_user_pagination_has_fixed_query_count(client):
    for index in range(5):
        client.post("/api/v1/auth/register", json={
            "email": f"page-user-{index}@example.com",
            "full_name": f"Page User {index}",
            "password": "password123",
        })

    headers = admin_headers(client)
    statements = []

    def record_query(_connection, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", record_query)
    try:
        response = client.get(
            "/api/v1/admin/users?page=2&page_size=2",
            headers=headers,
        )
    finally:
        event.remove(engine, "before_cursor_execute", record_query)

    assert response.status_code == 200
    assert response.json()["page"] == 2
    assert response.json()["page_size"] == 2
    assert response.json()["total"] == 6
    assert len(response.json()["items"]) == 2
    # Authentication, total count, and one aggregate collection query.
    assert len(statements) == 3


def test_collection_pagination_rejects_invalid_bounds(client):
    headers = admin_headers(client)
    assert client.get("/api/v1/admin/users?page=0", headers=headers).status_code == 422
    assert client.get("/api/v1/admin/users?page_size=101", headers=headers).status_code == 422


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


def test_security_update_requires_strict_types_and_aware_ban_dates(client):
    user = client.post("/api/v1/auth/register", json={
        "email": "typed-security@example.com",
        "full_name": "Typed Security",
        "password": "password123",
    }).json()
    url = f"/api/v1/admin/users/{user['id']}"
    headers = admin_headers(client)

    assert client.patch(url, json={"is_active": "false"}, headers=headers).status_code == 422
    assert client.patch(url, json={"banned_until": "not-a-date"}, headers=headers).status_code == 422
    assert client.patch(url, json={"banned_until": "2030-01-01T10:00:00"}, headers=headers).status_code == 422
    assert client.patch(url, json={"admin_role": "super_admin"}, headers=headers).status_code == 422

    db = TestingSessionLocal()
    try:
        unchanged = db.query(User).filter(User.id == user["id"]).one()
        assert unchanged.is_active is True
        assert unchanged.admin_role == "user"
    finally:
        db.close()


@pytest.mark.parametrize(("method", "path", "payload"), [
    ("patch", "/api/v1/admin/companies/999/approval", {"approved": "false"}),
    ("post", "/api/v1/admin/users/1/reset-password", {"new_password": "password123", "role": "admin"}),
    ("post", "/api/v1/admin/jobs", {"title": "Typed job", "unexpected": True}),
    ("patch", "/api/v1/admin/jobs/999", {"unexpected": True}),
    ("patch", "/api/v1/admin/moderation/profiles/999", {"clear_bio": True, "unexpected": True}),
])
def test_admin_mutations_reject_coerced_or_unknown_fields(client, method, path, payload):
    response = getattr(client, method)(path, json=payload, headers=admin_headers(client))
    assert response.status_code == 422


def test_moderator_cannot_modify_an_administrator(client):
    moderator, moderator_headers = create_admin_headers(
        client,
        "moderator@example.com",
        "moderator",
    )
    admin_users = client.get(
        "/api/v1/admin/users",
        headers=admin_headers(client),
    ).json()["items"]
    seeded_admin_id = next(user["id"] for user in admin_users if user["email"] == ADMIN_EMAIL)

    response = client.patch(
        f"/api/v1/admin/users/{seeded_admin_id}",
        json={"is_verified": False},
        headers=moderator_headers,
    )

    assert moderator["admin_role"] == "moderator"
    assert response.status_code == 403
    assert response.json()["detail"] == "Only super-admins can modify administrator accounts"

    escalation = client.patch(
        f"/api/v1/admin/users/{moderator['id']}",
        json={"admin_role": "super_admin", "is_admin": True},
        headers=moderator_headers,
    )
    assert escalation.status_code == 422
    db = TestingSessionLocal()
    try:
        unchanged = db.query(User).filter(User.id == moderator["id"]).one()
        assert unchanged.admin_role == "moderator"
    finally:
        db.close()


def test_final_active_super_admin_cannot_be_disabled_banned_or_deleted(client):
    headers = admin_headers(client)
    admin_id = client.get("/api/v1/admin/users", headers=headers).json()["items"][0]["id"]
    future_ban = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    disabled = client.patch(
        f"/api/v1/admin/users/{admin_id}",
        json={"is_active": False},
        headers=headers,
    )
    banned = client.patch(
        f"/api/v1/admin/users/{admin_id}",
        json={"banned_until": future_ban},
        headers=headers,
    )
    deleted = client.delete(f"/api/v1/admin/users/{admin_id}", headers=headers)

    assert disabled.status_code == 409
    assert banned.status_code == 409
    assert deleted.status_code == 409
    assert disabled.json()["detail"] == "The final active super-admin cannot be disabled"
    assert client.get("/api/v1/admin/summary", headers=headers).status_code == 200


def test_super_admin_change_is_allowed_when_another_active_super_admin_remains(client):
    second_admin, _ = create_admin_headers(client, "second-super@example.com", "super_admin")

    response = client.patch(
        f"/api/v1/admin/users/{second_admin['id']}",
        json={"is_active": False},
        headers=admin_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_privileged_changes_create_durable_audit_entries(client):
    user = client.post("/api/v1/auth/register", json={
        "email": "audited-user@example.com",
        "full_name": "Audited User",
        "password": "password123",
    }).json()

    response = client.patch(
        f"/api/v1/admin/users/{user['id']}",
        json={"is_verified": True},
        headers=admin_headers(client),
    )
    assert response.status_code == 200

    db = TestingSessionLocal()
    try:
        audit = db.query(AdminAuditLog).filter(
            AdminAuditLog.action == "update_user_security",
            AdminAuditLog.target_user_id == user["id"],
        ).one()
        assert audit.actor_user_id != user["id"]
        assert audit.resource_type == "user"
        assert audit.resource_id == str(user["id"])
        assert audit.details == {"fields": ["is_verified"]}
    finally:
        db.close()


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
    assert any(job["title"] == "Featured Frontend Engineer" for job in jobs.json()["items"])


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
