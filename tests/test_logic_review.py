"""LOGIC 검토 (app/logic) — 신호 연결도 · 강제 신호 시뮬레이션 · API.

실 데이터를 쓰지 않는다: 합성 PDF 로 표 · 선 · 화살촉 · 입력 막대 · 끊어 그린 교차 · 연결점을 그려 읽힌다.
"""
from __future__ import annotations

import ast
import time
from pathlib import Path

import pymupdf
import pytest

from app.logic import geom, graph, sim

ROOT = Path(__file__).resolve().parent.parent

W, H = 1191, 842
LX0, LX1 = 317.0, 872.0        # LOGIC 영역 (표의 세로 괘선 사이)
Y0, PITCH, NROW = 65.0, 10.8, 62


def _row_y(n):                 # n: 1부터 (왼쪽) — 가운데 높이
    return Y0 + (n - 0.5) * PITCH


def _arrow(page, tip, direction=(1, 0)):
    dx, dy = direction
    L, w = 4.5, 0.8
    bx, by = tip[0] - dx * L, tip[1] - dy * L
    pts = [pymupdf.Point(*tip), pymupdf.Point(bx - dy * w, by + dx * w), pymupdf.Point(bx + dy * w, by - dx * w)]
    sh = page.new_shape()
    sh.draw_polyline(pts + [pts[0]])
    sh.finish(color=(0, 0, 0), fill=(0, 0, 0), width=0)
    sh.commit()


def _line(page, *pts, width=0.48):
    sh = page.new_shape()
    sh.draw_polyline([pymupdf.Point(*p) for p in pts])
    sh.finish(color=(0, 0, 0), width=width, closePath=False)
    sh.commit()


def _table(page):
    for x in (79.4, 102.3, 252.8, LX0, LX1, 927.7, 1087.5, 1110.4):
        _line(page, (x, 36), (x, Y0 + NROW * PITCH))
    for k in range(NROW + 1):
        y = Y0 + k * PITCH
        _line(page, (22.5, y), (LX0, y))
        _line(page, (LX1, y), (1167, y))


def make_pdf(path):
    """입력 1·2 → OR (원 + 입력 막대) → 출력 21행.   입력 3 → AND 상자 ← OR 출력에서 갈라진 선(연결점).
    AND 출력 → 22행.  그 출력선을 세로선이 끊어 그린 교차로 지나간다 (이어지지 않아야 한다)."""
    doc = pymupdf.open()
    page = doc.new_page(width=W, height=H)
    _table(page)
    y1, y2, y3 = _row_y(1), _row_y(2), _row_y(3)
    # OR: 입력 막대 x=420 · 원 중심 (426, 이 둘 사이)
    bar_x = 420.0
    cy = (y1 + y2) / 2
    _line(page, (bar_x, y1 - 4), (bar_x, y2 + 4))
    sh = page.new_shape()
    sh.draw_circle(pymupdf.Point(bar_x + 6, cy), 6)
    sh.finish(color=(0, 0, 0), width=0.48)
    sh.commit()
    for y in (y1, y2):
        _line(page, (LX0, y), (bar_x, y))
        _arrow(page, (bar_x, y))
    # OR 출력 → 오른쪽 21행
    out_y = _row_y(1)
    _line(page, (bar_x + 12, cy), (600, cy), (600, out_y), (LX1, out_y))
    # 연결점 (500, cy) 에서 아래로 갈라져 AND 로
    sh = page.new_shape()
    sh.draw_circle(pymupdf.Point(500, cy), 1.3)
    sh.finish(color=(0, 0, 0), fill=(0, 0, 0), width=0.48)
    sh.commit()
    and_box = pymupdf.Rect(640, y3 - 8, 652, y3 + 8)
    _line(page, (500, cy), (500, y3 - 4), (640, y3 - 4))
    _arrow(page, (640, y3 - 4))
    _line(page, (LX0, y3 + 4), (640, y3 + 4))
    _arrow(page, (640, y3 + 4))
    sh = page.new_shape()
    sh.draw_rect(and_box)
    sh.finish(color=(0, 0, 0), width=0.48)
    sh.commit()
    out2 = _row_y(2)
    _line(page, (652, y3), (700, y3), (700, out2), (LX1, out2))
    # 끊어 그린 교차: 12행 가로선(왼쪽→오른쪽)을 x=760 세로선이 틈을 두고 지난다.
    # 세로선은 10행 입력에서 내려와 14행 출력으로 간다 — 가로선과 이어지지 않아야 한다.
    y12, y10, y14 = _row_y(12), _row_y(10), _row_y(14)
    _line(page, (LX0, y12), (LX1, y12))
    _line(page, (LX0, y10), (760, y10), (760, y12 - 2.5))
    _line(page, (760, y12 + 2.5), (760, y14), (LX1, y14))
    doc.save(path)
    return path


