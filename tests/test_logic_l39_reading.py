"""L39 — 남은 읽기 빈틈을 줄인 규칙 (1A1Y · 1A5J · HRSG 실측에서 나온 꼴).

합성 한 장에 하나씩:
  2행  → 세로로 내려가며 14행의 가로선을 **틈(1.8 행 간격)을 두고** 건넌다 → 51행        (끊어 그린 교차 · 1A1Y)
  4행  → 파선이 꺾이는 모서리 앞에서 끊긴다 (가로 끝 · 세로 시작이 모서리에서 각각 0.4 행 간격) → 52행   (1A5J)
  6행  옆에 펄스 표시 ⎍ (아무 데도 안 닿음)                                                        (1A5J 0001)
  8 · 9행 → 매크로 상자 왼쪽 단자 · 상자 안 오른쪽 아래에 운전 버튼 칸 셋 (A_SEL · M_SEL · F_RST)  (1A1Y MTS MACRO)
  20행 → 글자 'REMOTE' 상자 (들어오기만)                                                          (HRSG 상태 표시)
"""
from __future__ import annotations

import pymupdf
import pytest

from app.logic import analyse, graph
from tests.test_logic_l23_generic import LX0, LX1, H, P, W, _line, _rect, _sheet, ry


def _draw(page):
    _sheet(page, "XX_G-001",
           {2: ("HMI", "CROSS IN"), 4: ("HMI", "DASH IN"), 6: ("HMI", "PULSE"), 8: ("HMI", "MACRO A"),
            9: ("HMI", "MACRO B"), 14: ("HMI", "PASSING"), 20: ("HMI", "STATUS")},
           {51: ("CROSS OUT", ""), 52: ("DASH OUT", ""), 64: ("PASS OUT", ""), 70: ("MACRO OUT", "")})
    # 14행 가로선이 끝까지 지나간다
    _line(page, (LX0, ry(14)), (LX1, ry(14)))
    # 2 → x=450 세로로 내려가 14행 선을 틈 1.8P 로 건너 → 51행
    g = 0.9 * P
    _line(page, (LX0, ry(2)), (450, ry(2)), (450, ry(14) - g))
    _line(page, (450, ry(14) + g), (450, ry(30)), (760, ry(30)), (760, ry(51)), (LX1, ry(51)))
    # 4 → 파선 가로 (x=480 의 모서리 앞 0.4P 에서 끝남) · 세로 파선 (모서리 아래 0.4P 에서 시작) → 52행
    x = LX0
    while x + 6 < 480 - 0.4 * P:
        _line(page, (x, ry(4)), (x + 6, ry(4)))
        x += 9
    _line(page, (x, ry(4)), (480 - 0.4 * P, ry(4)))
    y = ry(4) + 0.4 * P
    while y + 6 < ry(12):
        _line(page, (480, y), (480, y + 6))
        y += 9
    _line(page, (480, y), (480, ry(12)), (780, ry(12)), (780, ry(52)), (LX1, ry(52)))
    # 6 옆의 펄스 표시 ⎍
    bx = LX0 + 10
    _line(page, (bx, ry(6) - 2), (bx + 4, ry(6) - 2), (bx + 4, ry(6) - 9), (bx + 10, ry(6) - 9), (bx + 10, ry(6) - 2),
          (bx + 14, ry(6) - 2))
    # 매크로 상자 — 왼쪽 단자 둘 (8 · 9행) · 오른쪽 단자 하나 → 70행 · 안 오른쪽 아래 운전 버튼 칸 셋
    mx0, my0, mx1, my1 = 560.0, ry(7) - P / 2, 680.0, ry(19)
    _rect(page, (mx0, my0, mx1, my1))
    page.insert_text((590, my0 + 8), "MTS MACRO", fontsize=6)
    for n, name in ((8, "A_MODE"), (9, "A_OPN")):
        _line(page, (LX0, ry(n)), (mx0, ry(n)))
        page.insert_text((mx0 + 2, ry(n) + 2), name, fontsize=5)
    _line(page, (mx1, ry(10)), (800, ry(10)), (800, ry(70)), (LX1, ry(70)))
    page.insert_text((mx1 - 22, ry(10) + 2), "C_OPN", fontsize=5)
    for k, name in enumerate(("A_SEL", "M_SEL", "F_RST")):
        y0 = my1 - (3 - k) * 9
        _rect(page, (mx1 - 30, y0, mx1, y0 + 9))
        page.insert_text((mx1 - 28, y0 + 7), name, fontsize=5)
    # 20 → 글자 상자 REMOTE (들어오기만)
    _line(page, (LX0, ry(20)), (600, ry(20)))
    _rect(page, (600, ry(20) - 5, 640, ry(20) + 5))
    page.insert_text((603, ry(20) + 2), "REMOTE", fontsize=6)


