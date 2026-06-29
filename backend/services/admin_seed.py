from sqlalchemy.orm import Session

from app.config import settings
from core.security import hash_password
from models.user import User


def ensure_default_admin(db: Session) -> None:
    admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
    if admin:
        changed = False
        if not admin.is_admin:
            admin.is_admin = True
            changed = True
        if admin.admin_role != "super_admin":
            admin.admin_role = "super_admin"
            changed = True
        if not admin.is_verified:
            admin.is_verified = True
            changed = True
        if changed:
            db.commit()
        return

    db.add(User(
        full_name=settings.ADMIN_FULL_NAME,
        email=settings.ADMIN_EMAIL,
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        is_active=True,
        is_verified=True,
        is_admin=True,
        admin_role="super_admin",
    ))
    db.commit()
