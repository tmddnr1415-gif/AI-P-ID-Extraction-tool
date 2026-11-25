"""L93 — 매크로 안쪽(Typical) 선이 신호를 주면 서는가: 19VA Typical 22장을 `spike/macro_line_sweep_l93.py` 로 전수 켜 보며 찾은 분석기 빈틈의 규칙들.

전체 수(22장 · 선 939 · 켜짐)는 원본 PDF 로 그 스크립트가 잰다 — 여기서는 규칙마다 작은 그림으로 본다."""
import os
import tempfile

import pymupdf

from app.logic import analyse as AN
from app.logic import draw

P, T = draw.PITCH, draw.TOP


def _doc(blocks, wires, left=None, right=None):
    doc = draw.new_doc("p", "t", "", 59)
    doc["form"] = "a5j"
    doc["blocks"], doc["wires"] = blocks, wires
    doc["left"], doc["right"] = left or {}, right or {}
    return {**doc, **draw.clean(doc)}


def _analyse_pdf(pdf_bytes, edit=None):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "d.pdf")
        d = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        if edit:
            edit(d[0])
        d.save(p)
        return AN.analyse(p)["sheets"][0]


def test_reversed_not_is_read_right_to_left():
    """⊠ 는 좌우가 같은 모양이다 — 왼쪽 선을 모는 것이 없고 오른쪽 선은 행이 몰고 있으면 신호는 오른쪽에서 들어와 왼쪽으로 나간다
    (19VA Typical MTS 의 CLOSE COMMAND 쪽 NOT · SWGR · MIT)."""
    y1, y2 = T + 3 * P - P / 2, T + 8 * P - P / 2
    nx = 560
    blocks = [{"id": "n", "kind": "NOT", "x": nx, "y": y2 - 4.5, "w": 9, "h": 9, "text": "NOT", "label": "", "param": {}},
              {"id": "a", "kind": "AND", "x": 450, "y": y2 + 3 * P - 7, "w": 14, "h": 14, "text": "AND", "label": "", "param": {}}]
    ya = y2 + 3 * P
    wires = [{"id": "w1", "pts": [[draw.LX0, y1], [640, y1], [640, y2], [nx + 9, y2]]},          # 왼쪽 3행 → 돌아서 NOT 의 **오른쪽**으로
             {"id": "w2", "pts": [[nx, y2], [420, y2], [420, ya], [450, ya]]},                    # NOT 의 왼쪽 → AND 의 입력 막대
             {"id": "w3", "pts": [[464, ya], [draw.LX1, ya]]}]
    doc = _doc(blocks, wires, {"3": {"fm": "", "kks": "", "desc": "IN"}}, {str(59 + 11): {"desc": "OUT", "kks": "", "to": ""}})
    s = _analyse_pdf(draw.to_pdf(doc))
    nb = next(k for k, b in s["blocks"].items() if b["func"] == "NOT")
    d = {q["side"]: q["dir"] for q in s["ports"] if q["block"] == nb}
    assert d == {"L": "out", "R": "in"}, d
    from app.logic import sim
    out_row = next(r for r in s["rows"] if r["side"] == "R")
    v0 = sim.simulate(s, {})["frames"][-1]["values"][out_row["net"]]
    v1 = sim.simulate(s, {"row:3": 1})["frames"][-1]["values"][out_row["net"]]
    assert (v0, v1) == (1, 0)                                                                     # 입력 0 → NOT 1 → AND 1 · 입력 1 → 0


def test_plain_not_is_not_flipped():
    y = T + 3 * P - P / 2
    doc = _doc([{"id": "n", "kind": "NOT", "x": 500, "y": y - 4.5, "w": 9, "h": 9, "text": "NOT", "label": "", "param": {}}],
               [{"id": "w1", "pts": [[draw.LX0, y], [500, y]]}, {"id": "w2", "pts": [[509, y], [draw.LX1, y]]}],
               {"3": {"fm": "", "kks": "", "desc": "IN"}}, {str(59 + 3): {"desc": "OUT", "kks": "", "to": ""}})
    s = _analyse_pdf(draw.to_pdf(doc))
    (nb, b), = s["blocks"].items()
    assert {q["side"]: q["dir"] for q in s["ports"] if q["block"] == nb} == {"L": "in", "R": "out"}


