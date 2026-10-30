"""Coordination metrics for a group: who contributes what, task health, a 0-100 score and warnings.

Contribution points per member = tasks they completed (as assignee) + files they uploaded + notes they wrote,
each counted once. Share % = a member's points / the group's points.

Score = weighted average of the components that have data (weights renormalised when one is missing):
  workload balance 30%  normalised entropy of the contribution shares (1 member holding it all -> 0)
  on-time work     30%  done-on-or-before-due / (done + overdue) among tasks that have a due date
  regular activity 20%  distinct active days in the last 7, where 4 days or more is full marks
  milestones       20%  submitted-or-reviewed / milestones that are due or already submitted
A group with no tasks, files, notes or milestones yet has no score (None) instead of a misleading 0.
"""
import math
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ActivityLog, FileRecord, Group, GroupHealth, MilestoneStatus, Milestone, Note, Task, TaskStatus, User,
)
from app.services.progress import INACTIVE_AFTER, group_stats
from app.services.timeutil import as_utc, utcnow

WEIGHTS = {"workload_balance": 0.30, "on_time": 0.30, "activity": 0.20, "milestones": 0.20}
DOMINANCE_PERCENT = 70
MIN_POINTS_FOR_SHARE_WARNINGS = 4  # don't call a 2-task group "unbalanced"
NEEDS_ATTENTION_BELOW = 50

