from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def task(world):
    r = world["alice"].post(f"/groups/{world['ga']['id']}/tasks", json={"title": "Write intro", "assignee_id": world["bob"].id})
    assert r.status_code == 201
    return r.json()


def actions(world):
    rows = world["alice"].get(f"/groups/{world['ga']['id']}/activity").json()
    return [a["action_type"] for a in rows]


def test_new_task_defaults_and_is_logged(world, task):
    assert task["status"] == "todo" and task["completed_at"] is None and task["created_by"] == world["alice"].id
    assert actions(world) == ["task_created"]


def test_status_change_to_done_sets_completed_at_and_logs(world, task):
    r = world["bob"].patch(f"/tasks/{task['id']}/status", json={"status": "done"})
    assert r.status_code == 200
    assert r.json()["status"] == "done" and r.json()["completed_at"] is not None
    assert actions(world)[0] == "task_completed"


def test_moving_out_of_done_clears_completed_at(world, task):
    bob = world["bob"]
    bob.patch(f"/tasks/{task['id']}/status", json={"status": "done"})
    r = bob.patch(f"/tasks/{task['id']}/status", json={"status": "in_progress"})
    assert r.json()["status"] == "in_progress" and r.json()["completed_at"] is None
    assert actions(world)[0] == "task_status_changed"


def test_same_status_is_a_no_op(world, task):
    world["bob"].patch(f"/tasks/{task['id']}/status", json={"status": "todo"})
    assert actions(world) == ["task_created"]


def test_invalid_status_rejected(world, task):
    r = world["bob"].patch(f"/tasks/{task['id']}/status", json={"status": "finished"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


def test_non_member_cannot_change_status(world, task):
    assert world["cara"].patch(f"/tasks/{task['id']}/status", json={"status": "done"}).status_code == 403
    assert world["teacher"].patch(f"/tasks/{task['id']}/status", json={"status": "done"}).status_code == 403
    assert world["alice"].get(f"/groups/{world['ga']['id']}/tasks").json()[0]["status"] == "todo"


def test_missing_task_is_404(world):
    assert world["alice"].patch("/tasks/9999/status", json={"status": "done"}).status_code == 404


def test_assignee_must_be_group_member(world):
    gid = world["ga"]["id"]
    assert world["alice"].post(f"/groups/{gid}/tasks", json={"title": "x", "assignee_id": world["cara"].id}).status_code == 400


def test_update_is_partial_and_can_unassign(world, task):
    alice = world["alice"]
    due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    r = alice.put(f"/tasks/{task['id']}", json={"due_date": due, "assignee_id": None})
    body = r.json()
    assert body["title"] == "Write intro" and body["assignee_id"] is None and body["due_date"].endswith("Z")
    assert alice.put(f"/tasks/{task['id']}", json={"title": "New"}).json()["due_date"] is not None  # untouched


def test_delete_task(world, task):
    assert world["bob"].delete(f"/tasks/{task['id']}").status_code == 204
    assert world["alice"].get(f"/groups/{world['ga']['id']}/tasks").json() == []
    assert actions(world)[0] == "task_deleted"


def test_dashboard_progress_and_overdue(world):
    alice, gid = world["alice"], world["ga"]["id"]
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    t1 = alice.post(f"/groups/{gid}/tasks", json={"title": "a", "due_date": past}).json()
    alice.post(f"/groups/{gid}/tasks", json={"title": "b"})
    d = alice.get(f"/groups/{gid}/dashboard").json()
    assert (d["total_tasks"], d["percent_done"], d["overdue_tasks"]) == (2, 0, 1)
    alice.patch(f"/tasks/{t1['id']}/status", json={"status": "done"})
    d = alice.get(f"/groups/{gid}/dashboard").json()
    assert (d["percent_done"], d["overdue_tasks"]) == (50, 0)
    card = world["teacher"].get(f"/projects/{world['project']['id']}/dashboard").json()["groups"][0]
    assert card["percent_done"] == 50 and card["member_count"] == 2
