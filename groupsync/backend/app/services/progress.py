from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ActivityLog, Group, Milestone, MilestoneStatus, Task, TaskStatus
from app.services.timeutil import as_utc, utcnow

INACTIVE_AFTER = timedelta(days=3)


def next_milestone(milestones: list[Milestone]) -> Milestone | None:
    pending = [m for m in milestones if m.status == MilestoneStatus.pending]
    pending.sort(key=lambda m: (m.due_date is None, as_utc(m.due_date) if m.due_date else 0, m.id))
    return pending[0] if pending else None


def final_milestone(milestones: list[Milestone]) -> Milestone | None:
    """The final milestone is the one due last (undated ones count as earliest; ties go to the newest)."""
    if not milestones:
        return None
    floor = datetime.min.replace(tzinfo=timezone.utc)
    return max(milestones, key=lambda m: (as_utc(m.due_date) if m.due_date else floor, m.id))


def group_stats(db: Session, group: Group) -> dict:
    now = utcnow()
    counts = dict(
        db.execute(
            select(Task.status, func.count()).where(Task.group_id == group.id).group_by(Task.status)
        ).all()
    )
    total = sum(counts.values())
    done = counts.get(TaskStatus.done, 0)
    overdue = db.scalar(
        select(func.count()).where(
            Task.group_id == group.id, Task.status != TaskStatus.done, Task.due_date < now
        )
    )
    milestones = list(db.scalars(select(Milestone).where(Milestone.group_id == group.id)))
    last_activity = db.scalar(select(func.max(ActivityLog.created_at)).where(ActivityLog.group_id == group.id))
    last_activity = as_utc(last_activity) if last_activity else None
    baseline = last_activity or as_utc(group.created_at)
    return {
        "total_tasks": total,
        "todo_tasks": counts.get(TaskStatus.todo, 0),
        "in_progress_tasks": counts.get(TaskStatus.in_progress, 0),
        "done_tasks": done,
        "percent_done": round(100 * done / total) if total else 0,
        "overdue_tasks": overdue or 0,
        "next_milestone": next_milestone(milestones),
        "last_activity_at": last_activity,
        "is_inactive": now - baseline > INACTIVE_AFTER,
    }
