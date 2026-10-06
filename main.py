"""기존 uvicorn main:app도 인증이 적용된 앱을 사용한다."""

from app.main import app

__all__ = ["app"]
