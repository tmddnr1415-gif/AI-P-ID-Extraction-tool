"""L79 — Logic 작성 첫 화면 · 매크로(Typical) 팔레트 · 매크로 내부 열기 · 신호 처리 메뉴."""
import os
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from app import main
    return TestClient(main.app)


def test_macros_without_a_set_come_from_the_common_dictionary(tmp_path, monkeypatch):
    os.environ.pop("PID_TYPICAL_SEED", None)
    monkeypatch.setenv("PID_TYPICAL_SEED", "1")
    c = _client(tmp_path, monkeypatch)
    r = c.get("/logic/api/drawings/macros")
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "묶음이 없어도 공통 Typical 사전의 타입이 팔레트에 선다"
    assert all(m["typ"].startswith("lib:") and m.get("tid") and "origin" in m for m in items)
    assert any(m["origin"] == "19VA" for m in items)


def test_page_has_home_palette_and_signal_menu():
    html = (ROOT / "app/static/logic_draw.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/logic_draw.js").read_text(encoding="utf-8")
    for k in ('id="home"', 'id="home-btn"', 'id="sig-link"', 'data-act="signal"', 'id="h-project"', 'id="macro-q"'):
        assert k in html
    for k in ("function showHome", "function renderHome", "function macroThumb", "function openMacroInside", "/logic/api/drawings/macros"):
        assert k in js
    # 매크로를 두 번 누르면 내부 동작(새 창) — 그림의 블록에서도
    assert "openMacroInside(macroOfBlock(b0))" in js
    idx = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    assert 'id="nav-logic-signal"' in idx and 'href="/logic/signal"' in idx
