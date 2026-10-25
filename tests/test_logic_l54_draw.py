"""L54 — LOGIC 작도: 그린 것을 PDF 로 내보내 분석기에 다시 넣으면 같은 블록 · 선 · 행이 나온다 (되읽기).

* 기호 사전의 모든 종류(글 주석 빼고)를 한 장에 놓고 행과 잇는다 → analyse 가 종류 · 입출력 수 · 행 글 · 시트 이름을 그대로 읽는다
* DXF 는 ezdxf 로 다시 열린다 (층 · 선 · 글)
* 저장 · 목록 · 지우기 · 작성자 필수 · 사람이 보낸 그림의 모양 맞추기(clean)
* 분석한 시트 → 그림 (from_sheet) → 다시 되읽기
* 작도 모듈은 P&ID 엔진을 부르지 않는다 (test_logic_review 의 AST 시험이 app/logic 전체를 본다)
"""
from __future__ import annotations

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import analyse, draw


def _doc():
    P = draw.PITCH
    N = 50
    ry = lambda n: draw.ry(n, N)
    doc = draw.new_doc("시험", "tester", N=N)
    doc["sheet_no"], doc["title"], doc["doc_no"] = "LD-001", "ROUND TRIP", "19VA-00GEN00-J09-9999"
    L, R = doc["left"], doc["right"]
    for n, (fm, desc) in {2: ("HMI", "PUMP A RUN"), 3: ("HMI", "PUMP B RUN"), 5: ("", "LEVEL LOW"), 7: ("", "TX A"), 8: ("", "TX B"),
                          9: ("", "TX C"), 11: ("", "SET"), 12: ("", "RESET"), 14: ("", "FLOW"), 16: ("", "ORA"), 17: ("", "ORB"),
                          19: ("", "NANDA"), 20: ("", "NANDB"), 22: ("", "DTIN"), 24: ("", "PDIN"), 26: ("", "CONNIN"),
                          28: ("", "NORA"), 29: ("", "NORB"), 31: ("", "ANNIN"), 33: ("", "SOEIN")}.items():
        L[str(n)] = {"fm": fm, "kks": "", "desc": desc}
    for n, (desc, to) in {51: ("BOTH RUN", "LD-002/2"), 52: ("LOW 3S", ""), 53: ("2OO3", ""), 54: ("LATCHED", ""), 55: ("NOT FLOW", ""),
                          56: ("OR OUT", ""), 57: ("NAND OUT", ""), 58: ("DT OUT", ""), 59: ("PD OUT", ""), 60: ("PB OUT", ""),
                          61: ("CONN OUT", ""), 62: ("NOR OUT", "")}.items():
        R[str(n)] = {"desc": desc, "kks": "", "to": to}
    B, Wn = doc["blocks"], doc["wires"]

    def blk(kind, x, ymid, **kw):
        spec = draw.SYMBOLS[kind]
        h, w = kw.pop("h", spec["h"]), kw.pop("w", spec["w"])
        b = {"id": f"b{len(B) + 1}", "kind": kind, "x": x, "y": round(ymid - h / 2, 2), "w": w, "h": h, "text": spec["text"],
             "label": kw.pop("label", ""), "param": kw.pop("param", {})}
        B.append(b)
        return b

    def wire(*pts, dashed=False):
        Wn.append({"id": f"w{len(Wn) + 1}", "pts": [list(p) for p in pts], "dashed": dashed})
    LX0, LX1 = draw.LX0, draw.LX1
    b = blk("AND", 500, (ry(2) + ry(3)) / 2); wire((LX0, ry(2)), (500, ry(2))); wire((LX0, ry(3)), (500, ry(3)))
    wire((516, b["y"] + 4.5), (700, b["y"] + 4.5), (700, ry(51)), (LX1, ry(51)))
    blk("GT", 500, ry(5), param={"t": 3}); wire((LX0, ry(5)), (500, ry(5))); wire((516, ry(5)), (710, ry(5)), (710, ry(52)), (LX1, ry(52)))
    blk("VOTE", 520, ry(8), param={"a": 2, "b": 3})
    for n in (7, 8, 9):
        wire((LX0, ry(n)), (520, ry(n)))
    wire((536, ry(8)), (720, ry(8)), (720, ry(53)), (LX1, ry(53)))
    blk("MEMORY", 540, (ry(11) + ry(12)) / 2, h=2 * P, param={"dominant": "set"})
    wire((LX0, ry(11)), (540, ry(11))); wire((LX0, ry(12)), (540, ry(12)))
    wire((552, ry(11)), (730, ry(11)), (730, ry(54)), (LX1, ry(54)))
    blk("NOT", 500, ry(14)); wire((LX0, ry(14)), (500, ry(14))); wire((516, ry(14)), (740, ry(14)), (740, ry(55)), (LX1, ry(55)))
    b = blk("OR", 500, (ry(16) + ry(17)) / 2); wire((LX0, ry(16)), (500, ry(16))); wire((LX0, ry(17)), (500, ry(17)))
    wire((516, b["y"] + 4.5), (750, b["y"] + 4.5), (750, ry(56)), (LX1, ry(56)))
    b = blk("NAND", 500, (ry(19) + ry(20)) / 2); wire((LX0, ry(19)), (500, ry(19))); wire((LX0, ry(20)), (500, ry(20)))
    wire((518, b["y"] + 4.5), (760, b["y"] + 4.5), (760, ry(57)), (LX1, ry(57)))
    blk("DT", 500, ry(22), param={"t": 4}); wire((LX0, ry(22)), (500, ry(22))); wire((516, ry(22)), (770, ry(22)), (770, ry(58)), (LX1, ry(58)))
    blk("PD", 500, ry(24), param={"t": 2}); wire((LX0, ry(24)), (500, ry(24))); wire((516, ry(24)), (780, ry(24)), (780, ry(59)), (LX1, ry(59)))
    blk("PB", 500, ry(36), label="START"); wire((514, ry(36)), (790, ry(36)), (790, ry(60)), (LX1, ry(60)))
    blk("CONN", 500, ry(26)); wire((LX0, ry(26)), (500, ry(26)))
    blk("CONN", 600, ry(38)); wire((600 + 4 + 8.8, ry(38)), (800, ry(38)), (800, ry(61)), (LX1, ry(61)))
    b = blk("NOR", 500, (ry(28) + ry(29)) / 2); wire((LX0, ry(28)), (500, ry(28))); wire((LX0, ry(29)), (500, ry(29)))
    wire((516, b["y"] + 4.5), (810, b["y"] + 4.5), (810, ry(62)), (LX1, ry(62)))
    blk("ANN", 560, ry(31)); wire((LX0, ry(31)), (560, ry(31)), dashed=True)
    blk("SOE", 560, ry(33)); wire((LX0, ry(33)), (560, ry(33)))
    blk("TEXT", 600, ry(45), w=80, h=8)
    B[-1]["text"] = "NOTE 1"
    return doc