@pytest.fixture(scope="module")
def sheet(tmp_path_factory):
    p = make_pdf(tmp_path_factory.mktemp("logic") / "syn.pdf")
    doc = pymupdf.open(p)
    pr = geom.read(doc[0], 1)
    sh = graph.build(pr)
    assert sh is not None, "표를 그린 장인데 Logic 시트로 읽지 못했다"
    return sh


def test_layout_reads_logic_area_and_rows(sheet):
    lay = sheet.layout
    assert abs(lay.logic[0] - LX0) < 0.5 and abs(lay.logic[2] - LX1) < 0.5
    assert abs(lay.pitch - PITCH) < 0.15
    assert len(lay.left_rows) == NROW and len(lay.right_rows) == NROW
    assert lay.right_rows[0][0] == NROW + 1, "오른쪽 표 행 번호는 왼쪽에 이어서 센다"


def _net_of_row(sh, side, n):
    return [r["net"] for r in sh.rows if r["side"] == side and r["n"] == n]


def test_bus_arrows_become_inputs_of_the_or_gate(sheet):
    circles = [b for b in sheet.blocks.values() if b.kind == "CIRCLE"]
    assert len(circles) == 1
    g = circles[0]
    assert g.bus, "화살촉이 닿는 막대가 원의 입력 막대로 붙어야 한다"
    ins = [p for p in sheet.ports if p.block == g.id and p.dir == "in"]
    outs = [p for p in sheet.ports if p.block == g.id and p.dir == "out"]
    assert len(ins) == 2 and len(outs) == 1
    assert {p.net for p in ins} == set(_net_of_row(sheet, "L", 1) + _net_of_row(sheet, "L", 2))


def test_dot_joins_the_branch_and_gap_crossing_does_not(sheet):
    or_out = [p.net for p in sheet.ports if sheet.blocks[p.block].kind == "CIRCLE" and p.dir == "out"][0]
    assert _net_of_row(sheet, "R", NROW + 1) == [or_out], "OR 출력이 21행으로 가야 한다"
    rect = [b for b in sheet.blocks.values() if b.kind == "RECT"][0]
    ins = {p.net for p in sheet.ports if p.block == rect.id and p.dir == "in"}
    assert or_out in ins, "연결점에서 갈라진 선은 같은 넷이다"
    and_out = [p.net for p in sheet.ports if p.block == rect.id and p.dir == "out"][0]
    assert _net_of_row(sheet, "R", NROW + 2) == [and_out]
    # 끊어 그린 세로선: 10행 입력 → 14행 출력이 한 넷(틈 건너 이어짐)이고 12행 가로선과는 다른 넷
    v = _net_of_row(sheet, "L", 10)
    assert v and v == _net_of_row(sheet, "R", NROW + 14)
    assert v != _net_of_row(sheet, "L", 12)
    assert sheet.nets[v[0]].get("jumps"), "틈 건너 이은 자리를 기록한다"
    assert not sheet.dangling, sheet.dangling


def _toy():
    """시뮬레이터 단위: in1,in2 → OR → n3 · n3,in4 → AND → n5 · n5 → PD(2초) → n6 → MEM S · in7 → MEM R."""
    blocks = {
        "OR": {"func": "OR", "logic": "or", "group": "", "param": {}},
        "AND": {"func": "AND", "logic": "and", "group": "", "param": {}},
        "PD": {"func": "PD", "logic": "pulse", "group": "", "param": {"t": 2}},
        "M": {"func": "MEMORY", "logic": "memory", "group": "", "param": {"dominant": "reset"}},
    }
    P = lambda b, n, d, role="": {"block": b, "net": n, "dir": d, "role": role, "cell": 0}
    ports = [P("OR", "1", "in"), P("OR", "2", "in"), P("OR", "3", "out"),
             P("AND", "3", "in"), P("AND", "4", "in"), P("AND", "5", "out"),
             P("PD", "5", "in"), P("PD", "6", "out"),
             P("M", "6", "in", "set"), P("M", "7", "in", "reset"), P("M", "8", "out", "q")]
    rows = [{"n": k, "side": "L", "net": str(k)} for k in (1, 2, 4, 7)] + [{"n": 30, "side": "R", "net": "8"}]
    nets = {str(k): {"segs": []} for k in range(1, 9)}
    return {"blocks": blocks, "ports": ports, "rows": rows, "nets": nets}


