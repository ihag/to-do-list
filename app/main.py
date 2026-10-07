from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.config import Settings, load_settings
from app.db import DB_PATH, DatabasePath, initialize_database, configured_database
from app.routers import auth, todos, workspaces
from app.security import (
    RequestBodyLimitMiddleware,
    security_headers,
    validation_error_response,
)


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
    application.add_middleware(RequestBodyLimitMiddleware)
    application.add_exception_handler(RequestValidationError, validation_error_response)
    application.middleware("http")(security_headers)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://ihag.github.io",
            "http://127.0.0.1:8080",
            "http://localhost:8080",
        ],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.include_router(auth.router)
    application.include_router(todos.router)
    application.include_router(workspaces.router)
    application.mount(
        "/",
        StaticFiles(directory=Path(__file__).resolve().parents[1] / "web", html=True),
        name="web",
    )
    return application


app = create_app(configured_database())
