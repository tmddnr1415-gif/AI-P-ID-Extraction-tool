"""L66 — LOGIC 작도: 눈금자 가이드선 · 점과 점 자동 경로 · 선 건너뛰기(화면) · 기호 색(화면) · 입력 수 · 겹침 비키기.

* 가이드선 · 건너뛰기 · 색은 화면 전용이다 — PDF · DXF 는 학습한 양식 그대로 흑백 · 그냥 교차
* 꺾임점에서 세 갈래로 갈라진 선은 시뮬레이션에서도 한 그물 (분석기는 맞닿은 토막 끝을 잇는다)
"""
from __future__ import annotations

from pathlib import Path

import pymupdf

from app.logic import draw, draw_sim

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app" / "static" / "logic_draw.js").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "static" / "logic_draw.css").read_text(encoding="utf-8")
HTML = (ROOT / "app" / "static" / "logic_draw.html").read_text(encoding="utf-8")


def _crossing_doc():
    N = 50
    ry = lambda n: draw.ry(n, N)
    d = draw.new_doc("x", "tester", N=N)
    d["form"] = "a5j"
    d["sheet_no"], d["title"], d["doc_no"] = "LD-1", "HOP", "19VA-00GEN00-J09-9999"
    d["left"] = {"1": {"desc": "A"}, "3": {"desc": "B"}}
    d["right"] = {str(N + 3): {"desc": "OA"}, str(N + 5): {"desc": "OB"}}
    d["wires"] = [{"id": "w1", "pts": [[draw.LX0, ry(3)], [draw.LX1, ry(3)]]},
                  {"id": "w2", "pts": [[draw.LX0, ry(1)], [600, ry(1)], [600, ry(5)], [draw.LX1, ry(5)]]}]
    for k in ("AND", "OR", "NOT", "GT", "MEMORY", "PB", "ANN", "CONN"):
        spec = draw.SYMBOLS[k]
        d["blocks"].append({"id": f"b{len(d['blocks']) + 1}", "kind": k, "x": 400 + 50 * len(d["blocks"]), "y": ry(20),
                            "w": spec["w"], "h": spec["h"], "text": spec["text"], "label": "", "param": {}})
    return d


def test_pdf_stays_black_and_crossings_stay_plain():
    """화면의 색 · 건너뛰기 반원은 PDF 에 없다 — 흑백 · 교차는 그냥 지나간다 (범례 G003: 몸통 교차 = 연결 아님)."""
    d = _crossing_doc()
    page = pymupdf.open(stream=draw.to_pdf(d), filetype="pdf")[0]
    cols = set()
    for dr in page.get_drawings():
        for c in (dr.get("color"), dr.get("fill")):
            if c:
                cols.add(tuple(round(v, 3) for v in c))
    assert cols <= {(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)}, cols
    # 교차 자리(600, 3행) 둘레에 곡선이 없다 — 반원은 화면에서만
    y = draw.ry(3, 50)
    for dr in page.get_drawings():
        r = dr["rect"]
        if r.x0 <= 606 and r.x1 >= 594 and r.y0 <= y + 1 and r.y1 >= y - 6:
            assert all(it[0] != "c" for it in dr["items"]), dr["items"]
    v = draw.verify(d)
    assert v["dangling"] == 0


def test_corner_branch_joins_in_simulation():
    """다른 선의 꺾임점에서 시작한 선은 그 선과 한 그물 (예전엔 끝 · 몸통만 보아 꺾임 갈래가 끊겼다)."""
    N = 50
    ry = lambda n: draw.ry(n, N)
    d = draw.new_doc("x", "t", N=N)
    d["left"] = {"2": {"desc": "IN"}}
    d["right"] = {str(N + 2): {"desc": "O1"}, str(N + 6): {"desc": "O2"}}
    d["wires"] = [{"id": "w1", "pts": [[draw.LX0, ry(2)], [600, ry(2)], [600, ry(4)], [draw.LX1 - 40, ry(4)], [draw.LX1 - 40, ry(2)], [draw.LX1, ry(2)]]},
                  {"id": "w2", "pts": [[600, ry(4)], [600, ry(6)], [draw.LX1, ry(6)]], "dots": [[600, ry(4)]]}]
    sh = draw_sim.to_sheet(d, 1)
    nets = {(r["side"], r["n"]): r["net"] for r in sh["rows"]}
    assert nets[("L", 2)] == nets[("R", N + 2)] == nets[("R", N + 6)]
    r = draw_sim.simulate([d], d["id"], forces={d["id"]: {"row:2": 1}})
    outs = {o["row"] for o in r["pages"][0]["outputs"]}
    assert {N + 2, N + 6} <= outs


