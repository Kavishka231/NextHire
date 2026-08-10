from models.admin_audit_log import AdminAuditLog
from models.user import User


def record_admin_audit(
    db,
    actor: User,
    action: str,
    resource_type: str,
    *,
    resource_id: int | str | None = None,
    target_user_id: int | None = None,
    details: dict | None = None,
) -> AdminAuditLog:
    entry = AdminAuditLog(
        actor_user_id=actor.id,
        action=action,
        target_user_id=target_user_id,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        details=details or {},
    )
    db.add(entry)
    return entry