@pytest.fixture(scope="module")
def sheet(tmp_path_factory):
    doc = pymupdf.open()
    _draw(doc.new_page(width=W, height=H))
    p = tmp_path_factory.mktemp("l39") / "read.pdf"
    doc.save(p)
    res = analyse.analyse(str(p))
    return next(s for s in res["sheets"] if s["sheet_no"] == "XX_G-001")


def _net(s, side, n):
    return next(r["net"] for r in s["rows"] if r["side"] == side and r["n"] == n)


def test_wide_broken_crossing_is_one_line_not_joined_to_the_crossed_line(sheet):
    assert _net(sheet, "L", 2) == _net(sheet, "R", 51)
    assert _net(sheet, "L", 2) != _net(sheet, "L", 14)            # 지나간 선과는 잇지 않는다 (범례 G003)


def test_dashed_line_broken_at_a_corner_is_joined(sheet):
    assert _net(sheet, "L", 4) == _net(sheet, "R", 52)


def test_pulse_glyph_is_not_a_dangling_signal(sheet):
    near6 = [f for f in sheet["findings"] if f["code"] == "C1_DANGLING" and abs(f["at"][1] - ry(6)) < P]
    assert not near6


def test_macro_box_with_operator_cells_is_a_block_and_cells_are_its_inputs(sheet):
    mac = [b for b in sheet["blocks"].values() if b["func"] == "MACRO"]
    assert len(mac) == 1
    mid = next(k for k, b in sheet["blocks"].items() if b["func"] == "MACRO")
    pins = {p.get("pin") for p in sheet["ports"] if p["block"] == mid and p["dir"] == "in"}
    assert {"A_SEL", "M_SEL", "F_RST"} <= pins
    pbs = [b for b in sheet["blocks"].values() if b["func"] == "PUSH BUTTON"]
    assert len(pbs) == 3
    assert not any(f["code"] == "C3_BLOCK_UNCONNECTED" for f in sheet["findings"])


def test_input_only_word_box_is_a_status_display(sheet):
    disp = [b for b in sheet["blocks"].values() if b["func"] == "DISPLAY"]
    assert disp and disp[0]["logic"] == "sink"


def test_group_frame_with_wiring_inside_stays_a_frame():
    """안에 배선을 품은 큰 틈(HRSG Typical 'MOTOR SUB-GROUP') 은 단자 같은 선이 변에 닿아도 틀이다."""
    from app.logic import geom
    r = geom.Rect(100, 100, 300, 300)
    inner = [geom.Rect(150 + 20 * k, 150, 160 + 20 * k, 160) for k in range(3)]
    pins = [geom.Poly([geom.Seg(50, 120 + 20 * k, 100, 120 + 20 * k)], (50, 120, 100, 160)) for k in range(3)]
    wiring = [geom.Poly([geom.Seg(150, 200 + 5 * k, 250, 200 + 5 * k)], (150, 200, 250, 215)) for k in range(4)]
    assert id(r) not in graph._group_frames([r] + inner, [], pins, 0.5)            # 단자 있고 안에 배선 없음 → 블록
    assert id(r) in graph._group_frames([r] + inner, [], pins + wiring, 0.5)       # 안에 배선 → 틀
    assert id(r) in graph._group_frames([r] + inner, [], [], 0.5)                  # 단자 없음 → 틀 (예전 그대로)
