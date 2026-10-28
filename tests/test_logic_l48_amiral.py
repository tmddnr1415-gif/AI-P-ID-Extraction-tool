"""L48 — 아미랄(19VA) 전수 시뮬레이션이 잡은 읽기 빈틈 다섯 (합성 PDF · 한 장).

① 단자 이름을 상자 안에 인쇄한 연산 상자(EQUAL · BIT_CNT · SPC)는 매크로가 아니라 그 연산이다 — 단자 이름에 상자 이름이
   붙지 않는다(`IN1EQUAL` ✕) · EQUAL 은 두 값이 같으면 1 · BIT_CNT 는 1 인 입력의 수.
② LOGIC 영역 경계 안쪽에서 시작해 표 쪽으로 1~2pt 삐져나간 행 선은 버리지 않고 그 행에 붙는다 (Typical 0015 M_SEL · LOCK · RESET).
③ 상자 안 글자 하나뿐인 판정 못 한 상자를 그 장의 NOTE 가 "INVERTED BY EACH MOMENTARY TRUE SIGNAL ON 'FLPX'" 로 정의하면 토글 (낱말은 아무것이나 — L22 시험이 SRST 를 AND 로 가르쳐 두므로 다른 낱말).
④ 선 둘이 교차하며 지나는 속 빈 작은 원은 이음점이다 (블록 아님).
⑤ 원 안 표시등 글자 하나 · 나가는 선 없음 = 표시등.
"""
from __future__ import annotations

import pymupdf
import pytest

from app.logic import analyse, sim

W, H = 1191.0, 842.0
P = 11.3
TOP = 70.0
N = 50
LCOLS = [30.0, 90.0, 110.0, 180.0, 320.0]
RCOLS = [870.0, 1010.0, 1080.0, 1100.0, 1160.0]
LX0, LX1 = LCOLS[-1], RCOLS[0]
K = (0, 0, 0)


def ry(n):
    return TOP + ((n - 1) % N) * P + P / 2


def _line(page, *pts, dashes=None):
    sh = page.new_shape()
    for a, b in zip(pts, pts[1:]):
        sh.draw_line(pymupdf.Point(*a), pymupdf.Point(*b))
    sh.finish(color=K, width=0.72, closePath=False, dashes=dashes)
    sh.commit()


def _rect(page, r):
    sh = page.new_shape()
    sh.draw_rect(pymupdf.Rect(*r))
    sh.finish(color=K, width=0.72)
    sh.commit()


def _circle(page, c, r):
    sh = page.new_shape()
    sh.draw_circle(pymupdf.Point(*c), r)
    sh.finish(color=K, width=0.72)
    sh.commit()


def _sheet(page, sheet_no, rows_l, rows_r):
    bottom = TOP + N * P
    for x in LCOLS + RCOLS:
        _line(page, (x, TOP - 2 * P), (x, bottom))
    for k in range(N + 1):
        _line(page, (LCOLS[0], TOP + k * P), (LX0, TOP + k * P))
        _line(page, (LX1, TOP + k * P), (RCOLS[-1], TOP + k * P))
    for x, t in ((40, "FROM"), (92, "NO."), (120, "TAG"), (140, "NO."), (220, "SERVICE"),
                 (900, "SERVICE"), (1020, "TAG"), (1040, "NO."), (1082, "NO."), (1120, "TO")):
        page.insert_text((x, TOP - 8), t, fontsize=7)
    for k in range(N):
        page.insert_text((95, TOP + k * P + 8), str(k + 1), fontsize=5)
        page.insert_text((1083, TOP + k * P + 8), str(N + k + 1), fontsize=5)
    for n, (fm, desc) in rows_l.items():
        page.insert_text((32, ry(n) + 2), fm, fontsize=5)
        page.insert_text((182, ry(n) + 2), desc, fontsize=5)
    for n, (desc, to) in rows_r.items():
        page.insert_text((872, ry(n) + 2), desc, fontsize=5)
        page.insert_text((1102, ry(n) + 2), to, fontsize=5)
    page.insert_text((950, 805), "1Z9Z-00GEN00-J09-0003", fontsize=8)
    page.insert_text((1100, 790), "SHEET", fontsize=5)
    page.insert_text((1098, 800), sheet_no, fontsize=7)