STATUS_ORDER = {"needs_attention": 0, "inactive": 1, "on_track": 2}


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def compute_coordination(db: Session, group: Group, now: datetime | None = None) -> dict:
    now = now or utcnow()
    stats = group_stats(db, group)
    members: list[User] = [m.user for m in sorted(group.members, key=lambda m: m.id)]

    tasks = list(db.scalars(select(Task).where(Task.group_id == group.id)))
    files = dict(db.execute(
        select(FileRecord.uploader_id, func.count()).where(FileRecord.group_id == group.id).group_by(FileRecord.uploader_id)
    ).all())
    notes = dict(db.execute(
        select(Note.author_id, func.count()).where(Note.group_id == group.id).group_by(Note.author_id)
    ).all())
    last_by_user = dict(db.execute(
        select(ActivityLog.user_id, func.max(ActivityLog.created_at)).where(ActivityLog.group_id == group.id).group_by(ActivityLog.user_id)
    ).all())
    week_ago = now - timedelta(days=7)
    recent = list(db.scalars(
        select(ActivityLog.created_at).where(ActivityLog.group_id == group.id, ActivityLog.created_at >= week_ago)
    ))
    milestones = list(db.scalars(select(Milestone).where(Milestone.group_id == group.id)))

    # ---- per member
    rows = []
    for u in members:
        mine = [t for t in tasks if t.assignee_id == u.id]
        completed = sum(1 for t in mine if t.status == TaskStatus.done)
        overdue = sum(1 for t in mine if t.status != TaskStatus.done and t.due_date and as_utc(t.due_date) < now)
        f, n = files.get(u.id, 0), notes.get(u.id, 0)
        last = last_by_user.get(u.id)
        last = as_utc(last) if last else None
        baseline = last or as_utc(group.created_at)
        rows.append({
            "user": u, "tasks_assigned": len(mine), "completed_tasks": completed, "overdue_tasks": overdue,
            "files_uploaded": f, "notes_added": n, "points": completed + f + n,
            "last_active_at": last, "days_inactive": max(0, (now - baseline).days),
            "is_inactive": now - baseline > INACTIVE_AFTER,
        })
    total_points = sum(r["points"] for r in rows)
    for r in rows:
        r["share_percent"] = round(100 * r["points"] / total_points) if total_points else 0

    # ---- score components (None = not enough data)
    n_members = len(rows)
    balance = None
    if n_members > 1 and total_points > 0:
        shares = [r["points"] / total_points for r in rows if r["points"] > 0]
        entropy = -sum(p * math.log(p) for p in shares)
        balance = round(100 * entropy / math.log(n_members))

    dated = [t for t in tasks if t.due_date and (t.status == TaskStatus.done or as_utc(t.due_date) < now)]
    on_time = None
    if dated:
        ok = sum(
            1 for t in dated
            if t.status == TaskStatus.done and (t.completed_at is None or as_utc(t.completed_at) <= as_utc(t.due_date))
        )
        on_time = round(100 * ok / len(dated))

    # Setup log entries (group created, member joined...) don't count: a brand-new group has no score yet
    has_signal = bool(tasks or total_points or milestones)
    active_days = len({as_utc(ts).date() for ts in recent})
    activity = min(100, round(100 * active_days / 4)) if has_signal else None

    relevant = [m for m in milestones if m.status != MilestoneStatus.pending or (m.due_date and as_utc(m.due_date) <= now)]
    milestone_score = None
    if relevant:
        milestone_score = round(100 * sum(1 for m in relevant if m.status != MilestoneStatus.pending) / len(relevant))

    components = {"workload_balance": balance, "on_time": on_time, "activity": activity, "milestones": milestone_score}
    available = {k: v for k, v in components.items() if v is not None}
    score = round(sum(WEIGHTS[k] * v for k, v in available.items()) / sum(WEIGHTS[k] for k in available)) if available else None

    # ---- warnings
    warnings: list[dict] = []

    def warn(code: str, severity: str, message: str, member_id: int | None = None):
        warnings.append({"code": code, "severity": severity, "message": message, "member_id": member_id})

    group_baseline = as_utc(group.created_at) if stats["last_activity_at"] is None else stats["last_activity_at"]
    if stats["is_inactive"]:
        warn("group_inactive", "danger", f"No activity in {(now - group_baseline).days} days")
    if stats["overdue_tasks"]:
        warn("tasks_overdue", "danger", f"{_plural(stats['overdue_tasks'], 'task')} overdue")

    dominant = False
    if n_members > 1 and total_points >= MIN_POINTS_FOR_SHARE_WARNINGS:
        top = max(rows, key=lambda r: r["share_percent"])
        if top["share_percent"] >= DOMINANCE_PERCENT:
            dominant = True
            warn("uneven_workload", "warning", f"{top['user'].name} has done {top['share_percent']}% of the work", top["user"].id)
        for r in rows:
            if r["points"] == 0:
                warn("no_contribution", "warning", f"{r['user'].name} hasn't contributed yet", r["user"].id)
    if not stats["is_inactive"]:
        for r in rows:
            if r["is_inactive"]:
                warn("member_inactive", "warning", f"{r['user'].name} has been inactive for {r['days_inactive']} days", r["user"].id)
    for m in milestones:
        if m.status == MilestoneStatus.pending and m.due_date and as_utc(m.due_date) < now:
            warn("milestone_overdue", "warning", f"Milestone '{m.title}' is overdue")

    # ---- status
    if stats["is_inactive"]:
        status = "inactive"
    elif stats["overdue_tasks"] or dominant or (score is not None and score < NEEDS_ATTENTION_BELOW):
        status = "needs_attention"
    else:
        status = "on_track"

    return {
        "group_id": group.id,
        "score": score,
        "status": status,
        "components": components,
        "task_health": {
            "todo": stats["todo_tasks"], "in_progress": stats["in_progress_tasks"], "done": stats["done_tasks"],
            "overdue": stats["overdue_tasks"], "total": stats["total_tasks"],
        },
        "percent_done": stats["percent_done"],
        "last_activity_at": stats["last_activity_at"],
        "is_inactive": stats["is_inactive"],
        "members": rows,
        "warnings": warnings,
        "calculated_at": now,
    }


def save_health(db: Session, result: dict) -> None:
    """Upsert the group_health row. The caller commits."""
    row = db.get(GroupHealth, result["group_id"])
    if row is None:
        row = GroupHealth(group_id=result["group_id"])
        db.add(row)
    row.coordination_score = result["score"]
    row.status = result["status"]
    row.calculated_at = result["calculated_at"]


def rank_key(result: dict) -> tuple:
    """Needs attention first, then inactive, then on track; lowest score first inside each bucket."""
    score = result["score"] if result["score"] is not None else 100
    return (STATUS_ORDER[result["status"]], score)
