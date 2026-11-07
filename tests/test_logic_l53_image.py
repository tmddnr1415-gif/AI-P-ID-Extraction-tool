"""L53 — 도면 그림과 분석이 읽은 것을 맞대어 잡은 읽기 빈틈 여섯 (HRSG G067 · G053 · G008 · G013 · G042 · 1A5J FG_G-101).

합성 한 장 `XY_G-003`:
  2행 → R52 긴 행 선, 그 위에 연결 기호 원이 **앉고**(원 바닥과 행 선 0.3pt) 3행 선에서 연결점 → 원으로 화살 토막
       (G067: 행 선이 원의 '입력 막대' 로 먹혀 두 행이 사라졌다 · 원에 닿는 끝은 단자다)
  2·3·4행 선 위에 칠한 ◆ 가 세로로 맞닿아 쌓임 (G067: ◆ 둘레 획이 선이 되어 네 행이 한 그물)
  6·7행 → AND 막대, 6행 화살촉은 한 path 에 두 번 그림 (G053)
  9행 → 0.09pt 기운 선 끝에 작은 닫힌 삼각형 → AND 막대 (1A5J FG_G-101 · 입력 하나뿐인 AND 는 도면대로 통과)
  11행 → 상자(누름단추)의 오른쪽 변에서 선, 변 밖에 글자 획이 선 옆에 나란히 (G008 `ST/BY-A` 의 A)
  14행 → AND 막대 하나 + 막대 앞에서 끊긴 선 (입력 하나지만 읽기 빈틈 — 통과로 보지 않는다)
  17·18행 → 파선 둘 + 칠한 화살촉 → AND 막대 (1A1Y HR_P001: 17행은 마지막 토막이 화살촉 밑에 깔려 꼭지까지,
       18행은 밑동 한 틈 앞에서 끝나고 화살촉 안에 짧은 토막 · 밑동이 축에서 0.06pt 비껴 있다)
"""
from __future__ import annotations

import pymupdf
import pytest

from app.logic import analyse, blocks as B, geom, graph, sim
from tests.test_logic_l23_generic import LX0, LX1, H, P, W, K, _line, _sheet, _text_box, ry


def _fill_tri(page, pts, twice=False):
    sh = page.new_shape()
    seq = [pymupdf.Point(*p) for p in (pts * 2 if twice else pts)]
    sh.draw_polyline(seq)
    sh.finish(color=None, fill=K, width=0, closePath=True)
    sh.commit()


def _diamond(page, cx, cy, half=5.2):
    """HRSG ◆ — 위·아래 반쪽 삼각형 둘 + 둘레 획 (밑변 공유)."""
    a, b, t, d = (cx - half, cy), (cx + half, cy), (cx, cy - half), (cx, cy + half)
    _fill_tri(page, [b, a, d])
    _fill_tri(page, [t, a, b])
    _line(page, d, b); _line(page, t, b); _line(page, d, a, t)


