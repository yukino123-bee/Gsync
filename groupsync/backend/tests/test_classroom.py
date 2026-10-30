import re
from datetime import timedelta

import pytest
from sqlalchemy import update

from app.config import settings
from app.models import ActivityLog, Group
from app.services.group_code import ALPHABET, generate_code, normalize_code
from app.services.timeutil import utcnow

CODE_RE = re.compile(rf"^GS-[{ALPHABET}]{{6}}$")


@pytest.fixture()
def room(make_user):
    """Two teachers and four students, with no groups yet."""
    return dict(
        t1=make_user("tea1", "teacher"), t2=make_user("tea2", "teacher"),
        ann=make_user("ann", "student"), ben=make_user("ben", "student"),
        cy=make_user("cy", "student"), dee=make_user("dee", "student"),
    )


def new_group(student, name="Team"):
    r = student.post("/groups", json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()


# ---- Group IDs ---------------------------------------------------------------------------------


def test_code_format_has_no_confusing_characters(db_session):
    for _ in range(300):
        code = generate_code(db_session)
        assert CODE_RE.match(code)
        assert not set(code[3:]) & set("01OIL")


def test_codes_are_forgiving_on_input():
    assert normalize_code(" gs-4k7p2q ") == "GS-4K7P2Q"
    assert normalize_code("4k7p2q") == "GS-4K7P2Q"
    assert normalize_code("gs 4k7p2q") == "GS-4K7P2Q"


def test_student_creates_group_and_becomes_member(room):
    g = new_group(room["ann"], "Ocean")
    assert CODE_RE.match(g["group_code"])
    assert g["status"] == "active" and g["join_enabled"] is True and g["project"] is None and g["teacher"] is None
    assert [m["id"] for m in g["members"]] == [room["ann"].id]
    assert [a["action_type"] for a in room["ann"].get(f"/groups/{g['id']}/activity").json()] == ["group_created"]


def test_teachers_cannot_create_groups_this_way(room):
    assert room["t1"].post("/groups", json={"name": "x"}).status_code == 403


def test_join_by_code(room):
    g = new_group(room["ann"])
    r = room["ben"].post("/groups/join", json={"group_code": g["group_code"].lower()})
    assert r.status_code == 200
    assert {m["id"] for m in r.json()["members"]} == {room["ann"].id, room["ben"].id}
    assert room["ben"].get("/groups/my").json()[0]["id"] == g["id"]


def test_join_errors_are_clear(room):
    g = new_group(room["ann"])
    bad = room["ben"].post("/groups/join", json={"group_code": "nonsense"})
    assert bad.status_code == 404 and "Group ID" in bad.json()["detail"]
    unknown = room["ben"].post("/groups/join", json={"group_code": "GS-ZZZZZZ"})
    assert unknown.status_code == 404
    again = room["ann"].post("/groups/join", json={"group_code": g["group_code"]})
    assert again.status_code == 409 and "already in" in again.json()["detail"]
    assert room["t1"].post("/groups/join", json={"group_code": g["group_code"]}).status_code == 403


def test_group_full_blocks_join(room, monkeypatch):
    monkeypatch.setattr(settings, "group_max_members", 2)
    g = new_group(room["ann"])
    assert room["ben"].post("/groups/join", json={"group_code": g["group_code"]}).status_code == 200
    full = room["cy"].post("/groups/join", json={"group_code": g["group_code"]})
    assert full.status_code == 409 and "full" in full.json()["detail"]


def test_disable_regenerate_enable_code(room):
    g = new_group(room["ann"])
    old = g["group_code"]
    assert room["ann"].patch(f"/groups/{g['id']}/code", json={"action": "disable"}).json()["join_enabled"] is False
    blocked = room["ben"].post("/groups/join", json={"group_code": old})
    assert blocked.status_code == 403 and "turned off" in blocked.json()["detail"]

    assert room["ann"].patch(f"/groups/{g['id']}/code", json={"action": "enable"}).json()["join_enabled"] is True
    new = room["ann"].patch(f"/groups/{g['id']}/code", json={"action": "regenerate"}).json()["group_code"]
    assert new != old and CODE_RE.match(new)
    assert room["ben"].post("/groups/join", json={"group_code": old}).status_code == 404  # old ID is dead
    assert room["ben"].post("/groups/join", json={"group_code": new}).status_code == 200


def test_only_creator_or_linked_teacher_can_change_code(room):
    g = new_group(room["ann"])
    room["ben"].post("/groups/join", json={"group_code": g["group_code"]})
    assert room["ben"].patch(f"/groups/{g['id']}/code", json={"action": "disable"}).status_code == 403  # member, not creator
    assert room["cy"].patch(f"/groups/{g['id']}/code", json={"action": "disable"}).status_code == 403
    assert room["t1"].patch(f"/groups/{g['id']}/code", json={"action": "disable"}).status_code == 403  # not linked yet
    room["t1"].post("/teacher/groups", json={"group_code": g["group_code"]})
    assert room["t1"].patch(f"/groups/{g['id']}/code", json={"action": "disable"}).status_code == 200


# ---- teacher adds groups -------------------------------------------------------------------------


def test_lookup_previews_then_add(room):
    g = new_group(room["ann"], "Ocean")
    room["ben"].post("/groups/join", json={"group_code": g["group_code"]})
    p = room["t1"].get(f"/groups/lookup/{g['group_code']}").json()
    assert p["name"] == "Ocean" and p["member_count"] == 2 and p["can_add"] is True and p["already_added"] is False
    assert {m["name"] for m in p["members"]} == {"ann", "ben"}

    card = room["t1"].post("/teacher/groups", json={"group_code": g["group_code"]})
    assert card.status_code == 201
    assert card.json()["name"] == "Ocean" and card.json()["member_count"] == 2 and card.json()["health"] in {"on_track", "needs_attention", "inactive"}
    assert [c["group_id"] for c in room["t1"].get("/teacher/groups").json()] == [g["id"]]
    assert room["t1"].get(f"/groups/lookup/{g['group_code']}").json()["blocked_reason"].endswith("already on your dashboard.")


def test_lookup_invalid_id_is_404_and_students_cannot_use_it(room):
    assert room["t1"].get("/groups/lookup/GS-ZZZZZZ").status_code == 404
    g = new_group(room["ann"])
    assert room["ann"].get(f"/groups/lookup/{g['group_code']}").status_code == 403


def test_add_twice_and_other_teacher(room):
    g = new_group(room["ann"])
    body = {"group_code": g["group_code"]}
    assert room["t1"].post("/teacher/groups", json=body).status_code == 201
    again = room["t1"].post("/teacher/groups", json=body)
    assert again.status_code == 409 and "already on your dashboard" in again.json()["detail"]
    other = room["t2"].post("/teacher/groups", json=body)
    assert other.status_code == 409 and "another teacher" in other.json()["detail"]
    assert room["t2"].get(f"/groups/lookup/{g['group_code']}").json()["can_add"] is False
    assert room["ann"].get(f"/groups/{g['id']}").json()["teacher"]["id"] == room["t1"].id


def test_archived_and_disabled_groups_cannot_be_added(room):
    g = new_group(room["ann"])
    room["ann"].patch(f"/groups/{g['id']}/code", json={"action": "disable"})
    r = room["t1"].post("/teacher/groups", json={"group_code": g["group_code"]})
    assert r.status_code == 403 and "disabled" in r.json()["detail"]
    room["ann"].patch(f"/groups/{g['id']}/code", json={"action": "enable"})
    room["t1"].post("/teacher/groups", json={"group_code": g["group_code"]})
    room["t1"].patch(f"/teacher/groups/{g['id']}", json={"archived": True})
    room["t1"].delete(f"/teacher/groups/{g['id']}")
    r = room["t2"].post("/teacher/groups", json={"group_code": g["group_code"]})
    assert r.status_code == 403 and "archived" in r.json()["detail"]


def test_remove_from_dashboard_keeps_the_group_and_can_be_readded_by_anyone(room):
    g = new_group(room["ann"])
    room["t1"].post("/teacher/groups", json={"group_code": g["group_code"]})
    room["ann"].post(f"/groups/{g['id']}/tasks", json={"title": "Keep me"})
    assert room["t1"].delete(f"/teacher/groups/{g['id']}").status_code == 204
    assert room["t1"].get("/teacher/groups").json() == []
    assert room["t1"].get(f"/groups/{g['id']}").status_code == 403  # access follows the link
    assert len(room["ann"].get(f"/groups/{g['id']}/tasks").json()) == 1
    assert room["t2"].post("/teacher/groups", json={"group_code": g["group_code"]}).status_code == 201


def test_rename_and_archive(room):
    g = new_group(room["ann"], "Old name")
    room["t1"].post("/teacher/groups", json={"group_code": g["group_code"]})
    r = room["t1"].patch(f"/teacher/groups/{g['id']}", json={"name": "  New name "})
    assert r.json()["name"] == "New name"
    assert room["ann"].get(f"/groups/{g['id']}").json()["name"] == "New name"

    room["t1"].patch(f"/teacher/groups/{g['id']}", json={"archived": True})
    assert room["t1"].get("/teacher/groups").json() == []  # hidden by default
    assert len(room["t1"].get("/teacher/groups?include_archived=true").json()) == 1
    assert room["ann"].post(f"/groups/{g['id']}/tasks", json={"title": "x"}).status_code == 403  # read-only
    assert room["ann"].get(f"/groups/{g['id']}/tasks").status_code == 200
    room["t1"].patch(f"/teacher/groups/{g['id']}", json={"archived": False})
    assert room["ann"].post(f"/groups/{g['id']}/tasks", json={"title": "x"}).status_code == 201


def test_other_teacher_cannot_manage_a_group(room):
    g = new_group(room["ann"])
    room["t1"].post("/teacher/groups", json={"group_code": g["group_code"]})
    assert room["t2"].patch(f"/teacher/groups/{g['id']}", json={"name": "hijack"}).status_code == 403
    assert room["t2"].delete(f"/teacher/groups/{g['id']}").status_code == 403
    assert room["t2"].get(f"/groups/{g['id']}/coordination").status_code == 403
    assert room["ann"].get("/teacher/groups").status_code == 403


def test_students_only_see_their_own_groups(room):
    g = new_group(room["ann"])
    assert room["ben"].get(f"/groups/{g['id']}").status_code == 403
    assert room["ben"].get(f"/groups/{g['id']}/coordination").status_code == 403
    assert room["ben"].get("/groups/my").json() == []


def test_attach_project_and_deleting_project_keeps_group(room):
    g = new_group(room["ann"])
    room["t1"].post("/teacher/groups", json={"group_code": g["group_code"]})
    pid = room["t1"].post("/projects", json={"title": "Climate"}).json()["id"]
    assert room["t2"].put(f"/teacher/groups/{g['id']}/project", json={"project_id": pid}).status_code == 403
    r = room["t1"].put(f"/teacher/groups/{g['id']}/project", json={"project_id": pid})
    assert r.json()["project_title"] == "Climate"
    assert room["ann"].get(f"/groups/{g['id']}").json()["project"]["title"] == "Climate"
    assert room["t1"].delete(f"/projects/{pid}").status_code == 204
    after = room["ann"].get(f"/groups/{g['id']}")
    assert after.status_code == 200 and after.json()["project"] is None


def test_legacy_project_groups_get_codes_and_appear_on_dashboard(room):
    pid = room["t1"].post("/projects", json={"title": "P"}).json()["id"]
    g = room["t1"].post(f"/projects/{pid}/groups", json={"name": "G", "member_ids": [room["ann"].id]}).json()
    assert CODE_RE.match(g["group_code"])
    assert [c["group_id"] for c in room["t1"].get("/teacher/groups").json()] == [g["id"]]
    # students who joined by code are managed by code, not by the project owner
    sg = new_group(room["ben"])
    room["t1"].post("/teacher/groups", json={"group_code": sg["group_code"]})
    assert room["t1"].post(f"/groups/{sg['id']}/members", json={"user_id": room["cy"].id}).status_code == 403


# ---- coordination ------------------------------------------------------------------------------


def finish_task(actor, group_id, title, assignee_id):
    t = actor.post(f"/groups/{group_id}/tasks", json={"title": title, "assignee_id": assignee_id}).json()
    assert actor.patch(f"/tasks/{t['id']}/status", json={"status": "done"}).status_code == 200


def coordination(actor, gid):
    r = actor.get(f"/groups/{gid}/coordination")
    assert r.status_code == 200, r.text
    return r.json()


def test_new_group_has_no_score_and_is_on_track(room):
    g = new_group(room["ann"])
    room["ben"].post("/groups/join", json={"group_code": g["group_code"]})
    c = coordination(room["ann"], g["id"])
    assert c["score"] is None and c["status"] == "on_track" and c["warnings"] == []
    assert c["task_health"] == {"todo": 0, "in_progress": 0, "done": 0, "overdue": 0, "total": 0}


def test_one_member_doing_everything_is_flagged(room):
    g = new_group(room["ann"])
    room["ben"].post("/groups/join", json={"group_code": g["group_code"]})
    room["t1"].post("/teacher/groups", json={"group_code": g["group_code"]})
    for i in range(5):
        finish_task(room["ann"], g["id"], f"t{i}", room["ann"].id)
    c = coordination(room["t1"], g["id"])
    shares = {m["user"]["name"]: m["share_percent"] for m in c["members"]}
    assert shares == {"ann": 100, "ben": 0}
    assert c["status"] == "needs_attention"
    messages = [w["message"] for w in c["warnings"]]
    assert "ann has done 100% of the work" in messages and "ben hasn't contributed yet" in messages
    assert c["components"]["workload_balance"] == 0
    assert c["task_health"]["done"] == 5


def test_even_work_scores_well(room):
    g = new_group(room["ann"])
    room["ben"].post("/groups/join", json={"group_code": g["group_code"]})
    for i in range(3):
        finish_task(room["ann"], g["id"], f"a{i}", room["ann"].id)
        finish_task(room["ben"], g["id"], f"b{i}", room["ben"].id)
    c = coordination(room["ann"], g["id"])
    assert [m["share_percent"] for m in c["members"]] == [50, 50]
    assert c["components"]["workload_balance"] == 100
    assert c["score"] >= 70 and c["status"] == "on_track" and c["warnings"] == []


def test_files_and_notes_count_toward_contribution(room):
    g = new_group(room["ann"])
    room["ben"].post("/groups/join", json={"group_code": g["group_code"]})
    room["ann"].post(f"/groups/{g['id']}/notes", json={"content": "n1"})
    room["ben"].post(f"/groups/{g['id']}/notes", json={"content": "n2"})
    room["ben"].post(f"/groups/{g['id']}/notes", json={"content": "n3"})
    members = {m["user"]["name"]: m for m in coordination(room["ann"], g["id"])["members"]}
    assert members["ben"]["notes_added"] == 2 and members["ben"]["share_percent"] == 67
    assert members["ann"]["notes_added"] == 1 and members["ann"]["share_percent"] == 33


def test_overdue_tasks_and_inactivity_warnings(room, db_session):
    g = new_group(room["ann"])
    room["t1"].post("/teacher/groups", json={"group_code": g["group_code"]})
    past = (utcnow() - timedelta(days=1)).isoformat()
    room["ann"].post(f"/groups/{g['id']}/tasks", json={"title": "late", "assignee_id": room["ann"].id, "due_date": past})
    c = coordination(room["t1"], g["id"])
    assert "1 task overdue" in [w["message"] for w in c["warnings"]] and c["status"] == "needs_attention"

    old = utcnow() - timedelta(days=5)
    db_session.execute(update(ActivityLog).values(created_at=old))
    db_session.execute(update(Group).values(created_at=old))
    db_session.commit()
    c = coordination(room["t1"], g["id"])
    assert c["status"] == "inactive" and c["is_inactive"] is True
    assert any(w["message"].startswith("No activity in 5 days") for w in c["warnings"])
    assert c["members"][0]["is_inactive"] is True


# ---- overview ----------------------------------------------------------------------------------


def test_overview_ranks_needs_attention_first_and_filters(room, db_session):
    good, bad, stale = new_group(room["ann"], "Good"), new_group(room["ben"], "Bad"), new_group(room["cy"], "Stale")
    for g in (good, bad, stale):
        room["t1"].post("/teacher/groups", json={"group_code": g["group_code"]})
    room["dee"].post("/groups/join", json={"group_code": good["group_code"]})
    room["dee"].post("/groups/join", json={"group_code": bad["group_code"]})
    for i in range(2):
        finish_task(room["ann"], good["id"], f"a{i}", room["ann"].id)
        finish_task(room["dee"], good["id"], f"d{i}", room["dee"].id)
    for i in range(5):
        finish_task(room["ben"], bad["id"], f"b{i}", room["ben"].id)
    old = utcnow() - timedelta(days=6)
    db_session.execute(update(ActivityLog).where(ActivityLog.group_id == stale["id"]).values(created_at=old))
    db_session.execute(update(Group).where(Group.id == stale["id"]).values(created_at=old))
    db_session.commit()

    o = room["t1"].get("/teacher/overview").json()
    assert [g["name"] for g in o["groups"]] == ["Bad", "Stale", "Good"]
    assert [g["health"] for g in o["groups"]] == ["needs_attention", "inactive", "on_track"]
    assert o["counts"] == {"total": 3, "needs_attention": 1, "inactive": 1, "on_track": 1}
    assert o["groups"][0]["top_warning"]

    only = room["t1"].get("/teacher/overview?status=inactive").json()
    assert [g["name"] for g in only["groups"]] == ["Stale"] and only["counts"]["total"] == 3
    assert room["t1"].get("/teacher/overview?status=bogus").status_code == 422
    assert room["t2"].get("/teacher/overview").json()["groups"] == []


def test_hourly_job_stores_group_health(room, db_session):
    from app.jobs.deadline_checker import run_deadline_checks
    from app.models import GroupHealth

    g = new_group(room["ann"])
    finish_task(room["ann"], g["id"], "t", room["ann"].id)
    run_deadline_checks(db_session)
    row = db_session.get(GroupHealth, g["id"])
    assert row is not None and row.status in {"on_track", "needs_attention", "inactive"} and row.calculated_at
