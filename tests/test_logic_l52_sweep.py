"""L52 — 모든 신호를 켜고 끄며 모든 선이 활성화되는지 센 전수 점검(`spike/logic_line_sweep.py`)이 잡은 둘.

① HRSG G043 — CAD 가 신호선과 AND 상자 테두리를 **한 path** 로 내보냈다 (입력 버스 → 상자 네 변 → 되돌아옴).
   상자는 블록으로 섰는데 테두리 토막이 선으로 남아 입력 선 L6 와 출력 선 R90 이 한 선이 되었고, 그 AND 는
   AND(x, NOT x) 꼴로 영영 0 이었다 (G030 · G035 · G040 · G042 · G044 도 같은 모양).
② 1A5J Typical 0014 — OR(자기 출력, x) 자기유지 고리는 처음 값이 없어 '모름' 으로 남아 화면이 0 으로 보이되
   `unread` 에 들었다.  전원이 들어온 순간 래치는 꺼져 있다 — 고리로만 서로를 모는 선은 0 에서 시작한다.
"""
from __future__ import annotations

import pymupdf
import pytest

from app.logic import analyse, sim
from tests.test_logic_l22_user import _P, _blk, _sheet as _dict_sheet
from tests.test_logic_l23_generic import LX0, LX1, H, P, W, _line, _sheet, ry


def _draw(page):
    _sheet(page, "XX_G-002", {2: ("HMI", "PERMISSIVE"), 3: ("HMI", "POSITION")}, {51: ("STOP MOV", "")})
    # 2행 → 세로 버스 x=450 → 상자 왼쪽 위 모서리 → 상자 네 변을 돌아 제자리 (한 path · G043 그대로)
    x0, y0 = 489.2, ry(2) - P / 2
    x1, y1 = x0 + 11.4, y0 + 11.5
    _line(page, (LX0, ry(2)), (450, ry(2)), (450, y0))
    _line(page, (450, y0), (x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))          # 5 토막 — 선 + 네 변
    page.insert_text((x0 + 2, y0 + 8), "AND", fontsize=5)
    # 3행 → 상자 왼쪽 변 (상자 높이 안)
    _line(page, (LX0, ry(3)), (470, ry(3)), (470, y0 + 8), (x0, y0 + 8))
    # 상자 오른쪽 변 가운데 → 51행
    _line(page, (x1, (y0 + y1) / 2), (700, (y0 + y1) / 2), (700, ry(51)), (LX1, ry(51)))


@pytest.fixture(scope="module")
def sheet(tmp_path_factory):
    doc = pymupdf.open()
    _draw(doc.new_page(width=W, height=H))
    p = tmp_path_factory.mktemp("l52") / "border.pdf"
    doc.save(p)
    res = analyse.analyse(str(p))
    return next(s for s in res["sheets"] if s["sheet_no"] == "XX_G-002")


def _net(s, side, n):
    return next(r["net"] for r in s["rows"] if r["side"] == side and r["n"] == n)


def test_block_border_drawn_in_the_wire_path_is_not_a_wire(sheet):
    assert _net(sheet, "L", 2) != _net(sheet, "R", 51)         # 입력과 출력이 한 선이 아니다
    ands = [b for b in sheet["blocks"].values() if b["logic"] == "and"]
    assert len(ands) == 1
    ins, outs, drivers, _, _ = sim._index(sheet)
    bid = next(k for k, b in sheet["blocks"].items() if b["logic"] == "and")
    assert {n for n, _, _ in ins[bid]} == {_net(sheet, "L", 2), _net(sheet, "L", 3)}
    assert [n for n, _, _ in outs[bid]] == [_net(sheet, "R", 51)]
    out = _net(sheet, "R", 51)
    r = sim.simulate(sheet, {"row:2": 1, "row:3": 1})
    assert r["frames"][-1]["values"][out] == 1
    r = sim.simulate(sheet, {"row:2": 1})
    assert r["frames"][-1]["values"][out] == 0                   # AND — 하나만으로는 안 선다