def _draw(page):
    rows_l = {2: ("", "SW OPENED"), 3: ("", "SW CLOSED"), 4: ("", "SW MID"), 6: ("", "A"), 7: ("", "B"),
              9: ("", "SLANT"), 12: ("", "C"), 14: ("", "ONLY ONE"), 17: ("", "DASH A"), 18: ("", "DASH B")}
    rows_r = {52: ("OPENED", ""), 53: ("CLOSED", ""), 54: ("MID", ""), 55: ("AND AB", ""), 59: ("PASS", ""),
              57: ("PB AND C", ""), 64: ("ONE", ""), 67: ("DASH AND", "")}
    _sheet(page, "XY_G-003", rows_l, rows_r)
    y2, y3, y4 = ry(2), ry(3), ry(4)
    _line(page, (LX0, y2), (LX1, y2))
    _line(page, (LX0, y3), (LX1, y3))
    _line(page, (LX0, y4), (LX1, y4))
    for y in (y2, y3, y4):
        _diamond(page, 350, y)
    # 연결 기호 원 — 바닥이 2행 선 0.3pt 위 · 3행 선의 연결점에서 올라오는 토막 + 화살
    r = 6.0
    cx, cy = 600.0, y2 - r - 0.3
    sh = page.new_shape(); sh.draw_circle(pymupdf.Point(cx, cy), r); sh.finish(color=K, width=0.72); sh.commit()
    _fill_tri(page, [(cx + r, cy - 2), (cx + r, cy + 2), (cx + r + 5, cy)])          # 꼭지 (연결 기호)
    sh = page.new_shape(); sh.draw_circle(pymupdf.Point(cx, y3), 1.4); sh.finish(color=K, fill=K, width=0); sh.commit()
    _line(page, (cx, y3), (cx, cy + r + 4))
    _fill_tri(page, [(cx - 1.5, cy + r + 4), (cx + 1.5, cy + r + 4), (cx, cy + r)])
    # 6·7행 → AND (막대) → 55행 · 6행 화살촉은 두 번 그린 한 path
    ya = (ry(6) + ry(7)) / 2
    out = _text_box(page, 450, ya, "AND", bar=True)
    _line(page, (LX0, ry(6)), (445, ry(6)))
    _fill_tri(page, [(445, ry(6) - 1.2), (445, ry(6) + 1.2), (450, ry(6))], twice=True)
    _line(page, (LX0, ry(7)), (445, ry(7)))
    _fill_tri(page, [(445, ry(7) - 1.2), (445, ry(7) + 1.2), (450, ry(7))])
    _line(page, out, (700, ya), (700, ry(55)), (LX1, ry(55)))
    # 9행 — 기운 선 + 작은 닫힌 삼각형 → AND (막대 · 입력 하나) → 56행
    y9 = ry(9)
    out = _text_box(page, 600, y9, "AND", bar=True)
    _line(page, (LX0, y9 - 0.09), (600, y9), (598.7, y9 + 0.42), (598.7, y9 - 0.45), (600, y9))
    _line(page, out, (LX1, y9))
    # 11행 — 누름단추 상자 → AND (12행과) → 57행 · 상자 오른쪽 변 밖에 글자 획이 선 옆에 나란히
    y11 = ry(11)
    _line(page, (380, y11 - 7), (410, y11 - 7), (410, y11 + 7), (380, y11 + 7), (380, y11 - 7))
    page.insert_text((383, y11 + 2), "START", fontsize=5)
    _line(page, (410, y11), (445, y11))
    _fill_tri(page, [(445, y11 - 1.2), (445, y11 + 1.2), (450, y11)])
    _line(page, (409.9, y11 + 0.6), (412.0, y11 + 0.6))                                # 'A' 가로획처럼
    yb = (y11 + ry(12)) / 2
    out = _text_box(page, 450, yb, "AND", bar=True)
    _line(page, (LX0, ry(12)), (445, ry(12)))
    _fill_tri(page, [(445, ry(12) - 1.2), (445, ry(12) + 1.2), (450, ry(12))])
    _line(page, out, (720, yb), (720, ry(57)), (LX1, ry(57)))
    # 14행 — 입력 하나뿐인 AND 인데 막대 앞에서 끊긴 선이 있다 (읽기 빈틈)
    y14 = ry(14)
    out = _text_box(page, 450, y14, "AND", bar=True)
    _line(page, (LX0, y14), (445, y14))
    _fill_tri(page, [(445, y14 - 1.2), (445, y14 + 1.2), (450, y14)])
    _line(page, (400, ry(15)), (447, ry(15)))                                           # 막대 3pt 앞에서 끝
    _line(page, out, (LX1, ry(64)))
    # 17·18행 — 파선(토막 5 · 틈 2.5) + 칠한 화살촉 → AND 막대 (1A1Y HR_P001 AND B6)
    yd = (ry(17) + ry(18)) / 2
    out = _text_box(page, 600, yd, "AND", bar=True)
    for y, last in ((ry(17), "tip"), (ry(18), "gap")):
        x = LX0
        while x + 5 <= 596 - 7.5:
            _line(page, (x, y), (x + 5, y)); x += 7.5
        if last == "tip":
            _line(page, (x, y), (600, y))                                  # 마지막 토막이 화살촉 밑에 깔려 꼭지까지
        else:
            _line(page, (x, y), (x + 5, y))                                # 밑동 한 틈 앞에서 끝남
            _line(page, (597.5, y), (600, y))                              # 화살촉 안의 짧은 토막
        _fill_tri(page, [(596.04, y - 1.0 + 0.06), (596.04, y + 1.0 + 0.06), (600, y)])
    _line(page, out, (LX1, ry(67)))


@pytest.fixture(scope="module")
def sheet(tmp_path_factory):
    doc = pymupdf.open()
    _draw(doc.new_page(width=W, height=H))
    p = tmp_path_factory.mktemp("l53") / "image.pdf"
    doc.save(p)
    res = analyse.analyse(str(p))
    return next(s for s in res["sheets"] if s["sheet_no"] == "XY_G-003")


def _net(s, side, n):
    return next(r["net"] for r in s["rows"] if r["side"] == side and r["n"] == n)


def _blk(s, logic, x, y):
    return next(k for k, b in s["blocks"].items() if b["logic"] == logic and abs(b["bbox"][0] - x) < 3 and abs(b["bbox"][1] - y) < 8)


def test_row_line_under_a_connector_circle_is_not_its_bus_and_stacked_diamonds_do_not_merge_rows(sheet):
    s = sheet
    assert _net(s, "L", 2) == _net(s, "R", 52)
    assert _net(s, "L", 3) == _net(s, "R", 53)
    assert _net(s, "L", 4) == _net(s, "R", 54)
    assert len({_net(s, "L", 2), _net(s, "L", 3), _net(s, "L", 4)}) == 3
    con = next(k for k, b in s["blocks"].items() if b["logic"] == "connector")
    assert [p["net"] for p in s["ports"] if p["block"] == con and p["dir"] == "in"] == [_net(s, "L", 3)]