def test_ruler_guides_are_screen_only():
    for name in ("rgStart", "bindRGuides", "drawRGuides", "rgSnapVal", "rgLoad", "rgSave"):
        assert f"function {name}(" in JS
    assert '"logic.draw.rg."' in JS                                   # 그림마다 브라우저에 기억 — 그림 파일에 안 들어간다
    assert "pointer-events: auto" in CSS.split(".dw-ruler {")[1].split("}")[0]   # 눈금자를 누를 수 있다
    assert 'id="rg-clear"' in HTML
    for k in ("rg", "guides", "ruler"):
        assert f'"{k}"' not in (ROOT / "app" / "logic" / "draw.py").read_text(encoding="utf-8")
    # 기호를 옮기거나 선의 점을 찍을 때 가이드선에 붙는다
    assert 'tx.push([v, [v, L.TOP, v, L.bottom], "guide"])' in JS and '"guide"]' in JS
    assert "rgNear(S.rg.v, p[0], gtol)" in JS


def test_point_to_point_router_rules():
    body = JS.split("function routeAStar(")[1].split("\nfunction routeCandidates(")[0]
    assert "p[0] <= L.LX0 + 0.3 || p[0] >= L.LX1 - 0.3" in body        # 표 경계를 따라가지 않는다 (행 자리를 다 잇는다)
    assert "CL = 0.13 * P" in body                                     # 분석기 허용치(0.08P)보다 넉넉히 띄운다
    assert "onBody(i, j)" in body                                      # 남의 선 몸통 위에서는 꺾지 않는다 (꺾으면 잇게 된다)
    assert "segInBox(p, q, bx)" in body                                # 기호 변을 따라 달리지 않는다
    assert "ownSegs" in body                                           # 같은 신호 선에서 갈라진다 (점)
    assert "routeAStar(a, b, endKind" in JS                            # 추천 경로 후보의 첫째
    assert "function onWireCorner(" in JS


def test_hops_are_drawn_on_screen():
    assert "function hopsOf(" in JS and "function hopPath(" in JS
    assert "A${r},${r} 0 0 ${sw}" in JS                                # 위로 볼록한 반원
    assert "hops.length ? el(\"path\"" in JS


def test_gate_colours_and_depth_on_screen_only():
    for cat in ("gate", "time", "mem", "src", "sink", "conn", "box", "macro"):
        assert f'id="gd-{cat}"' in HTML and f".blk.c-{cat}" in CSS
    assert "function blkCat(" in JS and '"blk c-" + blkCat(b.kind)' in JS
    assert "drop-shadow" in CSS.split("#blocks {")[1].split("}")[0]
    assert "body.dw-dragging #blocks { filter: none; }" in CSS        # 끄는 동안은 가볍게


def test_inputs_rows_and_clash():
    assert "function setInputs(" in JS and 'id="p-nin"' in JS
    assert "function alignPortsToRows(" in JS and "function portRowShift(" in JS
    assert "if (spec.bar && !spec.ab) setInputs(b, 2);" in JS          # 막대 게이트는 입력 둘로 시작
    assert "function clashes(" in JS and "function unclash(" in JS
    # 새 그림 창의 제목 칸이 대화상자 제목(#m-title)과 같은 id 를 쓰던 결함
    assert 'id="m-dtitle"' in JS and 'input id="m-title"' not in JS
