import pytest


def test_empty_list(client):
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_list_in_order(client):
    first = client.post("/todos", json={"title": "  장보기  "})
    assert first.status_code == 201
    assert first.json() == {"id": 1, "title": "장보기", "done": False, "due": None}
    second = client.post("/todos", json={"title": "청소"})
    assert second.status_code == 201
    assert client.get("/todos").json() == [first.json(), second.json()]


def test_toggle_twice(client):
    todo = client.post("/todos", json={"title": "장보기"}).json()
    path = f"/todos/{todo['id']}/toggle"
    first = client.patch(path)
    assert first.status_code == 200
    assert first.json() == {**todo, "done": True}
    assert client.get("/todos").json() == [first.json()]
    assert client.patch(path).json() == todo


def test_delete_and_do_not_reuse_id(client):
    client.post("/todos", json={"title": "장보기"})
    response = client.delete("/todos/1")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/todos").json() == []
    assert client.post("/todos", json={"title": "청소"}).json()["id"] == 2
    assert client.delete("/todos/1").status_code == 404


@pytest.mark.parametrize("method,path", [("patch", "/todos/99/toggle"), ("delete", "/todos/99")])
def test_missing_todo(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 404
    assert response.json() == {"detail": "Todo not found"}


@pytest.mark.parametrize("body,expected", [({"title": ""}, 400), ({"title": " \n\t "}, 400), ({}, 400), ({"title": None}, 400), ({"title": 123}, 422)])
def test_invalid_title(client, body, expected):
    assert client.post("/todos", json=body).status_code == expected
    assert client.get("/todos").json() == []
