"""LOGIC 검토 (app/logic) — 신호 연결도 · 강제 신호 시뮬레이션 · API.

실 데이터를 쓰지 않는다: 합성 PDF 로 표 · 선 · 화살촉 · 입력 막대 · 끊어 그린 교차 · 연결점을 그려 읽힌다.
"""
from __future__ import annotations

import ast
import os
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
    # L16 — 게이트가 모는 선은 직접 바꾸지 않는다: OR 의 입력이 1 이면 출력 0 을 줘도 1 이고 모순으로 말한다
    r = sim.simulate(s, {"row:1": 1, "net:3": 0})
    assert r["frames"][-1]["values"]["3"] == 1 and r["conflicts"] and r["unmet"]
    # 몰이가 없는 선은 예전처럼 직접 준다
    s2 = _toy()
    s2["rows"] = [x for x in s2["rows"] if x["n"] != 4]
    assert sim.simulate(s2, {"net:4": 1, "row:1": 1})["frames"][-1]["values"]["5"] == 1


def test_trace_goes_through_blocks_in_depth_order():
    # L14 — 연결 따라가기는 연결만 본다: AND 의 다른 입력이 0 이어도 지나간다 (사용자 확정)
    t = sim.trace(_toy(), "row:1")
    depth = {o["net"]: o["depth"] for o in t["order"]}
    assert depth["1"] == 0 and depth["3"] == 1 and depth["5"] == 2 and depth["8"] == 4
    assert not t["blocked"] and "AND" in {b["block"] for b in t["blocks"]}
    up = sim.trace(_toy(), "net:8", "up")
    assert {o["net"] for o in up["order"]} >= {"6", "7", "5", "3", "1", "2", "4"}


def test_scenario_finds_inputs_that_light_the_whole_chain():
    """L14 — 출력 하나를 고르면 범례 정의를 거꾸로 따라 입력 조합을 찾고, 앞으로 돌려 확인한다."""
    s = _toy()
    r = sim.scenario(s, "row:30")
    assert r["ok"] and r["forces"].get("row:4") == 1 and (r["forces"].get("row:1") == 1 or r["forces"].get("row:2") == 1)
    assert "row:7" not in r["forces"] or r["forces"]["row:7"] == 0          # RESET 은 주지 않는다
    v = sim.simulate(s, r["forces"])
    assert any(fr["values"]["8"] == 1 for fr in v["frames"])
    # 몰 길이 없는 출력은 찾았다고 하지 않는다
    s2 = _toy()
    s2["ports"] = [p for p in s2["ports"] if not (p["block"] == "AND" and p["net"] == "4")]
    r2 = sim.scenario(s2, "row:30")
    assert not r2["ok"] or r2["direct_nets"] == []


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
    # L6: 표 행마다 칸 자리 — FROM(FM) 칸 · TO 칸 · NO. 칸 (도면 위 표기와 이동에 쓴다)
    L = [t for t in s["table"] if t["side"] == "L"]
    R = [t for t in s["table"] if t["side"] == "R"]
    assert L and all("fm_box" in t and "no_box" in t for t in L)
    assert R and all("to_box" in t and "no_box" in t for t in R)
    for t in L + R:                                     # 칸은 그 행의 세로 범위 그대로
        for k in ("fm_box", "to_box", "no_box"):
            if t.get(k):
                assert t[k][1] == round(t["y0"], 2) and t[k][3] == round(t["y1"], 2) and t[k][0] < t[k][2]
    sim_r = client.post(f"/logic/api/jobs/{job}/sheet/1/simulate", json={"forces": {"row:1": 1, "bad": 3}}).json()
    assert sim_r["frames"]
    tr = client.post(f"/logic/api/jobs/{job}/sheet/1/trace", json={"start": "row:1"}).json()
    assert len(tr["order"]) >= 2
    assert client.get(f"/logic/api/jobs/{job}/page/1.png").headers["content-type"] == "image/png"
    # L7 — 묶음 점검 목록 · Excel 보고서 (판정 0 · 장마다의 findings 를 옮겨 적는다)
    fd = client.get(f"/logic/api/jobs/{job}/findings").json()
    assert fd["total"] == sum(len(x["findings"]) for x in [s]) and sum(c["n"] for c in fd["codes"]) == fd["total"]
    assert all(it["page"] == 1 and it["label"] for it in fd["items"])
    xr = client.get(f"/logic/api/jobs/{job}/report.xlsx")
    assert xr.status_code == 200 and xr.headers["content-type"].endswith("sheet") and "filename*=UTF-8" in xr.headers["content-disposition"]
    import io
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(xr.content))
    assert [w.title for w in wb] == ["요약", "from-to 불일치", "설명 다름", "연결 점검", "입력 행", "출력 행"]
    rows_in = [r for r in s["rows"] if r["side"] == "L"]
    rows_out = [r for r in s["rows"] if r["side"] == "R"]
    assert wb["입력 행"].max_row - 1 == len(rows_in) and wb["출력 행"].max_row - 1 == len(rows_out)
    # 장 그림은 분석이 끝나며 미리 그려 둔다 (L7) — 분석 프로세스가 쓴 캐시가 그대로 쓰인다
    from app.logic import store
    assert (store.job_dir(job) / "pages" / f"p1_z{store.ZOOM}.png").exists()
    # L8 — 메모 API (지우는 길이 없다)
    m = client.post(f"/logic/api/jobs/{job}/memo", json={"page": 1, "sheet_no": "G001", "text": "확인", "author": "홍길동", "at": [10, 20]}).json()
    assert client.post(f"/logic/api/jobs/{job}/memo", json={"page": 1, "text": "", "author": "홍길동"}).status_code == 400
    assert client.patch(f"/logic/api/jobs/{job}/memo/{m['id']}", json={"author": "김", "done": True}).json()["done"] is True
    assert client.patch(f"/logic/api/jobs/{job}/memo/none", json={"author": "김", "done": True}).status_code == 404
    assert len(client.get(f"/logic/api/jobs/{job}/memo").json()["items"]) == 1
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
    assert rb["ft"]["ok"] is True and "설명이 다릅니다" in rb["ft"]["warn"][0], "연결은 맞고 설명만 다르면 주황 (불일치 아님)"
    assert rc["ft"]["ok"] is False and "출력 신호가 없습니다" in rc["ft"]["why"][0]
    o85 = src["rows"][0]
    assert o85["ft"]["ok"] is False and "G035-31" in o85["ft"]["why"][0], "TO G035-31 의 FM 이 G049-96 이다"
    assert sum(f["code"] == "FT_MISMATCH" for sh in S for f in sh["findings"]) == 2
    assert sum(f["code"] == "FT_DESC_DIFF" for sh in S for f in sh["findings"]) == 1


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