@pytest.fixture(scope="module")
def doc():
    return _doc()


@pytest.fixture(scope="module")
def verified(doc):
    return draw.verify(doc)


def test_every_symbol_round_trips_through_the_analyser(doc, verified):
    v = verified
    assert v["sheet_no"] == {"drawn": "LD-001", "read": "LD-001"}
    kinds = {b["id"]: b for b in v["blocks"]}
    assert len(kinds) == len([b for b in doc["blocks"] if b["kind"] != "TEXT"])
    bad = [b for b in v["blocks"] if not b["ok"]]
    assert bad == [], bad
    byk = {}
    for b in v["blocks"]:
        byk.setdefault(b["kind"], []).append(b)
    assert byk["AND"][0]["inputs"] == 2 and byk["AND"][0]["outputs"] == 1
    assert byk["VOTE"][0]["inputs"] == 3
    assert byk["MEMORY"][0]["inputs"] == 2 and byk["MEMORY"][0]["outputs"] == 1
    assert byk["PB"][0]["inputs"] == 0 and byk["PB"][0]["outputs"] == 1
    assert {b["inputs"] + b["outputs"] for b in byk["CONN"]} == {1}
    assert v["extra_blocks"] == []
    assert v["rows"]["bad"] == [] and v["rows"]["read"] == v["rows"]["drawn"]
    assert v["dangling"] == 0
    assert v["ok"]


def test_timer_vote_and_memory_parameters_survive(doc):
    pdf = draw.to_pdf(doc)
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "a.pdf"
        p.write_bytes(pdf)
        res = analyse.analyse(str(p))
    s = res["sheets"][0]
    by = {b["func"]: b for b in s["blocks"].values()}
    assert by["GT"]["param"].get("t") == 3 and by["DT"]["param"].get("t") == 4 and by["PD"]["param"].get("t") == 2
    assert {k: by["VOTE"]["param"][k] for k in ("a", "b")} == {"a": 2, "b": 3}
    assert by["MEMORY"]["param"].get("dominant") == "set"
    assert by["PB"]["label"].replace(" ", "") in ("PBSTART", "PB")
    conns = [b for b in s["blocks"].values() if b["func"] == "CONNECTOR"]
    assert len(conns) == 2 and all(b["label"] == "A" for b in conns)        # 글자 A 는 범례 `|A`(아날로그 발생기)가 아니라 연결 기호다
    t = {(r["side"], r["n"]): r for r in s["table"]}
    assert t[("L", 2)]["fm"] == "HMI" and t[("R", 51)]["to"] == "LD-002/2"


