from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import Settings, load_settings
from app.db import DB_PATH, DatabasePath, initialize_database
from app.routers import auth, todos


@asynccontextmanager
async def lifespan(app: FastAPI):
    if app.state.settings is None:
        app.state.settings = load_settings()
    initialize_database(app.state.database_path)
    yield


def create_app(
    database_path: DatabasePath = DB_PATH, settings: Optional[Settings] = None
) -> FastAPI:
    application = FastAPI(title="TaskFlow API", lifespan=lifespan)
    application.state.database_path = database_path
    application.state.settings = settings
    application.include_router(auth.router)
    application.include_router(todos.router)
    application.mount(
        "/",
        StaticFiles(directory=Path(__file__).resolve().parents[1] / "web", html=True),
        name="web",
    )
    return application


app = create_app()
