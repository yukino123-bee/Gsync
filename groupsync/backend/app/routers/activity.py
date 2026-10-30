from fastapi import APIRouter, Query
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import ActivityLog, User
from app.schemas.workspace import ActivityOut
from app.services.access import authorize_group

router = APIRouter(tags=["activity"])


@router.get("/groups/{group_id}/activity", response_model=list[ActivityOut])
def list_activity(
    group_id: int,
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    authorize_group(db, group_id, user)
    rows = db.execute(
        select(ActivityLog, User.name).join(User, User.id == ActivityLog.user_id)
        .where(ActivityLog.group_id == group_id)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(limit).offset(offset)
    ).all()
    return [
        ActivityOut(
            id=a.id, group_id=a.group_id, user_id=a.user_id, user_name=name, action_type=a.action_type,
            reference_id=a.reference_id, description=a.description, created_at=a.created_at,
        )
        for a, name in rows
    ]
