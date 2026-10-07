from datetime import date
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    field_validator,
    model_validator,
)


EMOJIS = {
    "📋", "💼", "🌿", "🏠", "🎯", "📚", "💡", "💻",
    "🎨", "💪", "✈️", "🛒", "🎵", "❤️", "⭐", "☕",
}


class WorkspaceTodo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    done: StrictBool
    due: str = Field(max_length=10)

    @field_validator("title")
    @classmethod
    def valid_title(cls, value):
        if not value.strip():
            raise ValueError("Title must not be blank")
        return value

    @field_validator("due")
    @classmethod
    def valid_due(cls, value):
        if value and date.fromisoformat(value).isoformat() != value:
            raise ValueError("Invalid date")
        return value


class WorkspaceTopic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=60)
    emoji: Optional[str] = None
    open: StrictBool
    todos: list[WorkspaceTodo] = Field(max_length=1000)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value):
        if not value.strip():
            raise ValueError("Name must not be blank")
        return value

    @field_validator("emoji")
    @classmethod
    def valid_emoji(cls, value):
        if value is not None and value not in EMOJIS:
            raise ValueError("Unsupported emoji")
        return value


class WorkspaceState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(strict=True, ge=1, le=1)
    topics: list[WorkspaceTopic] = Field(max_length=100)

    @model_validator(mode="after")
    def unique_ids_and_size(self):
        ids = [topic.id for topic in self.topics]
        ids.extend(todo.id for topic in self.topics for todo in topic.todos)
        if len(ids) != len(set(ids)):
            raise ValueError("IDs must be unique")
        if len(self.model_dump_json().encode()) > 1_000_000:
            raise ValueError("Workspace must be smaller than 1 MB")
        return self


class WorkspaceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(strict=True, ge=0, le=9223372036854775806)
    state: WorkspaceState


class Workspace(BaseModel):
    revision: int
    state: WorkspaceState
