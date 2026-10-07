from copy import deepcopy

import pytest


def workspace():
    return {"version": 1, "topics": [{"id": "topic-1", "name": "업무", "emoji": "💼", "open": True, "todos": [{"id": "todo-1", "title": "보고서", "done": False, "due": "2026-10-10"}]}]}


def test_workspace_round_trip_and_current_user(raw_client, register_user):
    user, headers = register_user()
    assert raw_client.get("/users/me", headers=headers).json() == user
    empty = raw_client.get("/workspaces/current", headers=headers)
    assert empty.status_code == 200
    assert empty.headers["cache-control"] == "no-store"
    assert empty.json() == {"revision": 0, "state": {"version": 1, "topics": []}}
    state = workspace()
    saved = raw_client.put("/workspaces/current", headers=headers, json={"revision": 0, "state": state})
    assert saved.status_code == 200
    assert saved.json() == {"revision": 1, "state": state}
    state["topics"][0]["todos"][0]["done"] = True
    assert raw_client.put("/workspaces/current", headers=headers, json={"revision": 1, "state": state}).json()["revision"] == 2
    assert raw_client.get("/workspaces/current", headers=headers).json() == {"revision": 2, "state": state}


def test_stale_revision_never_overwrites(raw_client, register_user):
    _, headers = register_user()
    saved = workspace()
    assert raw_client.put("/workspaces/current", headers=headers, json={"revision": 0, "state": saved}).status_code == 200
    stale = deepcopy(saved)
    stale["topics"][0]["name"] = "덮어쓰기"
    response = raw_client.put("/workspaces/current", headers=headers, json={"revision": 0, "state": stale})
    assert response.status_code == 409
    assert raw_client.get("/workspaces/current", headers=headers).json()["state"] == saved


def test_accounts_are_isolated(raw_client, register_user):
    alice, alice_headers = register_user("alice")
    bob, bob_headers = register_user("bob")
    assert raw_client.put("/workspaces/current", headers=alice_headers, json={"revision": 0, "state": workspace()}).status_code == 200
    assert raw_client.get("/workspaces/current", headers=bob_headers).json()["state"]["topics"] == []
    assert raw_client.get("/users/me", headers=bob_headers).json() == bob
    forged = {"revision": 0, "state": workspace(), "user_id": alice["id"]}
    assert raw_client.put("/workspaces/current", headers=bob_headers, json=forged).status_code == 422
    assert raw_client.get("/workspaces/current", headers=alice_headers).json()["revision"] == 1


@pytest.mark.parametrize("method,path,body", [("GET", "/users/me", None), ("GET", "/workspaces/current", None), ("PUT", "/workspaces/current", {"revision": 0, "state": workspace()})])
@pytest.mark.parametrize("token", [None, "Bearer invalid"])
def test_workspace_requires_auth(raw_client, method, path, body, token):
    response = raw_client.request(method, path, json=body, headers={} if token is None else {"Authorization": token})
    assert response.status_code == 401


@pytest.mark.parametrize("invalid", ["blank-name", "duplicate-id", "invalid-date", "invalid-emoji", "wrong-bool", "extra-field", "negative-revision", "future-version", "long-title"])
def test_invalid_workspace_preserves_saved_data(raw_client, register_user, invalid):
    _, headers = register_user()
    body = {"revision": 0, "state": workspace()}
    topic = body["state"]["topics"][0]
    if invalid == "blank-name": topic["name"] = "   "
    elif invalid == "duplicate-id": topic["todos"][0]["id"] = topic["id"]
    elif invalid == "invalid-date": topic["todos"][0]["due"] = "2026-02-30"
    elif invalid == "invalid-emoji": topic["emoji"] = "x"
    elif invalid == "wrong-bool": topic["todos"][0]["done"] = "false"
    elif invalid == "extra-field": topic["owner"] = 123
    elif invalid == "negative-revision": body["revision"] = -1
    elif invalid == "future-version": body["state"]["version"] = 2
    elif invalid == "long-title": topic["todos"][0]["title"] = "a" * 201
    assert raw_client.put("/workspaces/current", headers=headers, json=body).status_code == 422
    assert raw_client.get("/workspaces/current", headers=headers).json()["revision"] == 0


