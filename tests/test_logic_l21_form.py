"""L21 — 19VA 양식 (진짜 글자 표 · 칸 사각형 표 · 모양으로 그린 게이트 · 범례 표에서 뜻 읽기).

합성 PDF 두 장:
  1쪽 범례 표  FUNCTION | SYMBOL | DEFINITION — AND(막대+네모) · OR(막대+사분원 넷) · NOT(⊠) · ON DELAY(둥근 상자 'ON')
  2쪽 Logic 시트  표를 칸마다 사각형으로 · 머리글 FROM|NO.|TAG NO.|SERVICE … SERVICE|TAG NO.|NO.|TO (진짜 글자)
           2·3행 → AND → 31행 · 2·3행 → OR → 33행 · 5행 → NOT → 32행 · 6행 → ON(2 SEC) → 34행
코드에는 게이트 모양 → 이름이 없다 — 범례 표가 정한다 (범례 행 순서를 바꾸면 뜻도 따라 바뀐다).
"""
from __future__ import annotations

import math

import pymupdf
import pytest

from app.logic import analyse, geom, refs, sim

W, H = 1191.0, 842.0
P = 11.3
TOP = 70.0
N = 30
LCOLS = [30.0, 90.0, 110.0, 180.0, 320.0]
RCOLS = [870.0, 1010.0, 1080.0, 1100.0, 1160.0]
LX0, LX1 = LCOLS[-1], RCOLS[0]
BLACK = (0, 0, 0)


def ry(n):
    """n 행 가운데 높이 (왼쪽 1~30 · 오른쪽 31~60)."""
    k = (n - 1) % N
    return TOP + k * P + P / 2


def _line(page, *pts):
    sh = page.new_shape()
    for a, b in zip(pts, pts[1:]):
        sh.draw_line(pymupdf.Point(*a), pymupdf.Point(*b))
    sh.finish(color=BLACK, width=0.72, closePath=False)
    sh.commit()


def _rect(page, r):
    sh = page.new_shape()
    sh.draw_rect(pymupdf.Rect(*r))
    sh.finish(color=BLACK, width=0.72)
    sh.commit()


def _arcs(page, cx, cy, r):
    """원을 사분원 넷 — 따로따로의 path (19VA 그리기)."""
    k = 0.5523 * r
    quads = [((cx, cy - r), (cx - k, cy - r), (cx - r, cy - k), (cx - r, cy)),
             ((cx - r, cy), (cx - r, cy + k), (cx - k, cy + r), (cx, cy + r)),
             ((cx, cy + r), (cx + k, cy + r), (cx + r, cy + k), (cx + r, cy)),
             ((cx + r, cy), (cx + r, cy - k), (cx + k, cy - r), (cx, cy - r))]
    for p0, p1, p2, p3 in quads:
        sh = page.new_shape()
        sh.draw_bezier(pymupdf.Point(*p0), pymupdf.Point(*p1), pymupdf.Point(*p2), pymupdf.Point(*p3))
        sh.finish(color=BLACK, width=0.72, closePath=False)
        sh.commit()


def _and(page, x, y):
    """막대 (x, y±1.25P) + 오른쪽 작은 네모.  → 출력 점."""
    _line(page, (x, y - 1.25 * P), (x, y + 1.25 * P))
    _rect(page, (x, y - 4.5, x + 8.5, y + 4.5))
    return (x + 8.5, y)


def _or(page, x, y):
    _line(page, (x, y - 1.25 * P), (x, y + 1.25 * P))
    _arcs(page, x + 4.8, y, 4.8)
    return (x + 9.6, y)


def _not(page, x, y):
    _rect(page, (x, y - 4, x + 8, y + 4))
    _line(page, (x, y - 4), (x + 8, y + 4))
    _line(page, (x, y + 4), (x + 8, y - 4))
    return (x, y), (x + 8, y)


def _on(page, x, y, label="ON"):
    """둥근 상자 (왼쪽 곧은 변 · 오른쪽 반원) + 안 글자."""
    _line(page, (x + 11.3, y - 5.65), (x, y - 5.65), (x, y + 5.65), (x + 11.3, y + 5.65))
    k = 0.5523 * 5.65
    sh = page.new_shape()
    sh.draw_bezier(pymupdf.Point(x + 11.3, y - 5.65), pymupdf.Point(x + 11.3 + k, y - 5.65),
                   pymupdf.Point(x + 16.95, y - k), pymupdf.Point(x + 16.95, y))
    sh.draw_bezier(pymupdf.Point(x + 16.95, y), pymupdf.Point(x + 16.95, y + k),
                   pymupdf.Point(x + 11.3 + k, y + 5.65), pymupdf.Point(x + 11.3, y + 5.65))
    sh.finish(color=BLACK, width=0.72, closePath=False)
    sh.commit()
    page.insert_text((x + 3, y + 2), label, fontsize=5)
    return (x, y), (x + 16.95, y)


