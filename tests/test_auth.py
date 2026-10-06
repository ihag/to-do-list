from datetime import datetime, timedelta, timezone
import secrets
import sqlite3

import jwt
import pytest

from app.services.auth import ALGORITHM, AUDIENCE, ISSUER, password_hasher


PROTECTED_REQUESTS = [
    ("GET", "/todos", None),
    ("POST", "/todos", {"title": "할일"}),
    ("PATCH", "/todos/1/toggle", None),
    ("DELETE", "/todos/1", None),
]


def test_signup_login_and_password_hash(raw_client, test_app, settings):
    body = {"username": "  Alice  ", "password": "test-password-123"}
    created = raw_client.post("/signup", json=body)
    assert created.status_code == 201
    assert created.json() == {"id": 1, "username": "alice"}
    with sqlite3.connect(test_app.state.database_path) as connection:
        hashed = connection.execute("SELECT password_hash FROM users").fetchone()[0]
    assert hashed != body["password"]
    assert hashed.startswith("$argon2id$")
    assert password_hasher.verify(body["password"], hashed)

    logged_in = raw_client.post("/login", json=body)
    assert logged_in.status_code == 200
    assert set(logged_in.json()) == {"access_token", "token_type"}
    assert logged_in.json()["token_type"] == "bearer"
    payload = jwt.decode(
        logged_in.json()["access_token"],
        settings.jwt_secret,
        algorithms=[ALGORITHM],
        issuer=ISSUER,
        audience=AUDIENCE,
        options={"require": ["sub", "exp", "iat", "iss", "aud"]},
    )
    assert payload["sub"] == "1"
    assert payload["exp"] - payload["iat"] == 30 * 60
    assert "password" not in payload
    assert "password_hash" not in payload
    headers = {"Authorization": "Bearer " + logged_in.json()["access_token"]}
    assert raw_client.get("/todos", headers=headers).status_code == 200


def test_duplicate_signup_returns_400(raw_client, register_user):
    register_user()
    response = raw_client.post(
        "/signup", json={"username": "ALICE", "password": "another-password"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Username already registered"}


@pytest.mark.parametrize("path", ["/signup", "/login"])
@pytest.mark.parametrize(
    "body",
    [
        {},
        {"username": "alice"},
        {"password": "password123"},
        {"username": "a", "password": "password123"},
        {"username": "invalid user", "password": "password123"},
        {"username": "alice", "password": ""},
        {"username": "alice", "password": "password123", "id": 999},
    ],
)
def test_invalid_auth_payload_returns_422(raw_client, path, body):
    assert raw_client.post(path, json=body).status_code == 422


def test_signup_rejects_short_password(raw_client):
    response = raw_client.post(
        "/signup", json={"username": "alice", "password": "short"}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("username,password", [("alice", "wrong-password"), ("unknown", "password123")])
def test_login_wrong_credentials_returns_401(raw_client, register_user, username, password):
    register_user()
    response = raw_client.post("/login", json={"username": username, "password": password})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Invalid or missing credentials"}


@pytest.mark.parametrize("method,path,body", PROTECTED_REQUESTS)
@pytest.mark.parametrize("authorization", [None, "Bearer", "Basic invalid", "Bearer not-a-jwt"])
def test_protected_endpoints_require_token(raw_client, method, path, body, authorization):
    headers = {} if authorization is None else {"Authorization": authorization}
    response = raw_client.request(method, path, json=body, headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("method,path,body", PROTECTED_REQUESTS)
@pytest.mark.parametrize("invalid_case", ["expired", "wrong-signature", "wrong-algorithm", "missing-exp", "wrong-audience", "wrong-issuer", "unknown-user", "invalid-subject"])
def test_invalid_jwt_is_rejected(raw_client, register_user, settings, method, path, body, invalid_case):
    user, _ = register_user()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "iat": now,
        "exp": now + timedelta(minutes=30),
        "iss": ISSUER,
        "aud": AUDIENCE,
    }
    secret = settings.jwt_secret
    algorithm = ALGORITHM
    if invalid_case == "expired":
        payload["exp"] = now - timedelta(minutes=1)
    elif invalid_case == "wrong-signature":
        secret = secrets.token_hex(32)
    elif invalid_case == "wrong-algorithm":
        algorithm = "HS384"
    elif invalid_case == "missing-exp":
        payload.pop("exp")
    elif invalid_case == "wrong-audience":
        payload["aud"] = "another-api"
    elif invalid_case == "wrong-issuer":
        payload["iss"] = "another-issuer"
    elif invalid_case == "unknown-user":
        payload["sub"] = "999"
    elif invalid_case == "invalid-subject":
        payload["sub"] = "invalid"
    token = jwt.encode(payload, secret, algorithm=algorithm)
    response = raw_client.request(
        method, path, json=body, headers={"Authorization": "Bearer " + token}
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_users_only_access_their_own_todos(raw_client, register_user):
    _, alice_headers = register_user("alice")
    _, bob_headers = register_user("bob")
    alice = raw_client.post("/todos", json={"title": "앨리스 할일"}, headers=alice_headers)
    bob = raw_client.post("/todos", json={"title": "밥 할일"}, headers=bob_headers)
    assert alice.status_code == bob.status_code == 201
    alice_todo, bob_todo = alice.json(), bob.json()

    assert raw_client.get("/todos", headers=alice_headers).json() == [alice_todo]
    assert raw_client.get("/todos", headers=bob_headers).json() == [bob_todo]
    for owner_todo, other_headers in ((alice_todo, bob_headers), (bob_todo, alice_headers)):
        path = f"/todos/{owner_todo['id']}"
        assert raw_client.patch(path + "/toggle", headers=other_headers).status_code == 404
        assert raw_client.delete(path, headers=other_headers).status_code == 404

    assert raw_client.get("/todos", headers=alice_headers).json() == [alice_todo]
    assert raw_client.get("/todos", headers=bob_headers).json() == [bob_todo]
    toggled = raw_client.patch(f"/todos/{alice_todo['id']}/toggle", headers=alice_headers)
    assert toggled.status_code == 200
    assert toggled.json()["done"] is True
    assert raw_client.get("/todos", headers=bob_headers).json() == [bob_todo]
    assert raw_client.delete(f"/todos/{bob_todo['id']}", headers=bob_headers).status_code == 204
    assert raw_client.get("/todos", headers=bob_headers).json() == []
    assert raw_client.get("/todos", headers=alice_headers).json() == [toggled.json()]


def test_client_cannot_set_todo_owner(raw_client, register_user):
    _, alice_headers = register_user("alice")
    bob, bob_headers = register_user("bob")
    response = raw_client.post(
        "/todos", json={"title": "소유자 위조", "user_id": bob["id"]}, headers=alice_headers
    )
    assert response.status_code == 422
    assert raw_client.get("/todos", headers=alice_headers).json() == []
    assert raw_client.get("/todos", headers=bob_headers).json() == []