def test_dxf_export_reopens_with_the_same_entities(doc):
    import ezdxf
    raw = draw.to_dxf(doc).decode("utf-8")
    d = ezdxf.read(io.StringIO(raw))
    msp = d.modelspace()
    layers = {e.dxf.layer for e in msp}
    assert {"TABLE", "TEXT", "SYMBOL", "WIRE", "TITLE"} <= layers
    assert sum(1 for e in msp if e.dxf.layer in ("WIRE", "DASHED") and e.dxftype() == "LWPOLYLINE") == len(doc["wires"])
    assert any(e.dxftype() == "CIRCLE" for e in msp)
    texts = {e.dxf.text for e in msp if e.dxftype() == "TEXT"}
    assert {"AND", "FROM", "TO", "SHEET NO.", "LD-001", "PUMP A RUN"} <= texts


def test_clean_rejects_unknown_kinds_and_clamps_coordinates():
    bad = {"N": "abc", "sheet_no": "X" * 100, "left": {"3": {"fm": "A"}, "999": {"fm": "B"}, "x": 1}, "right": [],
           "blocks": [{"kind": "ZZZ", "x": 1, "y": 1}, {"id": "k", "kind": "AND", "x": -50, "y": 99999, "w": "nan", "h": 1e9, "param": {"t": "x"}},
                      {"id": "k", "kind": "GT", "x": 10, "y": 10, "param": {"t": -5}}],
           "wires": [{"pts": [[0, 0]]}, {"pts": [[1, 1], [1, 1], [5, 5]]}, "junk"]}
    c = draw.clean(bad)
    assert c["N"] == draw.N_DEFAULT and len(c["sheet_no"]) == 40
    assert set(c["left"]) == {"3"} and c["right"] == {}
    assert [b["kind"] for b in c["blocks"]] == ["AND", "GT"]
    assert c["blocks"][0]["x"] == 0 and c["blocks"][0]["y"] == draw.H and c["blocks"][0]["w"] == draw.SYMBOLS["AND"]["w"] and c["blocks"][0]["h"] == 300
    assert c["blocks"][1]["id"] != "k" or c["blocks"][0]["id"] != "k"        # 같은 id 둘은 하나를 새로 준다
    assert c["blocks"][1]["param"]["t"] == 0
    assert len(c["wires"]) == 1 and c["wires"][0]["pts"] == [[1, 1], [5, 5]]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from app.logic import api
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def test_api_create_save_list_export_delete(client, doc):
    r = client.post("/logic/api/drawings", json={"name": "API", "author": "홍길동", "N": 40})
    assert r.status_code == 200
    d = r.json()
    assert d["N"] == 40 and d["author"] == "홍길동"
    assert client.put(f"/logic/api/drawings/{d['id']}", json={"doc": doc}).status_code == 400      # 작성자 없음
    r = client.put(f"/logic/api/drawings/{d['id']}", json={"author": "홍길동", "doc": {**doc, "name": "API 2"}})
    assert r.status_code == 200 and r.json()["saves"] == 1 and r.json()["name"] == "API 2" and len(r.json()["blocks"]) == len(doc["blocks"])
    items = client.get("/logic/api/drawings").json()["items"]
    assert [i["id"] for i in items] == [d["id"]] and items[0]["blocks"] == len(doc["blocks"])
    assert client.get(f"/logic/api/drawings/{d['id']}/export.pdf").content[:4] == b"%PDF"
    assert b"SECTION" in client.get(f"/logic/api/drawings/{d['id']}/export.dxf").content
    assert client.get("/logic/api/drawings/symbols").json()["symbols"].keys() == draw.SYMBOLS.keys()
    assert client.delete(f"/logic/api/drawings/{d['id']}").status_code == 400
    assert client.delete(f"/logic/api/drawings/{d['id']}?author=홍길동").status_code == 200
    assert client.get("/logic/api/drawings").json()["items"] == []
    assert client.get(f"/logic/api/drawings/{d['id']}").status_code == 404


def test_from_sheet_rebuilds_a_drawing_that_round_trips(doc):
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "a.pdf"
        p.write_bytes(draw.to_pdf(doc))
        res = analyse.analyse(str(p))
    s = res["sheets"][0]
    d2 = draw.from_sheet(s, "다시", "tester")
    assert d2["sheet_no"] == "LD-001" and d2["title"] == "ROUND TRIP"           # 제목은 문서 번호 위 글줄에서 읽힌다
    assert {b["kind"] for b in d2["blocks"]} >= {"AND", "GT", "VOTE", "MEMORY", "NOT", "OR", "NAND", "NOR", "DT", "PD", "PB", "CONN"}
    assert d2["left"]["2"]["fm"] == "HMI" and d2["right"]["51"]["to"] == "LD-002/2"
    assert d2["wires"]
    v = draw.verify(d2)
    assert v["rows"]["bad"] == [] and v["sheet_no"]["read"] == "LD-001"
    assert all(b["ok"] for b in v["blocks"] if b["kind"] not in ("CONN",)), [b for b in v["blocks"] if not b["ok"]]
