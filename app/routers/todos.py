import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db import get_connection
from app.models.auth import User
from app.models.todo import Todo, TodoCreate
from app.services.auth import get_current_user
from app.services import todos


router = APIRouter(prefix="/todos", tags=["todos"])


@router.post("", response_model=Todo, status_code=status.HTTP_201_CREATED)
def create_todo(
    body: TodoCreate,
    user: User = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_connection),
) -> Todo:
    try:
        return todos.add_todo(connection, user.id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[Todo])
def list_todos(
    user: User = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_connection),
) -> list[Todo]:
    return todos.list_todos(connection, user.id)


@router.patch("/{id}/toggle", response_model=Todo)
def toggle_todo(
    id: int,
    user: User = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_connection),
) -> Todo:
    todo = todos.toggle_todo(connection, user.id, id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(
    id: int,
    user: User = Depends(get_current_user),
    connection: sqlite3.Connection = Depends(get_connection),
) -> Response:
    if not todos.delete_todo(connection, user.id, id):
        raise HTTPException(status_code=404, detail="Todo not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
