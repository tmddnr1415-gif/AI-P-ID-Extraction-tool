"""hotfix84 — 새 회사 양식 (Takhiatash · Hyundai · DIN 19227 · KKS) 이 통째로 안 읽히던 다섯 자리.

  1. 테두리를 선이 아니라 **사각형(quad) 하나**로 그린다 → 양식 칸을 못 쟀다
  2. 노트 열이 없고 NOTES 머리말이 도면 안에 있다 → 별표 뜻·유닛 배수를 못 읽었다
  3. 범례 머리말이 다른 낱말이다 (`2. VALVES` · `3. ACTUATORS` · `ELECTRICAL SIGNAL`)
  4. ISA 문자표가 **한 글자당 한 줄** 꼴이다 (DIN 19227)
  5. 원·버블 캡을 "곡선 + 아주 짧은 직선" 으로 그린다 → 버블·모터 원을 하나도 못 찾았다

기존 네 문서(AL NOUF1 · TC2 · QFE · UAD)는 이 길에 **닿지 않는다** — 정확한 머리말·선 테두리·
곡선만의 캡을 쓰므로 새 갈래는 앞 갈래가 비었을 때만 돈다.  회귀가 그것을 잰다.
"""
import ast
import inspect
import types

import pymupdf
import pytest

from app import pipeline as P
from app.engine import derive_layout as dl
from app.engine import detect_symbols as ds
from app.engine import extract_titleblocks as tb
from app.engine import isa_table
from app.engine import legend_rules as lr
from app.engine import pidcache


def _load(path):
    _d, pages = pidcache.load_pages(str(path))
    return pages


def _stub_cap(page, cx, cy, r, side):
    """버블 캡 하나를 Takhiatash 처럼 `l c l` (짧은 직선 + 베지어 + 짧은 직선) 로."""
    k = 4 / 3 * r * side
    stub = 0.1 * r
    sh = page.new_shape()
    sh.draw_line((cx - side * stub, cy - r), (cx, cy - r))
    sh.draw_bezier((cx, cy - r), (cx + k, cy - r), (cx + k, cy + r), (cx, cy + r))
    sh.draw_line((cx, cy + r), (cx - side * stub, cy + r))
    sh.finish(width=0.3, closePath=False)
    sh.commit()


def _stub_stadium(page, x0, y0, w, h):
    r = h / 2
    sh = page.new_shape()
    sh.draw_line((x0 + r, y0), (x0 + w - r, y0))
    sh.draw_line((x0 + r, y0 + h), (x0 + w - r, y0 + h))
    sh.finish(width=0.3)
    sh.commit()
    _stub_cap(page, x0 + r, y0 + r, r, -1)
    _stub_cap(page, x0 + w - r, y0 + r, r, 1)


# ---------------------------------------------------------------- 5. 곡선 판정

def test_curve_path_admits_tiny_stubs_but_not_sides():
    P0 = pymupdf.Point
    arc = ("c", P0(0, 0), P0(4, 0), P0(4, 8), P0(0, 8))
    stub = ("l", P0(-0.5, 0), P0(0, 0))
    side = ("l", P0(-6, 0), P0(0, 0))
    box = pymupdf.Rect(-0.5, 0, 3, 8)
    assert pidcache.curve_path([arc], box)
    assert pidcache.curve_path([stub, arc, stub], box)
    assert not pidcache.curve_path([side, arc], box)
    assert not pidcache.curve_path([stub], box)          # 곡선이 없으면 호가 아니다


def test_stub_led_caps_make_bubbles(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=400)
    for i in range(3):
        _stub_stadium(page, 60 + i * 60, 60, 37, 11.3)
    path = tmp_path / "stub_bubbles.pdf"
    doc.save(path)
    doc.close()
    found = ds.bubble_outlines(_load(path)[0])
    assert len(found) == 3
    assert all(abs(o.rect.width - 37) < 0.6 and abs(o.rect.height - 11.3) < 0.6 for o in found)


def test_round_box_keeps_curve_only_paths_as_before():
    P0 = pymupdf.Point
    d = {"items": [("c", P0(0, 0), P0(4, 0), P0(4, 8), P0(0, 8))],
         "bbox": pymupdf.Rect(0, 0, 4, 8)}
    assert pidcache.round_box(d, pymupdf.Matrix(1, 1)) is d["bbox"]
    d2 = {"items": [("l", P0(0, 0), P0(5, 0))], "bbox": pymupdf.Rect(0, 0, 5, 0.1)}
    assert pidcache.round_box(d2, pymupdf.Matrix(1, 1)) is None


