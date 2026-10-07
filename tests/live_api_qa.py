"""운영 테스트 계정으로 권한과 PostgreSQL 저장을 검증한다."""

import secrets
import sys

import httpx


def main():
    base = sys.argv[1].rstrip("/")
    with httpx.Client(base_url=base, timeout=30) as client:
        accounts = []
        for _ in range(2):
            body = {
                "username": "qa_api_" + secrets.token_hex(6),
                "password": secrets.token_urlsafe(24),
            }
            created = client.post("/signup", json=body)
            assert created.status_code == 201
            assert client.post("/signup", json=body).status_code == 400
            assert client.post(
                "/login", json={**body, "password": "wrong-password"}
            ).status_code == 401
            logged_in = client.post("/login", json=body)
            assert logged_in.status_code == 200
            headers = {
                "Authorization": "Bearer " + logged_in.json()["access_token"]
            }
            accounts.append((created.json(), headers))
        alice, alice_headers = accounts[0]
        bob, bob_headers = accounts[1]
        assert client.get("/users/me", headers=alice_headers).json() == alice
        assert client.get("/users/me", headers=bob_headers).json() == bob
        for path in ("/users/me", "/workspaces/current", "/todos"):
            assert client.get(path).status_code == 401
        empty = client.get("/workspaces/current", headers=alice_headers).json()
        assert empty["revision"] == 0
        state = {
            "version": 1,
            "topics": [{
                "id": "qa-topic", "name": "권한 검증", "open": True,
                "emoji": "📋", "todos": [],
            }],
        }
        body = {"revision": 0, "state": state}
        saved = client.put("/workspaces/current", headers=alice_headers, json=body)
        assert saved.status_code == 200
        assert saved.json()["revision"] == 1
        assert client.put(
            "/workspaces/current", headers=alice_headers, json=body
        ).status_code == 409
        assert client.get(
            "/workspaces/current", headers=bob_headers
        ).json()["state"]["topics"] == []
        forged = {**body, "user_id": alice["id"]}
        assert client.put(
            "/workspaces/current", headers=bob_headers, json=forged
        ).status_code == 422
        todo = client.post(
            "/todos", headers=alice_headers,
            json={"title": "운영 PostgreSQL 검증", "due": "2026-10-10"},
        )
        assert todo.status_code == 201
        todo_id = todo.json()["id"]
        assert client.get("/todos", headers=bob_headers).json() == []
        assert client.patch(
            f"/todos/{todo_id}/toggle", headers=bob_headers
        ).status_code == 404
        assert client.delete(
            f"/todos/{todo_id}", headers=bob_headers
        ).status_code == 404
        toggled = client.patch(
            f"/todos/{todo_id}/toggle", headers=alice_headers
        )
        assert toggled.status_code == 200
        assert toggled.json()["done"] is True
        assert client.get("/todos", headers=alice_headers).json() == [toggled.json()]
        preflight = client.options("/workspaces/current", headers={
            "Origin": "https://ihag.github.io",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        })
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == "https://ihag.github.io"
    print("Live PostgreSQL API QA passed: login failures, duplicate signup, own-user data, cross-account isolation, stale revisions, owner forgery, legacy todos, Pages CORS.")


if __name__ == "__main__":
    main()
