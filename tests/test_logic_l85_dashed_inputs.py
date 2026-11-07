"""L85 — 분석기: 파선 입력이 블록에 붙는다 (19VA 846쪽 차등 시뮬레이션에서 원본 PDF 로 확인한 분석 결함 셋).

① 파선의 끝 토막이 상자 변 2.4~3pt 앞(틈)에서 멈춘다 — 그 줄의 틈 길이만큼 더 가 보고 단자로 (BIT_CNT IN1~IN6 · ⎍ 펄스 상자)
② 막대 게이트 입력: 끝 토막이 막대 위에서 겹쳐 끝나고 막대 위에 작은 점 — '점에 닿음' 으로 끝나 입력이 빠졌다 (FW11_P002 ·
   같은 줄의 겹친 토막 모양은 합성으로 재현하지 못해 19VA 차등 시뮬레이션으로만 확인)
③ 막대 앞 화살촉의 5pt 조각이 입력으로 잡혀(모는 쪽 없음 → 늘 0) AND 가 늘 0 — 진짜 입력이 있을 때 조각은 뺀다 (0028)
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pymupdf
import pytest

from app.logic import analyse

_spec = importlib.util.spec_from_file_location("l21", Path(__file__).with_name("test_logic_l21_form.py"))
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)
P, LX0, LX1, ry = F.P, F.LX0, F.LX1, F.ry
DASH, GAP = 5.67, 2.83


def _dashed(page, x0, x1, y, end_gap=0.0):
    """x0 → x1 가로 파선 — 토막마다 따로 그린 선 (19VA).  end_gap > 0 이면 마지막 토막이 x1 앞 end_gap 에서 멈춘다."""
    x = x0
    stop = x1 - end_gap
    while x < stop - 0.3:
        F._line(page, (x, y), (min(x + DASH, stop), y))
        x += DASH + GAP


def _dot0(page, x, y):
    """길이 0 의 선 — 막대 위 작은 점 (19VA)."""
    sh = page.new_shape()
    sh.draw_line(pymupdf.Point(x, y), pymupdf.Point(x, y))
    sh.finish(color=F.BLACK, width=0.0)
    sh.commit()


def _page(doc):
    page = doc.new_page(width=F.W, height=F.H)
    for cols in (F.LCOLS, F.RCOLS):
        for a, b in zip(cols, cols[1:]):
            F._rect(page, (a, F.TOP - 2 * P, b, F.TOP))
            for k in range(F.N):
                F._rect(page, (a, F.TOP + k * P, b, F.TOP + (k + 1) * P))
    for x, t in ((40, "FROM"), (92, "NO."), (120, "TAG"), (140, "NO."), (220, "SERVICE"),
                 (900, "SERVICE"), (1020, "TAG"), (1040, "NO."), (1082, "NO."), (1120, "TO")):
        page.insert_text((x, F.TOP - 8), t, fontsize=7)
    page.insert_text((560, F.TOP - 8), "LOGIC", fontsize=7)
    for k in range(F.N):
        page.insert_text((95, F.TOP + k * P + 8), str(k + 1), fontsize=5)
        page.insert_text((1083, F.TOP + k * P + 8), str(F.N + k + 1), fontsize=5)
    for n, d in ((2, "A RUN"), (3, "B RUN"), (5, "TRIP")):
        page.insert_text((182, ry(n) + 2), d, fontsize=5)
    for n, d in ((31, "BOTH"), (32, "NOT TRIP")):
        page.insert_text((872, ry(n) + 2), d, fontsize=5)
    page.insert_text((1100, 808), "AA10_G085", fontsize=7)
    # ② 2 · 3 → AND (막대) → 31 — 파선 입력, 끝 토막이 막대 위에서 끝나고 그 자리에 길이 0 점
    y1, y2 = ry(2), ry(3)
    ax = 500.0
    for y in (y1, y2):
        _dashed(page, LX0, ax, y)
        _dot0(page, ax, y)
    o = F._and(page, ax, (y1 + y2) / 2)
    F._line(page, o, (700, o[1]), (700, ry(31)), (LX1, ry(31)))
    # ① 5 → NOT → 32 — 파선 끝 토막이 상자 변 2.5pt 앞에서 멈춘다
    i, o = F._not(page, 600, ry(5))
    _dashed(page, LX0, i[0], ry(5), end_gap=2.5)
    F._line(page, o, (680, o[1]), (680, ry(32)), (LX1, ry(32)))


@pytest.fixture(scope="module")
def sheet(tmp_path_factory):
    doc = pymupdf.open()
    F._legend(doc)
    _page(doc)
    p = tmp_path_factory.mktemp("l85") / "dashed.pdf"
    doc.save(p)
    res = analyse.analyse(p)
    return next(s for s in res["sheets"] if s["page"] == 2)


def _block_at(s, x, y):
    return next(bid for bid, b in s["blocks"].items() if b["bbox"][0] - 2 <= x <= b["bbox"][2] + 2 and b["bbox"][1] - 2 <= y <= b["bbox"][3] + 2)


def test_bar_gate_with_dots_on_the_bar_keeps_both_inputs(sheet):
    """막대 위 점(길이 0 선)이 있어도 두 입력이 막대에 붙는다."""
    bid = _block_at(sheet, 504.0, (ry(2) + ry(3)) / 2)
    ins = {p["net"] for p in sheet["ports"] if p["block"] == bid and p["dir"] == "in"}
    rows = {r["net"]: r["n"] for r in sheet["rows"] if r["side"] == "L"}
    assert {rows.get(n) for n in ins} == {2, 3}, (ins, rows)


def test_dashed_end_short_of_the_box_still_attaches(sheet):
    bid = _block_at(sheet, 604.0, ry(5))
    ins = [p for p in sheet["ports"] if p["block"] == bid and p["dir"] == "in"]
    rows = {r["net"]: r["n"] for r in sheet["rows"] if r["side"] == "L"}
    assert [rows.get(p["net"]) for p in ins] == [5]
