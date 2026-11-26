"""L97 — 판독 안 되던 짧은 파선: 블록 사이를 잇는 토막 둘 · 셋짜리 파선 (19VA 제어 루프 장의 ⊠ → SPC 단자 · ⊠ → 표시등 · 0006/0007 의 ⊠ → AND).

원인 넷 (전부 `graph._dash_chains`): ① 첫 · 끝 토막이 반 토막이라 '고르지 않다' 로 버림 ② 짧은 파선은 끝을 화살촉 토막 · 블록 변까지 이어 주지 않음
③ 살짝 기운 토막(4.5pt 에 0.04pt)은 가로 토막으로 치지 않음 ④ 꺾인 파선은 선분마다 무늬를 새로 시작하는데 모퉁이에서 이어 주지 않음.
전체 수(827장 — 출력 없는 연산자 161 → …)는 원본 PDF 로 잰다 (기록 L97) — 여기서는 원인마다 작은 그림으로 본다."""
import os
import tempfile

import pymupdf

from app.logic import analyse as AN
from app.logic import draw, sim

P, T = draw.PITCH, draw.TOP
D, G = 5.67, 2.8                     # 19VA 의 토막 · 틈 (pt)


def _doc(blocks, wires, left=None, right=None):
    doc = draw.new_doc("p", "t", "", 59)
    doc["form"] = "a5j"
    doc["blocks"], doc["wires"] = blocks, wires
    doc["left"], doc["right"] = left or {}, right or {}
    return {**doc, **draw.clean(doc)}


def _analyse(doc, edit):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "d.pdf")
        d = pymupdf.open(stream=draw.to_pdf(doc), filetype="pdf")
        edit(d[0])
        d.save(p)
        return AN.analyse(p)["sheets"][0]


def _stroke(pg, pts):
    sh = pg.new_shape()
    sh.draw_polyline([pymupdf.Point(*q) for q in pts])
    sh.finish(color=(0, 0, 0), width=0.71, closePath=False)
    sh.commit()


def _tipped(pg, a, b):
    """몸통 a→b 끝에 촉을 획 셋으로 (19VA 가 그리는 그대로 — 한 경로)."""
    ux = 1 if b[0] > a[0] else (-1 if b[0] < a[0] else 0)
    uy = 1 if b[1] > a[1] else (-1 if b[1] < a[1] else 0)
    k = (b[0] - 1.3 * ux, b[1] - 1.3 * uy)
    w = (0.4 * uy, 0.4 * ux)
    _stroke(pg, [a, b, (k[0] + w[0], k[1] + w[1]), (k[0] - w[0], k[1] - w[1]), (b[0] - 0.3 * ux, b[1] - 0.1 * uy)])


def _scene(and_x, and_y, row_out=3):
    """3행 → NOT(500) … (여기에 파선을 그린다) … AND(and_x) → 오른쪽 행.  → (doc, y, NOT 오른쪽 변 x)"""
    y = T + 3 * P - P / 2
    blocks = [{"id": "n", "kind": "NOT", "x": 500, "y": y - 4.5, "w": 9, "h": 9, "text": "NOT", "label": "", "param": {}},
              {"id": "a", "kind": "AND", "x": and_x, "y": and_y - 7, "w": 14, "h": 14, "text": "AND", "label": "", "param": {}}]
    wires = [{"id": "w1", "pts": [[draw.LX0, y], [500, y]]}, {"id": "w3", "pts": [[and_x + 14, and_y], [draw.LX1, and_y]]}]
    rn = str(59 + 3 + round((and_y - y) / P))
    return _doc(blocks, wires, {"3": {"fm": "", "kks": "", "desc": "IN"}}, {rn: {"desc": "OUT", "kks": "", "to": ""}}), y, 509.0


def _check(s):
    nb = next(k for k, b in s["blocks"].items() if b["func"] == "NOT")
    ab = next(k for k, b in s["blocks"].items() if b["func"] == "AND")
    out = [q["net"] for q in s["ports"] if q["block"] == nb and q["dir"] == "out"]
    ins = [q["net"] for q in s["ports"] if q["block"] == ab and q["dir"] == "in"]
    assert out and ins and out[0] in ins, ([(q["block"], q["side"], q["dir"], q["net"]) for q in s["ports"]])
    row = next(r for r in s["rows"] if r["side"] == "R")
    v = [sim.simulate(s, f)["frames"][-1]["values"][row["net"]] for f in ({}, {"row:3": 1})]
    assert v == [1, 0], v                              # 입력 0 → NOT 1 → AND 1 · 입력 1 → 0


