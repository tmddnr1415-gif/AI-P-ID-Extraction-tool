"""L91 — 매크로를 이 프로젝트에만 고치기: 기호 창에서 공통 사전 매크로를 두 번 눌러 '이 프로젝트에서 열기' 하면
그 Typical 장을 묶음(프로젝트)에 사본으로 들여와 연다 · 고쳐 저장해도 공통 사전과 다른 프로젝트는 그대로.

화면 흐름(두 번 누름 → 새 창 → 시뮬레이션 → 시간 고침 → 저장)은 `spike/ui_human_draw_l86.py` 의 L91 단계가 브라우저로 본다."""
from pathlib import Path

from tests.test_logic_l87_find import _client, _set_of_two


def _sig(items):
    return [(a["id"], a.get("edited"), a.get("origin"), a.get("blocks")) for a in items]


def test_project_copy_of_common_typical_saves_only_in_project(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_TYPICAL_SEED", "1")                       # 공통 Typical 씨앗을 켠다 (L63 시험과 같이)
    c = _client(tmp_path, monkeypatch)
    sid, d1, _ = _set_of_two(c)
    typ0 = c.get("/logic/api/drawings/typicals").json()["items"]
    tid = next(t["id"] for t in typ0 if t["pins_in"] and t["pins_out"] and "SOV" in t["title"])
    # 기호 창이 부르는 그 길 — 묶음에 사전 Typical 장을 들여온다
    r = c.post(f"/logic/api/drawings/sets/{sid}/sheet", json={"library": tid, "author": "t"})
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["set"] == sid and doc["typical"] and doc["source"]["library"] == tid
    info = c.get(f"/logic/api/drawings/sets/{sid}").json()
    assert any(m["did"] == doc["id"] for m in info["macros"])        # 이 묶음의 매크로로 보인다
    # 시간 기호 하나를 고쳐 저장
    b = next(b for b in doc["blocks"] if (b.get("param") or {}).get("t") is not None)
    b["param"]["t"] = float(b["param"]["t"]) + 5
    c.put(f"/logic/api/drawings/{doc['id']}", json={"author": "t", "doc": doc})
    got = c.get(f"/logic/api/drawings/{doc['id']}").json()
    assert next(x for x in got["blocks"] if x["id"] == b["id"])["param"]["t"] == b["param"]["t"]
    assert _sig(c.get("/logic/api/drawings/typicals").json()["items"]) == _sig(typ0)   # 공통 사전은 그대로


def test_palette_offers_project_scope_and_main_reloads_set():
    root = Path(__file__).resolve().parents[1] / "app" / "static"
    pal = (root / "logic_draw_palette.js").read_text(encoding="utf-8")
    main = (root / "logic_draw.js").read_text(encoding="utf-8")
    assert "이 프로젝트에서 열기" in pal and "공통 사전을 고치기" in pal
    assert "/logic/api/drawings/sets/" in pal and 't: "setchanged"' in pal
    assert 'm.t === "setchanged"' in main and "set: S.doc.set || null" in main
