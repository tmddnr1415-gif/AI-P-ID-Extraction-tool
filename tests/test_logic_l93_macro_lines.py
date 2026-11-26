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


def test_memory_priority_mark_is_still_read():
    """메모리의 우선 칸(S 또는 R 를 두른 원 · 범례 'A CIRCLE AROUND S OR R') — L93 의 뒤집기 규칙을 넣으며 이 표시 읽기가 끊겼었다
    (19VA 메모리 115개가 전부 '우선 없음' 이 되어 S · R 이 함께 1 일 때 RESET 우선 대신 상태를 뒤집었다)."""
    y = T + 4 * P
    doc = _doc([{"id": "m", "kind": "MEMORY", "x": 500, "y": y - P, "w": 13.7, "h": 2 * P, "text": "", "label": "", "param": {"dominant": ""}}],
               [{"id": "w1", "pts": [[draw.LX0, y - P / 2], [500, y - P / 2]]}, {"id": "w2", "pts": [[draw.LX0, y + P / 2], [500, y + P / 2]]},
                {"id": "w3", "pts": [[513.7, y - P / 2], [draw.LX1, y - P / 2]]}])

    def edit(pg):                                                                                 # 아래 칸(R)에 내접한 원 — 19VA 가 그리는 그대로
        sh = pg.new_shape()
        sh.draw_circle(pymupdf.Point(500 + 13.7 / 2, y + P / 2), P / 2 - 0.3)
        sh.finish(color=(0, 0, 0), width=0.71)
        sh.commit()
    plain = _analyse_pdf(draw.to_pdf(doc))
    marked = _analyse_pdf(draw.to_pdf(doc), edit)
    dom = lambda sh: [(b["param"] or {}).get("dominant") for b in sh["blocks"].values() if b["logic"] == "memory"]
    assert dom(plain) == [""] and dom(marked) == ["reset"], (dom(plain), dom(marked))


def test_vote_equal_sign_means_exactly_when_the_document_also_prints_ge():
    """L95 — `2=3` 은 문서가 '이상' 을 `≥` 로 따로 찍을 때 '정확히 2 개' (19VA CO01_G014: `2≥3` 과 `2=3` 이 같은 입력에 나란히 · 출력 'TWO CEP RUNNING').
    부등호 글자가 없는 문서(1A5J — '≥' 의 밑줄이 획이라 글자로는 `=`)는 예전대로 '이상'."""
    from app.logic import analyse, sim
    mk = lambda *labels: [{"blocks": {f"B{i}": {"logic": "vote", "label": t, "param": {"a": int(t[0]), "b": 3, "op": "ge"}} for i, t in enumerate(labels)}}]
    both = mk("2=3", "1=3", "2≥3")
    analyse._vote_equal_sign(both)
    assert [b["param"]["op"] for b in both[0]["blocks"].values()] == ["eq", "eq", "ge"]
    only = mk("2=3", "1=3")
    analyse._vote_equal_sign(only)
    assert [b["param"]["op"] for b in only[0]["blocks"].values()] == ["ge", "ge"]
    # L99 — 그림은 '이상' 을 `2/3` 으로 그린다: 똑같이 그린 묶음을 PDF 로 내어 다시 올려도 `2=3` 은 '정확히' 로 남아야 한다
    drawn = mk("2=3", "2/3")
    analyse._vote_equal_sign(drawn)
    assert [b["param"]["op"] for b in drawn[0]["blocks"].values()] == ["eq", "ge"]
    # 세 대가 다 돌면 'TWO RUNNING' · 'ONE RUNNING' 은 0 이어야 한다
    assert sim._vote3([1, 1, 1], 2, 3, "eq") == 0 and sim._vote3([1, 1, 0], 2, 3, "eq") == 1 and sim._vote3([1, 0, 0], 1, 3, "eq") == 1