def test_three_piece_dash_with_half_dashes_and_a_stroked_arrow_joins_two_blocks():
    """⊠ → [반 토막 · 틈 · 토막 · 틈 · 화살촉 토막] → 블록 — 첫 토막 2.83 과 가운데 토막 5.67 이 꼭 두 배라 '고르지 않다' 로 떨어졌고,
    끝의 화살촉 토막까지 틈 하나를 이어 주지도 않았다 (긴 파선만 이어 줬다)."""
    x1 = 509.0 + D / 2 + G + D + G + D / 2
    doc, y, x0 = _scene(x1, T + 3 * P - P / 2)

    def edit(pg):
        _stroke(pg, [(x0, y), (x0 + D / 2, y)])
        _stroke(pg, [(x0 + D / 2 + G, y), (x0 + D / 2 + G + D, y)])
        _tipped(pg, (x1 - D / 2, y), (x1, y))
    _check(_analyse(doc, edit))


def test_slightly_tilted_two_piece_dash_into_a_filled_arrow_joins_two_blocks():
    """0006 · 0007: ⊠ 가운데 → AND 변으로 0.1pt 기울어 그은 토막 둘 — 둘째 토막은 채운 화살촉 안에 들어가 있다.  기운 토막은 가로 토막으로 치지 않아
    파선 후보에도 못 들었다 (NOT 출력 없음 · AND 입력 없음)."""
    x1 = 509.0 + 4.47 + 3.5 + 4.47
    doc, y, x0 = _scene(x1, T + 3 * P - P / 2)

    def edit(pg):
        _stroke(pg, [(x0, y - 0.06), (x0 + 4.47, y - 0.02)])
        _stroke(pg, [(x1 - 4.47, y + 0.02), (x1, y + 0.06)])
        sh = pg.new_shape()
        sh.draw_polyline([pymupdf.Point(x1 - 5.25, y - 0.85), pymupdf.Point(x1 - 5.25, y + 0.95), pymupdf.Point(x1, y + 0.06)])
        sh.finish(color=(0, 0, 0), fill=(0, 0, 0), width=0, closePath=True)
        sh.commit()
    _check(_analyse(doc, edit))


def test_dash_that_turns_corners_restarts_its_pattern_on_every_leg():
    """FW11_P111: AND → 가로 토막 둘 · (모퉁이) · 세로 토막 셋 · (모퉁이) · 가로 토막 + 화살촉 → OR.  꺾인 파선은 선분마다 무늬를 새로 시작한다 —
    한 줄의 끝에서 틈 하나를 가면 다음 줄 첫 토막의 시작점이다."""
    xc = 509.0 + D / 2 + G + D + G                      # 모퉁이 x
    yb = (T + 3 * P - P / 2) + 2 * P                    # 두 행 아래
    x1 = xc + D / 2 + G + D
    doc, y, x0 = _scene(x1, yb)

    def edit(pg):
        _stroke(pg, [(x0, y), (x0 + D / 2, y)])
        _stroke(pg, [(x0 + D / 2 + G, y), (xc - G, y)])
        _stroke(pg, [(xc, y), (xc, y + D / 2)])
        _stroke(pg, [(xc, y + D / 2 + G), (xc, y + D / 2 + G + D)])
        _stroke(pg, [(xc, y + D / 2 + 2 * G + D), (xc, y + D / 2 + 2 * G + 2 * D)])
        assert abs((y + D / 2 + 3 * G + 2 * D) - yb) < 0.2          # 모퉁이까지 틈 하나
        _stroke(pg, [(xc, yb), (xc + D / 2, yb)])
        _tipped(pg, (x1 - D, yb), (x1, yb))
    _check(_analyse(doc, edit))