def _legend(doc, order=("AND", "OR", "NOT", "ON DELAY"), pics=None):
    pics = pics or order
    page = doc.new_page(width=W, height=H)
    xs = [100.0, 200.0, 300.0, 600.0]           # FUNCTION | SYMBOL | DEFINITION
    y0, rh = 100.0, 30.0
    page.insert_text((120, y0 - 5), "FUNCTION", fontsize=8)
    page.insert_text((230, y0 - 5), "SYMBOL", fontsize=8)
    page.insert_text((400, y0 - 5), "DEFINITION", fontsize=8)
    y_end = y0 + rh * len(order)
    for x in xs:
        _line(page, (x, y0 - 15), (x, y_end))
    for k in range(len(order) + 1):
        _line(page, (xs[0], y0 + k * rh), (xs[-1], y0 + k * rh))
    _line(page, (xs[0], y0 - 15), (xs[-1], y0 - 15))
    for k, (name, pic) in enumerate(zip(order, pics)):
        cy = y0 + k * rh + rh / 2
        page.insert_text((110, cy + 3), name, fontsize=7)
        page.insert_text((310, cy + 3), "OUTPUT EXISTS ONLY WHEN", fontsize=6)
        name = pic
        if name == "AND":
            _and(page, 240, cy)
        elif name == "OR":
            _or(page, 240, cy)
        elif name == "NOT":
            _not(page, 240, cy)
        elif name == "ON DELAY":
            _on(page, 238, cy)


def _logic(doc):
    page = doc.new_page(width=W, height=H)
    # 표 — 칸마다 사각형 (19VA)
    for cols in (LCOLS, RCOLS):
        for a, b in zip(cols, cols[1:]):
            _rect(page, (a, TOP - 2 * P, b, TOP))                       # 머리글 칸
            for k in range(N):
                _rect(page, (a, TOP + k * P, b, TOP + (k + 1) * P))
    for x, t in ((40, "FROM"), (92, "NO."), (120, "TAG"), (140, "NO."), (220, "SERVICE"),
                 (900, "SERVICE"), (1020, "TAG"), (1040, "NO."), (1082, "NO."), (1120, "TO")):
        page.insert_text((x, TOP - 8), t, fontsize=7)
    page.insert_text((560, TOP - 8), "LOGIC", fontsize=7)
    for k in range(N):
        page.insert_text((95, TOP + k * P + 8), str(k + 1), fontsize=5)
        page.insert_text((1083, TOP + k * P + 8), str(N + k + 1), fontsize=5)
    text = {2: ("AA10_G001-5", "11ABC01CP001", "PUMP A RUNNING"), 3: ("", "", "PUMP B RUNNING"),
            5: ("", "", "TRIP"), 6: ("", "", "LEVEL LOW")}
    for n, (fm, tag, desc) in text.items():
        page.insert_text((32, ry(n) + 2), fm, fontsize=5)
        page.insert_text((112, ry(n) + 2), tag, fontsize=5)
        page.insert_text((182, ry(n) + 2), desc, fontsize=5)
    outs = {31: ("BOTH RUNNING", "BB20_G002-7"), 32: ("NOT TRIP", ""), 33: ("ANY RUNNING", ""), 34: ("LOW 2S", "")}
    for n, (desc, to) in outs.items():
        page.insert_text((872, ry(n) + 2), desc, fontsize=5)
        page.insert_text((1102, ry(n) + 2), to, fontsize=5)
    # 타이틀블록 — 도면번호 · 시트 번호
    page.insert_text((950, 805), "19XX-00GEN00-J09-0001", fontsize=8)
    page.insert_text((1100, 808), "AA10_G002", fontsize=7)
    # 2·3 → AND → 31
    y1, y2 = ry(2), ry(3)
    ym = (y1 + y2) / 2
    ax = 500.0
    _line(page, (LX0, y1), (ax, y1))
    _line(page, (LX0, y2), (ax, y2))
    o = _and(page, ax, ym)
    _line(page, o, (700, o[1]), (700, ry(31)), (LX1, ry(31)))
    # 같은 두 입력에서 갈라져 OR → 33 (연결점)
    for y, x in ((y1, 420.0), (y2, 440.0)):
        sh = page.new_shape()
        sh.draw_circle(pymupdf.Point(x, y), 1.2)
        sh.finish(color=BLACK, fill=BLACK, width=0.3)
        sh.commit()
    oy = ry(7)
    _line(page, (420, y1), (420, oy - 4), (560, oy - 4))
    _line(page, (440, y2), (440, oy + 4), (560, oy + 4))
    o = _or(page, 560, oy)
    _line(page, o, (720, o[1]), (720, ry(33)), (LX1, ry(33)))
    # 5 → NOT → 32
    i, o = _not(page, 600, ry(5) + 0.0)
    _line(page, (LX0, ry(5)), i)
    _line(page, o, (680, o[1]), (680, ry(32)), (LX1, ry(32)))
    # 4 → ON (2 SEC) → 34
    i, o = _on(page, 600, ry(10))
    page.insert_text((602, ry(10) + 13), "2 SEC", fontsize=5)
    _line(page, (LX0, ry(6)), (580, ry(6)), (580, ry(10)), i)
    _line(page, o, (740, o[1]), (740, ry(34)), (LX1, ry(34)))