def test_arrowhead_drawn_twice_in_one_path_still_attaches_the_row_to_the_bar(sheet):
    s = sheet
    bid = _blk(s, "and", 450, (ry(6) + ry(7)) / 2 - 4.5)
    ins, outs, *_ = sim._index(s)
    assert {n for n, _, _ in ins[bid]} == {_net(s, "L", 6), _net(s, "L", 7)}
    r = sim.simulate(s, {"row:6": 1, "row:7": 1})
    assert r["frames"][-1]["values"][_net(s, "R", 55)] == 1


def test_slanted_line_with_a_tiny_closed_arrowhead_reaches_the_bar_and_a_lone_input_and_passes(sheet):
    s = sheet
    bid = _blk(s, "and", 600, ry(9) - 4.5)
    ins, *_ = sim._index(s)
    assert [n for n, _, _ in ins[bid]] == [_net(s, "L", 9)]
    assert s["blocks"][bid]["param"].get("as_drawn") == 1
    r = sim.simulate(s, {"row:9": 1})
    assert r["frames"][-1]["values"][_net(s, "R", 59)] == 1 and bid not in r["short_gates"]
    r = sim.simulate(s, {})
    assert r["frames"][-1]["values"][_net(s, "R", 59)] == 0


def test_lone_input_and_with_a_broken_line_near_its_bar_is_still_a_reading_gap(sheet):
    s = sheet
    bid = _blk(s, "and", 450, ry(14) - 4.5)
    assert not s["blocks"][bid]["param"].get("as_drawn")
    r = sim.simulate(s, {"row:14": 1})
    assert r["frames"][-1]["values"][_net(s, "R", 64)] == 0 and bid in r["short_gates"]


def test_glyph_stroke_beside_the_wire_end_does_not_steal_the_button_output(sheet):
    s = sheet
    box = next(k for k, b in s["blocks"].items() if abs(b["bbox"][0] - 380) < 1 and abs(b["bbox"][2] - 410) < 1)
    assert [p["dir"] for p in s["ports"] if p["block"] == box] == ["out"]
    bid = _blk(s, "and", 450, (ry(11) + ry(12)) / 2 - 4.5)
    ins, *_ = sim._index(s)
    assert len(ins[bid]) == 2


def test_cell_rim_strokes_are_not_letters():
    """HRSG 누름단추 — 겹상자의 안쪽 테두리 선 · 깎은 모서리 꺾은선이 글자와 한 덩이로 묶여 AUTO 가 '8' 로 읽혔다."""
    cell = (366.2, 132.0, 385.64, 144.48)
    S = geom.Seg
    def poly(*segs):
        bb = (min(min(s.x0, s.x1) for s in segs), min(min(s.y0, s.y1) for s in segs),
              max(max(s.x0, s.x1) for s in segs), max(max(s.y0, s.y1) for s in segs))
        return geom.Poly(list(segs), bb, False, 0)
    rim = [poly(S(367.6, 133.4, 384.2, 133.4)), poly(S(367.6, 143.0, 384.2, 143.0)),
           poly(S(366.2, 132.0, 367.6, 133.4), S(367.6, 133.4, 367.6, 143.0), S(367.6, 143.0, 366.2, 144.48)),
           poly(S(384.2, 133.4, 385.64, 132.0)), poly(S(384.2, 143.0, 385.64, 144.48))]
    letters = [poly(S(370.4, 140.4, 371.7, 136.1), S(371.7, 136.1, 373.0, 140.4)), poly(S(370.9, 139.0, 372.6, 139.0)),
               poly(S(373.9, 136.1, 373.9, 140.4), S(373.9, 140.4, 376.2, 140.4), S(376.2, 140.4, 376.2, 136.1)),
               poly(S(378.1, 136.1, 378.1, 140.4)), poly(S(377.0, 136.1, 379.3, 136.1)),
               poly(S(379.9, 136.1, 382.5, 136.1), S(382.5, 136.1, 382.5, 140.4), S(382.5, 140.4, 379.9, 140.4), S(379.9, 140.4, 379.9, 136.1))]
    cs, vert = B._cell_chars(rim + letters, cell)
    assert len(cs) == 4 and not vert                       # A · U · T · O — 테두리 장식은 글자와 안 묶인다
    assert max(c.w for c in cs) < 0.3 * (cell[2] - cell[0])


def test_dashed_inputs_with_filled_arrowheads_attach_to_the_bar(sheet):
    """1A1Y HR_P001 — 밑동으로 되돌아가는 다리 · 축에서 비낀 다리가 두 입력을 삼켰다 (AND 가 출력 단자만 가졌다)."""
    s = sheet
    bid = _blk(s, "and", 600, (ry(17) + ry(18)) / 2 - 4.5)
    ins, *_ = sim._index(s)
    assert {n for n, _, _ in ins[bid]} == {_net(s, "L", 17), _net(s, "L", 18)}
    r = sim.simulate(s, {"row:17": 1, "row:18": 1})
    assert r["frames"][-1]["values"][_net(s, "R", 67)] == 1
    r = sim.simulate(s, {"row:17": 1})
    assert r["frames"][-1]["values"][_net(s, "R", 67)] == 0