def test_memo_is_kept_with_history_and_never_deleted(tmp_path):
    """L8 — 메모는 지우지 않는다: 고치면 앞 글이 이력 · 완료/숨김은 표시 · 작성자·내용 필수."""
    from app.logic import memo
    d = tmp_path / "job"
    d.mkdir()
    a = memo.add(d, 27, "G034", "PD 3초 확인", "홍길동", at=[100.5, 200])
    b = memo.add(d, 27, "G034", "시트 메모", "홍길동")
    assert a["at"] == [100.5, 200.0] and b["at"] is None
    with pytest.raises(ValueError):
        memo.add(d, 27, "G034", "  ", "홍길동")
    with pytest.raises(ValueError):
        memo.add(d, 27, "G034", "글", "")
    m = memo.update(d, a["id"], "김철수", text="PD 5초로 고침", done=True)
    assert m["text"] == "PD 5초로 고침" and m["done"] is True
    assert m["history"][0]["text"] == "PD 3초 확인"
    memo.update(d, b["id"], "김철수", hidden=True)
    items = memo.load(d)["items"]
    assert len(items) == 2 and items[1]["hidden"] is True
    with pytest.raises(KeyError):
        memo.update(d, "없는것", "김철수", done=True)


def test_gate_values_and_latch_table_are_in_the_screen_code():
    """L8 — 게이트 단자 1/0 과 S-R 래치 표는 시뮬레이터의 값(L.values)을 읽는다 (화면이 다시 판정하지 않는다)."""
    js = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")
    for name in ("function drawSimMarks", "function drawLatchTable", "function latchTableHtml",
                 "function setFull", "function saveMemo", "function drawPins"):
        assert name in js
    body = js.split("function portVal", 1)[1].split("\nfunction ", 1)[0]
    assert "L.values" in body
    html = (ROOT / "app/static/logic.html").read_text(encoding="utf-8")
    for i in ("show-ports", "show-latch", "full", "memo-list", "latches"):
        assert f'id="{i}"' in html


def _sheet(page, no, rows, blocks=None, ports=None):
    nets = {r["net"]: {"segs": []} for r in rows}
    for p in ports or []:
        nets.setdefault(p["net"], {"segs": []})
    return {"page": page, "sheet_no": no, "rows": rows, "blocks": blocks or {}, "ports": ports or [], "nets": nets}


def test_output_row_force_and_to_links_carry_on_until_a_gate_stops():
    """L9 — 출력 행을 1 로 주면 그 행의 TO 로 다음 시트 입력이 1, 거기서 AND 가 막으면 머문다.

    A: 출력 95 (설명 있음 · TO B-10) · 96 (설명 없음 · TO C-6 — 95 의 TO 목록이 이어진 것).
    B: 입력 10 의 FM 은 다른 곳(Z-1 · 도면 어긋남)이어도 A 의 TO 로 받는다 → 그대로 출력 50 → TO C-7.
    C: 입력 6, 7, 8 → AND → 출력 40.  6·7 만 오면 AND 는 0 (머문다) · 8 까지 주면 1.
    """
    P = lambda b, n, d: {"block": b, "net": n, "dir": d, "role": "", "cell": 0}
    A = _sheet(1, "A1", [{"n": 95, "side": "R", "net": "a", "desc": "READY", "to": "B1-10"},
                         {"n": 96, "side": "R", "net": "a2", "desc": "", "to": "C1-6"}])
    B = _sheet(2, "B1", [{"n": 10, "side": "L", "net": "b", "desc": "X", "fm": "Z1-1"},
                         {"n": 50, "side": "R", "net": "b", "desc": "X", "to": "C1-7"}])
    C = _sheet(3, "C1", [{"n": 6, "side": "L", "net": "c6"}, {"n": 7, "side": "L", "net": "c7"},
                         {"n": 8, "side": "L", "net": "c8"}, {"n": 40, "side": "R", "net": "co", "desc": "Y"}],
               {"G": {"func": "AND", "logic": "and", "group": "", "param": {}}},
               [P("G", "c6", "in"), P("G", "c7", "in"), P("G", "c8", "in"), P("G", "co", "out")])
    b = sim.simulate_bundle([A, B, C], {1: {"row:95": 1}}, None, 3)
    v = b["focus"]["frames"][-1]["values"]
    assert v["c6"] == 1 and v["c7"] == 1 and v["c8"] == 0 and v["co"] == 0     # AND 가 막아 머문다
    hops = {c["sheet_no"]: c["hop"] for c in b["pages"]}
    assert hops["B1"] == 1 and hops["C1"] in (1, 2)
    b = sim.simulate_bundle([A, B, C], {1: {"row:95": 1}, 3: {"row:8": 1}}, None, 3)
    assert b["focus"]["frames"][-1]["values"]["co"] == 1                       # 조건이 풀리면 지난다
    b = sim.simulate_bundle([A, B, C], {1: {"row:95": 0}}, None, 3)
    assert b["focus"]["frames"][-1]["values"]["c6"] == 0


def _one(logic, n_in, label="", param=None):
    """블록 하나 · 입력 행 n_in 개 → 출력 행 90."""
    blocks = {"G": {"func": logic.upper(), "logic": logic, "group": "", "label": label, "param": param or {}}}
    P = lambda b, n, d, role="": {"block": b, "net": n, "dir": d, "role": role, "cell": 0}
    ports = [P("G", f"i{k}", "in") for k in range(n_in)] + [P("G", "o", "out")]
    rows = [{"n": k + 1, "side": "L", "net": f"i{k}"} for k in range(n_in)] + [{"n": 90, "side": "R", "net": "o"}]
    nets = {f"i{k}": {"segs": []} for k in range(n_in)}
    nets["o"] = {"segs": []}
    return {"blocks": blocks, "ports": ports, "rows": rows, "nets": nets}


def _out(s, ones=()):
    return sim.simulate(s, {f"row:{k}": 1 for k in ones})["frames"][-1]["values"]["o"]


