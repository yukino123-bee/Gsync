from tests.conftest import API

CREDS = {"name": "Zed", "email": "Zed@Test.dev", "password": "password123", "role": "student"}


def test_register_returns_tokens_and_hides_password(client):
    r = client.post(f"{API}/auth/register", json=CREDS)
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "zed@test.dev"  # normalized
    assert body["user"]["role"] == "student"
    assert "password" not in r.text and "hash" not in r.text
    assert body["access_token"] and body["refresh_token"]


def test_register_duplicate_email_conflicts(client):
    client.post(f"{API}/auth/register", json=CREDS)
    r = client.post(f"{API}/auth/register", json={**CREDS, "email": "zed@test.dev"})
    assert r.status_code == 409
    assert r.json() == {"detail": "Email is already registered"}


def test_cannot_self_register_as_admin(client):
    r = client.post(f"{API}/auth/register", json={**CREDS, "role": "admin"})
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)


def test_register_validates_input(client):
    assert client.post(f"{API}/auth/register", json={**CREDS, "password": "short"}).status_code == 422
    assert client.post(f"{API}/auth/register", json={**CREDS, "email": "nope"}).status_code == 422


def test_login_success_and_me(client):
    client.post(f"{API}/auth/register", json=CREDS)
    r = client.post(f"{API}/auth/login", json={"email": "zed@test.dev", "password": "password123"})
    assert r.status_code == 200
    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200 and me.json()["name"] == "Zed"


def test_login_wrong_password_and_unknown_user_look_the_same(client):
    client.post(f"{API}/auth/register", json=CREDS)
    a = client.post(f"{API}/auth/login", json={"email": "zed@test.dev", "password": "wrongpass"})
    b = client.post(f"{API}/auth/login", json={"email": "ghost@test.dev", "password": "wrongpass"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_login_is_rate_limited(client):
    client.post(f"{API}/auth/register", json=CREDS)
    bad = {"email": "zed@test.dev", "password": "wrongpass"}
    codes = [client.post(f"{API}/auth/login", json=bad).status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]
    # Even the right password is blocked while the limit is active
    ok = client.post(f"{API}/auth/login", json={"email": "zed@test.dev", "password": "password123"})
    assert ok.status_code == 429 and "Retry-After" in ok.headers


def test_refresh_flow_and_token_type_separation(client):
    tokens = client.post(f"{API}/auth/register", json=CREDS).json()
    r = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200 and r.json()["access_token"]
    # access token is not accepted as a refresh token, and vice versa
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["access_token"]}).status_code == 401
    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert me.status_code == 401


def test_protected_routes_require_a_valid_token(client):
    assert client.get(f"{API}/auth/me").status_code == 401
    assert client.get(f"{API}/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.get(f"{API}/groups/my").status_code == 401


def test_push_token_can_be_saved(make_user):
    u = make_user("pushy", "student")
    assert u.put("/auth/push-token", json={"push_token": "ExponentPushToken[abc]"}).status_code == 200