# ---------------------------------------------------------------- 1·2. 양식

def _quad_form(tmp_path, pages=3, notes=True):
    doc = pymupdf.open()
    for _ in range(pages):
        page = doc.new_page(width=1191, height=842)
        sh = page.new_shape()                        # 종이 윤곽 (종이 가장자리 위)
        sh.draw_line((0.3, 0.5), (1190.8, 0.5))
        sh.draw_line((1190.8, 0.5), (1190.8, 841.4))
        sh.draw_line((0.3, 841.4), (1190.8, 841.4))
        sh.finish(width=0.36)
        sh.commit()
        sh = page.new_shape()                        # 테두리 — quad 하나
        sh.draw_quad(pymupdf.Rect(28.6, 7.6, 1183.8, 834.3).quad)
        sh.finish(width=0.96)
        sh.commit()
        if notes:
            page.insert_text((977, 28), "NOTES", fontsize=7)
            page.insert_text((977, 45), "1. ITEMS * MARK ARE SUPPLIED BY PUMP SUPPLIER.", fontsize=5)
    path = tmp_path / "quad_form.pdf"
    doc.save(path)
    doc.close()
    return path


def test_a_quad_border_is_the_frame_and_the_paper_edge_is_not(tmp_path):
    pages = _load(_quad_form(tmp_path))
    fr = dl._frame(pages)
    assert fr is not None
    left, top, right, bottom, column = (round(v, 1) for v in fr[:5])
    assert (left, top, right, bottom) == (28.6, 7.6, 1183.8, 834.3)
    assert column == right                          # 노트 열을 긋지 않은 양식


def test_notes_are_found_under_the_form_heading_when_no_column(tmp_path):
    lay = dl.derive(_load(_quad_form(tmp_path)))
    x0, y0, x1, _y1 = lay.items["regions.notes_area"].value
    assert x0 < 977 < x1 and y0 < 28
    assert "NOTES heading" in lay.items["regions.notes_area"].evidence


def test_line_drawn_frames_never_reach_the_box_fallback():
    src = inspect.getsource(dl._frame)
    # 상자 테두리는 선 테두리를 **못 찾았을 때만** 본다 (TC2 는 종이 둘레에 quad 를 두 개 더 긋는다)
    assert src.index("keep(vx), keep(hy)") < src.index("_box_edges(")


# ---------------------------------------------------------------- 3. 범례 머리말

def test_heading_alternatives_are_tried_only_after_the_exact_heading():
    src = inspect.getsource(lr._page_with)
    assert src.index("_line_with(pc, want)") < src.index("HEADING_ALTERNATIVES")
    assert lr.HEADING_ALTERNATIVES["LINE VALVES"] == ("§ VALVES",)


def test_numbered_section_heading(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=400)
    page.insert_text((50, 50), "2. VALVES", fontsize=6)
    page.insert_text((50, 80), "14. VALVES BODIES & FAILURE MODES", fontsize=6)
    path = tmp_path / "sec.pdf"
    doc.save(path)
    doc.close()
    pc = _load(path)[0]
    hit = lr._section_heading(pc, ["VALVES"])
    assert hit is not None and hit.y0 < 60          # `14. VALVES BODIES ...` 는 머리말이 아니다
    assert lr._section_heading(pc, ["ACTUATORS"]) is None


# ---------------------------------------------------------------- 4. ISA 목록 꼴

def test_isa_list_form(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=500)
    fs = 4.5
    page.insert_text((108, 84), "FIRST LETTER", fontsize=fs)
    page.insert_text((195.7, 84), "SUCCEEDING LETTERS", fontsize=fs)
    page.insert_text((70, 96), "MEASURED OR INITIATING VARIABLE", fontsize=fs)
    page.insert_text((163, 96), "MODIFIER", fontsize=fs)
    page.insert_text((195.6, 96), "DISPLAY OR OUTPUT FUNCTIONS", fontsize=fs)
    rows = [("A", "ANALYSIS", "", "ALARM LIMIT VALUE"),
            ("C", "CONDUCTIVITY", "", "CONTROLLING, CLOSED LOOP CONTROL"),
            ("D", "DENSITY", "DIFFERENCE", ""),
            ("I", "CURRENT", "", "INDICATION"),
            ("P", "PRESSURE", "", "TEST-POINT CONNECTION"),
            ("S", "SPEED", "", "SWITCHING"),
            ("T", "TEMPERATURE", "", "TRANSMITTING")]
    y = 108
    for letter, var, mod, fn in rows:
        page.insert_text((58, y), letter, fontsize=fs)
        page.insert_text((70, y), var, fontsize=fs)
        if mod:
            page.insert_text((162.4, y), mod, fontsize=fs)
        if fn:
            page.insert_text((195.3, y), fn, fontsize=fs)
        page.insert_text((330, y), "KKS TABLE WORDS HERE", fontsize=fs)   # 옆 표 — 읽으면 안 된다
        y += 10
    path = tmp_path / "isa_list.pdf"
    doc.save(path)
    doc.close()
    pages = _load(path)
    for pc in pages:
        pc.analysis_scope = "LEGEND"
    t = isa_table.derive(pages)
    assert t.succeeding.get("T") == ("TRANSMITTING",)
    assert t.succeeding.get("I") == ("INDICATION",)
    assert "KKS" not in " ".join(w for v in t.succeeding.values() for w in v)
    assert t.first.get("PD") == ("PRESSURE", "DIFFERENCE")      # 수식어 = 첫 글자 뒤의 글자
    assert t.decompose("PDIT") == ("PD", "IT")
    assert "one-row-per-letter" in t.note
    # 제어 기능 — DIN 의 C 는 CONTROLLING
    assert P.control_function_reason("TIC", 1, t)
    assert not P.control_function_reason("PIT", 0, t)