def test_every_gate_follows_the_legend_g003_truth_table():
    """L10 — 범례 G003 정의 그대로.  입력 조건이 만족되지 않으면 출력은 나오지 않는다."""
    import itertools
    for n in (2, 3):
        for ones in itertools.chain.from_iterable(itertools.combinations(range(1, n + 1), k) for k in range(n + 1)):
            k = len(ones)
            assert _out(_one("and", n), ones) == (1 if k == n else 0)      # ALL INPUTS TRUE
            assert _out(_one("or", n), ones) == (1 if k >= 1 else 0)       # ANY INPUT TRUE
            assert _out(_one("nand", n), ones) == (1 if k < n else 0)      # ANY INPUT FALSE
            assert _out(_one("nor", n), ones) == (1 if k == 0 else 0)      # ALL INPUTS FALSE
    assert _out(_one("not", 1), (1,)) == 0 and _out(_one("not", 1)) == 1   # NOT
    vote = _one("unknown", 3, label="2/3")                                   # A/B — AT LEAST A OUT OF B
    assert [_out(vote, o) for o in ((), (1,), (1, 2), (1, 2, 3))] == [0, 0, 1, 1]


def test_a_gate_whose_inputs_were_not_read_gives_no_output():
    """입력을 다 읽지 못한 게이트는 출력을 내지 않는다 — 읽힌 입력만으로 결과가 정해질 때만 낸다."""
    assert _out(_one("and", 1), (1,)) == 0           # 하나만 읽힌 AND — 그 하나가 1 이어도 0
    assert _out(_one("not", 0)) == 0                 # 입력이 안 읽힌 NOT — 1 을 내지 않는다
    assert _out(_one("nor", 1)) == 0                 # 하나만 읽힌 NOR — 다 0 인지 모른다
    assert _out(_one("or", 1), (1,)) == 1            # 하나만 읽힌 OR 라도 그 하나가 1 이면 1 (정해진다)
    assert _out(_one("nand", 1)) == 1                # 읽힌 입력이 0 이면 NAND 는 1 (정해진다)
    r = sim.simulate(_one("and", 1), {"row:1": 1})
    assert r["short_gates"] == ["G"] and any("입력을 다 읽지 못한" in n for n in r["notes"])
    # 몰이가 없는 선(도면에서 끊긴 입력)도 모름 — NOT 뒤로 1 이 나오지 않는다
    s = _one("not", 1)
    s["rows"] = [r for r in s["rows"] if r["side"] == "R"]
    assert sim.simulate(s, {})["frames"][-1]["values"]["o"] == 0
    # 판정 못 한 블록은 출력을 내지 않는다
    assert _out(_one("unknown", 2, label="MAN"), (1, 2)) == 0


def test_basic_memory_changes_state_when_both_inputs_rise_together():
    blocks = {"M": {"func": "MEMORY", "logic": "memory", "group": "", "param": {"dominant": ""}}}
    P = lambda b, n, d, role="": {"block": b, "net": n, "dir": d, "role": role, "cell": 0}
    s = {"blocks": blocks, "rows": [{"n": 1, "side": "L", "net": "a"}, {"n": 2, "side": "L", "net": "b"}],
         "ports": [P("M", "a", "in", "set"), P("M", "b", "in", "reset"), P("M", "c", "out", "q"), P("M", "d", "out", "qn")],
         "nets": {k: {"segs": []} for k in "abcd"}}
    v = sim.simulate(s, {})["frames"][-1]["values"]
    assert v["c"] == 0 and v["d"] == 1                                        # C · D 는 언제나 반대
    r = sim.simulate(s, {"row:1": 1, "row:2": 1})                             # 함께 1 → 상태가 바뀐다
    assert r["frames"][-1]["values"]["c"] == 1
    r = sim.simulate(s, {"row:1": 1, "row:2": 1}, r["state"])                 # 그대로 유지되면 다시 안 바뀐다
    assert r["frames"][-1]["values"]["c"] == 1
    for dom, want in (("set", 1), ("reset", 0)):
        s["blocks"]["M"]["param"]["dominant"] = dom
        assert sim.simulate(s, {"row:1": 1, "row:2": 1})["frames"][-1]["values"]["c"] == want


def test_moving_signal_reports_design_errors_on_the_to_path():
    """L11 — TO 를 따라 이동하다 그 시트·행이 없거나 잘못 연결돼 있으면 설계 오류로 알린다."""
    A = _sheet(1, "A1", [{"n": 95, "side": "R", "net": "a", "desc": "READY", "to": "B1-10"},
                         {"n": 96, "side": "R", "net": "a2", "desc": "", "to": "B1-11"},
                         {"n": 97, "side": "R", "net": "a3", "desc": "", "to": "Q9-1"},
                         {"n": 98, "side": "R", "net": "a4", "desc": "", "to": "B1-77"},
                         {"n": 99, "side": "R", "net": "a5", "desc": "", "to": "P1-5"}])
    B = _sheet(2, "B1", [{"n": 10, "side": "L", "net": "b", "desc": "READY", "fm": "Z1-1",
                          "ref": {"sheet": "Z1", "row": 1, "page": None}},
                         {"n": 11, "side": "L", "net": "c", "desc": "", "fm": ""},
                         {"n": 12, "side": "L", "net": "d", "desc": "READY", "fm": "A1-95",
                          "ref": {"sheet": "A1", "row": 95, "page": 1, "src_row": 95}}])
    b = sim.simulate_bundle([A, B], {1: {"row:95": 1}}, None, 1)
    errs = {e["to"]: e for e in b["design_errors"]}
    assert errs["B1-10"]["kind"] == "error" and "FM 은 Z1-1" in errs["B1-10"]["why"]      # 잘못 연결
    assert errs["B1-11"]["kind"] == "error" and "비어" in errs["B1-11"]["why"]            # 빈 행
    assert errs["Q9-1"]["kind"] == "other"                                                # 다른 묶음 계열
    assert errs["B1-77"]["kind"] == "error" and "77행 입력이 없습니다" in errs["B1-77"]["why"]
    assert errs["B1-12"]["kind"] == "error" and "TO 는" in errs["B1-12"]["why"]          # FM 은 오는데 TO 목록에 없음
    assert errs["P1-5"]["kind"] == "other"
    # 신호가 0 이면 이동하지 않으므로 아무 오류도 없다
    assert not sim.simulate_bundle([A, B], {}, None, 1)["design_errors"]


