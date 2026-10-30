def test_register_login_logout(client, new_user):
    headers, name = new_user
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["username"] == name and me["onboarded"] is False
    assert client.post("/api/auth/login", json={"username": name, "password": "secret123"}).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_duplicate_username_and_bad_password(client, new_user):
    _, name = new_user
    r = client.post("/api/auth/register", json={"username": name, "password": "another1"})
    assert r.status_code == 409 and r.json()["error"] == "username_taken"
    r = client.post("/api/auth/login", json={"username": name, "password": "wrong-pass"})
    assert r.status_code == 401


def test_validation_and_auth_errors(client):
    r = client.post("/api/auth/register", json={"username": "a b", "password": "1"})
    assert r.status_code == 422 and r.json()["error"] == "validation_error"
    assert client.get("/api/me/dashboard").status_code == 401


def test_password_is_hashed(db, new_user):
    _, name = new_user
    stored = db.users.find_one({"username": name})["password"]
    assert "secret123" not in str(stored) and len(stored["hash"]) == 64


def test_sessions_have_ttl_index(db):
    idx = db.sessions.index_information()["session_ttl"]
    assert idx["expireAfterSeconds"] == 0
