import sqlite3
from typing import Optional

from app.models.todo import Todo, TodoCreate


def add_todo(connection: sqlite3.Connection, user_id: int, body: TodoCreate) -> Todo:
    title = (body.title or "").strip()
    if not title:
        raise ValueError("Title is required")
    with connection:
        cursor = connection.execute(
            "INSERT INTO todos (title, due, user_id) VALUES (?, ?, ?) RETURNING id",
            (title, body.due.isoformat() if body.due else None, user_id),
        )
        todo = Todo(id=cursor.fetchone()["id"], title=title, due=body.due)
    return todo


def list_todos(connection: sqlite3.Connection, user_id: int) -> list[Todo]:
    rows = connection.execute(
        "SELECT id, title, done, due FROM todos WHERE user_id = ? ORDER BY id",
        (user_id,),
    ).fetchall()
    return [Todo(**dict(row)) for row in rows]


def toggle_todo(connection: sqlite3.Connection, user_id: int, todo_id: int) -> Optional[Todo]:
    with connection:
        cursor = connection.execute(
            "UPDATE todos SET done = 1 - done WHERE id = ? AND user_id = ?",
            (todo_id, user_id),
        )
        if cursor.rowcount == 0:
            return None
        row = connection.execute(
            "SELECT id, title, done, due FROM todos WHERE id = ? AND user_id = ?",
            (todo_id, user_id),
        ).fetchone()
        todo = Todo(**dict(row))
    return todo


def delete_todo(connection: sqlite3.Connection, user_id: int, todo_id: int) -> bool:
    with connection:
        cursor = connection.execute(
            "DELETE FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id)
        )
    return cursor.rowcount == 1
