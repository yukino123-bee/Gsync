from sqlalchemy.orm import Session

from app.models import ActivityLog


def log_activity(
    db: Session,
    group_id: int,
    user_id: int,
    action_type: str,
    description: str,
    reference_id: int | None = None,
) -> None:
    """Add a contribution-log row. The caller commits, so it is atomic with the change itself."""
    db.add(
        ActivityLog(
            group_id=group_id,
            user_id=user_id,
            action_type=action_type,
            description=description[:500],
            reference_id=reference_id,
        )
    )
