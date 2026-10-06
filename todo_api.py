"""기존 uvicorn todo_api:app 실행 경로를 유지한다."""

from app.main import app

__all__ = ["app"]