def test_macro_pins_match_typical_rows_through_the_legend_abbreviations():
    """L12 — 단자 이름 → (범례 약어표) 뜻 → Typical 시트 행.  코드에 단자 이름이 없다 (도면 글자만)."""
    from app.logic import macro as M
    abbr = [("A_OPEN", "AUTO OPEN"), ("EN_OPEN", "OPEN PERMISSIVE CONDITION"), ("OVRID1", "OVERRIDE OPEN"),
            ("FDbk1", "OPENEND STATUS"), ("FDbk0", "CLOSED STATUS"), ("CMD1", "OPEN COMMAND"), ("CMD0", "CLOSE COMMAND")]
    rows = [(14, "AUTO OPEN"), (18, "OPEN PERMISSIVE CONDITION"), (26, "OVERRIDE OPEN"),
            (34, "OPENED STATUS"), (40, "CLOSED STATUS")]
    got = M._assign([("a", "AOPEN"), ("b", "ENOPEN"), ("c", "OVRD1"), ("d", "FDOPEN"), ("e", "FDCLOSE")], rows, abbr)
    assert {k: v[0] for k, v in got.items()} == {"a": 14, "b": 18, "c": 26, "d": 34, "e": 40}
    out = M._assign([("x", "CMD"), ("y", "CMDO")], [(69, "OPEN COMMAND"), (77, "CLOSE COMMAND")], abbr)
    assert out["x"][0] == 69 and out["y"][0] == 77                   # 끝 글자 못 읽음 · O/0 바꿔 읽음
    assert M.name_sim("CMD1", "CMD0") < M.NAME_MIN                   # 끝의 1/0 은 뜻이 반대
    assert M._type_code("MOV BLOCK (OPEN CLOSE) <TYPE-Ⅲ-1>") == "III-1"
    src = (ROOT / "app/logic/macro.py").read_text(encoding="utf-8")
    for word in ("A_OPEN", "EN_OPEN", "CMD1", "G012", "MOV BLOCK"):
        assert f'"{word}"' not in src


def test_macro_block_runs_its_typical_sheet_and_drives_its_outputs():
    P = lambda b, n, d, role="": {"block": b, "net": n, "dir": d, "role": role, "cell": 0}
    typ = _sheet(2, "T1", [{"n": 10, "side": "L", "net": "t1"}, {"n": 11, "side": "L", "net": "t2"},
                           {"n": 70, "side": "R", "net": "to", "desc": "OPEN COMMAND"}],
                 {"G": {"func": "AND", "logic": "and", "group": "", "param": {}}},
                 [P("G", "t1", "in"), P("G", "t2", "in"), P("G", "to", "out")])
    mac = {"func": "MACRO", "logic": "macro", "group": "", "param": {}, "label": "",
           "macro": {"sheet": "T1", "page": 2,
                     "inputs": [{"at": "0,1", "net": "p1", "pin": "A", "row": 10}, {"at": "0,2", "net": "p2", "pin": "B", "row": 11}],
                     "outputs": [{"at": "9,1", "net": "po", "pin": "CMD", "row": 70}]}}
    par = _sheet(1, "A1", [{"n": 1, "side": "L", "net": "p1"}, {"n": 2, "side": "L", "net": "p2"},
                           {"n": 80, "side": "R", "net": "po", "desc": "OPEN CMD"}],
                 {"M": mac}, [P("M", "p1", "in"), P("M", "p2", "in"), P("M", "po", "out")])
    v = lambda f: sim.simulate_bundle([par, typ], {1: f}, None, 1)
    assert v({"row:1": 1})["focus"]["frames"][-1]["values"]["po"] == 0          # AND — 하나만
    b = v({"row:1": 1, "row:2": 1})
    assert b["focus"]["frames"][-1]["values"]["po"] == 1                       # 둘 다 → 매크로 출력 1
    assert b["macros"][1]["M"]["inputs"] == {"10": 1, "11": 1} and b["macros"][1]["M"]["outputs"] == {"70": 1}


def test_activation_box_always_outputs_one():
    """범례 G003 ACTIVATION — 글자 '1' 상자: OUTPUT ALWAYS EXISTS."""
    blocks = {"A": {"func": "SIGNAL", "logic": "source", "group": "", "label": "1", "param": {}},
              "Z": {"func": "SIGNAL", "logic": "source", "group": "", "label": "0", "param": {}}}
    P = lambda b, n, d: {"block": b, "net": n, "dir": d, "role": "", "cell": 0}
    s = {"blocks": blocks, "ports": [P("A", "a", "out"), P("Z", "z", "out")], "rows": [], "nets": {"a": {"segs": []}, "z": {"segs": []}}}
    v = sim.simulate(s, {})["frames"][-1]["values"]
    assert v["a"] == 1 and v["z"] == 0
    assert sim.simulate(s, {"block:A": 0})["frames"][-1]["values"]["a"] == 0    # 사람이 0 으로 줄 수 있다


def test_forcing_one_connector_lights_its_partner():
    """L13 — 같은 글자 연결 기호(A ↔ A)는 한 신호: 한쪽을 1 로 주면 다른 쪽에서 나가는 선도 1."""
    P = lambda b, n, d: {"block": b, "net": n, "dir": d, "role": "", "cell": 0}
    blocks = {"C1": {"func": "CONNECTOR", "logic": "connector", "group": "A", "label": "A", "param": {}},
              "C2": {"func": "CONNECTOR", "logic": "connector", "group": "A", "label": "A", "param": {}}}
    s = {"blocks": blocks, "rows": [], "ports": [P("C1", "x", "out"), P("C2", "y", "out")],
         "nets": {"x": {"segs": []}, "y": {"segs": []}}}
    v = sim.simulate(s, {"net:x": 1})["frames"][-1]["values"]
    assert v["x"] == 1 and v["y"] == 1
    v = sim.simulate(s, {"block:C2": 1})["frames"][-1]["values"]
    assert v["x"] == 1 and v["y"] == 1


