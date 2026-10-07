from dataclasses import dataclass, replace
from threading import Lock
from typing import Optional


@dataclass
class Todo:
    id: int
    title: str
    completed: bool = False


class TodoRepository:
    """Process-local list storage; return snapshots to keep mutations internal."""

    def __init__(self) -> None:
        self._todos: list[Todo] = []
        self._next_id = 1
        self._lock = Lock()

    def add(self, title: str) -> Todo:
        with self._lock:
            todo = Todo(id=self._next_id, title=title)
            self._next_id += 1
            self._todos.append(todo)
            return replace(todo)

    def list(self) -> list[Todo]:
        with self._lock:
            return [replace(todo) for todo in self._todos]

    def toggle(self, todo_id: int) -> Optional[Todo]:
        with self._lock:
            for todo in self._todos:
                if todo.id == todo_id:
                    todo.completed = not todo.completed
                    return replace(todo)
            return None

    def delete(self, todo_id: int) -> bool:
        with self._lock:
            for index, todo in enumerate(self._todos):
                if todo.id == todo_id:
                    self._todos.pop(index)
                    return True
            return False
