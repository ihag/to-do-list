from datetime import datetime, timedelta, timezone
import secrets
import sqlite3
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from pwdlib import PasswordHash

from app.config import Settings
from app.db import get_connection, INTEGRITY_ERRORS
from app.models.auth import User


ALGORITHM = "HS256"
ISSUER = "taskflow"
AUDIENCE = "taskflow-api"
password_hasher = PasswordHash.recommended()
# 존재하지 않는 사용자도 비밀번호 검증 비용을 동일하게 지불한다.
dummy_password_hash = password_hasher.hash(secrets.token_urlsafe(32))
bearer = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Invalid or missing credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def signup(connection: sqlite3.Connection, username: str, password: str) -> User:
    hashed = password_hasher.hash(password)
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?) RETURNING id",
                (username, hashed),
            )
            user = User(id=cursor.fetchone()["id"], username=username)
    except INTEGRITY_ERRORS as exc:
        raise HTTPException(status_code=400, detail="Username already registered") from exc
    return user


def authenticate(connection: sqlite3.Connection, username: str, password: str) -> User:
    row = connection.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    hashed = row["password_hash"] if row else dummy_password_hash
    valid = password_hasher.verify(password, hashed)
    if row is None or not valid:
        raise unauthorized()
    return User(id=row["id"], username=row["username"])


def create_access_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
            "iss": ISSUER,
            "aud": AUDIENCE,
        },
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    connection: sqlite3.Connection = Depends(get_connection),
) -> User:
    if credentials is None:
        raise unauthorized()
    try:
        payload = jwt.decode(
            credentials.credentials,
            request.app.state.settings.jwt_secret,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
        )
        subject = payload["sub"]
        user_id = int(subject)
        if str(user_id) != subject or not 0 < user_id <= 9223372036854775807:
            raise ValueError("Invalid token subject")
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise unauthorized() from exc
    row = connection.execute(
        "SELECT id, username FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None:
        raise unauthorized()
    return User(**dict(row))