def test_forcing_a_gate_output_sets_its_inputs_logically():
    """L13 — AND 뒤를 1 로 주면 그 입력들은 AND 가 1 을 낼 수 있는 값으로 (NOT 을 지나면 반대로)."""
    P = lambda b, n, d: {"block": b, "net": n, "dir": d, "role": "", "cell": 0}
    blocks = {"N": {"func": "NOT", "logic": "not", "group": "", "param": {}},
              "G": {"func": "AND", "logic": "and", "group": "", "param": {}},
              "O": {"func": "OR", "logic": "or", "group": "", "param": {}}}
    ports = [P("N", "r3", "in"), P("N", "n3", "out"),
             P("G", "r1", "in"), P("G", "r2", "in"), P("G", "n3", "in"), P("G", "g", "out"),
             P("O", "r4", "in"), P("O", "r5", "in"), P("O", "o", "out")]
    rows = [{"n": k, "side": "L", "net": f"r{k}"} for k in (1, 2, 3, 4, 5)]
    s = {"blocks": blocks, "ports": ports, "rows": rows, "nets": {n: {"segs": []} for n in ("r1", "r2", "r3", "r4", "r5", "n3", "g", "o")}}
    r = sim.simulate(s, {"net:g": 1})
    assert r["implied"] == {"row:1": 1, "row:2": 1, "row:3": 0}
    v = r["frames"][-1]["values"]
    assert v["r1"] == v["r2"] == 1 and v["r3"] == 0 and v["n3"] == 1 and v["g"] == 1
    ro = sim.simulate(s, {"net:o": 1})                                   # L17 — OR=1: 입력 하나를 골라 앞으로 돌려 확인
    assert ro["choice"] == {"row:4": 1} and ro["implied"] == {"row:4": 1} and not ro["unmet"]
    assert ro["frames"][-1]["values"]["o"] == 1 and ro["frames"][-1]["values"]["r5"] == 0
    assert sim.simulate(s, {"net:o": 0})["implied"] == {"row:4": 0, "row:5": 0}
    r = sim.simulate(s, {"net:g": 1, "row:3": 1})                      # 사람이 준 값과 어긋나면 모순으로 말한다
    assert r["conflicts"] and r["implied"].get("row:3") is None


def test_logic_first_screen_projects_and_materials(tmp_path, monkeypatch):
    """L14 — 첫 화면: LOGIC 프로젝트는 실행 전용 · 자료 다섯 중 Logic 만 필수 · 나머지는 보관만."""
    from fastapi.testclient import TestClient
    from app import main
    from app.logic import api, run
    monkeypatch.setattr(api, "_start", run.run)
    client = TestClient(main.app)
    j = client.get("/logic/api/projects").json()
    kinds = [m["kind"] for m in j["materials"]]
    assert kinds == ["logic", "loop", "sysdesc", "iolist", "logictable"]
    assert [m["kind"] for m in j["materials"] if m["required"]] == ["logic"]
    assert client.post("/logic/api/projects", json={"name": "  "}).status_code == 400
    p = client.post("/logic/api/projects", json={"name": "HRSG PJT", "author": "홍길동"}).json()
    assert p["mode"] == "epc" and p["name"] == "HRSG PJT"
    assert client.post("/logic/api/projects", json={"name": "hrsg pjt"}).status_code == 409
    pdf = make_pdf(tmp_path / "up.pdf").read_bytes()
    # Logic 없이 다른 자료만 → 거절
    r = client.post("/logic/api/jobs", data={"project": "HRSG PJT"},
                    files={"iolist": ("io.xlsx", b"x", "application/octet-stream")})
    assert r.status_code == 400 and "필수" in r.json()["detail"]
    # 없는 프로젝트 → 거절 · 자료 확장자 틀림 → 거절
    assert client.post("/logic/api/jobs", data={"project": "없음"},
                       files={"logic": ("a.pdf", pdf, "application/pdf")}).status_code == 400
    assert client.post("/logic/api/jobs", data={"project": "HRSG PJT"},
                       files={"logic": ("a.pdf", pdf, "application/pdf"),
                              "iolist": ("io.exe", b"x", "application/octet-stream")}).status_code == 400
    r = client.post("/logic/api/jobs", data={"project": "HRSG PJT", "author": "홍길동"},
                    files={"logic": ("a.pdf", pdf, "application/pdf"),
                           "iolist": ("io.xlsx", b"io", "application/octet-stream")})
    assert r.status_code == 200, r.text
    job = r.json()["id"]
    assert r.json()["materials"] == {"logic": "a.pdf", "iolist": "io.xlsx"}
    for _ in range(200):
        st = client.get(f"/logic/api/jobs/{job}").json()
        if st["state"] in ("done", "failed"):
            break
        time.sleep(0.1)
    assert st["state"] == "done" and st["project"] == "HRSG PJT"
    jobs = client.get("/logic/api/jobs").json()["jobs"]
    me = next(x for x in jobs if x["id"] == job)
    assert me["project"] == "HRSG PJT" and set(me["materials"]) == {"logic", "iolist"}
    # Logic 만으로 분석한 것과 같은 결과 — 다른 자료는 판정에 닿지 않는다
    assert client.get(f"/logic/api/jobs/{job}/sheets").json()["sheets"]
    # 출력 행 동작 예시 API
    s = client.get(f"/logic/api/jobs/{job}/sheet/1").json()
    out = next((r for r in s["rows"] if r["side"] == "R" and r.get("net") is not None), None)
    if out:
        sc = client.post(f"/logic/api/jobs/{job}/sheet/1/scenario", json={"target": f"row:{out['n']}"}).json()
        assert "ok" in sc
    assert client.post(f"/logic/api/jobs/{job}/sheet/1/scenario", json={"target": "x"}).status_code == 400


def test_timer_default_is_ten_seconds_and_the_user_can_change_it():
    """L15 — 도면에 시간이 없는 타이머는 기본 10초 · 사람이 바꾼 시간이 이긴다 · 세는 타이머는 틀에 남는다."""
    s = _toy()
    s["blocks"]["PD"]["param"] = {}                                   # 도면이 시간을 적지 않았다
    assert sim.DEFAULT_T == 10.0
    r = sim.simulate(s, {"row:1": 1, "row:4": 1})
    assert r["frames"][-1]["t"] == pytest.approx(10.0)
    assert any("10초" in n for n in r["notes"])
    run = r["frames"][0]["running"]
    assert run == [{"block": "PD", "left": 10.0, "T": 10.0}], "세기 시작한 타이머 · 남은 시간"
    r = sim.simulate(s, {"row:1": 1, "row:4": 1}, timers={"PD": 3.5})
    assert r["frames"][-1]["t"] == pytest.approx(3.5) and not any("10초" in n for n in r["notes"])
    # 도면 값(2초)도 사람이 바꾼 값에 진다 · 틀린 값은 버린다
    s2 = _toy()
    assert sim.simulate(s2, {"row:1": 1, "row:4": 1}, timers={"PD": 7})["frames"][-1]["t"] == pytest.approx(7)
    assert sim.simulate(s2, {"row:1": 1, "row:4": 1}, timers={"PD": -1})["frames"][-1]["t"] == pytest.approx(2)
    # 묶음째 돌릴 때도 장마다 시간이 간다
    s2.update(page=3, sheet_no="G003")
    b = sim.simulate_bundle([s2], {3: {"row:1": 1, "row:4": 1}}, focus=3, timers={3: {"PD": 4}})
    assert b["focus"]["frames"][-1]["t"] == pytest.approx(4)