# ---------------------------------------------------------------- 같은 태그 = 한 루프

class _Isa:
    first = {"P": ("PRESSURE",), "L": ("LEVEL",)}
    succeeding = {"I": ("INDICATION",), "T": ("TRANSMITTING",), "S": ("SWITCHING",),
                  "A": ("ALARM",)}

    def decompose(self, tag):
        t = tag.upper()
        if t[:1] in self.first and t[1:] and all(c in self.succeeding for c in t[1:]):
            return t[:1], t[1:]
        return None

    def words_for(self, anchor):
        return ()


def _row(key, typ, tag, lines=0):
    ev = {"anchor": typ}
    if lines:
        ev["detail"] = {"bubble_lines": lines}
    return P.Row(key=key, tab="FIELD", page_no=6, drawing_no="B-SBA-M-32-001", type=typ,
                 tag_no=tag, rect=(0, 0, 10, 10), evidence=ev)


def test_lined_function_bubbles_fold_into_the_field_bubble_of_the_same_tag():
    rows = [_row("pit", "PIT", "00SBA20CP001"), _row("pisa", "PISA", "00SBA20CP001", lines=1),
            _row("ls", "LS", "10GMM21CL101"), _row("la", "LA", "10GMM21CL101", lines=1),
            _row("lsa", "LSA", "10GMM21CL101", lines=2),
            # 선 없는 버블이 둘 — 고르지 않는다
            _row("pi1", "PIT", "00SBA30CP001"), _row("pi2", "PS", "00SBA30CP001"),
            _row("pisa2", "PISA", "00SBA30CP001", lines=1)]
    facts, folded = P._fold_readouts(rows, _Isa())
    assert {"pisa", "la", "lsa"} <= folded
    assert "pisa2" not in folded
    assert any(f["basis"] == "TAG_LOOP" for f in facts["folded"])


# ---------------------------------------------------------------- 유닛 자리 없는 도면번호

def test_drawing_numbers_without_a_unit_field_have_no_unit_code():
    assert tb.parse_unit_code("B-SBA-M-32-001") is None
    assert tb.parse_unit_code("D00P-10LBA10-M05-0001") == "10"
    assert tb.parse_unit_code("D02J-31PGB0-M05-0001") == "31"
    assert "유닛 자리가 없고" in P.default_mult_reason(None)
    assert P.default_mult_reason("10") == P.DEFAULT_MULT_REASON % "10"


def test_unit_falls_back_to_the_legend_actuator_circle(monkeypatch):
    bf = types.SimpleNamespace(values={})
    monkeypatch.setattr(lr, "actuator_circle", lambda pages: (6.69, "x"))
    assert lr.legend_unit(bf) == 1.0                       # 페이지 없이 부르면 예전 그대로
    assert lr.legend_unit(bf, [object()]) == round(6.69 / 14.22, 4)
    bf2 = types.SimpleNamespace(values={"circle_diameter": 6.06})
    assert lr.legend_unit(bf2, [object()]) == 1.0          # 나비 원이 있으면 그것이 이긴다


def test_valve_rows_read_their_tag_from_the_tag_bubble():
    """밸브 몸체 안에는 태그 글자가 없다 — 지시선 끝 버블(`tag_rect`) 자리에서 읽는다."""
    src = inspect.getsource(P._attach_tags)
    assert '"tag_rect"' in src and src.index('"tag_rect"') < src.index("tagsys.assign(") + 400
