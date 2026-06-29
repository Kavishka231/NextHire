from sqlalchemy.orm import Session

from models.notification import Notification
from models.user import User


def create_notification(db: Session, user_id: int, title: str, message: str, kind: str = "info") -> Notification:
    notification = Notification(user_id=user_id, title=title, message=message, kind=kind)
    db.add(notification)
    return notification


def notify_admins(db: Session, title: str, message: str, kind: str = "admin") -> None:
    admins = db.query(User).filter(User.is_admin.is_(True), User.is_active.is_(True)).all()
    for admin in admins:
        create_notification(db, admin.id, title, message, kind)
