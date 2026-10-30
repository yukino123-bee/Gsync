import pytest

PDF = ("a.pdf", b"%PDF-1.4 test", "application/pdf")


def test_students_cannot_use_teacher_endpoints(world):
    alice, pid, gid = world["alice"], world["project"]["id"], world["ga"]["id"]
    assert alice.post("/projects", json={"title": "x"}).status_code == 403
    assert alice.get("/projects").status_code == 403
    assert alice.get(f"/projects/{pid}/dashboard").status_code == 403
    assert alice.post(f"/projects/{pid}/groups", json={"name": "x"}).status_code == 403
    assert alice.post(f"/projects/{pid}/groups/randomize", json={"group_size": 2}).status_code == 403
    assert alice.post(f"/groups/{gid}/members", json={"user_id": world["dave"].id}).status_code == 403
    assert alice.get("/users/students").status_code == 403
    assert alice.get("/admin/users").status_code == 403


def test_non_members_get_403_on_every_group_endpoint(world):
    gid = world["ga"]["id"]
    cara = world["cara"]  # student in a different group
    for url in ("tasks", "milestones", "files", "notes", "activity", "dashboard"):
        assert cara.get(f"/groups/{gid}/{url}").status_code == 403, url
    assert cara.get(f"/groups/{gid}").status_code == 403
    assert cara.post(f"/groups/{gid}/tasks", json={"title": "x"}).status_code == 403
    assert cara.post(f"/groups/{gid}/notes", json={"content": "x"}).status_code == 403
    assert cara.post(f"/groups/{gid}/files", files={"file": PDF}).status_code == 403
    assert world["dave"].get(f"/groups/{gid}/tasks").status_code == 403  # in no group at all


def test_other_teacher_cannot_access_project_or_groups(world):
    t2, pid, gid = world["other_teacher"], world["project"]["id"], world["ga"]["id"]
    assert t2.get(f"/projects/{pid}").status_code == 403
    assert t2.put(f"/projects/{pid}", json={"title": "hijack"}).status_code == 403
    assert t2.delete(f"/projects/{pid}").status_code == 403
    assert t2.get(f"/groups/{gid}/tasks").status_code == 403
    assert t2.get(f"/groups/{gid}/evaluations/summary").status_code == 403
    assert t2.post(f"/groups/{gid}/members", json={"user_id": world["dave"].id}).status_code == 403


def test_owning_teacher_has_read_only_access(world):
    teacher, alice, gid = world["teacher"], world["alice"], world["ga"]["id"]
    alice.post(f"/groups/{gid}/tasks", json={"title": "t"})
    assert len(teacher.get(f"/groups/{gid}/tasks").json()) == 1
    assert teacher.post(f"/groups/{gid}/tasks", json={"title": "x"}).status_code == 403
    assert teacher.post(f"/groups/{gid}/notes", json={"content": "x"}).status_code == 403
    assert teacher.post(f"/groups/{gid}/files", files={"file": PDF}).status_code == 403
    task_id = teacher.get(f"/groups/{gid}/tasks").json()[0]["id"]
    assert teacher.patch(f"/tasks/{task_id}/status", json={"status": "done"}).status_code == 403


def test_groups_my_only_lists_own_groups(world):
    assert [g["id"] for g in world["alice"].get("/groups/my").json()] == [world["ga"]["id"]]
    assert [g["id"] for g in world["cara"].get("/groups/my").json()] == [world["gb"]["id"]]
    assert world["dave"].get("/groups/my").json() == []


def test_only_teacher_comments_and_members_can_read_them(world):
    teacher, alice, cara, gid = world["teacher"], world["alice"], world["cara"], world["ga"]["id"]
    m = alice.post(f"/groups/{gid}/milestones", json={"title": "Draft"}).json()
    assert alice.post(f"/milestones/{m['id']}/comments", json={"content": "hi"}).status_code == 403
    assert world["other_teacher"].post(f"/milestones/{m['id']}/comments", json={"content": "hi"}).status_code == 403
    assert teacher.post(f"/milestones/{m['id']}/comments", json={"content": "Good start"}).status_code == 201
    assert alice.get(f"/milestones/{m['id']}/comments").json()[0]["content"] == "Good start"
    assert cara.get(f"/milestones/{m['id']}/comments").status_code == 403


