from contextlib import closing
import os
from pathlib import Path
import sqlite3
from typing import Iterator, Union

from fastapi import Request
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row


DatabasePath = Union[str, Path]
DB_PATH = Path(__file__).resolve().parent.parent / "todos.sqlite3"
INTEGRITY_ERRORS = (sqlite3.IntegrityError, psycopg.IntegrityError)


class PostgresConnection:
    def __init__(self, url):
        self.connection = psycopg.connect(url, row_factory=dict_row, connect_timeout=10)

    def execute(self, query, parameters=()):
        return self.connection.execute(query.replace("?", "%s"), parameters)

    def __enter__(self):
        return self

    def __exit__(self, error_type, error, traceback):
        if error_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()

    def close(self):
        self.connection.close()


def configured_database():
    load_dotenv(DB_PATH.parent / ".env", override=False)
    url = os.environ.get("DATABASE_URL")
    if os.environ.get("VERCEL") and not url:
        raise RuntimeError("DATABASE_URL is required in production")
    return url or DB_PATH


WORKSPACES_SCHEMA = """
    CREATE TABLE IF NOT EXISTS workspaces (
        user_id BIGINT PRIMARY KEY REFERENCES users(id),
        revision BIGINT NOT NULL DEFAULT 0,
        state TEXT NOT NULL
    )
"""

USERS_SCHEMA = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    )
"""

TODOS_SCHEMA = """
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
        due TEXT,
        user_id INTEGER REFERENCES users(id)
    )
"""


def connect(database_path: DatabasePath) -> sqlite3.Connection:
    if str(database_path).startswith(("postgres://", "postgresql://")):
        return PostgresConnection(str(database_path))
    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: DatabasePath) -> None:
    with closing(connect(database_path)) as connection:
        if isinstance(connection, PostgresConnection):
            with connection:
                connection.execute(
                    USERS_SCHEMA.replace(
                        "INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY"
                    )
                )
                connection.execute(
                    TODOS_SCHEMA.replace(
                        "INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY"
                    ).replace("user_id INTEGER", "user_id BIGINT")
                )
                connection.execute(WORKSPACES_SCHEMA)
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_todos_user_id ON todos(user_id)"
                )
            return
        columns = connection.execute("PRAGMA table_info(todos)").fetchall()
        if columns and "user_id" not in {row["name"] for row in columns}:
            # 기존 DB 변경은 승인 후 명시적 마이그레이션으로만 수행한다.
            raise RuntimeError(
                "Legacy database needs migration. After approval, run: "
                "python -m app.migrate_auth --confirm"
            )
        with connection:
            connection.execute(USERS_SCHEMA)
            connection.execute(TODOS_SCHEMA)
            connection.execute(WORKSPACES_SCHEMA)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_todos_user_id ON todos(user_id)"
            )


def migrate_auth(database_path: DatabasePath) -> None:
    with closing(connect(database_path)) as connection:
        # BEGIN으로 스키마 변경 전체를 하나의 트랜잭션으로 묶는다.
        connection.execute("BEGIN IMMEDIATE")
        with connection:
            connection.execute(USERS_SCHEMA)
            columns = connection.execute("PRAGMA table_info(todos)").fetchall()
            if not columns:
                connection.execute(TODOS_SCHEMA)
            elif "user_id" not in {row["name"] for row in columns}:
                connection.execute(
                    "ALTER TABLE todos ADD COLUMN user_id INTEGER REFERENCES users(id)"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_todos_user_id ON todos(user_id)"
            )


def get_connection(request: Request) -> Iterator[sqlite3.Connection]:
    # 요청마다 연결을 만들고 응답 후 닫는다.
    with closing(connect(request.app.state.database_path)) as connection:
        with connection:
            yield connection
