import pytest


REGISTER_URL      = "/api/v1/auth/register"
LOGIN_URL         = "/api/v1/auth/login"
REFRESH_URL       = "/api/v1/auth/refresh"
LOGOUT_URL        = "/api/v1/auth/logout"
ME_URL            = "/api/v1/auth/me"
FORGOT_URL        = "/api/v1/auth/forgot-password"
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
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


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


def test_me_unauthenticated(client):
    res = client.get(ME_URL)
    assert res.status_code == 401


# ── Refresh ───────────────────────────────────────────────────────────────────

def test_refresh_token(client, registered_user):
    login_res = client.post(LOGIN_URL, json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    refresh_token = login_res.json()["refresh_token"]

    res = client.post(REFRESH_URL, json={"refresh_token": refresh_token})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_refresh_invalid_token(client):
    res = client.post(REFRESH_URL, json={"refresh_token": "bad.token.here"})
    assert res.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

def test_logout(client, registered_user):
    login_res = client.post(LOGIN_URL, json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    refresh_token = login_res.json()["refresh_token"]

    logout_res = client.post(LOGOUT_URL, json={"refresh_token": refresh_token})
    assert logout_res.status_code == 200

    # Refresh should fail after logout
    res = client.post(REFRESH_URL, json={"refresh_token": refresh_token})
    assert res.status_code == 401


# ── Forgot password ───────────────────────────────────────────────────────────

def test_forgot_password_always_200(client):
    # Should return 200 even for unknown emails (security best practice)
    res = client.post(FORGOT_URL, json={"email": "unknown@example.com"})
    assert res.status_code == 200


# ── Change password ───────────────────────────────────────────────────────────

def test_change_password(client, registered_user, auth_headers):
    res = client.put(CHANGE_PASS_URL, json={
        "current_password": registered_user["password"],
        "new_password": "newpassword456",
    }, headers=auth_headers)
    assert res.status_code == 200

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


def test_change_password_wrong_current(client, registered_user, auth_headers):
    res = client.put(CHANGE_PASS_URL, json={
        "current_password": "wrongpassword",
        "new_password": "newpassword456",
    }, headers=auth_headers)
    assert res.status_code == 401