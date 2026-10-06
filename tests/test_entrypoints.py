from app.main import app
from main import app as main_app
from todo_api import app as todo_app


def test_all_entrypoints_use_authenticated_app():
    assert main_app is todo_app is app
    paths = app.openapi()["paths"]
    for path in ("/todos", "/todos/{id}/toggle", "/todos/{id}"):
        for operation in paths[path].values():
            assert operation["security"] == [{"HTTPBearer": []}]