def test_activating_an_output_finds_and_flashes_the_inputs_it_needs():
    """L15 — 출력(행 · 블록이 모는 선)을 1 로 주면 범례 정의로 필요한 입력을 찾아 켜고 주황으로 3번 점등한다."""
    s = _toy()
    sc = sim.scenario(s, "net:5")                                      # AND 출력 = 블록이 모는 선
    assert sc["ok"] and {k for k, v in sc["forces"].items() if v == 1} >= {"row:4"}
    src = (Path(__file__).resolve().parents[1] / "app/static/logic.js").read_text(encoding="utf-8")
    assert "if (v === 1 && wantsScenario(key)) { activateOutput(key); return; }" in src
    assert "const NEED_FLASH = 3;" in src and "flashNeed(on)" in src
    assert 'type: "macro-need"' in src and "handleMacroNeed" in src, "매크로 새 창 ↔ 부모 창이 같이 활성화"
    assert "timers: L.timers" in src and "startCount(run)" in src, "타이머 시간을 보내고 실제로 센다"


def test_forcing_an_and_output_chains_back_and_never_bypasses_the_gate():
    """L16 — AND 출력을 1 로 주면 앞쪽 입력이 줄줄이 1 이 되고(AND ← AND ← 메모리 SET), 입력 하나라도 0 으로
    남으면 AND 출력은 나가지 않는다 (사용자 지시 — "12 · 14 번이 활성화 안 되었는데 AND 의 Output 이 나가면 안 된다")."""
    P = lambda b, n, d, role="": {"block": b, "net": n, "dir": d, "role": role, "cell": 0}
    blocks = {"A1": {"func": "AND", "logic": "and", "group": "", "param": {}},
              "A2": {"func": "AND", "logic": "and", "group": "", "param": {}},
              "M": {"func": "MEMORY", "logic": "memory", "group": "", "param": {}}}
    ports = [P("A2", "r1", "in"), P("A2", "r2", "in"), P("A2", "a2", "out"),
             P("M", "r3", "in", "set"), P("M", "r4", "in", "reset"), P("M", "q", "out", "q"),
             P("A1", "a2", "in"), P("A1", "q", "in"), P("A1", "r5", "in"), P("A1", "o", "out")]
    rows = [{"n": k, "side": "L", "net": f"r{k}"} for k in (1, 2, 3, 4, 5)] + [{"n": 74, "side": "R", "net": "o"}]
    s = {"blocks": blocks, "ports": ports, "rows": rows,
         "nets": {n: {"segs": []} for n in ("r1", "r2", "r3", "r4", "r5", "a2", "q", "o")}}
    r = sim.simulate(s, {"row:74": 1})
    assert r["implied"] == {"row:1": 1, "row:2": 1, "row:3": 1, "row:4": 0, "row:5": 1}
    v = r["frames"][-1]["values"]
    assert v["o"] == 1 and v["a2"] == 1 and v["q"] == 1 and not r["unmet"]
    # 사람이 입력 하나(5행)를 0 으로 두면 AND 는 1 을 내지 않는다 — 출력을 직접 켜지 않는다
    r = sim.simulate(s, {"row:74": 1, "row:5": 0})
    assert r["frames"][-1]["values"]["o"] == 0
    assert r["unmet"] and r["unmet"][0]["block"] == "A1" and r["conflicts"]
    # 선(net) 으로 줘도 같다
    assert sim.simulate(s, {"net:o": 1, "row:2": 0})["frames"][-1]["values"]["o"] == 0


def test_reset_all_clears_every_forced_signal_in_the_screen():
    """L16 — 강제 신호 전체 리셋 단추: 모든 시트의 강제 · 상태 · 거꾸로 맞춘 값 · 예시를 지운다."""
    js = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")
    html = (ROOT / "app/static/logic.html").read_text(encoding="utf-8")
    assert "강제 신호 전체 리셋" in html and '$("#reset").onclick = resetAll' in js
    body = js[js.index("function resetAll()"):js.index("function setForce(")]
    for k in ("L.allForces = {}", "L.states = {}", "L.implied = {}", "L.scenario = null"):
        assert k in body


def test_forcing_an_output_chains_through_the_sheet_that_sends_its_input():
    """L16 — 출력 조건에 다른 시트에서 오는 입력이 있으면 그 시트의 출력까지 줄줄이 켠다 (그 시트의 게이트가 막으면 머문다)."""
    P = lambda b, n, d: {"block": b, "net": n, "dir": d, "role": "", "cell": 0}
    A = _sheet(1, "A1", [{"n": 1, "side": "L", "net": "a1"}, {"n": 2, "side": "L", "net": "a2"},
                         {"n": 50, "side": "R", "net": "ao", "desc": "READY"}],
               {"G": {"func": "AND", "logic": "and", "group": "", "param": {}}},
               [P("G", "a1", "in"), P("G", "a2", "in"), P("G", "ao", "out")])
    C = _sheet(3, "C1", [{"n": 6, "side": "L", "net": "c6", "ref": {"page": 1, "row": 50}},
                         {"n": 7, "side": "L", "net": "c7"}, {"n": 40, "side": "R", "net": "co"}],
               {"G": {"func": "AND", "logic": "and", "group": "", "param": {}}},
               [P("G", "c6", "in"), P("G", "c7", "in"), P("G", "co", "out")])
    b = sim.simulate_bundle([A, C], {3: {"row:40": 1}}, None, 3)
    assert b["focus"]["frames"][-1]["values"]["co"] == 1
    assert b["chain_forces"] == {1: {"row:50": 1}}
    assert b["pulled"][0]["from_sheet"] == "A1" and b["pulled"][0]["row"] == 6
    # 보내는 시트의 입력을 사람이 0 으로 두면 그 시트 AND 가 막고 — 뒤 시트 출력도 나가지 않는다
    b = sim.simulate_bundle([A, C], {3: {"row:40": 1}, 1: {"row:1": 0}}, None, 3)
    assert b["focus"]["frames"][-1]["values"]["co"] == 0 and b["focus"]["unmet"]