def make(path, order=("AND", "OR", "NOT", "ON DELAY")):
    doc = pymupdf.open()
    _legend(doc, order)
    _logic(doc)
    doc.save(path)
    return path


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return analyse.analyse(make(tmp_path_factory.mktemp("l21") / "form.pdf"))


def _sheet(res):
    return next(s for s in res["sheets"] if s["page"] == 2)


def test_cell_drawn_table_is_found_and_columns_come_from_the_header(result):
    s = _sheet(result)
    assert s["sheet_no"] == "AA10_G002"
    t = {(r["side"], r["n"]): r for r in s["table"]}
    assert t[("L", 2)]["fm"] == "AA10_G001-5"
    assert t[("L", 2)]["kks"] == "11ABC01CP001"
    assert t[("L", 2)]["desc"] == "PUMP A RUNNING"
    assert t[("R", 31)]["desc"] == "BOTH RUNNING" and t[("R", 31)]["to"] == "BB20_G002-7"
    assert t[("L", 3)]["fm"] == "" and t[("L", 7)]["desc"] == ""          # 빈 칸은 빈 칸 (선 글자로 읽지 않는다)


def test_gate_meaning_comes_from_the_legend_shapes(result):
    s = _sheet(result)
    got = sorted((b["func"], b["logic"]) for b in s["blocks"].values())
    assert got == [("AND", "and"), ("GT", "delay_on"), ("NOT", "not"), ("OR", "or")]
    assert result["legend"]["pages"] == [1]
    timer = next(b for b in s["blocks"].values() if b["logic"] == "delay_on")
    assert timer["param"].get("t") == 2


def test_swapping_legend_rows_swaps_the_meaning(tmp_path):
    """모양 → 뜻은 코드가 아니라 범례가 정한다 — 범례가 AND 칸에 원 그림을, OR 칸에 네모 그림을 그리면 판정도 바뀐다."""
    doc = pymupdf.open()
    _legend(doc, ("AND", "OR", "NOT", "ON DELAY"), pics=("OR", "AND", "NOT", "ON DELAY"))
    _logic(doc)
    p = tmp_path / "swap.pdf"
    doc.save(p)
    s = _sheet(analyse.analyse(str(p)))
    square = next(b for b in s["blocks"].values() if abs(b["bbox"][0] - 500) < 1)      # 막대 + 네모
    circle = next(b for b in s["blocks"].values() if abs(b["bbox"][0] - 560) < 1)      # 막대 + 원
    assert square["func"] == "OR" and circle["func"] == "AND"


def test_simulation_on_the_new_form_follows_the_gates(result):
    s = _sheet(result)

    def outs(forces):
        res = sim.simulate_bundle(result["sheets"], {s["page"]: forces}, focus=s["page"])
        fr = res["focus"]["frames"][-1]
        vals = fr.get("values", fr)
        return {r["n"]: vals.get(str(r["net"])) for r in s["rows"] if r["side"] == "R"}
    assert outs({}) == {31: 0, 32: 1, 33: 0, 34: 0}
    assert outs({"row:2": 1}) == {31: 0, 32: 1, 33: 1, 34: 0}
    assert outs({"row:2": 1, "row:3": 1, "row:5": 1}) == {31: 1, 32: 0, 33: 1, 34: 0}


def test_sheet_reference_shapes():
    assert refs.REF.match("GT11_G001-74").groups() == ("GT11_G001", "74")
    assert refs.REF.match("G031-81").groups() == ("G031", "81")
    assert [m.groups() for m in refs.REF_ANY.finditer("HH10_G141-14HH10_G154-12")] == [("HH10_G141", "14"), ("HH10_G154", "12")]
    assert refs.series("HH10_P003") == "P" and refs.series("G031") == "G"
    assert refs.REF.match("SWGR/MCC") is None


def test_quarter_arcs_make_one_circle_but_letter_size_rings_do_not(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=200, height=200)
    _arcs(page, 50, 50, 4.8)
    _arcs(page, 120, 50, 1.0)
    p = tmp_path / "arcs.pdf"
    doc.save(p)
    pr = geom.read(pymupdf.open(p)[0], 1)
    rs = sorted(round(c.r, 1) for c, _ in pr.rings)
    assert rs == [1.0, 4.8]
    assert all(abs(c.cx - 50) < 0.1 or abs(c.cx - 120) < 0.1 for c, _ in pr.rings)
    assert math.isclose(max(c.r for c, _ in pr.rings), 4.8, abs_tol=0.05)
