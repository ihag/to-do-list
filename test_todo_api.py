import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_added_todo_appears_in_list(client):
    created = client.post("/todos", json={"title": "장보기"})
    assert created.status_code == 201
    assert created.json() == {
        "id": 1,
        "title": "장보기",
        "done": False,
        "due": None,
    }

    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == [created.json()]


def test_missing_title_returns_400(client):
    response = client.post("/todos", json={})
    assert response.status_code == 400
    assert response.json() == {"detail": "Title is required"}
    assert client.get("/todos").json() == []


@pytest.mark.parametrize(
    "method,path",
    [("patch", "/todos/999/toggle"), ("delete", "/todos/999")],
)
def test_missing_id_returns_404(client, method, path):
    created = client.post("/todos", json={"title": "유지할 할일"})
    assert created.status_code == 201

    response = client.request(method, path)
    assert response.status_code == 404
    assert response.json() == {"detail": "Todo not found"}
    assert client.get("/todos").json() == [created.json()]


def test_toggle_twice_and_delete(client):
    created = client.post("/todos", json={"title": "장보기", "due": "2026-10-08"})
    assert created.status_code == 201
    todo = created.json()
    assert todo["due"] == "2026-10-08"
    path = f"/todos/{todo['id']}"
    toggled = client.patch(path + "/toggle")
    assert toggled.status_code == 200
    assert toggled.json() == {**todo, "done": True}
    assert client.get("/todos").json() == [toggled.json()]
    assert client.patch(path + "/toggle").json() == todo
    deleted = client.delete(path)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get("/todos").json() == []
    assert client.post("/todos", json={"title": "새 할일"}).json()["id"] > todo["id"]


def test_data_persists_after_restart(tmp_path, settings):
    database_path = tmp_path / "todos.sqlite3"
    body = {"username": "alice", "password": "test-password-123"}
    with TestClient(create_app(database_path, settings)) as first_client:
        assert first_client.post("/signup", json=body).status_code == 201
        logged_in = first_client.post("/login", json=body)
        assert logged_in.status_code == 200
        token = logged_in.json()["access_token"]
        first_client.headers.update({"Authorization": "Bearer " + token})
        created = first_client.post("/todos", json={"title": "보존", "due": "2026-10-08"})
        assert created.status_code == 201
        todo = created.json()
        toggled = first_client.patch(f"/todos/{todo['id']}/toggle")
        assert toggled.status_code == 200
        expected = toggled.json()

    # 앱 객체까지 새로 만들어 사용자, 비밀번호, 토큰, 할일의 영속성을 확인한다.
    with TestClient(create_app(database_path, settings)) as restarted_client:
        restarted_client.headers.update({"Authorization": "Bearer " + token})
        response = restarted_client.get("/todos")
        assert response.status_code == 200
        assert response.json() == [expected]
        assert restarted_client.post("/login", json=body).status_code == 200
        assert restarted_client.post("/todos", json={"title": "추가"}).json()["id"] > todo["id"]