def _op_box(page, x, y, name, left, right, w=56.0, h=50.0):
    """단자 이름을 안에 인쇄한 상자 (19VA EQUAL · BIT_CNT) — 이름은 가운데 위 · 단자 이름은 변에 붙여."""
    _rect(page, (x, y, x + w, y + h))
    page.insert_text((x + w / 2 - 8, y + 7), name, fontsize=5)
    for k, t in enumerate(left):
        page.insert_text((x + 1.5, y + 8 + k * P), t, fontsize=4.5)
    for k, t in enumerate(right):
        page.insert_text((x + w - 12, y + 8 + k * P), t, fontsize=4.5)


def _draw(page):
    _sheet(page, "AB_G-101",
           {2: ("", "A"), 3: ("", "B"), 6: ("", "D"), 12: ("", "C1"), 13: ("", "C2"), 20: ("", "E"), 25: ("", "G")},
           {51: ("EQUAL OUT", ""), 56: ("D OUT", ""), 62: ("COUNT OUT", ""), 70: ("TOGGLE OUT", ""), 75: ("G OUT", "")})
    # ① EQUAL: 2 · 3 → 상자 → 51
    x, y = 500.0, ry(2) - 8
    _op_box(page, x, y, "EQUAL", ["IN1", "IN2"], ["OUT"], h=44)
    _line(page, (LX0, ry(2)), (x, ry(2)))
    _line(page, (LX0, ry(3)), (x, ry(3)))
    _line(page, (x + 56, ry(2)), (700, ry(2)), (700, ry(51)), (LX1, ry(51)))
    # ② 6행 선은 표 쪽으로 1.5pt 삐져나가 시작한다 → 56
    _line(page, (LX0 - 1.5, ry(6)), (LX0 + 20, ry(6)), (LX0 + 20, ry(6) - 4), (470, ry(6) - 4), (470, ry(6)), (LX1, ry(56)))
    # ① BIT_CNT: 12 · 13 → 상자 → 62
    x2, y2 = 500.0, ry(12) - 8
    _op_box(page, x2, y2, "BIT_CNT", ["IN1", "IN2"], ["OUT"])
    _line(page, (LX0, ry(12)), (x2, ry(12)))
    _line(page, (LX0, ry(13)), (x2, ry(13)))
    _line(page, (x2 + 56, ry(12)), (LX1, ry(62)))
    # ③ FLPX 상자 + NOTE: 20 → FLPX → 70
    x3, y3 = 520.0, ry(20) - 5
    _rect(page, (x3, y3, x3 + 18, y3 + 10))
    page.insert_text((x3 + 1.5, y3 + 7), "FLPX", fontsize=4.5)
    _line(page, (LX0, ry(20)), (x3, ry(20)))
    _line(page, (x3 + 18, ry(20)), (LX1, ry(70)))
    page.insert_text((LX0 + 10, TOP + N * P + 20), "NOTE.1", fontsize=6)
    page.insert_text((LX0 + 10, TOP + N * P + 30),
                     'OUTPUT STATE IS INVERTED BY EACH MOMENTARY TRUE SIGNAL ON "FLPX" (THAT IS, THE OUTPUT IS INVERTED'
                     ' WHEN THE INPUT GOES FROM FALSE TO TRUE).', fontsize=5)
    # ④ 25행 선이 속 빈 원을 지나고 세로 파선 틀이 그 원을 가로지른다 → 75
    cx, cy = 600.0, ry(25)
    _circle(page, (cx, cy), 2.8)
    _line(page, (LX0, cy), (cx - 2.8, cy))
    _line(page, (cx + 2.8, cy), (LX1, ry(75)))
    _line(page, (cx, cy - 2.8), (cx, cy - 40), dashes="[3 3] 0")
    _line(page, (cx, cy + 2.8), (cx, cy + 40), dashes="[3 3] 0")
    # ⑤ 표시등 — 원 안 글자 G · 선 없음
    _circle(page, (640, ry(35)), 6)
    page.insert_text((637.5, ry(35) + 2), "G", fontsize=6)


