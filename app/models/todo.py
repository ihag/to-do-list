from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Todo(BaseModel):
    id: int
    title: str
    done: bool = False
    due: Optional[date] = None


class TodoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # 제목 누락은 라우터에서 400으로 처리한다.
    title: Optional[str] = None
    due: Optional[date] = None
