"""L23 — 처음 보는 프로젝트의 Logic 양식도 읽는다 (1A5J · 1A1Y 에서 드러난 것).

합성 묶음 두 장 — 범례 표가 **없고** (학습 사전만), 쪽이 **270° 회전**으로 저장돼 있다 (1A5J 처럼):
  시트 `AB_G-101`  시트 이름이 정해진 꼴이 아니다 → 타이틀블록 캡션 `SHEET` 아래 칸에서 읽는다
     2 · 3행 → [AND 글자 상자] → 51행 (TO `AB_G-102/2`)
     5행 → [DI 글자 상자 · 3 sec] → 52행          (ISA DI = 켜짐 지연)
     6 · 7 · 8행 → [2/3 글자 상자] → 53행          (투표 A/B)
     9 → S · 10 → R → [위·아래 두 칸 상자] → 54행  (글자를 못 읽어도 모양으로 메모리)
     11행 → 파선 틀 위의 속 빈 원 → 55행           (이음점 — 블록이 아니다 · 파선 틀은 신호선이 아니다)
  시트 `AB_G-102`  2행 FM `AB_G-101/51` · FROM 칸이 장 테두리를 겸한다 (1A1Y)
"""
from __future__ import annotations

import pymupdf
import pytest

from app.logic import analyse, fromto, geom, refs, sim

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


def _text_box(page, x, y, text, w=14.0, h=9.0, bar=False):
    """글자를 넣은 상자 (1A1Y `AND` · `DI` · `2/3`) — 막대가 있으면 왼쪽에 입력 막대."""
    if bar:
        _line(page, (x, y - 1.25 * P), (x, y + 1.25 * P))
    _rect(page, (x, y - h / 2, x + w, y + h / 2))
    page.insert_text((x + 1.5, y + 2), text, fontsize=5)
    return (x + w, y)


def _sheet(page, sheet_no, rows_l, rows_r, frame_table=False):
    """표 — 긴 괘선 양식.  frame_table 이면 표 바깥 변이 없다 (장 테두리가 겸한다 · 1A1Y)."""
    lcols = LCOLS[1:] if frame_table else LCOLS
    rcols = RCOLS[:-1] if frame_table else RCOLS
    bottom = TOP + N * P
    for x in lcols + rcols:
        _line(page, (x, TOP - 2 * P), (x, bottom))
    for k in range(N + 1):
        _line(page, (LCOLS[0], TOP + k * P), (LX0, TOP + k * P))
        _line(page, (LX1, TOP + k * P), (RCOLS[-1], TOP + k * P))
    if frame_table:                               # 장 테두리 — 굵게 칠한 띠
        sh = page.new_shape()
        sh.draw_rect(pymupdf.Rect(10, 10, W - 10, H - 10))
        sh.draw_rect(pymupdf.Rect(LCOLS[0] - 2, 12, RCOLS[-1] + 2, H - 12))
        sh.finish(color=None, fill=K, even_odd=True, width=0)
        sh.commit()
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
    # 타이틀블록 — 캡션 SHEET 아래 칸에 시트 이름 (꼴이 정해지지 않은 이름)
    page.insert_text((950, 805), "1Z9Z-00GEN00-J09-0003", fontsize=8)
    page.insert_text((1100, 790), "SHEET", fontsize=5)
    page.insert_text((1098, 800), sheet_no, fontsize=7)