def make(path):
    doc = pymupdf.open()
    _draw(doc.new_page(width=W, height=H))
    doc.save(path)
    return path


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return analyse.analyse(make(tmp_path_factory.mktemp("l48") / "amiral_like.pdf"))


@pytest.fixture(scope="module")
def sheet(result):
    return next(s for s in result["sheets"] if s["sheet_no"] == "AB_G-101")


def _net(s, side, n):
    return next(r["net"] for r in s["rows"] if r["side"] == side and r["n"] == n)


def _of(s, func):
    return [b for b in s["blocks"].values() if b.get("func") == func]


def test_pin_boxes_are_operators_not_macros(sheet):
    eq = _of(sheet, "EQUAL")
    cnt = _of(sheet, "BIT COUNTER")
    assert len(eq) == 1 and len(cnt) == 1
    assert eq[0]["aop"] == "equal" and cnt[0]["aop"] == "count"
    assert not _of(sheet, "MACRO")
    assert sorted(eq[0]["pins"].values()) == ["IN1", "IN2", "OUT"]          # 상자 이름이 단자 이름에 붙지 않는다
    assert sorted(cnt[0]["pins"].values()) == ["IN1", "IN2", "OUT"]


def test_equal_is_one_only_when_both_inputs_match(result, sheet):
    pg = sheet["page"]
    o = _net(sheet, "R", 51)
    for a, b, want in ((1, 1, 1), (1, 0, 0), (0, 0, 1)):
        r = sim.simulate_bundle(result["sheets"], {pg: {"row:2": a, "row:3": b}}, None, pg)["focus"]
        assert r["frames"][-1]["values"][o] == want, (a, b)


def test_bit_counter_counts_true_inputs(result, sheet):
    pg = sheet["page"]
    cnt = _of(sheet, "BIT COUNTER")[0]
    bid = next(k for k, v in sheet["blocks"].items() if v is cnt)
    for f, want in (({"row:12": 1, "row:13": 1}, 2.0), ({"row:12": 1}, 1.0), ({}, 0.0)):
        r = sim.simulate_bundle(result["sheets"], {pg: f} if f else {}, None, pg)["focus"]
        assert r["analog"]["ops"][bid]["out"] == want, f


def test_row_line_poking_into_the_table_is_still_read(result, sheet):
    pg = sheet["page"]
    assert _net(sheet, "L", 6) is not None
    r = sim.simulate_bundle(result["sheets"], {pg: {"row:6": 1}}, None, pg)["focus"]
    assert r["frames"][-1]["values"][_net(sheet, "R", 56)] == 1


def test_note_defined_toggle_flips_on_each_rising_edge(result, sheet):
    tog = _of(sheet, "TOGGLE")
    assert len(tog) == 1 and tog[0]["logic"] == "toggle"
    o = _net(sheet, "R", 70)
    st = None
    seen = []
    for v in (1, 0, 1, 0):
        r = sim.simulate(sheet, {"row:20": v}, st)
        st = r["state"]
        seen.append(r["frames"][-1]["values"][o])
    assert seen == [1, 1, 0, 0]


def test_crossing_circle_is_a_pass_point_and_lamp_is_a_sink(result, sheet):
    pg = sheet["page"]
    assert not [b for b in sheet["blocks"].values() if b.get("func") == "UNKNOWN" and b.get("kind") == "CIRCLE"]
    r = sim.simulate_bundle(result["sheets"], {pg: {"row:25": 1}}, None, pg)["focus"]
    assert r["frames"][-1]["values"][_net(sheet, "R", 75)] == 1
    lamps = _of(sheet, "LIGHT")
    assert len(lamps) == 1 and lamps[0]["label"] == "G" and lamps[0]["logic"] == "sink"
