import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from models.password_reset_token import PasswordResetToken
from models.refresh_token import RefreshToken
from models.user import User
from app.config import settings
from core.security import create_access_token
from tests.conftest import TestingSessionLocal

REGISTER_URL      = "/api/v1/auth/register"
LOGIN_URL         = "/api/v1/auth/login"
REFRESH_URL       = "/api/v1/auth/refresh"
LOGOUT_URL        = "/api/v1/auth/logout"
ME_URL            = "/api/v1/auth/me"
FORGOT_URL        = "/api/v1/auth/forgot-password"
RESET_URL         = "/api/v1/auth/reset-password"
CHANGE_PASS_URL   = "/api/v1/auth/change-password"

VALID_USER = {
    "email": "john@example.com",
    "full_name": "John Doe",
    "password": "securepass123",
}


# ── Register ──────────────────────────────────────────────────────────────────

def test_register_success(client):
    res = client.post(REGISTER_URL, json=VALID_USER)
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == VALID_USER["email"]
    assert body["full_name"] == VALID_USER["full_name"]
    assert "hashed_password" not in body


def test_register_duplicate_email(client):
    client.post(REGISTER_URL, json=VALID_USER)
    res = client.post(REGISTER_URL, json=VALID_USER)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]


def test_register_short_password(client):
    res = client.post(REGISTER_URL, json={**VALID_USER, "password": "short"})
    assert res.status_code == 422


def test_register_invalid_email(client):
    res = client.post(REGISTER_URL, json={**VALID_USER, "email": "not-an-email"})
    assert res.status_code == 422


def test_auth_logs_business_events(client, caplog):
    with caplog.at_level(logging.INFO):
        res = client.post(REGISTER_URL, json=VALID_USER)
        assert res.status_code == 201
        failed_login = client.post(LOGIN_URL, json={
            "email": VALID_USER["email"],
            "password": "wrongpassword",
        })

    assert failed_login.status_code == 401
    assert any(
        hasattr(record, "event")
        and record.event == "user_registered"
        and record.user_id is not None
        and record.outcome == "success"
        for record in caplog.records
    )
    assert any(
        hasattr(record, "event")
        and record.event == "login_failed"
        and record.reason == "invalid_credentials"
        and record.outcome == "failure"
        for record in caplog.records
    )


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_success(client):
    client.post(REGISTER_URL, json=VALID_USER)
    res = client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "password": VALID_USER["password"],
    })
    assert res.status_code == 200
    body = res.json()
    assert "access_token"  in body
    assert "refresh_token" not in body
    assert body["token_type"] == "bearer"
    assert res.cookies.get(settings.REFRESH_COOKIE_NAME)
    assert "HttpOnly" in res.headers["set-cookie"]
    assert "SameSite=lax" in res.headers["set-cookie"]


def test_login_wrong_password(client):
    client.post(REGISTER_URL, json=VALID_USER)
    res = client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "password": "wrongpassword",
    })
    assert res.status_code == 401


def test_login_unknown_email(client):
    res = client.post(LOGIN_URL, json={
        "email": "nobody@example.com",
        "password": "whatever",
    })
    assert res.status_code == 401


# ── Me ────────────────────────────────────────────────────────────────────────

def test_me_authenticated(client, registered_user, auth_headers):
    res = client.get(ME_URL, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == registered_user["email"]


def test_token_with_old_token_version_is_rejected(client, registered_user):
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == registered_user["email"]).one()
        old_token = create_access_token({
            "user_id": user.id,
            "email": user.email,
            "token_version": user.token_version - 1,
        })
    finally:
        db.close()

    response = client.get(ME_URL, headers={"Authorization": f"Bearer {old_token}"})
    assert response.status_code == 401


def test_expired_ban_does_not_block_existing_token(client, registered_user, auth_headers):
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == registered_user["email"]).one()
        user.banned_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()

    response = client.get(ME_URL, headers=auth_headers)
    assert response.status_code == 200


def test_me_unauthenticated(client):
    res = client.get(ME_URL)
    assert res.status_code == 401


# ── Refresh ───────────────────────────────────────────────────────────────────

def test_refresh_token(client, registered_user):
    login_res = client.post(LOGIN_URL, json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    refresh_token = login_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    res = client.post(REFRESH_URL)
    assert res.status_code == 200
    assert "access_token" in res.json()
    assert "refresh_token" not in res.json()
    rotated_token = res.cookies.get(settings.REFRESH_COOKIE_NAME)
    assert rotated_token != refresh_token

    # Rotation makes the submitted token unusable.
    client.cookies.set(settings.REFRESH_COOKIE_NAME, refresh_token)
    assert client.post(REFRESH_URL).status_code == 401

    # The newly issued token can itself be rotated.
    client.cookies.set(settings.REFRESH_COOKIE_NAME, rotated_token)
    assert client.post(REFRESH_URL).status_code == 200


def test_refresh_token_has_expiry(client, registered_user):
    before_login = datetime.now(timezone.utc)
    client.post(LOGIN_URL, json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })

    db = TestingSessionLocal()
    try:
        record = db.query(RefreshToken).one()
        assert record.expires_at is not None
        assert record.expires_at.replace(tzinfo=timezone.utc) > before_login
    finally:
        db.close()