def _sheet1(page):
    _sheet(page, "AB_G-101",
           {2: ("HMI", "PUMP A RUN"), 3: ("HMI", "PUMP B RUN"), 5: ("FIELD", "LEVEL LOW"),
            6: ("", "TX A HIGH"), 7: ("", "TX B HIGH"), 8: ("", "TX C HIGH"), 9: ("", "SET"), 10: ("", "RESET"),
            11: ("", "PASS")},
           {51: ("BOTH RUN", "AB_G-102/2"), 52: ("LOW 3S", ""), 53: ("2OO3 HIGH", ""), 54: ("LATCHED", ""),
            55: ("PASSED", "")})
    # 2 · 3 → AND → 31
    ym = (ry(2) + ry(3)) / 2
    _line(page, (LX0, ry(2)), (500, ry(2)))
    _line(page, (LX0, ry(3)), (500, ry(3)))
    o = _text_box(page, 500, ym, "AND", bar=True)
    _line(page, o, (700, o[1]), (700, ry(51)), (LX1, ry(51)))
    # 5 → DI (3 sec) → 32
    _line(page, (LX0, ry(5)), (500, ry(5)))
    o = _text_box(page, 500, ry(5), "DI")
    page.insert_text((502, ry(5) + 11), "3 sec", fontsize=5)
    _line(page, o, (710, o[1]), (710, ry(52)), (LX1, ry(52)))
    # 6 · 7 · 8 → 2/3 → 33
    for n in (6, 7, 8):
        _line(page, (LX0, ry(n)), (520, ry(n)))
    o = _text_box(page, 520, ry(7), "2/3", bar=True)
    _line(page, o, (720, o[1]), (720, ry(53)), (LX1, ry(53)))
    # 9 → S · 10 → R → 두 칸 상자 → 34   (칸 글자는 획으로 — 읽지 못하게 짧은 꺾은선)
    x, y0 = 540.0, ry(9) - P / 2
    _rect(page, (x, y0, x + 9, y0 + P))
    _rect(page, (x, y0 + P, x + 9, y0 + 2 * P))
    _line(page, (x + 3, y0 + 3), (x + 6, y0 + 3), (x + 3, y0 + 6), (x + 6, y0 + 8))
    _line(page, (x + 3, y0 + P + 8), (x + 3, y0 + P + 3), (x + 6, y0 + P + 5), (x + 3, y0 + P + 6))
    _line(page, (LX0, ry(9)), (x, ry(9)))
    _line(page, (LX0, ry(10)), (x, ry(10)))
    _line(page, (x + 9, ry(9)), (730, ry(9)), (730, ry(54)), (LX1, ry(54)))
    # 파선 틀 (큰 네모) — 위에 속 빈 원 하나 · 11 → 원 → 35
    fx0, fy0, fx1, fy1 = 400.0, ry(11) - 3 * P, 820.0, ry(28)
    for (a, b) in (((fx0, fy0), (fx1, fy0)), ((fx1, fy0), (fx1, fy1)), ((fx1, fy1), (fx0, fy1))):
        _line(page, a, b, dashes="[3 3] 0")
    _line(page, (fx0, fy1), (fx0, ry(11) + 3), dashes="[3 3] 0")
    _line(page, (fx0, ry(11) - 3), (fx0, fy0), dashes="[3 3] 0")
    _circle(page, (fx0, ry(11)), 2.8)
    _line(page, (LX0, ry(11)), (fx0 - 2.8, ry(11)))
    _line(page, (fx0 + 2.8, ry(11)), (740, ry(11)), (740, ry(55)), (LX1, ry(55)))


def _sheet2(page):
    _sheet(page, "AB_G-102", {2: ("AB_G-101/51", "BOTH RUN")}, {51: ("GO", "")}, frame_table=True)
    _line(page, (LX0, ry(2)), (600, ry(2)), (600, ry(51)), (LX1, ry(51)))


def make(path):
    """두 장을 그리고, 저장은 270° 회전한 쪽으로 (화면은 같은 모양 — 1A5J 처럼 글자 좌표가 회전 전 좌표로 나온다)."""
    src = pymupdf.open()
    _sheet1(src.new_page(width=W, height=H))
    _sheet2(src.new_page(width=W, height=H))
    doc = pymupdf.open()
    for i in range(len(src)):
        p = doc.new_page(width=H, height=W)
        p.show_pdf_page(p.rect, src, i, rotate=270)
        p.set_rotation(270)
    doc.save(path)
    return path


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return analyse.analyse(make(tmp_path_factory.mktemp("l23") / "new.pdf"))


def _s(res, no):
    return next(s for s in res["sheets"] if s["sheet_no"] == no)


def test_rotated_page_words_land_in_display_coordinates(tmp_path):
    src = pymupdf.open()
    a = src.new_page(width=400, height=200)
    a.insert_text((50, 100), "HELLO", fontsize=12)
    d = pymupdf.open()
    p = d.new_page(width=200, height=400)
    p.show_pdf_page(p.rect, src, 0, rotate=270)
    p.set_rotation(270)
    w = geom.words(p)[0]
    assert abs(w[0] - 50) < 1 and abs(w[3] - 103.6) < 1          # get_text 는 회전 전 좌표 (87, 310 …) 를 준다


