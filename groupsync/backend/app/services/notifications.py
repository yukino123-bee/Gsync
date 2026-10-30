from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification
from app.services.timeutil import utcnow


def notify(
    db: Session,
    user_id: int,
    title: str,
    body: str,
    type_: str,
    group_id: int | None = None,
    reference_id: int | None = None,
) -> Notification | None:
    """Create a notification unless the same (user, type, reference) was already sent today (UTC)."""
    start_of_day = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(Notification.id).where(
        Notification.user_id == user_id,
        Notification.type == type_,
        Notification.reference_id == reference_id,
        Notification.created_at >= start_of_day,
    )
    if db.scalar(stmt) is not None:
        return None
    n = Notification(
        user_id=user_id, title=title, body=body[:500], type=type_, group_id=group_id, reference_id=reference_id
    )
    db.add(n)
    db.flush()
    return n
