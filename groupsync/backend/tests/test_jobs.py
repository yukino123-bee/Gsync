from datetime import timedelta
from unittest import mock

from app.jobs.deadline_checker import run_deadline_checks
from app.models import ActivityLog, Group, Notification, Task
from app.services.timeutil import utcnow


def run(db):
    with mock.patch("app.jobs.deadline_checker.send_push_for") as push:
        return run_deadline_checks(db), push


def types(db, user_id):
    return sorted(n.type for n in db.query(Notification).filter_by(user_id=user_id))


def test_due_soon_and_overdue_notifications(world, db_session):
    alice, bob, gid = world["alice"], world["bob"], world["ga"]["id"]
    alice.post(f"/groups/{gid}/tasks", json={"title": "soon", "assignee_id": bob.id, "due_date": (utcnow() + timedelta(hours=5)).isoformat()})
    alice.post(f"/groups/{gid}/tasks", json={"title": "late", "assignee_id": alice.id, "due_date": (utcnow() - timedelta(hours=5)).isoformat()})
    alice.post(f"/groups/{gid}/tasks", json={"title": "far", "assignee_id": bob.id, "due_date": (utcnow() + timedelta(days=5)).isoformat()})
    run(db_session)
    assert types(db_session, bob.id) == ["group_overdue", "task_due_soon"]
    assert types(db_session, alice.id) == ["group_overdue", "task_overdue"]
    assert types(db_session, world["cara"].id) == []  # other group untouched


def test_done_tasks_are_ignored(world, db_session):
    alice, gid = world["alice"], world["ga"]["id"]
    t = alice.post(f"/groups/{gid}/tasks", json={"title": "late", "assignee_id": alice.id, "due_date": (utcnow() - timedelta(hours=5)).isoformat()}).json()
    alice.patch(f"/tasks/{t['id']}/status", json={"status": "done"})
    run(db_session)
    assert db_session.query(Notification).filter(Notification.type.in_(["task_overdue", "group_overdue"])).count() == 0


def test_no_duplicates_on_the_same_day(world, db_session):
    gid, alice = world["ga"]["id"], world["alice"]
    alice.post(f"/groups/{gid}/tasks", json={"title": "late", "assignee_id": alice.id, "due_date": (utcnow() - timedelta(hours=5)).isoformat()})
    first, _ = run(db_session)
    second, _ = run(db_session)
    assert first > 0 and second == 0


def test_inactive_group_notifies_members_and_teacher(world, db_session):
    gid = world["ga"]["id"]
    alice = world["alice"]
    alice.post(f"/groups/{gid}/notes", json={"content": "hi"})
    # Everything quiet for 4 days
    db_session.query(ActivityLog).update({"created_at": utcnow() - timedelta(days=4)})
    db_session.query(Group).update({"created_at": utcnow() - timedelta(days=10)})
    db_session.commit()
    run(db_session)
    for who in (world["alice"], world["bob"], world["teacher"]):
        assert "group_inactive" in types(db_session, who.id), who.user["name"]
    assert "group_inactive" in types(db_session, world["cara"].id)  # group B never had activity
    assert types(db_session, world["other_teacher"].id) == []


def test_recently_active_group_is_not_flagged(world, db_session):
    world["alice"].post(f"/groups/{world['ga']['id']}/notes", json={"content": "hi"})
    db_session.query(Group).update({"created_at": utcnow() - timedelta(days=10)})
    db_session.commit()
    run(db_session)
    assert "group_inactive" not in types(db_session, world["alice"].id)
    assert "group_inactive" in types(db_session, world["cara"].id)


def test_push_is_attempted_for_new_notifications(world, db_session):
    gid, alice = world["ga"]["id"], world["alice"]
    alice.post(f"/groups/{gid}/tasks", json={"title": "late", "assignee_id": alice.id, "due_date": (utcnow() - timedelta(hours=1)).isoformat()})
    _, push = run(db_session)
    assert push.call_count == 1 and len(push.call_args.args[1]) > 0
