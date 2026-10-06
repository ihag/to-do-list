import secrets

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings():
    return Settings(jwt_secret=secrets.token_hex(32), access_token_expire_minutes=30)


@pytest.fixture
def test_app(tmp_path, settings):
    return create_app(tmp_path / "todos.sqlite3", settings=settings)


@pytest.fixture
def raw_client(test_app):
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture
def register_user(raw_client):
    def register(username="alice", password="test-password-123"):
        body = {"username": username, "password": password}
        created = raw_client.post("/signup", json=body)
        assert created.status_code == 201
        logged_in = raw_client.post("/login", json=body)
        assert logged_in.status_code == 200
        return created.json(), {
            "Authorization": "Bearer " + logged_in.json()["access_token"]
        }

    return register


@pytest.fixture
def client(raw_client, register_user):
    _, headers = register_user()
    raw_client.headers.update(headers)
    return raw_client