def test_hop_over_a_slightly_slanted_line_still_joins():
    """다른 선을 넘는 뜀(반원)의 틈 — 지나가는 가로선이 0.25pt 기울어 있어도 같은 선으로 잇는다 (19VA Typical SOV)."""
    y = T + 6 * P - P / 2
    doc = _doc([], [{"id": "w1", "pts": [[draw.LX0, y], [draw.LX1, y + 0.25]]}],                 # 거의 가로 (LOGIC 폭에 0.25pt)
               {"6": {"fm": "", "kks": "", "desc": "A"}}, {str(59 + 6): {"desc": "A OUT", "kks": "", "to": ""}})
    x = 500.0

    def edit(pg):
        sh = pg.new_shape()                                                                       # 세로선: 위 토막 · 틈(뜀 2.8pt) · 아래 토막
        sh.draw_line(pymupdf.Point(x, y - 4 * P), pymupdf.Point(x, y - 1.3))
        sh.draw_line(pymupdf.Point(x, y + 1.5), pymupdf.Point(x, y + 4 * P))
        sh.finish(color=(0, 0, 0), width=0.71)
        sh.commit()
    s = _analyse_pdf(draw.to_pdf(doc), edit)
    vert = [n for n in s["nets"].values() if any(abs(sg[0] - x) < 0.5 and abs(sg[2] - x) < 0.5 for sg in n["segs"])]
    assert len(vert) == 1 and len([sg for sg in vert[0]["segs"] if abs(sg[0] - x) < 0.5]) == 2      # 두 토막이 한 그물
    assert len(s["nets"]) == 2                                                                    # 지나가는 가로선과는 잇지 않는다


def test_hairline_outline_of_a_filled_arrowhead_is_not_a_line():
    """칠한 화살촉의 테두리를 굵기 0 인 획으로 한 번 더 그린 양식 — 그 테두리가 '몰이 없는 선' 으로 블록에 붙지 않는다 (19VA Typical PS3)."""
    y = T + 3 * P - P / 2
    doc = _doc([{"id": "g", "kind": "PD", "x": 500, "y": y - P / 2, "w": 1.15 * P, "h": P, "text": "PD", "label": "", "param": {"t": 1}}],
               [{"id": "w1", "pts": [[draw.LX0, y], [500, y]]}, {"id": "w2", "pts": [[500 + 1.15 * P, y], [draw.LX1, y]]}],
               {"3": {"fm": "", "kks": "", "desc": "IN"}}, {str(59 + 3): {"desc": "OUT", "kks": "", "to": ""}})
    tri = [pymupdf.Point(494.4, y - 0.9), pymupdf.Point(494.4, y + 0.9), pymupdf.Point(500, y)]   # 길이 5.6pt — 글자 크기(0.45P)를 넘는다

    def edit(pg):
        sh = pg.new_shape()
        sh.draw_polyline(tri + [tri[0]])
        sh.finish(color=None, fill=(0, 0, 0), width=0)
        sh.commit()
        sh = pg.new_shape()
        sh.draw_line(tri[0], tri[1]); sh.draw_line(tri[1], tri[2]); sh.draw_line(tri[2], tri[0])
        sh.finish(color=(0, 0, 0), width=0)
        sh.commit()
    base = _analyse_pdf(draw.to_pdf(doc))
    s = _analyse_pdf(draw.to_pdf(doc), edit)
    key = lambda sh: {(q["block"], q["net"], q["dir"]) for q in sh["ports"]}
    assert len(s["nets"]) == len(base["nets"]) == 2 and key(s) == key(base) and not s.get("dangling")   # 테두리 획이 새 그물 · 새 단자를 만들지 않는다
