from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.security import decode_token
from models.user import User
from app.database import get_db
from app.observability import set_user_context

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db)
):
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("user_id")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")
    if user.banned_until:
        banned_until = (
            user.banned_until
            if user.banned_until.tzinfo
            else user.banned_until.replace(tzinfo=timezone.utc)
        )
        if banned_until > datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Account is temporarily banned")
    if payload.get("token_version") != user.token_version:
        raise HTTPException(status_code=401, detail="Token has been revoked")

    set_user_context(user.id)
    return user


def require_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_admin_role(*allowed_roles: str):
    def dependency(current_user: User = Depends(require_admin)):
        if current_user.admin_role == "super_admin" or current_user.admin_role in allowed_roles:
            return current_user
        raise HTTPException(status_code=403, detail="Insufficient admin permissions")
    return dependency
