"""54회차 — 태그 버블이 가리키는 밸브는 **도면이 그은 지시선**이 말한다 (9차 [A]).

`attach_tags` 는 지시선을 읽지 않고 가장 가까운 몸체를 줬고, 그 반경
`tag_reach` 는 AL NOUF1 p6 에서 잰 절대 pt 190.0 이었다 (§9 위반).  A3 로 그린
붐비는 장에서는 그 반경 안에 밸브가 열 개 넘게 들어온다 — TC2 p10 실측: `XV`
가 자기 밸브(34.1pt) 대신 유량계 배열의 다른 밸브(29.6pt)를 집었고, `PCV` 는
자기 밸브가 검출되지 않아 103.6pt 떨어진 남의 밸브를 집었다.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "engine"))

import detect_valves as dv     # noqa: E402


class _PC:
    """`drawings()` 와 회전 행렬만 가진 가짜 쪽."""

    def __init__(self, lines):
        self._lines = lines
        self.page = type("P", (), {"rotation_matrix": pymupdf.Matrix(1, 0, 0, 1, 0, 0)})()
        self.page_no = 1

    def drawings(self):
        return [{"items": [("l", pymupdf.Point(*a), pymupdf.Point(*b))],
                 "bbox": pymupdf.Rect(min(a[0], b[0]), min(a[1], b[1]),
                                      max(a[0], b[0]), max(a[1], b[1]))}
                for a, b in self._lines]


def _body(x0, y0, x1, y1, kind="GLOBE"):
    return dv.Body(kind, pymupdf.Rect(x0, y0, x1, y1), "H")


BUB = pymupdf.Rect(100, 100, 134, 112)


def _attach(lines, bodies, tag="XV"):
    pc = _PC(lines)
    saved = dv.bubble_tags
    dv.bubble_tags = lambda _pc, _lay=None: [(tag, BUB)]
    try:
        dv.attach_tags(pc, bodies, dv.LAYOUT)
    finally:
        dv.bubble_tags = saved
    return bodies


def test_the_leader_wins_over_the_nearer_body():
    """자기 밸브가 34pt, 남의 밸브가 30pt 여도 지시선이 가리킨 쪽이다 (TC2 p10 `XV`)."""
    mine = _body(150, 130, 158, 135)          # 지시선 끝이 들어 있다
    other = _body(112, 130, 120, 135)         # 더 가깝다
    _attach([((130, 112), (154, 132))], [other, mine])
    assert mine.tag == "XV" and other.tag == ""
    assert mine.evidence["tag_leader"] > 0


def test_a_leader_that_lands_on_nothing_claims_nothing():
    """★ 도면이 가리킨 자리에 몸체가 없으면 **아무 몸체도 주지 않는다**.

    그 태그는 53회차 [B-3] 의 `VALVE_TAG_NO_BODY` 행이 되어 버블 자리에 서고
    모양 칸은 빈다 — 없는 모양을 지어내지 않는다 (§2.1 ③).
    """
    far = _body(300, 300, 308, 305)
    _attach([((130, 112), (154, 132))], [far])
    assert far.tag == ""


def test_without_a_leader_the_old_nearest_rule_still_runs():
    """지시선이 아예 없는 버블은 옛 규칙 그대로다 (AL NOUF1 198개 중 1개)."""
    near = _body(112, 130, 120, 135)
    _attach([], [near])
    assert near.tag == "XV"
    assert "tag_leader" not in near.evidence


def test_the_leader_is_read_in_one_step():
    """§2.3 — 찾은 끝에서 다시 선을 찾지 않는다 (순회가 아니다)."""
    src = inspect.getsource(dv._leader)
    assert "_leader(" not in src.split("\n", 1)[1]        # 재귀 없음
    assert "while" not in src and "_leader_index" not in src


def test_the_leader_slack_is_the_drawn_edge_not_a_new_constant():
    """허용치는 `bubble_outlines` 가 이미 쓰는 `side_slack` 하나다 (선 굵기)."""
    src = inspect.getsource(dv.attach_tags)
    assert "ds.LAYOUT.side_slack" in src
    # 새 숫자를 코드에 적지 않았다 — 옛 절대 pt(`tag_reach`)는 폴백 갈래에만 남는다
    body = src.split('"""', 2)[2]
    assert "side_slack" in body and "190" not in body


def test_the_leader_may_stop_at_the_stem_just_outside_the_body():
    """★ 지시선은 밸브의 **스템 끝**에서 멈추지 몸체 안까지 들어오지 않는다.

    실측 (AL NOUF1 p26 `MOV`): 지시선 끝 (667.1, 556.4) ↔ 몸체
    `[659.6, 556.6, 665.7, 573.6]` — 오른쪽으로 1.4pt 밖.  포함만 보면 자기
    밸브를 놓치고 글리프 사전이 그 무리의 이름표를 잃는다 (`H 4 / M 32` → `M 17`).
    넓히는 값은 **그 몸체의 짧은 변**이라 새 상수가 아니다.
    """
    mine = dv.Body("BUTTERFLY", pymupdf.Rect(659.6, 556.6, 665.7, 573.6), "H")
    bub = pymupdf.Rect(676, 509, 761, 537)
    pc = _PC([((684.3, 536.4), (667.1, 556.4))])
    saved = dv.bubble_tags
    dv.bubble_tags = lambda _pc, _lay=None: [("MOV", bub)]
    try:
        dv.attach_tags(pc, [mine], dv.LAYOUT)
    finally:
        dv.bubble_tags = saved
    assert mine.tag == "MOV"


def test_a_body_far_from_the_leader_end_is_not_claimed():
    """넉넉히 본다고 아무 몸체나 집지 않는다 — 자기 크기 안이어야 한다."""
    far = dv.Body("GATE", pymupdf.Rect(700, 700, 708, 717), "H")
    bub = pymupdf.Rect(676, 509, 761, 537)
    pc = _PC([((684.3, 536.4), (667.1, 556.4))])
    saved = dv.bubble_tags
    dv.bubble_tags = lambda _pc, _lay=None: [("MOV", bub)]
    try:
        dv.attach_tags(pc, [far], dv.LAYOUT)
    finally:
        dv.bubble_tags = saved
    assert far.tag == ""


def test_a_leader_that_ends_on_the_actuator_names_that_valve():
    """★ 도면은 지시선을 **모터 원까지만** 긋기도 한다 (AL NOUF1 p46 `MOV`).

    세로 버블에서 곧장 아래로 내려온 지시선이 `M` 원에서 끝나고 밸브는 그 아래
    스템 끝에 있다.  그 원은 이미 `attach_actuators` 가 그 밸브의 것으로 짝지어
    두었으므로 새 짐작이 아니다.
    """
    v = dv.Body("GLOBE", pymupdf.Rect(290, 400, 298, 417), "H")
    v.actuator = "MOTOR"
    v.actuator_rect = (286, 350, 302, 366)
    bub = pymupdf.Rect(279, 246, 308, 331)
    pc = _PC([((293, 331), (294, 358))])
    saved = dv.bubble_tags
    dv.bubble_tags = lambda _pc, _lay=None: [("MOV", bub)]
    try:
        dv.attach_tags(pc, [v], dv.LAYOUT)
    finally:
        dv.bubble_tags = saved
    assert v.tag == "MOV"


def test_the_body_is_looked_at_before_its_actuator():
    """몸체가 먼저다 — 액추에이터는 몸체가 안 걸릴 때만 본다."""
    src = inspect.getsource(dv._body_at)
    assert 'for probe in ("rect", "actuator_rect")' in src
