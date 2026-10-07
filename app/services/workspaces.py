import json

from fastapi import HTTPException

from app.models.workspace import Workspace, WorkspaceWrite


def get_workspace(connection, user_id):
    # 최초 로그인만 빈 워크스페이스를 만든다. 기존 데이터는 덮어쓰지 않는다.
    connection.execute(
        "INSERT INTO workspaces (user_id, revision, state) VALUES (?, 0, ?) "
        "ON CONFLICT (user_id) DO NOTHING",
        (user_id, '{"version":1,"topics":[]}'),
    )
    row = connection.execute(
        "SELECT revision, state FROM workspaces WHERE user_id = ?", (user_id,)
    ).fetchone()
    return Workspace(revision=row["revision"], state=json.loads(row["state"]))


def save_workspace(connection, user_id, body: WorkspaceWrite):
    get_workspace(connection, user_id)
    # 버전 비교와 저장을 한 문장으로 실행해 동시 변경의 덮어쓰기를 막는다.
    row = connection.execute(
        "UPDATE workspaces SET state = ?, revision = revision + 1 "
        "WHERE user_id = ? AND revision = ? RETURNING revision",
        (body.state.model_dump_json(exclude_none=True), user_id, body.revision),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=409, detail="Workspace changed on another device")
    return Workspace(revision=row["revision"], state=body.state)
