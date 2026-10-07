from pathlib import Path
import subprocess
import struct
import xml.etree.ElementTree as ET

import pytest


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


@pytest.mark.parametrize(
    "code",
    [
        "1f4cb", "1f4bc", "1f33f", "1f3e0", "1f3af", "1f4da", "1f4a1", "1f4bb",
        "1f3a8", "1f4aa", "2708", "1f6d2", "1f3b5", "2764", "2b50", "2615",
    ],
)
def test_emoji_assets_available_and_safe(raw_client, code):
    image = raw_client.get(f"/emojis/{code}.png")
    assert image.status_code == 200
    assert image.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", image.content[16:24]) == (256, 256)
    response = raw_client.get(f"/emojis/{code}.svg")
    assert response.status_code == 200
    svg = ET.fromstring(response.content)
    assert svg.tag == "{http://www.w3.org/2000/svg}svg"
    assert svg.attrib["preserveAspectRatio"] == "xMidYMid meet"
    _, _, width, height = map(float, svg.attrib["viewBox"].split())
    assert width > 0 and height > 0
    assert not svg.findall(".//{http://www.w3.org/2000/svg}script")
    assert not svg.findall(".//{http://www.w3.org/2000/svg}image")


def test_emoji_license_available(raw_client):
    assert raw_client.get("/emojis/NOTICE.txt").status_code == 200
    assert raw_client.get("/emojis/LICENSE-GRAPHICS.txt").status_code == 200
    assert raw_client.get("/emojis/missing.svg").status_code == 404
