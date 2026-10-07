import pytest

from app.security import MAX_REQUEST_BYTES


@pytest.mark.parametrize("path", ["/signup", "/login"])
@pytest.mark.parametrize(
    "body",
    [
        {"password": "never-echo-this-password"},
        {"username": "alice", "password": "never-echo-this-password" * 20},
        {"username": "alice", "password": "never-echo-this-password", "extra": 1},
    ],
)
def test_auth_validation_does_not_echo_password(raw_client, path, body):
    response = raw_client.post(path, json=body)
    assert response.status_code == 422
    assert "never-echo-this-password" not in response.text
    assert all("input" not in error for error in response.json()["detail"])
    assert response.headers["cache-control"] == "no-store"


def test_login_token_and_private_data_are_not_cached(raw_client, register_user):
    _, headers = register_user()
    response = raw_client.post(
        "/login", json={"username": "alice", "password": "test-password-123"}
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    for path in ("/todos", "/users/me", "/workspaces/current"):
        response = raw_client.get(path, headers=headers)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert raw_client.get(path).headers["cache-control"] == "no-store"


def test_host_header_cannot_bypass_private_cache_policy(raw_client, register_user):
    _, headers = register_user()
    headers["Host"] = "attacker.example/other"
    response = raw_client.get("/todos", headers=headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("path", ["/", "/app.js", "/.env", "/todos"])
def test_security_headers_on_success_and_errors(raw_client, path):
    response = raw_client.get(path)
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_static_page_restricts_scripts_and_connections(raw_client):
    page = raw_client.get("/").text
    assert 'http-equiv="Content-Security-Policy"' in page
    assert "script-src 'self'" in page
    assert "object-src 'none'" in page
    assert "base-uri 'none'" in page
    assert "connect-src 'self' https://taskflow-sync-rla2fma-2683.vercel.app" in page


@pytest.mark.parametrize("path", ["/signup", "/login", "/workspaces/current"])
def test_oversized_requests_are_rejected_before_parsing(raw_client, path):
    method = "PUT" if path.startswith("/workspaces") else "POST"
    response = raw_client.request(method, path, content=b"x" * (MAX_REQUEST_BYTES + 1))
    assert response.status_code == 413
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"detail": "Request body too large"}


@pytest.mark.anyio
async def test_chunked_request_cannot_bypass_body_limit():
    from app.security import RequestBodyLimitMiddleware

    messages = iter([
        {"type": "http.request", "body": b"x" * MAX_REQUEST_BYTES, "more_body": True},
        {"type": "http.request", "body": b"x", "more_body": False},
    ])
    sent = []

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    async def app(scope, receive, send):
        pytest.fail("Oversized body reached the app")

    await RequestBodyLimitMiddleware(app)(
        {"type": "http", "method": "POST"}, receive, send
    )
    assert sent[0]["status"] == 413
