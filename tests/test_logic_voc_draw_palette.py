"""VOC (2026-10-30 · LOGIC 작도) — 매크로가 보이지 않음 · 기호/글자 상자가 잘려 보임.

* 매크로 팔레트는 묶음에 들지 않은 그림에도 공통 Typical 사전(처음부터 들고 있는 씨앗)을 보인다.
* 팔레트 칸은 셋째 칸이 카드 밖으로 넘치지 않는다 (minmax(0, 1fr)).
"""
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent


def test_macros_without_a_set_come_from_the_typical_library(monkeypatch):
    monkeypatch.delenv("PID_TYPICAL_SEED", raising=False)
    from app.main import app
    ms = TestClient(app).get("/logic/api/drawings/macros").json()["items"]      # L79 이 같은 주소를 items 로 (옛 VOC 는 macros)
    assert len(ms) >= 20
    assert all(m["typ"].startswith("lib:") and m["pins_in"] and m["pins_out"] for m in ms)


def test_set_typical_is_not_listed_twice():
    from app.logic import draw_sets, library
    lib = library.typicals()
    if not lib:
        return
    tid, ty = next(iter(lib.items()))
    sheet_no = (ty.get("sheet") or {}).get("sheet_no") or ty.get("sheet_no")
    doc = {"id": "x", "typical": True, "sheet_no": sheet_no, "title": "T", "left": {"1": {"desc": "A"}}, "right": {"51": {"desc": "B"}}}
    ms = draw_sets.macro_types([doc])
    assert sum(1 for m in ms if (m.get("sheet") or {}).get("sheet_no") == sheet_no and m["typ"].startswith("lib:")) == 0


def test_palette_columns_do_not_overflow():
    css = (ROOT / "app/static/logic_draw.css").read_text(encoding="utf-8")
    assert "repeat(2, minmax(0, 1fr))" in css
    js = (ROOT / "app/static/logic_draw.js").read_text(encoding="utf-8")
    assert "function fitIcon" in js and "/logic/api/drawings/macros" in js
