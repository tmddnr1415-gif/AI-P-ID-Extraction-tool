"""3D 계측제어 화면 /ic3d — 세션 7 화면을 옮겨 와 그대로 준다 (공통 띠 없음 · 대시보드 iframe)."""
import subprocess

from fastapi.testclient import TestClient

from app import paths
from app.main import app

c = TestClient(app)


def test_redirect_keeps_query():
    r = c.get("/ic3d?embed=1", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/ic3d/?embed=1"


def test_page_served_unchanged_without_shell():
    r = c.get("/ic3d/?embed=1")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    src = paths.resource("app", "static", "ic3d", "index.html").read_bytes()
    assert r.content == src
    assert b"/static/shell.js" not in r.content and b"pidUpdateTag" not in r.content


def test_side_file_and_unknown():
    assert c.get("/ic3d/viewer-real.html").status_code == 200
    assert c.get("/ic3d/server.py").status_code == 404
    assert c.get("/ic3d/../main.py").status_code == 404


def test_not_in_offline_shell():
    assert not any("ic3d" in u for u in c.get("/offline/shell").json()["urls"])


def test_imported_matches_release_sources():
    import json
    rs = json.loads(paths.resource("config", "release_sources.json").read_text(encoding="utf-8"))
    ic = rs["sources"]["IC3D"]
    assert ic["branch"] == "claude/practical-newton-n6bt58" and ic["imported"]
    for f in ("index.html", "viewer-real.html"):
        try:
            orig = subprocess.run(["git", "show", f"{ic['imported']}:app/{f}"], capture_output=True, check=True).stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return                              # 커밋이 없는 사본(회사 PC)에서는 건너뜀
        assert orig == paths.resource("app", "static", "ic3d", f).read_bytes()