def _latch_sheet(x_logic="source"):
    """L1 → OR(자기 출력 9, 1) = 9 → AND(9, L2) → R30.  x_logic 이 unknown 이면 OR 의 둘째 입력이 판정 못 한 블록."""
    rows = [{"n": 1, "side": "L", "net": "1", "desc": "SET", "fm": ""},
            {"n": 2, "side": "L", "net": "2", "desc": "ENABLE", "fm": ""},
            {"n": 30, "side": "R", "net": "8", "desc": "OUT", "to": ""}]
    blocks = {"OR": _blk("OR", "or"), "AND": _blk("AND", "and", (300, 100, 330, 130))}
    ports = [_P("OR", "1", "in"), _P("OR", "9", "in"), _P("OR", "9", "out"),
             _P("AND", "9", "in"), _P("AND", "2", "in"), _P("AND", "8", "out")]
    if x_logic == "unknown":
        blocks["X"] = _blk("UNKNOWN", "unknown", (200, 300, 230, 330))
        ports += [_P("X", "7", "out"), _P("OR", "7", "in")]
        rows[0] = {"n": 1, "side": "L", "net": "7", "desc": "SET", "fm": ""}
        ports[0] = _P("OR", "7", "in")
    return _dict_sheet(1, "G001", rows, blocks, ports)


def test_feedback_loop_starts_at_zero_and_is_not_unread():
    s = _latch_sheet()
    r = sim.simulate(s, {})
    fr = r["frames"][-1]
    assert fr["values"]["9"] == 0 and fr["values"]["8"] == 0
    assert "9" not in fr["unread"] and "8" not in fr["unread"]
    r = sim.simulate(s, {"row:1": 1, "row:2": 1})
    assert r["frames"][-1]["values"]["8"] == 1
    # 켜 둔 뒤 SET 을 떼도 자기유지 (고리의 OR)
    st = r["state"]
    r2 = sim.simulate(s, {"row:2": 1}, state=st, now=1.0)
    assert r2["frames"][-1]["values"]["9"] == 1


def test_loop_fed_by_an_unknown_block_stays_unread():
    s = _latch_sheet("unknown")
    r = sim.simulate(s, {})
    fr = r["frames"][-1]
    assert "9" in fr["unread"]                                   # 판정 못 한 블록에 기대는 고리는 모름 그대로


def test_scenario_can_hold_a_cross_sheet_fed_row_at_zero():
    """③ 19VA HH10_G154 — OP REQ = L12 AND NOT(L32 OR L34).  L32 'AUX BLR SYS NOT RUNNING' 은 다른 장의 NOT 이
    쉬는 값 1 로 보내므로, 예시 찾기가 '0 이어야 하는 행은 가만히 두면 0' 으로 보면 그 출력을 영영 못 세운다."""
    a = _dict_sheet(1, "G001",
                    [{"n": 1, "side": "L", "net": "1", "desc": "RUNNING", "fm": ""},
                     {"n": 30, "side": "R", "net": "2", "desc": "NOT RUNNING", "to": "G002-5"}],
                    {"N": _blk("NOT", "not")}, [_P("N", "1", "in"), _P("N", "2", "out")])
    b = _dict_sheet(2, "G002",
                    [{"n": 5, "side": "L", "net": "5", "desc": "NOT RUNNING", "fm": "G001-30",
                      "ref": {"sheet": "G001", "row": 30, "page": 1, "other_bundle": False, "src_row": 30}},
                     {"n": 6, "side": "L", "net": "6", "desc": "REQ", "fm": ""},
                     {"n": 40, "side": "R", "net": "8", "desc": "OP REQ", "to": ""}],
                    {"N": _blk("NOT", "not"), "A": _blk("AND", "and", (300, 100, 330, 130))},
                    [_P("N", "5", "in"), _P("N", "7", "out"), _P("A", "7", "in"), _P("A", "6", "in"), _P("A", "8", "out")])
    sheets = [a, b]
    r = sim.simulate_bundle(sheets, {}, None, 2, cache={})["focus"]
    assert r["frames"][-1]["values"]["5"] == 1                   # 쉬는 값이 1 로 들어온다
    sc = sim.scenario(b, "net:8", 1, sheets=sheets, cache={})
    assert sc["ok"] and sc["forces"].get("row:5") == 0 and sc["forces"].get("row:6") == 1
