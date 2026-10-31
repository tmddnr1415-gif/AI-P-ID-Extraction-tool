"""L56 — LOGIC 작도 묶음: 여러 장의 FROM/TO 가 이어지고, 매크로가 Typical 시트와 이어지고, 노트 · 설정값 · 선 글이 인쇄되어
분석기가 그대로 읽는다.  학습한 양식(크기)은 기호 사전에 얹힌다.  판정 코드는 verify 만 분석기를 **그대로** 부른다.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import draw, draw_sets


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from app.logic import api
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _mk(client, name, **kw):
    r = client.post("/logic/api/drawings", json={"name": name, "author": "홍길동", **kw})
    assert r.status_code == 200
    return r.json()


def _put(client, doc, **extra):
    r = client.put(f"/logic/api/drawings/{doc['id']}", json={"author": "홍길동", "doc": doc, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def _wire(pts, **kw):
    return {"id": "", "pts": [list(p) for p in pts], **kw}


def _three_sheet_set(client):
    """주 장 G001 (매크로 → 출력 51행 TO G002-2) · Typical T001 (AOPEN · ACLOSE → AND → CMD) · 받는 장 G002."""
    N = draw.N_DEFAULT
    ry = lambda n: draw.ry(n, N)
    main = _mk(client, "MAIN")
    main["sheet_no"], main["title"], main["doc_no"] = "G001", "MAIN SHEET", "1-1"
    main = _put(client, main, set="", set_name="")                      # 바깥 몸통의 set 칸 — 없으면 그대로
    sid = "abc123def456"
    main = _put(client, main, set=sid, set_name="시험 묶음", order=1)
    assert main["set"] == sid and main["set_name"] == "시험 묶음"        # put 의 바깥 몸통 set 칸이 저장된다 (화면 set-make)
    # Typical
    r = client.post(f"/logic/api/drawings/sets/{sid}/sheet", json={"author": "홍길동", "name": "MOV TYPICAL", "sheet_no": "T001", "typical": True})
    assert r.status_code == 200
    typ = r.json()
    assert typ["typical"] and typ["set"] == sid and typ["order"] == 2
    typ["title"], typ["doc_no"] = "MOV BLOCK (OPEN CLOSE) <TYPE-III-1>", "1-2"
    typ["left"] = {"1": {"fm": "", "kks": "AOPEN", "desc": "AUTO OPEN"}, "2": {"fm": "", "kks": "ACLOSE", "desc": "AUTO CLOSE"}}
    typ["right"] = {str(N + 1): {"desc": "OPEN COMMAND", "kks": "CMD", "to": ""}}
    ymid = (ry(1) + ry(2)) / 2
    sp = draw.SYMBOLS["AND"]
    typ["blocks"] = [{"id": "a1", "kind": "AND", "x": 500, "y": round(ymid - sp["h"] / 2, 2), "w": sp["w"], "h": sp["h"], "text": "AND", "param": {}}]
    typ["wires"] = [_wire([(320, ry(1)), (500, ry(1))]), _wire([(320, ry(2)), (500, ry(2))]),
                    _wire([(500 + sp["w"], ymid), (700, ymid), (700, ry(N + 1)), (870, ry(N + 1))])]
    typ = _put(client, typ)
    # 매크로 타입 — 묶음의 Typical 에서
    info = client.get(f"/logic/api/drawings/sets/{sid}").json()
    ms = [m for m in info["macros"] if m["typ"] == "T001"]
    assert ms and [p["name"] for p in ms[0]["pins_in"]] == ["AOPEN", "ACLOSE"] and [p["name"] for p in ms[0]["pins_out"]] == ["CMD"]
    m = ms[0]
    mb = draw.macro_block(m["title"], "T001", m["pins_in"], m["pins_out"], 480, ry(5) - draw.MACRO_TOP - 0.5 * draw.PITCH)
    main["left"] = {"5": {"fm": "", "kks": "", "desc": "PB OPEN"}, "6": {"fm": "", "kks": "", "desc": "PB CLOSE"}}
    main["right"] = {str(N + 1): {"desc": "MOV OPEN CMD", "kks": "", "to": "G002-2"}}
    ports = {p[3]: p for p in draw.ports_of(mb)}
    main["blocks"] = [mb]
    main["wires"] = [_wire([(320, ry(5)), (ports["AOPEN"][0], ports["AOPEN"][1])]),
                     _wire([(320, ry(6)), (ports["ACLOSE"][0], ports["ACLOSE"][1])]),
                     _wire([(ports["CMD"][0], ports["CMD"][1]), (800, ports["CMD"][1]), (800, ry(N + 1)), (870, ry(N + 1))])]
    main = _put(client, main)
    r = client.post(f"/logic/api/drawings/sets/{sid}/sheet", json={"author": "홍길동", "name": "RECEIVER", "sheet_no": "G002"})
    rx = r.json()
    rx["doc_no"] = "1-3"
    rx = _put(client, rx)
    return sid, main, typ, rx


def test_autolink_fills_the_receiving_sheet_and_links_judge_consistent(client):
    sid, main, typ, rx = _three_sheet_set(client)
    r = client.post(f"/logic/api/drawings/sets/{sid}/autolink", json={"author": "홍길동", "did": main["id"]})
    assert r.status_code == 200
    rx2 = client.get(f"/logic/api/drawings/{rx['id']}").json()
    assert rx2["left"]["2"]["fm"] == "G001-51" and rx2["left"]["2"]["desc"] == "MOV OPEN CMD"      # 받는 장의 빈 칸이 채워진다
    links = client.get(f"/logic/api/drawings/sets/{sid}/links").json()
    L = links["docs"][rx2["id"]]["left"]["2"]
    assert L["ref"]["sheet"] == "G001" and L["ref"]["did"] == main["id"] and L["ft"]["ok"] is True
    R = links["docs"][main["id"]]["right"][str(draw.N_DEFAULT + 1)]
    assert R["targets"][0]["did"] == rx2["id"] and not [f for f in links["findings"] if f["code"] == "FT_MISMATCH"]
    # 상대 칸을 다른 곳으로 적으면 분석기 판정이 불일치를 말한다
    rx2["left"]["2"]["fm"] = "G001-52"
    _put(client, rx2)
    links = client.get(f"/logic/api/drawings/sets/{sid}/links").json()
    assert links["docs"][rx2["id"]]["left"]["2"]["ft"]["ok"] is False


@pytest.mark.slow
def test_set_round_trips_macro_to_typical_through_the_analyser(client):
    sid, main, typ, rx = _three_sheet_set(client)
    client.post(f"/logic/api/drawings/sets/{sid}/autolink", json={"author": "홍길동", "did": main["id"]})
    v = client.post(f"/logic/api/drawings/sets/{sid}/verify").json()
    assert v["ok"] and v["read"] == 3 and v["fromto_bad"] == 0
    mac = [b["macro"] for sh in v["sheets"] for b in sh.get("blocks", []) if b["kind"] == "MACRO"]
    assert mac and mac[0]["sheet"] == "T001" and mac[0]["pins_drawn"] == 3 and mac[0]["pins"] == 3
    pdf = client.get(f"/logic/api/drawings/sets/{sid}/export.pdf").content
    assert pdf[:4] == b"%PDF"


def test_set_routes_come_before_single_drawing_routes(client):
    assert client.get("/logic/api/drawings/sets").json() == {"items": []}
    assert client.get("/logic/api/drawings/sets/zzz").status_code == 404


def test_notes_above_text_and_wire_label_are_printed_and_read(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from app.logic import analog, analyse
    N = draw.N_DEFAULT
    ry = lambda n: draw.ry(n, N)
    doc = draw.new_doc("노트", "홍길동")
    doc["sheet_no"], doc["doc_no"], doc["title"] = "G001", "19VA-00GEN00-J09-0001", "NOTES TEST"
    doc["notes"] = ['OUTPUT STATE IS INVERTED BY EACH MOMENTARY TRUE SIGNAL ON "SRST"', "둘째 노트", ""]
    doc["left"] = {"1": {"fm": "", "kks": "00PAB10CP001", "desc": "PRESSURE"}, "2": {"fm": "", "kks": "", "desc": "START"}}
    doc["right"] = {str(N + 1): {"desc": "OUT A", "kks": "", "to": ""}, str(N + 2): {"desc": "OUT B", "kks": "", "to": ""}}
    doc["blocks"] = [{"id": "b1", "kind": "BOX", "x": 420, "y": ry(1) - 4.5, "w": 16, "h": 9, "text": "HH/", "param": {"above": "202.4 barg"}},
                     {"id": "b2", "kind": "GT", "x": 500, "y": ry(2) - 4.5, "w": 16, "h": 9, "param": {"t": 3, "above": "주석"}}]
    doc["wires"] = [_wire([(320, ry(1)), (420, ry(1))], label="0~250 barg"), _wire([(436, ry(1)), (870, ry(1))]),
                    _wire([(320, ry(2)), (500, ry(2))]), _wire([(516, ry(2)), (870, ry(2))])]
    c = draw.clean(doc)
    assert c["notes"] == doc["notes"][:2] and c["blocks"][0]["param"]["above"] == "202.4 barg" and c["wires"][0]["label"] == "0~250 barg"
    assert any(t[2] == "202.4 barg" for t in draw.block_geometry(c["blocks"][0])["texts"])
    pdf = tmp_path / "n.pdf"
    pdf.write_bytes(draw.to_pdf(doc))
    import pymupdf
    words = " ".join(w[4] for w in pymupdf.open(str(pdf))[0].get_text("words"))
    assert "NOTES" in words and '"SRST"' in words and "2. 둘째" in words and "0~250" in words
    assert b"SECTION" in draw.to_dxf(doc)
    v = draw.verify(doc)
    assert v["ok"] and {b["id"]: b["ok"] for b in v["blocks"]} == {"b1": True, "b2": True} and v["dangling"] == 0
    res = analyse.analyse(str(pdf))
    s = res["sheets"][0]
    gt = next(b for b in s["blocks"].values() if b.get("logic") == "delay_on")
    assert gt["param"]["t"] == 3                                        # 위 글이 타이머 시간을 흔들지 않는다
    analog.read_drawing(str(pdf), res["sheets"])
    mon = next(b for b in s["blocks"].values() if b.get("func") == "SIGNAL MONITOR")
    assert mon["param"]["sp"] == 202.4 and mon["param"]["sp_unit"] == "barg"       # 설정값이 시뮬레이션 초기값으로
    row1 = next(r for r in s["rows"] if r["side"] == "L" and r["n"] == 1)
    assert row1.get("range") and row1["range"]["lo"] == 0 and row1["range"]["hi"] == 250


def test_style_is_applied_in_pitch_units_and_restores():
    base = {k: (v["w"], v["h"]) for k, v in draw.SYMBOLS.items()}
    try:
        draw.apply_style({"sizes": {"AND": {"w_p": 2.0, "h_p": 1.0, "n": 3}}})
        assert draw.SYMBOLS["AND"]["w"] == round(2.0 * draw.PITCH, 1) and draw.SYMBOLS["AND"]["h"] == round(1.0 * draw.PITCH, 1)
    finally:
        draw.apply_style(draw.load_style())
    st = draw.load_style()
    assert st and "sizes" in st and set(st["sizes"]) >= {"AND", "OR", "NOT", "GT", "MEMORY", "PB", "CONN"}
    for k, (w, h) in base.items():
        assert (draw.SYMBOLS[k]["w"], draw.SYMBOLS[k]["h"]) == (w, h)


def test_from_sheet_mends_corner_gaps_and_marks_junction_dots():
    P = draw.PITCH
    segs = [[400, 100, 500, 100], [500.8, 100.9, 500.8, 150], [400, 150, 600, 150]]      # 모서리 틈 · 아래 선 몸통에 T 자
    out = draw._mend(segs, [(400, 100), (400, 150), (600, 150)])
    pts = {(round(a, 1), round(b, 1)) for s in out for a, b in ((s[0], s[1]), (s[2], s[3]))}
    ends = [(s[0], s[1]) for s in out] + [(s[2], s[3]) for s in out]
    assert any(abs(a - 500.8) < 1.0 and abs(b - 100) < 1.0 for a, b in ends)        # 꺾인 모서리가 만난다 (세로선의 위 끝이 가로선 끝으로)
    assert len(out) >= 3
