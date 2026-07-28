from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from models.refresh_token import RefreshToken
from models.user import User
from tests.conftest import TestingSessionLocal
from tasks.token_cleanup_task import cleanup_refresh_tokens
from app.config import settings


def test_cleanup_removes_expired_and_revoked_tokens(client, registered_user):
    login = client.post("/api/v1/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    active_token = login.cookies.get(settings.REFRESH_COOKIE_NAME)

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == registered_user["email"]).one()
        db.add_all([
            RefreshToken(
                token="expired-token",
                user_id=user.id,
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            ),
            RefreshToken(
                token="revoked-token",
                user_id=user.id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
                is_revoked=True,
            ),
        ])
        db.commit()
    finally:
        db.close()

    with patch("tasks.token_cleanup_task.SessionLocal", TestingSessionLocal):
        assert cleanup_refresh_tokens() == 2

    db = TestingSessionLocal()
    try:
        assert db.query(RefreshToken).filter(
            RefreshToken.token == active_token,
        ).one()
        assert db.query(RefreshToken).count() == 1
    finally:
        db.close()
