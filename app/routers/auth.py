import sqlite3

from fastapi import APIRouter, Depends, Request, status

from app.db import get_connection
from app.models.auth import LoginRequest, SignupRequest, Token, User
from app.services import auth


router = APIRouter(tags=["auth"])


@router.post("/signup", response_model=User, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, connection: sqlite3.Connection = Depends(get_connection)) -> User:
    return auth.signup(connection, body.username, body.password.get_secret_value())


@router.post("/login", response_model=Token)
def login(
    body: LoginRequest,
    request: Request,
    connection: sqlite3.Connection = Depends(get_connection),
) -> Token:
    user = auth.authenticate(connection, body.username, body.password.get_secret_value())
    return Token(access_token=auth.create_access_token(user.id, request.app.state.settings))