def test_simulation_follows_the_legend_definitions():
    s = _toy()
    r = sim.simulate(s, {"row:1": 1})
    v = r["frames"][-1]["values"]
    assert v["3"] == 1 and v["5"] == 0 and v["8"] == 0          # AND 은 둘 다 1 이어야
    r = sim.simulate(s, {"row:1": 1, "row:4": 1}, r["state"])
    f0, f_last = r["frames"][0], r["frames"][-1]
    assert f0["values"]["6"] == 1, "PD: 입력이 0→1 이면 바로 1"
    assert f_last["values"]["6"] == 0 and len(r["frames"]) == 2, "PD: t 뒤 0 (틀이 하나 더)"
    assert f_last["t"] == pytest.approx(2.0)
    assert f_last["values"]["8"] == 1, "메모리는 펄스가 끝나도 1 을 지킨다"
    assert f0["depth"]["5"] > f0["depth"]["3"], "깊이는 블록을 지날수록 커진다"
    # 입력을 풀어도 래치 유지 · RESET 이 들어오면 0
    r = sim.simulate(s, {}, r["state"])
    assert r["frames"][-1]["values"]["8"] == 1
    r = sim.simulate(s, {"row:7": 1}, r["state"])
    assert r["frames"][-1]["values"]["8"] == 0
    # 선 강제는 몰이를 이긴다
    r = sim.simulate(s, {"row:1": 1, "net:3": 0})
    assert r["frames"][-1]["values"]["3"] == 0


def test_trace_goes_through_blocks_in_depth_order():
    t = sim.trace(_toy(), "row:1")
    depth = {o["net"]: o["depth"] for o in t["order"]}
    assert depth["1"] == 0 and depth["3"] == 1 and depth["5"] == 2 and depth["8"] == 4
    up = sim.trace(_toy(), "net:8", "up")
    assert {o["net"] for o in up["order"]} >= {"6", "7", "5", "3", "1", "2", "4"}


def test_logic_package_does_not_import_the_pid_engine():
    """P&ID 판정 엔진은 부르지 않는다 (지시문 §3)."""
    for p in (ROOT / "app" / "logic").glob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for n in names:
                assert not n.startswith("app.engine") and n not in ("app.pipeline", "pipeline"), (p.name, n)


def test_vocab_is_the_legend_list():
    from app.logic import blocks
    v = blocks.vocab()
    for name in ("AND", "OR", "NOT", "NAND", "NOR", "GT", "DT", "PD"):
        assert name in v["functions"]