def test_expired_refresh_token_is_rejected(client, registered_user):
    login = client.post(LOGIN_URL, json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    token = login.cookies.get(settings.REFRESH_COOKIE_NAME)

    db = TestingSessionLocal()
    try:
        record = db.query(RefreshToken).filter(RefreshToken.token == token).one()
        record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()

    assert client.post(REFRESH_URL).status_code == 401


def test_refresh_invalid_token(client):
    client.cookies.set(settings.REFRESH_COOKIE_NAME, "bad.token.here")
    res = client.post(REFRESH_URL)
    assert res.status_code == 401


def test_refresh_requires_cookie(client):
    client.cookies.clear()
    assert client.post(REFRESH_URL).status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

def test_logout(client, registered_user):
    login_res = client.post(LOGIN_URL, json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    refresh_token = login_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    logout_res = client.post(LOGOUT_URL)
    assert logout_res.status_code == 200
    assert settings.REFRESH_COOKIE_NAME not in client.cookies

    # Refresh should fail after logout
    client.cookies.set(settings.REFRESH_COOKIE_NAME, refresh_token)
    res = client.post(REFRESH_URL)
    assert res.status_code == 401


# ── Forgot password ───────────────────────────────────────────────────────────

def test_forgot_password_always_200(client):
    # Should return 200 even for unknown emails (security best practice)
    res = client.post(FORGOT_URL, json={"email": "unknown@example.com"})
    assert res.status_code == 200


def test_forgot_password_unknown_email_does_not_queue_email(client):
    with patch("services.auth_service.send_password_reset_email.delay") as queue_email:
        res = client.post(FORGOT_URL, json={"email": "unknown@example.com"})
    assert res.status_code == 200
    queue_email.assert_not_called()


def test_forgot_password_does_not_expose_queue_failure(client):
    client.post(REGISTER_URL, json=VALID_USER)
    with patch(
        "services.auth_service.send_password_reset_email.delay",
        side_effect=RuntimeError("queue unavailable"),
    ):
        res = client.post(FORGOT_URL, json={"email": VALID_USER["email"]})
    assert res.status_code == 200
    assert res.json()["message"] == "If the email exists, password reset instructions were sent"


def test_reset_password_is_one_time_and_revokes_sessions(client):
    client.post(REGISTER_URL, json=VALID_USER)
    login = client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "password": VALID_USER["password"],
    })
    old_refresh_token = login.cookies.get(settings.REFRESH_COOKIE_NAME)
    old_access_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    with patch("services.auth_service.send_password_reset_email.delay") as queue_email:
        requested = client.post(FORGOT_URL, json={"email": VALID_USER["email"]})
    assert requested.status_code == 200
    reset_token = queue_email.call_args.args[1]

    reset = client.post(RESET_URL, json={
        "token": reset_token,
        "new_password": "replacement-password-456",
    })
    assert reset.status_code == 200
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == VALID_USER["email"]).one()
        assert user.token_version == 1
    finally:
        db.close()
    assert client.get(ME_URL, headers=old_access_headers).status_code == 401
    client.cookies.set(settings.REFRESH_COOKIE_NAME, old_refresh_token)
    assert client.post(REFRESH_URL).status_code == 401
    assert client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "password": VALID_USER["password"],
    }).status_code == 401
    assert client.post(LOGIN_URL, json={
        "email": VALID_USER["email"],
        "password": "replacement-password-456",
    }).status_code == 200
    assert client.post(RESET_URL, json={
        "token": reset_token,
        "new_password": "another-password-789",
    }).status_code == 400


def test_new_reset_request_invalidates_previous_token(client):
    client.post(REGISTER_URL, json=VALID_USER)
    with patch("services.auth_service.send_password_reset_email.delay") as queue_email:
        client.post(FORGOT_URL, json={"email": VALID_USER["email"]})
        first_token = queue_email.call_args.args[1]
        client.post(FORGOT_URL, json={"email": VALID_USER["email"]})
        second_token = queue_email.call_args.args[1]

    assert client.post(RESET_URL, json={
        "token": first_token,
        "new_password": "replacement-password-456",
    }).status_code == 400
    assert client.post(RESET_URL, json={
        "token": second_token,
        "new_password": "replacement-password-456",
    }).status_code == 200


def test_expired_reset_token_is_rejected(client):
    client.post(REGISTER_URL, json=VALID_USER)
    with patch("services.auth_service.send_password_reset_email.delay") as queue_email:
        client.post(FORGOT_URL, json={"email": VALID_USER["email"]})
    reset_token = queue_email.call_args.args[1]

    db = TestingSessionLocal()
    try:
        record = db.query(PasswordResetToken).one()
        record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    assert client.post(RESET_URL, json={
        "token": reset_token,
        "new_password": "replacement-password-456",
    }).status_code == 400


# ── Change password ───────────────────────────────────────────────────────────

def test_change_password(client, registered_user, auth_headers):
    login = client.post(LOGIN_URL, json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    old_refresh_token = login.cookies.get(settings.REFRESH_COOKIE_NAME)

    res = client.put(CHANGE_PASS_URL, json={
        "current_password": registered_user["password"],
        "new_password": "newpassword456",
    }, headers=auth_headers)
    assert res.status_code == 200
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == registered_user["email"]).one()
        assert user.token_version == 1
    finally:
        db.close()
    assert client.get(ME_URL, headers=auth_headers).status_code == 401
    client.cookies.set(settings.REFRESH_COOKIE_NAME, old_refresh_token)
    assert client.post(REFRESH_URL).status_code == 401

    # Old password should no longer work
    login_res = client.post(LOGIN_URL, json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    assert login_res.status_code == 401

    # New password should work
    login_res2 = client.post(LOGIN_URL, json={
        "email": registered_user["email"],
        "password": "newpassword456",
    })
    assert login_res2.status_code == 200
    new_headers = {"Authorization": f"Bearer {login_res2.json()['access_token']}"}
    assert client.get(ME_URL, headers=new_headers).status_code == 200


def test_change_password_wrong_current(client, registered_user, auth_headers):
    res = client.put(CHANGE_PASS_URL, json={
        "current_password": "wrongpassword",
        "new_password": "newpassword456",
    }, headers=auth_headers)
    assert res.status_code == 401