def test_legacy_topics_without_emoji(raw_client, register_user):
    _, headers = register_user()
    state = workspace()
    del state["topics"][0]["emoji"]
    result = raw_client.put("/workspaces/current", headers=headers, json={"revision": 0, "state": state})
    assert result.status_code == 200
    assert result.json()["state"] == state


def test_cors_allows_pages_and_rejects_unknown_origin(raw_client):
    headers = {"Origin": "https://ihag.github.io", "Access-Control-Request-Method": "PUT", "Access-Control-Request-Headers": "Authorization,Content-Type"}
    response = raw_client.options("/workspaces/current", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == headers["Origin"]
    headers["Origin"] = "https://unknown.example"
    assert raw_client.options("/workspaces/current", headers=headers).status_code == 400


def multiple_workspaces():
    return {
        "version": 1,
        "topics": [],
        "workspaces": [
            {"id": "default", "name": "업무", "emoji": "💼", "topics": workspace()["topics"]},
            {"id": "personal", "name": "개인", "emoji": "🌿", "topics": []},
        ],
    }


def test_multiple_workspaces_round_trip_delete_and_isolation(raw_client, register_user):
    _, headers = register_user("spaces_alice")
    _, other = register_user("spaces_bob")
    state = multiple_workspaces()
    saved = raw_client.put("/workspaces/current", headers=headers, json={"revision": 0, "state": state})
    assert saved.status_code == 200
    assert saved.json()["state"] == state
    assert raw_client.get("/workspaces/current", headers=headers).json()["state"] == state
    assert "workspaces" not in raw_client.get("/workspaces/current", headers=other).json()["state"]
    state["workspaces"][1]["name"] = "개인 프로젝트"
    state["workspaces"][1]["emoji"] = "🎯"
    state["workspaces"].pop(0)
    assert raw_client.put("/workspaces/current", headers=headers, json={"revision": 1, "state": state}).json()["state"] == state
    state["workspaces"] = []
    assert raw_client.put("/workspaces/current", headers=headers, json={"revision": 2, "state": state}).status_code == 200
    assert raw_client.get("/workspaces/current", headers=headers).json()["state"] == state


@pytest.mark.parametrize("invalid", ["blank", "long", "emoji", "duplicate-space", "duplicate-topic", "mixed-legacy", "too-many"])
def test_invalid_multiple_workspaces_preserves_data(raw_client, register_user, invalid):
    _, headers = register_user()
    state = multiple_workspaces()
    assert raw_client.put("/workspaces/current", headers=headers, json={"revision": 0, "state": state}).status_code == 200
    broken = deepcopy(state)
    spaces = broken["workspaces"]
    if invalid == "blank":
        spaces[0]["name"] = " "
    elif invalid == "long":
        spaces[0]["name"] = "x" * 61
    elif invalid == "emoji":
        spaces[0]["emoji"] = "x"
    elif invalid == "duplicate-space":
        spaces[1]["id"] = spaces[0]["id"]
    elif invalid == "duplicate-topic":
        spaces[1]["topics"] = deepcopy(spaces[0]["topics"])
    elif invalid == "mixed-legacy":
        broken["topics"] = workspace()["topics"]
    elif invalid == "too-many":
        broken["workspaces"] = [{"id": str(i), "name": "공간", "emoji": "📋", "topics": []} for i in range(51)]
    assert raw_client.put("/workspaces/current", headers=headers, json={"revision": 1, "state": broken}).status_code == 422
    assert raw_client.get("/workspaces/current", headers=headers).json()["state"] == state