def test_api_round_trip(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    from app.logic import api, run
    monkeypatch.setattr(api, "_start", run.run)               # 분석을 같은 프로세스에서 바로 (시험)
    client = TestClient(main.app)
    pdf = make_pdf(tmp_path / "up.pdf")
    r = client.post("/logic/api/jobs", files={"file": ("up.pdf", pdf.read_bytes(), "application/pdf")})
    assert r.status_code == 200, r.text
    job = r.json()["id"]
    for _ in range(200):
        st = client.get(f"/logic/api/jobs/{job}").json()
        if st["state"] in ("done", "failed"):
            break
        time.sleep(0.1)
    assert st["state"] == "done", st
    sheets = client.get(f"/logic/api/jobs/{job}/sheets").json()["sheets"]
    assert len(sheets) == 1
    s = client.get(f"/logic/api/jobs/{job}/sheet/1").json()
    assert s["nets"] and s["order"]
    sim_r = client.post(f"/logic/api/jobs/{job}/sheet/1/simulate", json={"forces": {"row:1": 1, "bad": 3}}).json()
    assert sim_r["frames"]
    tr = client.post(f"/logic/api/jobs/{job}/sheet/1/trace", json={"start": "row:1"}).json()
    assert len(tr["order"]) >= 2
    assert client.get(f"/logic/api/jobs/{job}/page/1.png").headers["content-type"] == "image/png"
    assert client.post("/logic/api/jobs", files={"file": ("x.pdf", b"not a pdf", "application/pdf")}).status_code == 400
    assert client.get("/logic/api/jobs/zzz").status_code == 404
    assert client.get("/logic").status_code == 200
    assert client.delete(f"/logic/api/jobs/{job}").status_code == 204


def test_every_line_is_digital_and_gate_waits_for_all_inputs():
    """L3 사용자 지시: 모든 선은 1/0 · AND 는 A 만 활성이면 뒤로 안 나간다 · 판정 못 한 블록 뒤는 0."""
    s = _toy()
    s["blocks"]["U"] = {"func": "UNKNOWN", "logic": "unknown", "group": "", "param": {}}
    s["ports"] += [{"block": "U", "net": "3", "dir": "in", "role": "", "cell": 0},
                   {"block": "U", "net": "9", "dir": "out", "role": "", "cell": 0}]
    s["nets"]["9"] = {"segs": []}
    s["nets"]["10"] = {"segs": []}                 # 몰이 없는 선
    for forces in ({}, {"row:1": 1}, {"row:4": 1}, {"row:1": 1, "row:4": 1}):
        r = sim.simulate(s, forces)
        for fr in r["frames"]:
            assert set(fr["values"].values()) <= {0, 1}, (forces, fr["values"])
    a_only = sim.simulate(s, {"row:1": 1})["frames"][-1]["values"]
    b_only = sim.simulate(s, {"row:4": 1})["frames"][-1]["values"]
    both = sim.simulate(s, {"row:1": 1, "row:4": 1})["frames"][0]["values"]
    assert a_only["5"] == 0 and b_only["5"] == 0 and both["5"] == 1
    assert a_only["9"] == 0 and a_only["10"] == 0
    # NOT · NAND · NOR 는 범례 G003 정의 그대로 (입력 0 이면 NOT 출력 1)
    t = {"blocks": {"N": {"func": "NOT", "logic": "not", "group": "", "param": {}}},
         "ports": [{"block": "N", "net": "1", "dir": "in", "role": "", "cell": 0},
                   {"block": "N", "net": "2", "dir": "out", "role": "", "cell": 0}],
         "rows": [{"n": 1, "side": "L", "net": "1"}], "nets": {"1": {"segs": []}, "2": {"segs": []}}}
    assert sim.simulate(t, {})["frames"][-1]["values"]["2"] == 1
    assert sim.simulate(t, {"row:1": 1})["frames"][-1]["values"]["2"] == 0


def test_active_output_carries_to_linked_sheets():
    """L4 사용자 지시: 출력 행이 1 이면 그 행을 FM 으로 받는 다른 장의 입력도 1 — 게이트 조건대로 이어진다."""
    def gate(page, no, logic, ins, out, ref=None):
        ports = [{"block": "G", "net": str(n), "dir": "in", "role": "", "cell": 0} for n in ins]
        ports.append({"block": "G", "net": str(out), "dir": "out", "role": "", "cell": 0})
        rows = [{"n": n, "side": "L", "net": str(n), **({"ref": ref} if ref and n == ins[0] else {})} for n in ins]
        rows.append({"n": 70, "side": "R", "net": str(out)})
        return {"page": page, "sheet_no": no, "blocks": {"G": {"func": logic.upper(), "logic": logic, "group": "", "param": {}}},
                "ports": ports, "rows": rows, "nets": {str(n): {"segs": []} for n in [*ins, out]}}
    a = gate(1, "G001", "or", [1], 9)
    b = gate(2, "G002", "and", [1, 2], 9, ref={"sheet": "G001", "row": 70, "page": 1})
    c = gate(3, "G003", "or", [1], 9, ref={"sheet": "G002", "row": 70, "page": 2})
    a["rows"][-1]["refs_in"] = [{"sheet": "G002", "page": 2, "row": 1}]
    b["rows"][-1]["refs_in"] = [{"sheet": "G003", "page": 3, "row": 1}]
    S = [a, b, c]
    r = sim.simulate_bundle(S, {1: {"row:1": 1}}, None, 2)
    assert r["linked"][2] == {1: 1}, "G001-70 이 1 이면 G002 1행도 1"
    assert r["focus"]["frames"][-1]["values"]["9"] == 0, "AND 는 다른 입력이 0 이면 멈춘다"
    assert not any(p["page"] == 3 and p["hop"] is not None for p in r["pages"])
    r = sim.simulate_bundle(S, {1: {"row:1": 1}, 2: {"row:2": 1}}, None, 3)
    assert r["focus"]["frames"][-1]["values"]["9"] == 1, "AND 조건이 맞으면 G003 까지 이어진다"
    hops = {p["sheet_no"]: p["hop"] for p in r["pages"]}
    assert hops["G001"] == 0 and hops["G002"] == 0 and hops["G003"] == 1   # 사람이 준 장에서 몇 장째
    r = sim.simulate_bundle(S, {1: {"row:1": 1}, 2: {"row:1": 0, "row:2": 1}}, None, 2)
    assert r["focus"]["frames"][-1]["values"]["9"] == 0, "사람이 준 0 이 연결보다 이긴다"


def test_from_to_mismatch_is_reported():
    """L5 사용자 지시: from-to 가 맞지 않으면 붉게 — FM ↔ TO 양쪽과 설명을 도면 글자 그대로 대조한다."""
    from app.logic import fromto

    def sheet(page, no, table, wired):
        return {"page": page, "sheet_no": no, "table": table, "findings": [],
                "rows": [{"n": n, "side": sd, "net": str(n), "at": [0, 0]} for sd, n in wired]}
    src = sheet(1, "G049", [
        {"side": "R", "n": 85, "desc": "HP DRUM CBD MOV CLOSED", "to": "G035-31"},
        {"side": "R", "n": 86, "desc": "", "to": "G023-8"},           # TO 목록이 아래 행으로 이어진다
        {"side": "R", "n": 95, "desc": "HP DRUM CBD MOV READY", "to": "G025-8"},
        {"side": "R", "n": 96, "desc": "", "to": ""},
    ], [("R", 85), ("R", 95)])
    a = sheet(2, "G023", [{"side": "L", "n": 8, "fm": "G049-86", "desc": "HP DRUM CBD MOV CLOSED"}], [("L", 8)])
    b = sheet(3, "G025", [{"side": "L", "n": 8, "fm": "G049-95", "desc": "HP DRUM CBD MOV CLOSED"}], [("L", 8)])
    c = sheet(4, "G035", [{"side": "L", "n": 31, "fm": "G049-96", "desc": "X"}], [("L", 31)])
    for sh in (a, b, c):
        for r in sh["rows"]:
            r["fm"] = sh["table"][0]["fm"]; r["desc"] = sh["table"][0]["desc"]
    S = [src, a, b, c]
    fromto.check(S)
    fromto.check(S)                                                     # 여러 번 불러도 같다
    ra, rb, rc = a["rows"][0], b["rows"][0], c["rows"][0]
    assert ra["ft"]["ok"] is True and ra["ref"]["src_row"] == 85, "86행은 85행 신호의 TO 이어짐"
    assert rb["ft"]["ok"] is False and "설명이 다릅니다" in rb["ft"]["why"][0]
    assert rc["ft"]["ok"] is False and "출력 신호가 없습니다" in rc["ft"]["why"][0]
    o85 = src["rows"][0]
    assert o85["ft"]["ok"] is False and "G035-31" in o85["ft"]["why"][0], "TO G035-31 의 FM 이 G049-96 이다"
    assert sum(f["code"] == "FT_MISMATCH" for sh in S for f in sh["findings"]) == 3


def test_from_is_matched_by_fm_sheet_and_row_not_kks():
    """사용자 확정: FROM 은 KKS 가 아니라 FM 칸의 시트 번호 + 행 No. 로 식별하고 맞댄다."""
    from app.logic import fromto
    src = {"page": 1, "sheet_no": "G048", "findings": [], "rows": [{"n": 95, "side": "R", "net": "1", "at": [0, 0]}],
           "table": [{"side": "R", "n": 95, "desc": "PUMP READY", "to": "G025-7", "kks": "10AAA01AA001"}]}
    dst = {"page": 2, "sheet_no": "G025", "findings": [],
           "rows": [{"n": 7, "side": "L", "net": "1", "at": [0, 0], "fm": "G048-95", "desc": "PUMP READY", "kks": "99ZZZ99ZZ999"},
                    {"n": 8, "side": "L", "net": "2", "at": [0, 0], "fm": "", "desc": "PUMP READY", "kks": "10AAA01AA001"}],
           "table": [{"side": "L", "n": 7, "fm": "G048-95", "desc": "PUMP READY", "kks": "99ZZZ99ZZ999"},
                     {"side": "L", "n": 8, "fm": "", "desc": "PUMP READY", "kks": "10AAA01AA001"}]}
    fromto.check([src, dst])
    r7, r8 = dst["rows"]
    assert r7["ft"]["ok"] is True and r7["ref"] == {"sheet": "G048", "row": 95, "page": 1, "other_bundle": False, "src_row": 95}
    assert "ft" not in r8 and "ref" not in r8, "KKS 가 같아도 FM 이 없으면 잇지 않는다"
    assert [x["row"] for x in src["rows"][0]["refs_in"]] == [7]