def test_solid_line_through_a_junction_dot_stays_solid():
    """접합점이 앉은 실선의 두 토막(점이 가린 틈)을 파선으로 바꾸지 않는다 — 고치는 도중에 실선 장(0009)의 선이 파선으로 바뀌어 ⊠ 방향이 뒤집혔었다."""
    y, y2 = T + 3 * P - P / 2, T + 5 * P - P / 2
    blocks = [{"id": "a", "kind": "AND", "x": 600, "y": y - 7, "w": 14, "h": 14, "text": "AND", "label": "", "param": {}},
              {"id": "o", "kind": "AND", "x": 600, "y": y2 - 7, "w": 14, "h": 14, "text": "AND", "label": "", "param": {}}]
    wires = [{"id": "w1", "pts": [[draw.LX0, y], [600, y]]}, {"id": "w2", "pts": [[540, y], [540, y2], [600, y2]]},
             {"id": "w3", "pts": [[614, y], [draw.LX1, y]]}, {"id": "w4", "pts": [[614, y2], [draw.LX1, y2]]}]
    doc = _doc(blocks, wires, {"3": {"fm": "", "kks": "", "desc": "IN"}},
               {str(59 + 3): {"desc": "A", "kks": "", "to": ""}, str(59 + 5): {"desc": "B", "kks": "", "to": ""}})
    s = _analyse(doc, lambda pg: None)
    assert not any(n.get("dashed") for n in s["nets"].values())
    assert [sim.simulate(s, {"row:3": 1})["frames"][-1]["values"][r["net"]] for r in s["rows"] if r["side"] == "R"] == [1, 1]


def test_feedback_chain_drawn_right_to_left_is_reversed_as_a_whole():
    """CO02_P031 · CC01_P024: AND 출력 → ⎍ → ⊠ → 그 AND 의 입력으로 되돌아오는 고리를 오른쪽에서 왼쪽으로 그렸다.  상자 하나만 보면 ⎍ 의 왼쪽은 ⊠ 가
    '몰고' 있어 뒤집히지 않았다 — AND 출력과 ⎍ 출력이 한 선을 함께 몰고, ⊠ 왼쪽 선(AND 입력)은 모는 것이 없었다."""
    yt, yb = T + 3 * P - P / 2, T + 6 * P - P / 2
    blocks = [{"id": "n", "kind": "NOT", "x": 480, "y": yt - 4.5, "w": 9, "h": 9, "text": "NOT", "label": "", "param": {}},
              {"id": "p", "kind": "PD", "x": 520, "y": yt - 6, "w": 13, "h": 12, "text": "", "label": "", "param": {"t": 1}},
              {"id": "a", "kind": "AND", "x": 560, "y": yb - 7, "w": 14, "h": 14, "text": "AND", "label": "", "param": {}}]
    wires = [{"id": "w1", "pts": [[draw.LX0, yb + 3], [560, yb + 3]]},                              # 행 → AND
             {"id": "w2", "pts": [[574, yb], [draw.LX1, yb]]},                                      # AND → 출력 행
             {"id": "w3", "pts": [[620, yb], [620, yt], [533, yt]]},                                # AND 출력에서 갈라져 올라가 ⎍ 의 **오른쪽**으로
             {"id": "w4", "pts": [[520, yt], [489, yt]]},                                           # ⎍ 왼쪽 → ⊠ 오른쪽
             {"id": "w5", "pts": [[480, yt], [450, yt], [450, yb - 3], [560, yb - 3]]}]             # ⊠ 왼쪽 → 내려와 AND 입력
    doc = _doc(blocks, wires, {"6": {"fm": "", "kks": "", "desc": "IN"}}, {str(59 + 6): {"desc": "OUT", "kks": "", "to": ""}})
    s = _analyse(doc, lambda pg: None)
    side = lambda f: {q["side"]: q["dir"] for q in s["ports"] if s["blocks"][q["block"]]["func"] == f and q["side"] in ("L", "R")}
    assert side("NOT") == {"L": "out", "R": "in"} and side("PD") == {"L": "out", "R": "in"}, (side("NOT"), side("PD"))
    drv = {}
    for q in s["ports"]:
        if q["dir"] == "out":
            drv.setdefault(q["net"], []).append(q["block"])
    assert all(len(v) == 1 for v in drv.values()), drv                                              # 한 선을 두 블록이 함께 몰지 않는다
