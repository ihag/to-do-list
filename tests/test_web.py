from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_web_page_and_assets(raw_client):
    response = raw_client.get("/")
    assert response.status_code == 200
    assert "TaskFlow" in response.text
    assert "text/html" in response.headers["content-type"]
    assert raw_client.get("/styles.css").status_code == 200
    assert raw_client.get("/missing.css").status_code == 404
    assert raw_client.get("/.env").status_code == 404
    assert raw_client.get("/todos.sqlite3").status_code == 404
    assert raw_client.get("/%2e%2e/.env").status_code == 404


def test_workspace_behavior():
    result = subprocess.run(
        ["node", str(ROOT / "tests" / "web_store_test.cjs")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_web_assets():
    html = (ROOT / "web" / "index.html").read_text()
    for asset in ("styles.css", "store.js", "app.js"):
        assert asset in html
        assert (ROOT / "web" / asset).is_file()
    assert 'lang="ko"' in html
    assert "line-through" in (ROOT / "web" / "styles.css").read_text()
