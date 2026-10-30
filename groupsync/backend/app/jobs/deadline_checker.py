import logging
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ActivityLog, Group, GroupMember, GroupStatus, Notification, Task, TaskStatus, TeacherGroup
from app.services.coordination import compute_coordination, save_health
from app.services.notifications import notify
from app.services.progress import INACTIVE_AFTER
from app.services.push import send_push_for
from app.services.timeutil import as_utc, utcnow

log = logging.getLogger(__name__)


def _due_soon(db: Session, now, created: list[Notification]) -> None:
    tasks = db.scalars(
        select(Task).join(Group, Group.id == Task.group_id).where(
            Group.status == GroupStatus.active,
            Task.status != TaskStatus.done,
            Task.assignee_id.is_not(None),
            Task.due_date > now,
            Task.due_date <= now + timedelta(hours=24),
        )
    )
    for t in tasks:
        n = notify(db, t.assignee_id, "Task due soon", f"'{t.title}' is due within 24 hours.", "task_due_soon", t.group_id, t.id)
        if n:
            created.append(n)


def _overdue(db: Session, now, created: list[Notification]) -> None:
    overdue_by_group: dict[int, int] = {}
    active_tasks = (
        select(Task).join(Group, Group.id == Task.group_id)
        .where(Group.status == GroupStatus.active, Task.status != TaskStatus.done, Task.due_date < now)
    )
    for t in db.scalars(active_tasks):
        overdue_by_group[t.group_id] = overdue_by_group.get(t.group_id, 0) + 1
        if t.assignee_id:
            n = notify(db, t.assignee_id, "Task overdue", f"'{t.title}' is past its due date.", "task_overdue", t.group_id, t.id)
            if n:
                created.append(n)
    # One summary per group for everyone in it
    for group_id, count in overdue_by_group.items():
        group = db.get(Group, group_id)
        member_ids = db.scalars(select(GroupMember.user_id).where(GroupMember.group_id == group_id))
        for uid in member_ids:
            n = notify(
                db, uid, "Group has overdue tasks",
                f"{group.name} has {count} overdue task{'s' if count != 1 else ''}.",
                "group_overdue", group_id, group_id,
            )
            if n:
                created.append(n)


def _inactive_groups(db: Session, now, created: list[Notification]) -> None:
    cutoff = now - INACTIVE_AFTER
    for group in db.scalars(select(Group).where(Group.status == GroupStatus.active)):
        last = db.scalar(select(func.max(ActivityLog.created_at)).where(ActivityLog.group_id == group.id))
        if as_utc(last or group.created_at) > cutoff:
            continue
        recipients = set(db.scalars(select(GroupMember.user_id).where(GroupMember.group_id == group.id)))
        teacher_id = db.scalar(select(TeacherGroup.teacher_id).where(TeacherGroup.group_id == group.id))
        if teacher_id:
            recipients.add(teacher_id)
        for uid in recipients:
            n = notify(
                db, uid, "Inactive group", f"{group.name} has had no activity for 3 days.",
                "group_inactive", group.id, group.id,
            )
            if n:
                created.append(n)


def _refresh_health(db: Session, now) -> None:
    """Store the latest coordination score and health status for every active group."""
    for group in db.scalars(select(Group).where(Group.status == GroupStatus.active)):
        save_health(db, compute_coordination(db, group, now))


def run_deadline_checks(db: Session | None = None) -> int:
    """Create due-soon / overdue / inactive notifications and push them. Returns how many were created."""
    own_session = db is None
    db = db or SessionLocal()
    try:
        now = utcnow()
        created: list[Notification] = []
        _due_soon(db, now, created)
        _overdue(db, now, created)
        _inactive_groups(db, now, created)
        _refresh_health(db, now)
        db.commit()
        send_push_for(db, created)
        log.info("Deadline check created %d notifications", len(created))
        return len(created)
    except Exception:
        db.rollback()
        log.exception("Deadline check failed")
        raise
    finally:
        if own_session:
            db.close()
