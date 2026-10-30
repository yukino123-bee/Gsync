import os
import tempfile

# Must be set before the app is imported
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="groupsync_test_uploads_")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.routers.auth import login_limiter

from app.security import pwd_context

pwd_context.update(bcrypt__rounds=4)  # fast hashing in tests

API = "/api/v1"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _fk(conn, _):
        conn.cursor().execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db_session):
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    login_limiter.clear_all()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class Actor:
    def __init__(self, client, user, token):
        self.client, self.user, self.id = client, user, user["id"]
        self.headers = {"Authorization": f"Bearer {token}"}

    def get(self, url, **kw):
        return self.client.get(API + url, headers=self.headers, **kw)

    def post(self, url, **kw):
        return self.client.post(API + url, headers=self.headers, **kw)

    def put(self, url, **kw):
        return self.client.put(API + url, headers=self.headers, **kw)

    def patch(self, url, **kw):
        return self.client.patch(API + url, headers=self.headers, **kw)

    def delete(self, url, **kw):
        return self.client.delete(API + url, headers=self.headers, **kw)


@pytest.fixture()
def make_user(client):
    def _make(name: str, role: str) -> Actor:
        r = client.post(
            f"{API}/auth/register",
            json={"name": name, "email": f"{name}@test.dev", "password": "password123", "role": role},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        return Actor(client, body["user"], body["access_token"])

    return _make


@pytest.fixture()
def world(make_user):
    """A teacher, a project with group A (alice, bob) and group B (cara), plus outsiders."""
    teacher = make_user("teacher", "teacher")
    other_teacher = make_user("teacher2", "teacher")
    alice, bob, cara, dave = (make_user(n, "student") for n in ("alice", "bob", "cara", "dave"))
    project = teacher.post("/projects", json={"title": "Project"}).json()
    group_a = teacher.post(
        f"/projects/{project['id']}/groups", json={"name": "A", "member_ids": [alice.id, bob.id]}
    ).json()
    group_b = teacher.post(
        f"/projects/{project['id']}/groups", json={"name": "B", "member_ids": [cara.id]}
    ).json()
    return dict(
        teacher=teacher, other_teacher=other_teacher, alice=alice, bob=bob, cara=cara, dave=dave,
        project=project, ga=group_a, gb=group_b,
    )
