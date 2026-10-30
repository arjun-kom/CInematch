import os

import pytest

# Always use a separate database; the tests delete it when they finish.
os.environ["MONGO_DB"] = os.environ.get("TEST_MONGO_DB", "cinematch_test")

from fastapi.testclient import TestClient  # noqa: E402
from pymongo.errors import PyMongoError  # noqa: E402

from app.db import get_db, init_db  # noqa: E402
from app.main import app  # noqa: E402


def _up():
    try:
        get_db().command("ping")
        return True
    except PyMongoError:
        return False


if not _up():
    pytest.skip("MongoDB is not reachable (set MONGO_URL)", allow_module_level=True)


@pytest.fixture(scope="session")
def db():
    database = get_db()
    database.client.drop_database(database.name)
    init_db(database, seed_users=True)
    yield database
    database.client.drop_database(database.name)


@pytest.fixture(scope="session")
def client(db):
    with TestClient(app) as c:
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def new_user(client):
    """Register a fresh user and return (headers, username)."""
    import uuid
    name = "u" + uuid.uuid4().hex[:8]
    r = client.post("/api/auth/register", json={"username": name, "password": "secret123"})
    assert r.status_code == 201, r.text
    return auth(r.json()["token"]), name


@pytest.fixture()
def demo(client):
    r = client.post("/api/auth/login", json={"username": "demo", "password": "demo1234"})
    return auth(r.json()["token"])