def test_forcing_any_gate_output_reaches_it_only_through_its_inputs():
    """L17 — AND 뿐 아니라 모든 게이트: 출력 행을 1/0 으로 주면 범례 정의로 입력을 골라(정해지지 않으면 갈래 하나를
    앞으로 돌려 확인) 게이트가 그 값을 낸다.  게이트 출력이 입력과 어긋나는 일은 없다."""
    def run(s, v, **kw):
        r = sim.simulate(s, {"row:90": v}, **kw)
        fr = r["frames"]
        ins = {p["net"] for p in s["ports"] if p["dir"] == "in"}
        return r, fr[-1]["values"], [f["values"]["o"] for f in fr], ins

    for lg, n in (("and", 3), ("or", 3), ("nand", 3), ("nor", 3), ("not", 1)):
        for v in (1, 0):
            s = _one(lg, n)
            r, val, outs, _ = run(s, v)
            assert not r["unmet"] and val["o"] == v, (lg, v)
            iv = [val[f"i{k}"] for k in range(n)]
            assert sim.gate3(lg, iv) == v, (lg, v, iv)               # 게이트가 낸 값 — 직접 켠 것이 아니다
    # OR=1 · NOR=0 은 입력 **하나**만 고른다 (나머지는 0 그대로)
    for lg, v in (("or", 1), ("nor", 0)):
        r, val, _, _ = run(_one(lg, 3), v)
        assert sum(val[f"i{k}"] for k in range(3)) == 1 and len(r["choice"]) == 1
    # 사람이 0 으로 준 입력은 고르지 않고 다른 입력을 고른다
    r = sim.simulate(_one("or", 3), {"row:90": 1, "row:1": 0})
    assert not r["unmet"] and r["frames"][-1]["values"]["i0"] == 0
    # 투표 2/3 — 두 입력을 1 로
    r, val, _, _ = run(_one("unknown", 3, label="2/3"), 1)
    assert not r["unmet"] and sum(val[f"i{k}"] for k in range(3)) == 2
    # 타이머 — GT 는 t초 뒤 · PD 는 입력이 1 로 바뀌는 순간
    for lg in ("delay_on", "pulse", "delay_off"):
        r, val, outs, _ = run(_one(lg, 1, param={"t": 2}), 1)
        assert not r["unmet"] and 1 in outs and val["i0"] == 1, lg
    # 입력이 하나뿐인 AND — 조건을 확인할 수 없어 1 을 내지 않는다 (L10) · 블록 자체를 눌러도 같다
    r, val, _, _ = run(_one("and", 1), 1)
    assert r["unmet"] and val["o"] == 0
    r = sim.simulate(_one("and", 0), {"block:G": 1})
    assert r["unmet"] and r["frames"][-1]["values"]["o"] == 0


def test_forcing_a_latched_memory_to_zero_resets_it():
    """L17 — 이미 SET 된 래치의 Q 를 0 으로 주면 RESET 입력을 1 로 (범례 G003 메모리)."""
    P = lambda b, n, d, role="": {"block": b, "net": n, "dir": d, "role": role, "cell": 0}
    blocks = {"M": {"func": "MEMORY", "logic": "memory", "group": "", "label": "", "param": {}}}
    ports = [P("M", "s", "in", "set"), P("M", "r", "in", "reset"), P("M", "o", "out", "q")]
    rows = [{"n": 1, "side": "L", "net": "s"}, {"n": 2, "side": "L", "net": "r"}, {"n": 90, "side": "R", "net": "o"}]
    s = {"blocks": blocks, "ports": ports, "rows": rows, "nets": {n: {"segs": []} for n in "sro"}}
    on = sim.simulate(s, {"row:90": 1})
    assert not on["unmet"] and on["frames"][-1]["values"]["s"] == 1 and on["frames"][-1]["values"]["o"] == 1
    off = sim.simulate(s, {"row:90": 0}, state=on["state"])
    v = off["frames"][-1]["values"]
    assert not off["unmet"] and v["o"] == 0 and v["r"] == 1 and v["s"] == 0


def test_no_gate_ever_outputs_against_its_inputs_random_circuits():
    """L18 — 사용자 확정: *앞으로 모든 Logic 의 논리 게이트는 논리적으로 동작해야 한다.*  무작위 회로 300개에 무작위
    강제(입력 행 · 게이트 출력 선 · 게이트 블록)를 줘도 **모든 틀**에서 AND·OR·NAND·NOR·NOT·투표의 출력이 그 틀의
    입력으로 범례 G003 이 내는 값과 같다 (출력 선을 직접 켜서 건너뛰는 일이 없다)."""
    import random
    rnd = random.Random(17)
    P = lambda b, n, d, role="": {"block": b, "net": n, "dir": d, "role": role, "cell": 0}
    kinds = ["and", "or", "nand", "nor", "not", "vote", "memory", "delay_on", "pulse"]
    for case in range(300):
        nets = [f"r{k}" for k in range(1, 6)]
        rows = [{"n": k, "side": "L", "net": f"r{k}"} for k in range(1, 6)]
        blocks, ports = {}, []
        for i in range(rnd.randint(2, 7)):
            lg = rnd.choice(kinds)
            bid, out = f"B{i}", f"o{i}"
            k = 1 if lg in ("not", "delay_on", "pulse") else (3 if lg == "vote" else rnd.randint(2, 3))
            src = rnd.sample(nets, min(k, len(nets)))
            b = {"func": lg.upper(), "logic": "unknown" if lg == "vote" else lg, "group": "",
                 "label": "2/3" if lg == "vote" else "", "param": {"t": 1} if lg in ("delay_on", "pulse") else {}}
            blocks[bid] = b
            if lg == "memory":
                ports += [P(bid, src[0], "in", "set"), P(bid, src[1], "in", "reset"), P(bid, out, "out", "q")]
            else:
                ports += [P(bid, n, "in") for n in src] + [P(bid, out, "out")]
            nets.append(out)
        rows.append({"n": 90, "side": "R", "net": nets[-1]})
        s = {"blocks": blocks, "ports": ports, "rows": rows, "nets": {n: {"segs": []} for n in nets}}
        forces = {}
        for _ in range(rnd.randint(1, 3)):
            pick = rnd.choice(["row", "net", "block", "out"])
            v = rnd.randint(0, 1)
            if pick == "row":
                forces[f"row:{rnd.randint(1, 5)}"] = v
            elif pick == "net":
                forces[f"net:{rnd.choice(nets[5:])}"] = v
            elif pick == "block":
                forces[f"block:{rnd.choice(list(blocks))}"] = v
            else:
                forces["row:90"] = v
        r = sim.simulate(s, forces)
        ins, outs, drivers, _, _ = sim._index(s)
        for fr in r["frames"]:
            unread = set(fr["unread"])
            val = lambda n: None if n in unread else fr["values"].get(n, 0)
            for bid, b in blocks.items():
                vt = sim._vote_of(b)
                if b["logic"] not in sim.MIN_INPUTS and not vt:
                    continue
                iv = [val(n) for n, _, _ in ins[bid]]
                exp = sim._vote3(iv, *vt) if vt else sim.gate3(b["logic"], iv)
                for n, _, _ in outs[bid]:
                    assert fr["values"].get(n, 0) == (exp or 0), (case, forces, bid, b["logic"], iv)


