from contextlib import closing
import sqlite3

from fastapi.testclient import TestClient
import pytest

from app.db import connect, initialize_database, migrate_auth
from app.main import create_app


@pytest.fixture
def legacy_database(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE todos (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, due TEXT)"
        )
        connection.execute(
            "INSERT INTO todos (title, done, due) VALUES (?, ?, ?)",
            ("소유자 없는 기존 할일", 1, "2026-10-08"),
        )
    return path


def test_legacy_database_requires_explicit_migration(legacy_database):
    with pytest.raises(RuntimeError, match="migration"):
        initialize_database(legacy_database)
    with sqlite3.connect(legacy_database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM todos").fetchone()[0] == 1
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'users'"
        ).fetchone() is None
        assert "user_id" not in {
            row[1] for row in connection.execute("PRAGMA table_info(todos)")
        }


def test_migration_preserves_data_and_hides_unowned_todos(legacy_database, settings):
    migrate_auth(legacy_database)
    migrate_auth(legacy_database)
    with sqlite3.connect(legacy_database) as connection:
        assert connection.execute(
            "SELECT id, title, done, due, user_id FROM todos"
        ).fetchall() == [(1, "소유자 없는 기존 할일", 1, "2026-10-08", None)]
    with TestClient(create_app(legacy_database, settings)) as client:
        credentials = {"username": "alice", "password": "test-password-123"}
        assert client.post("/signup", json=credentials).status_code == 201
        login = client.post("/login", json=credentials)
        client.headers.update({"Authorization": "Bearer " + login.json()["access_token"]})
        assert client.get("/todos").json() == []
        assert client.patch("/todos/1/toggle").status_code == 404
        assert client.delete("/todos/1").status_code == 404
        created = client.post("/todos", json={"title": "새 할일"})
        assert created.status_code == 201
        assert created.json()["id"] == 2
        assert client.get("/todos").json() == [created.json()]


def test_foreign_key_enforced(tmp_path):
    path = tmp_path / "todos.sqlite3"
    initialize_database(path)
    with closing(connect(path)) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            with connection:
                connection.execute(
                    "INSERT INTO todos (title, user_id) VALUES (?, ?)", ("할일", 999)
                )