def test_sheet_ids_and_fm_to_link_on_a_rotated_unfamiliar_form(result):
    s1, s2 = _s(result, "AB_G-101"), _s(result, "AB_G-102")
    t1 = {(r["side"], r["n"]): r for r in s1["table"]}
    assert t1[("L", 2)]["fm"] == "HMI" and t1[("L", 2)]["desc"] == "PUMP A RUN"
    assert t1[("R", 51)]["to"] == "AB_G-102/2"
    t2 = {(r["side"], r["n"]): r for r in s2["table"]}
    assert t2[("L", 2)]["fm"] == "AB_G-101/51"                     # FROM 칸이 장 테두리를 겸해도 읽는다
    fromto.check(result["sheets"])
    row = next(r for r in s2["rows"] if r["side"] == "L" and r["n"] == 2)
    assert row["ref"]["sheet"] == "AB_G-101" and row["ref"]["page"] == s1["page"]
    assert row["ft"]["ok"] is True


def test_gates_by_their_own_text_and_shape(result):
    s = _s(result, "AB_G-101")
    by_x = sorted(((round(b["bbox"][0]), b["func"], b["logic"]) for b in s["blocks"].values()))
    funcs = {f for _, f, _ in by_x}
    assert {"AND", "GT", "VOTE", "MEMORY"} <= funcs
    timer = next(b for b in s["blocks"].values() if b["logic"] == "delay_on")
    assert timer["param"].get("t") == 3
    vote = next(b for b in s["blocks"].values() if b["logic"] == "vote")
    assert {k: vote["param"][k] for k in ("a", "b")} == {"a": 2, "b": 3}      # L51 — op 열쇠는 따로
    assert not any(b["kind"] == "CIRCLE" and b["func"] == "UNKNOWN" for b in s["blocks"].values())   # 이음점 원은 블록이 아니다


def test_simulation_runs_through_the_new_gates_and_across_sheets(result):
    s1, s2 = _s(result, "AB_G-101"), _s(result, "AB_G-102")
    fromto.check(result["sheets"])

    def outs(forces, s=s1):
        res = sim.simulate_bundle(result["sheets"], {s1["page"]: forces}, focus=s["page"])
        vals = res["focus"]["frames"][-1]["values"]
        return {r["n"]: vals.get(str(r["net"]), vals.get(r["net"])) for r in s["rows"] if r["side"] == "R"}
    o = outs({})
    assert o[51] == 0 and o[53] == 0 and o[54] == 0 and o[55] == 0
    o = outs({"row:2": 1, "row:3": 1, "row:6": 1, "row:8": 1, "row:9": 1, "row:11": 1})
    assert o[51] == 1 and o[53] == 1 and o[54] == 1 and o[55] == 1
    assert outs({"row:2": 1, "row:3": 1}, s=s2)[51] == 1                 # 51 → TO AB_G-102/2 → 그 장 51
    assert outs({"row:2": 1})[51] == 0                                      # AND 는 입력 둘 다


def test_reference_grammar_is_read_not_memorised():
    assert refs.full("0016/72") == ("0016", 72)
    assert refs.full("FG_G-301-64") == ("FG_G-301", 64)
    assert refs.full("HR_G908/75") == ("HR_G908", 75)
    assert refs.full("G031-81") == ("G031", 81) and refs.full("GT11_G001-74") == ("GT11_G001", 74)
    assert refs.full("G54-85") is None                                     # 옛 꼴의 땅 — 잘못 읽은 G054 (HRSG 불변)
    for t in ("HMI", "FROM DRIVE", "HMI/LOGIC", "SWGR/MCC", "C/O", "THIS SHEET. 100", "1A5J-00GEN00-J09-0002"):
        assert refs.full(t) is None and refs.find(t) == []
    assert refs.find("0016/72 0016/77") == [("0016", 72), ("0016", 77)]
    b = refs.Bundle(["HR_G902", "HR_P001", "BD_G011"])
    assert b.mine("HR_G908") and b.mine("BD_P001")
    assert b.other("GT_G910") and b.other("HRSG_036")                       # 다른 문서 (계통 접두가 이 묶음에 없음)
    assert refs.Bundle(["0016", "FG_G-101"]).mine("FG_G-301")


def test_layout_does_not_crash_when_long_lines_share_one_x():
    pr = geom.Prims(1, W, H)
    pr.polys = [geom.Poly([geom.Seg(500.0, 10.0, 500.0, 800.0)], (500.0, 10.0, 500.0, 800.0)) for _ in range(6)]
    assert geom.layout(pr) is None                                         # 예전엔 max() 빈 목록으로 분석 전체가 멈췄다