def test_peer_evaluations_are_teacher_only(world):
    teacher, alice, bob, gid = world["teacher"], world["alice"], world["bob"], world["ga"]["id"]
    m = alice.post(f"/groups/{gid}/milestones", json={"title": "Final"}).json()
    alice.put(f"/milestones/{m['id']}", json={"status": "submitted"})

    assert alice.post(f"/groups/{gid}/evaluations", json={"evaluations": [{"evaluatee_id": bob.id, "rating": 5, "comment": "secret"}]}).status_code == 201
    # Neither the evaluator, the evaluatee, nor an outsider can read ratings
    for who in (alice, bob, world["cara"]):
        assert who.get(f"/groups/{gid}/evaluations/summary").status_code == 403
    assert "secret" not in bob.get(f"/groups/{gid}/evaluations/status").text
    summary = teacher.get(f"/groups/{gid}/evaluations/summary").json()
    bob_row = next(m for m in summary["members"] if m["user"]["id"] == bob.id)
    assert bob_row["average_rating"] == 5 and bob_row["ratings"][0]["comment"] == "secret"


def test_evaluation_rules(world):
    alice, bob, gid = world["alice"], world["bob"], world["ga"]["id"]
    body = {"evaluations": [{"evaluatee_id": bob.id, "rating": 4}]}
    assert alice.post(f"/groups/{gid}/evaluations", json=body).status_code == 409  # no final milestone yet
    m = alice.post(f"/groups/{gid}/milestones", json={"title": "Final"}).json()
    alice.put(f"/milestones/{m['id']}", json={"status": "submitted"})
    assert alice.post(f"/groups/{gid}/evaluations", json={"evaluations": [{"evaluatee_id": alice.id, "rating": 5}]}).status_code == 400
    assert alice.post(f"/groups/{gid}/evaluations", json={"evaluations": [{"evaluatee_id": bob.id, "rating": 6}]}).status_code == 422
    assert alice.post(f"/groups/{gid}/evaluations", json=body).status_code == 201
    assert alice.post(f"/groups/{gid}/evaluations", json=body).status_code == 409


def test_notifications_are_private(world, db_session):
    from app.models import Notification

    db_session.add(Notification(user_id=world["alice"].id, title="t", body="b", type="x"))
    db_session.commit()
    nid = world["alice"].get("/notifications").json()[0]["id"]
    assert world["bob"].get("/notifications").json() == []
    assert world["bob"].patch(f"/notifications/{nid}/read").status_code == 404
    assert world["alice"].patch(f"/notifications/{nid}/read").json()["is_read"] is True


def test_file_download_is_group_scoped(world):
    alice, bob, cara, teacher, gid = world["alice"], world["bob"], world["cara"], world["teacher"], world["ga"]["id"]
    fid = alice.post(f"/groups/{gid}/files", files={"file": PDF}).json()["id"]
    assert bob.get(f"/files/{fid}/download").content == PDF[1]
    assert teacher.get(f"/files/{fid}/download").status_code == 200
    assert cara.get(f"/files/{fid}/download").status_code == 403
    assert world["other_teacher"].get(f"/files/{fid}/download").status_code == 403


@pytest.mark.parametrize(
    "filename,content,expected",
    [("evil.exe", b"MZ..", 400), ("fake.pdf", b"not a pdf", 400), ("../../etc/passwd.pdf", b"%PDF-1", 201)],
)
def test_upload_validation_and_filename_sanitizing(world, filename, content, expected):
    r = world["alice"].post(f"/groups/{world['ga']['id']}/files", files={"file": (filename, content, "application/octet-stream")})
    assert r.status_code == expected
    if expected == 201:
        assert r.json()["filename"] == "passwd.pdf"


def test_upload_size_limit_and_versioning(world):
    alice, gid = world["alice"], world["ga"]["id"]
    big = b"%PDF" + b"0" * (10 * 1024 * 1024)
    assert alice.post(f"/groups/{gid}/files", files={"file": ("big.pdf", big, "application/pdf")}).status_code == 413
    v1 = alice.post(f"/groups/{gid}/files", files={"file": PDF}).json()
    v2 = alice.post(f"/groups/{gid}/files", files={"file": PDF}).json()
    assert (v1["version"], v2["version"]) == (1, 2)
    listing = {f["version"]: f["is_latest"] for f in alice.get(f"/groups/{gid}/files").json()}
    assert listing == {1: False, 2: True}


def test_one_group_per_student_per_project_and_randomize(world):
    teacher, pid = world["teacher"], world["project"]["id"]
    assert teacher.post(f"/groups/{world['gb']['id']}/members", json={"user_id": world['alice'].id}).status_code == 409
    r = teacher.post(f"/projects/{pid}/groups/randomize", json={"group_size": 2})
    assert r.status_code == 201
    assert [len(g["members"]) for g in r.json()] == [1]  # only dave was ungrouped
    assert teacher.post(f"/projects/{pid}/groups/randomize", json={"group_size": 2}).status_code == 400