def test_status_popup_lists_given_signals_and_resulting_outputs():
    """L19 — 신호 현황 팝업: 사람이 준 신호(모든 시트)와 그에 따라 1 이 된 출력 행을 설명 · TO 와 함께 낸다.
    신호가 닿았는데 게이트가 막은 시트는 받은 입력이 남는다.  화면은 머리줄을 끌어 옮기고 자리를 기억한다."""
    P = lambda b, n, d: {"block": b, "net": n, "dir": d, "role": "", "cell": 0}
    A = _sheet(1, "A1", [{"n": 95, "side": "R", "net": "a", "desc": "READY", "to": "C1-6"}])
    C = _sheet(3, "C1", [{"n": 6, "side": "L", "net": "c6", "desc": "IN6", "fm": "A1-95"},
                         {"n": 7, "side": "L", "net": "c7", "desc": "IN7"},
                         {"n": 40, "side": "R", "net": "co", "desc": "OUT", "to": ""}],
               {"G": {"func": "AND", "logic": "and", "group": "", "param": {}}},
               [P("G", "c6", "in"), P("G", "c7", "in"), P("G", "co", "out")])
    b = sim.simulate_bundle([A, C], {1: {"row:95": 1}}, None, 1)
    pg = {c["sheet_no"]: c for c in b["pages"]}
    assert pg["A1"]["forced"] == [{"key": "row:95", "value": 1, "kind": "row", "row": 95, "side": "R",
                                   "desc": "READY", "ref": "C1-6"}]
    assert [x["row"] for x in pg["A1"]["outputs"]] == [95]
    assert pg["C1"]["outputs"] == [] and [x["desc"] for x in pg["C1"]["inputs"]] == ["IN6"]   # AND 가 막았다
    b = sim.simulate_bundle([A, C], {1: {"row:95": 1}, 3: {"row:7": 1}}, None, 1)
    pg = {c["sheet_no"]: c for c in b["pages"]}
    assert pg["C1"]["outputs"][0]["desc"] == "OUT" and pg["C1"]["outputs"][0]["ref"] == ""      # 최종 출력
    assert pg["C1"]["forced"][0]["desc"] == "IN7"
    js = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")
    html = (ROOT / "app/static/logic.html").read_text(encoding="utf-8")
    assert 'id="sigpop"' in html and 'id="sig-toggle"' in html
    body = js[js.index("function renderSigPop()"):js.index("function renderFindings()")]
    assert "pointerdown" in body and "SIGPOP_POS" in body and "goToRef" in body
    assert "fetch(" not in body and "post(" not in body       # 서버가 낸 값을 읽기만 한다
    assert "data-off" in body and "unforce(" in body                    # 다른 시트의 신호도 이 창에서 끈다
    uf = js[js.index("function unforce("):js.index("function placeSigPop(")]
    assert "delete f[key]" in uf and "runSim(" in uf
    rc = js[js.index("function renderChain()"):js.index("function renderFindings()")]
    assert "renderSigPop()" in rc


def test_status_write_survives_windows_lock(tmp_path, monkeypatch):
    """L20 — Windows 에서 화면이 status.json 을 읽는 순간 os.replace 가 WinError 5 로 거절돼도 분석은 멈추지 않는다."""
    from app.logic import store
    monkeypatch.setattr(store, "REPLACE_WAIT", 0.0)
    real = os.replace
    calls = {"n": 0}

    def flaky(a, b):
        calls["n"] += 1
        if calls["n"] <= 3:
            raise PermissionError(5, "Access is denied")
        return real(a, b)

    monkeypatch.setattr(store.os, "replace", flaky)
    store.write_status(tmp_path, {"state": "running", "done": 1})
    assert store.read_status(tmp_path)["done"] == 1
    assert not list(tmp_path.glob("*.tmp*"))

    def always(a, b):
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(store.os, "replace", always)
    store.write_status(tmp_path, {"state": "running", "done": 2})     # 예외 없이 — 자리에 바로 쓴다
    assert store.read_status(tmp_path)["done"] == 2
    assert not list(tmp_path.glob("*.tmp*"))
    (tmp_path / "status.json").write_text("{깨진", encoding="utf-8")
    assert store.read_status(tmp_path)["done"] == 2                 # 반쯤 쓴 글이면 직전 상태


def test_analysis_finishes_even_if_every_file_swap_is_refused(tmp_path, monkeypatch):
    """L20 (둘째) — 현장에서 고친 뒤에도 같은 문장으로 멈췄다.  바꿔 넣기가 **매번** 거절돼도 분석은 끝까지 가고 '완료' 가 남는다."""
    from app.logic import run, store
    monkeypatch.setattr(store, "REPLACE_WAIT", 0.0)

    def always(a, b):
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(store.os, "replace", always)
    d = tmp_path / "abcdef012345"
    d.mkdir()
    make_pdf(d / "source.pdf")
    (d / "status.json").write_text('{"state": "queued"}', encoding="utf-8")
    run.run(d)
    st = store.read_status(d)
    assert st["state"] == "done", st
    assert store.read_result(d)["sheets"]
    assert not list(d.glob("*.tmp*"))
