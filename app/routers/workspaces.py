from fastapi import APIRouter, Depends, Response

from app.db import get_connection
from app.models.auth import User
from app.models.workspace import Workspace, WorkspaceWrite
from app.services.auth import get_current_user
from app.services.workspaces import get_workspace, save_workspace


router = APIRouter(tags=["workspaces"])


@router.get("/users/me", response_model=User)
def current_user(response: Response, user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return user


@router.get(
    "/workspaces/current", response_model=Workspace, response_model_exclude_none=True
)
def read_workspace(
    response: Response,
    user: User = Depends(get_current_user),
    connection=Depends(get_connection),
):
    response.headers["Cache-Control"] = "no-store"
    return get_workspace(connection, user.id)


@router.put(
    "/workspaces/current", response_model=Workspace, response_model_exclude_none=True
)
def write_workspace(
    body: WorkspaceWrite,
    response: Response,
    user: User = Depends(get_current_user),
    connection=Depends(get_connection),
):
    response.headers["Cache-Control"] = "no-store"
    return save_workspace(connection, user.id, body)
