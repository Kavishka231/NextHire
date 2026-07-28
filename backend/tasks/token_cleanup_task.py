from datetime import datetime, timezone

from sqlalchemy import or_

from app.database import SessionLocal
from models.refresh_token import RefreshToken
from tasks.celery_app import celery_app


@celery_app.task(name="tasks.token_cleanup_task.cleanup_refresh_tokens")
def cleanup_refresh_tokens() -> int:
    """Delete refresh tokens that can no longer be used."""
    db = SessionLocal()
    try:
        deleted = (
            db.query(RefreshToken)
            .filter(
                or_(
                    RefreshToken.is_revoked.is_(True),
                    RefreshToken.expires_at <= datetime.now(timezone.utc),
                )
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
