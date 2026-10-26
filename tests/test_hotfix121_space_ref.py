"""hotfix121 — 판넬 화면 10-26 판(d890bb5): Ref. PJT Room Layout 자료(ref.js)를 같은 서버가 준다."""
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def test_screen_loads_ref_from_static_and_keeps_our_adaptations():
    s = (ROOT / "app/static/space/index.html").read_text(encoding="utf-8")
    assert '<script src="/static/space/ref.js"></script>' in s     # /space 는 끝 빗금이 없어 상대 경로면 /ref.js 가 된다
    assert '<script src="/static/offline.js" data-app="space"></script>' in s
    assert "confirm(" not in s and "prompt(" not in s               # 대시보드 iframe 은 막는다
    assert "if(!AUTH_TOKEN)" not in s
    assert "await preflight(" in s


def test_ref_js_is_served():
    from app import main
    c = TestClient(main.app)
    r = c.get("/static/space/ref.js")
    assert r.status_code == 200 and "window.CRSPACE_REF" in r.text
