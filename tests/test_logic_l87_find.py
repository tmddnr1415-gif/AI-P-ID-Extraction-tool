"""L87 — draw.io 에서 배운 '찾기'(Ctrl+F · 묶음 전체) 의 서버 쪽: GET /logic/api/drawings/sets/{sid}/search.

화면 쪽(이 장 · 저장 안 한 변경 · 고르개 · 미니맵 · 메뉴 · 끌어 선 …)은 `spike/ui_human_draw_l86.py` 의 L87 단계가 브라우저로 본다
(`tests/test_logic_l86_human_draw.py`, `-m ui`)."""


def _client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PID_DRAW_SEED", "0")
    from app import main
    return TestClient(main.app)


def _set_of_two(c):
    a = c.post("/logic/api/drawings", json={"name": "A", "author": "t", "sheet_no": "FG_G-301", "title": "BFP A START"}).json()
    sid = "a1b2c3d4e5f6"
    a.update({"set": sid, "set_name": "펌프", "order": 1,
              "left": {"1": {"kks": "10LAC10 CP001", "desc": "BFP A START PB"}},
              "right": {str(a["N"] + 1): {"desc": "BFP A START CMD", "to": "FG_G-302-1"}},
              "blocks": [{"id": "b1", "kind": "GT", "x": 400, "y": 70, "w": 17.5, "h": 11.3, "text": "GT", "label": "", "param": {"t": 2, "above": "T = 2 s"}}],
              "wires": [{"id": "w1", "pts": [[320, 75.65], [400, 75.65]], "label": "0~250 barg"}], "notes": ["START PERMISSIVE"]})
    c.put(f"/logic/api/drawings/{a['id']}", json={"author": "t", "doc": a, "set": sid, "set_name": "펌프"})
    r = c.post(f"/logic/api/drawings/sets/{sid}/sheet", json={"sheet_no": "FG_G-302", "name": "B", "author": "t"}).json()
    r.update({"left": {"1": {"fm": "FG_G-301-60", "desc": "BFP A START CMD"}}})
    c.put(f"/logic/api/drawings/{r['id']}", json={"author": "t", "doc": r})
    return sid, a["id"], r["id"]


def test_set_search_finds_text_on_every_sheet(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    sid, d1, d2 = _set_of_two(c)
    hits = c.get(f"/logic/api/drawings/sets/{sid}/search", params={"q": "start cmd"}).json()["hits"]
    where = {(h["sheet_no"], h["where"]) for h in hits}
    assert ("FG_G-301", "오른쪽 1행 설명") in where and ("FG_G-302", "왼쪽 1행 설명") in where
    assert hits[0]["did"] == d1                                    # 장 차례대로
    # 공백 · 대소문자 무시 (TAG 를 붙여 써도 띄어 써도)
    tag = c.get(f"/logic/api/drawings/sets/{sid}/search", params={"q": "10lac10cp001"}).json()["hits"]
    assert [h["where"] for h in tag] == ["왼쪽 1행 TAG"] and tag[0]["n"] == 1
    # 기호 위 글 · 선 아래 글 · NOTE · FROM
    for q, kind in (("T = 2", "block"), ("250 BARG", "wire"), ("permissive", "note"), ("FG_G-301-60", "row")):
        hs = c.get(f"/logic/api/drawings/sets/{sid}/search", params={"q": q}).json()["hits"]
        assert hs and hs[0]["kind"] == kind, (q, hs)
    assert hs[0]["did"] == d2
    assert c.get(f"/logic/api/drawings/sets/{sid}/search", params={"q": ""}).json()["hits"] == []
    assert c.get("/logic/api/drawings/sets/ffffffffffff/search", params={"q": "x"}).status_code == 404


def test_set_search_limit(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    sid, _, _ = _set_of_two(c)
    r = c.get(f"/logic/api/drawings/sets/{sid}/search", params={"q": "BFP", "limit": 2}).json()
    assert len(r["hits"]) == 2 and r["more"] is True


def test_palette_window_page_and_channel(tmp_path, monkeypatch):
    """L88 — 기호 · 매크로 창: 페이지가 서고, 그림 창과 같은 BroadcastChannel 이름 · 같은 말(pick · state · items)을 쓴다."""
    from pathlib import Path
    c = _client(tmp_path, monkeypatch)
    r = c.get("/logic/draw/palette")
    assert r.status_code == 200 and "logic_draw_palette.js" in r.text
    root = Path(__file__).resolve().parents[1] / "app" / "static"
    main, pal = (root / "logic_draw.js").read_text(encoding="utf-8"), (root / "logic_draw_palette.js").read_text(encoding="utf-8")
    assert 'BroadcastChannel("logic.draw.palette")' in main and 'BroadcastChannel("logic.draw.palette")' in pal
    for t in ('t: "pick"', 't: "inside"', 't: "cancel"', 't: "hello"', 't: "alive"'):
        assert t in pal
    for t in ('t: "items"', 't: "state"', 'm.t === "pick"', 'm.t === "inside"', 'm.t === "cancel"'):
        assert t in main
    css = (root / "logic_draw.css").read_text(encoding="utf-8")
    assert ".dw-toast { pointer-events: none;" in css          # 알림이 그림 위의 누르기를 가로채지 않게
