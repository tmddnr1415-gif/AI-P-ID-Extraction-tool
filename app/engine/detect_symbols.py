#!/usr/bin/env python3
"""Phase 0 verification spike #2 — symbol detection on one page (docs/design.md 부록 A).

Scope is deliberately one page: page 6, `D00P-10LBA10-M05-0001` (HP Steam
System Group 10).  The result is compared against the 12 rows of the Field
Instrument Excel whose `P&ID No.` is that drawing.

Method — text anchor + geometry verification (docs/design.md §6.1).  No LLM,
no OCR: the sheet is vector, so every instrument tag letter is extractable text
and every bubble is a vector path.

    1. anchor scan       ISA function letters in the drawing area
    2. geometry verify   the anchor must sit inside an instrument bubble, which
                         on these sheets is a 68 x 22.6 pt stadium built from
                         two arc caps 56.6 pt apart (either orientation)
    3. exclusion filters  see below
    4. type mapping      drawing anchor -> Excel TYPE

Exclusion filters
-----------------
`TITLE_BLOCK`   anything in the right-hand title block / notes column.

`VENDOR_MARK`   the asterisk marks above a bubble.  Their meaning is read from
                this page's own NOTES rather than assumed, per docs/design.md
                §10.1 (the mark dictionary is page-scoped, never global).  On
                page 6 the notes define:
                    *   supplied by HRSG
                    **  supplied by ST supplier
                Both are vendor-supplied, so neither belongs in the SCT field
                instrument list.

`SCT_SUPPLIER_SCOPE`  the supplier scope regions marked by 'SCT' text.  Two
                shapes occur on this page and both are handled:

                · a closed chain-dashed rectangle — 'SCT SUPPLIER' around the
                  turbines, Rect(1183, 162, 1910, 484).  Symbols inside are out.

                · a scope break on a pipe — the two 'SCT / HRSG' markers.  There
                  is no rectangle here: the pipe itself is drawn broken up to
                  the break point and solid after it, which is the drawing's way
                  of saying "not in contract up to here".  The break sits at
                  x = 633.3, exactly where the 'SCT' text starts.  An instrument
                  is inside the vendor region when its drop line lands on the
                  broken part of the pipe.

`NOT_FIELD_INSTRUMENT`  TW (thermowell) and FT never appear in the field
                instrument list.  FE was in this set when only page 6 had been
                checked; the full Excel has 18 FE rows, so it was moved back to
                the field instruments (see RULESET_V2).

`VALVE`         MOV and friends are valves, so they belong to the valve
                deliverables (docs/design.md §1.3), not this one.

Usage
-----
    python spike/detect_symbols.py --pdf data/pid_total.pdf --page 6 \
           --compare data/CZE_Field_Instrument.xlsx \
           --json out/detect_page006.json --png out/detect_page006.png
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
import re
import sys
from dataclasses import dataclass, field
from typing import NamedTuple
from pathlib import Path

try:
    import pymupdf
except ImportError:  # pragma: no cover
    sys.exit("PyMuPDF is required:  pip install pymupdf")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import projectconfig  # noqa: E402
from pidcache import load_pages  # noqa: E402

CFG = projectconfig.load()


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------
# Drawing anchor -> Excel TYPE.  The drawing uses transmitter letters (TT/PT)
# while the Excel uses indicating-transmitter letters (TIT/PIT).
#
# Two rule versions are kept so that a measurement can be compared like for
# like.  V1 is what page 6 alone justified; V2 corrects the entries that the
# full 563-row Excel disproved.
_V1_FIELD_TYPE_MAP = {
    "TT": "TIT", "PT": "PIT", "LT": "LIT", "PDT": "PDIT",
    "TI": "TI", "PI": "PI", "LI": "LI", "FI": "FI",
    "TIT": "TIT", "PIT": "PIT", "LIT": "LIT", "PDIT": "PDIT", "FIT": "FIT",
    "LS": "LS", "FS": "FS", "RO": "RO",
}
_V1_NOT_FIELD = frozenset({"TW", "FE", "FT"})

# V2 kept only so the effect of each correction stays measurable.
_V2_FIELD_TYPE_MAP = dict(_V1_FIELD_TYPE_MAP)
_V2_FIELD_TYPE_MAP.update({"FE": "FE", "LSH": "LS", "LSHH": "LS", "LSL": "LS"})
_V2_NOT_FIELD = frozenset({"TW", "FT"})

# V3 is the shipping ruleset and now comes from the project config
# (out/project_deps.md P1/P2).  The tag vocabulary itself is LEGEND — legend
# page 3's FIRST LETTER x SUCCEEDING LETTERS matrix defines TT, FE, LG and the
# rest — but the correspondence to the Excel TYPE column is not in the legend at
# all (it prints no TIT, FIT or LI), so it is a convention of this deliverable.
_V3_FIELD_TYPE_MAP = {str(k): str(v) for k, v in CFG.get("anchors.type_map").items()}
_V3_NOT_FIELD = frozenset(str(x) for x in CFG.get("anchors.not_field"))

# Valve anchors -> the valve deliverables, not this list.
#
# LEGEND, so it stays in code: legend page 3 lists PSV / PRV / BPRV under
# SELF-ACTUATED DEVICES and FCV / LCV / PCV / TCV in the CONTROL DEVICE column,
# and page 4 draws MOV / HCV / HV under VALVE BODY WITH ACTUATOR.
VALVE_ANCHORS = frozenset({"MOV", "HOV", "HV", "XV", "CV", "FCV", "TCV", "PCV",
                           "LCV", "NRV", "PSV", "PRV", "BPRV"})


@dataclass(frozen=True)
class Ruleset:
    name: str
    field_type_map: dict
    not_field: frozenset
    valves: frozenset = VALVE_ANCHORS
    disabled: frozenset = frozenset()   # scope rules switched off

    @property
    def anchors(self) -> frozenset:
        return frozenset(self.field_type_map) | self.not_field | self.valves


# SCT_SUPPLIER_SCOPE is off by default.
#
# Measured over all 49 drawings (spike/detect_all.py): with VENDOR_MARK active,
# enabling SCT changes detections 622 -> 620 and true positives 458 -> 456.
# Every symbol it uniquely removes is a row the Excel keeps — the two RO
# bubbles on p20 D00P-11LAB00-M05-0001 at (1118.5, 809.4) and (1118.5, 1300.0).
# It never uniquely catches a correct exclusion on any system, so it costs
# recall and buys nothing.  The code stays because the scope-break geometry it
# reads is real and will matter once piping scope is modelled separately from
# equipment supply; enable it with --enable-rule SCT_SUPPLIER_SCOPE.
DEFAULT_DISABLED = frozenset({"SCT_SUPPLIER_SCOPE"})

RULESET_V1 = Ruleset("v1-page6", _V1_FIELD_TYPE_MAP, _V1_NOT_FIELD, disabled=frozenset())
RULESET_V2 = Ruleset("v2-excel-verified", _V2_FIELD_TYPE_MAP, _V2_NOT_FIELD,
                     disabled=DEFAULT_DISABLED)
RULESET_V3 = Ruleset("v3-anchor-audit", _V3_FIELD_TYPE_MAP, _V3_NOT_FIELD,
                     disabled=DEFAULT_DISABLED)

# Back-compat aliases used by the single-page script.
FIELD_TYPE_MAP = _V3_FIELD_TYPE_MAP
NOT_FIELD_INSTRUMENT = _V3_NOT_FIELD
ANCHORS = RULESET_V3.anchors

# Glyph sizes seen in the mark legends of the pages that draw their marks.
# Used only to *notice* a mark on a page whose own legend is missing, never to
# interpret one — that stays page-scoped (docs/design.md §10.1).
KNOWN_GLYPH_SIZES = tuple(tuple(float(v) for v in pair)
                          for pair in (CFG.get_or("vendor_marks.glyph_sizes", []) or []))

# Shape of an ISA function-letter tag, used only to spot anchors the dictionary
# above is missing.  Matching this does not make something a detection.
#
# LEGEND: page 3's matrix tops out at five letters (PDAHL), which is where the
# bound comes from — not from anything project-specific.
ISA_LIKE_RE = re.compile(r"^[A-Z]{1,5}$")


@dataclass(frozen=True)
class Layout:
    # The drawing area; everything to the right is title block and notes.
    drawing_area: tuple = (38.0, 35.0, 1960.0, 1650.0)
    notes_area: tuple = (1960.0, 35.0, 2384.0, 1250.0)

    # Instrument bubble: a stadium built from two arc caps joined by straight
    # sides.  Sizes are NOT fixed — this document uses at least two families
    # (68.0 x 22.6 and 85.1 x 28.4) plus rarer ones, so the detector measures
    # them per page instead.  These bounds only say "an arc cap is roughly a
    # 2:1 rounded end of a plausible size"; the stadium length falls out of the
    # geometry.
    cap_span: tuple = (7.0, 50.0)       # long side of a cap
    cap_ratio: tuple = (1.6, 2.4)       # long/short of a cap
    brk_corner_tol: float = 3.0         # how far a dashed box's corner may miss
    side_tol: float = 0.8               # how close a side must run to the cap edge
    side_slack: float = 1.5             # how far a side may fall short of the caps
    anchor_slack: float = 3.0

    # Vendor asterisk marks sit just above the bubble.
    mark_blob: tuple = (1.5, 8.0)        # a raw path fragment of a mark
    mark_glyph_span: tuple = (3.0, 8.0)  # a whole clustered mark
    mark_cluster_gap: float = 2.0        # below the 4.5pt gap between two marks
    notes_text_x_max: float = 2330.0     # right edge of the notes text column
    box_edge_cover: float = 0.35         # how much of a box edge must be drawn
    box_mark_margin: float = 20.0        # how far outside a box its mark may sit
    note_line_gap: float = 20.0          # max y gap for a wrapped note line
    mark_above: float = 25.0
    # 19회차 — 별표가 버블 **옆**에 찍힌 장이 있다 (p25 · p27 · p30).
    # 마크가 가로로 얼마나 떨어져 찍히는가.  이 문서가 답했다 — 마크 646개를
    # 유클리드 최근접 버블에 붙여 가로 간격을 세면
    #
    #     0.00 ~ 8.58pt   386개   (8.49~8.58 에만 63개 — 옆자리 무리)
    #     8.58 ~ 10.59    **0개**  ← 빈 띠
    #    10.59            1개  ·  14.10~14.13  3개  ·  20.28 이상 나머지
    #
    # 문턱을 그 빈 띠 안 어디에 두어도 결과가 같으므로 임의값이 아니다
    # (17회차 C-4 · 16회차 `brk_max_mark` 와 같은 논법).
    mark_side: float = 10.0
    note_mark_row_tol: float = 6.0

    # Broken (dashed / chain-dashed) line runs.
    brk_max_mark: float = 20.0
    brk_max_gap: float = 6.0
    brk_bridge: float = 26.0
    brk_min_marks: int = 6
    brk_min_span: float = 40.0

    # Tying a scope marker to its geometry, and an instrument to a pipe run.
    scope_text_tol: float = 30.0
    drop_x_tol: float = 2.0
    drop_end_tol: float = 1.5
    # Whether a dashed scope box is built from both of its horizontal edges or
    # from the vertical the label stands beside.  Off by default: see
    # `find_sct_scopes`.
    scope_box_both_edges: bool = False


def _layout_from_config(cfg=CFG) -> Layout:
    """Build the layout, taking every PROJECT-classified value from config.

    Values left as dataclass defaults are the LEGEND / algorithm ones: the cap
    and side tolerances describe the bubble shape that legend pages 3-4 draw,
    and the broken-line parameters describe the line styles legend page 2
    prints.  Neither changes with the project.
    """
    d = Layout()
    box = cfg.get_or("vendor_marks.package_box",
                     {"edge_cover": d.box_edge_cover,
                      "mark_margin": d.box_mark_margin})
    # Broken-line geometry.  These were left as dataclass defaults because legend
    # page 2 draws the line styles and a style does not move with the project -
    # but it does move with the *sheet*: on an A0 print of the same drawing office's
    # form the chain-dash long mark measures 21.25 pt against the 20.0 here, so
    # every dashed boundary on that project fell out of the filter.  A project may
    # therefore supply them; with the block absent the defaults are unchanged, which
    # is the case for every project that has run so far.
    brk = cfg.data.get("broken_line") or {}
    return Layout(
        drawing_area=tuple(cfg.get_or("regions.drawing_area", d.drawing_area)),
        notes_area=tuple(cfg.get_or("regions.notes_area", d.notes_area)),
        notes_text_x_max=float(cfg.get_or("regions.notes_text_x_max", d.notes_text_x_max)),
        mark_blob=tuple(cfg.get_or("vendor_marks.blob_span", d.mark_blob)),
        mark_glyph_span=tuple(cfg.get_or("vendor_marks.glyph_span", d.mark_glyph_span)),
        mark_cluster_gap=float(cfg.get_or("vendor_marks.cluster_gap", d.mark_cluster_gap)),
        mark_above=float(cfg.get_or("vendor_marks.above", d.mark_above)),
        mark_side=float(cfg.get_or("vendor_marks.side", d.mark_side)),
        note_mark_row_tol=float(cfg.get_or("vendor_marks.note_row_tol", d.note_mark_row_tol)),
        note_line_gap=float(cfg.get_or("vendor_marks.note_line_gap", d.note_line_gap)),
        box_edge_cover=float(box["edge_cover"]),
        box_mark_margin=float(box["mark_margin"]),
        scope_text_tol=float(cfg.get_or("sct_scope.text_tol", d.scope_text_tol)),
        drop_x_tol=float(cfg.get_or("sct_scope.drop_x_tol", d.drop_x_tol)),
        drop_end_tol=float(cfg.get_or("sct_scope.drop_end_tol", d.drop_end_tol)),
        scope_box_both_edges=bool(
            (cfg.data.get("sct_scope") or {}).get("box_from_both_edges")),
        **{k: float(brk[k]) if k != "brk_min_marks" else int(brk[k])
           for k in ("brk_max_mark", "brk_max_gap", "brk_bridge",
                     "brk_min_marks", "brk_min_span", "brk_corner_tol")
           if k in brk},
    )


LAYOUT = _layout_from_config()


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def _inside(x, y, region) -> bool:
    x0, y0, x1, y1 = region
    return x0 <= x <= x1 and y0 <= y <= y1


def find_bubbles(pc, lay: Layout = LAYOUT) -> list[pymupdf.Rect]:
    """Instrument bubbles, measured rather than assumed.

    A bubble is two arc caps facing each other with *straight sides joining
    them*.  Requiring both sides is what makes this size-free: an adjacent pair
    of caps belonging to two different bubbles has no sides between it, so it
    is rejected without needing to know how long a stadium is supposed to be.
    That matters because this document set uses more than one bubble size, and
    the page 6 constants (68.0 x 22.6) do not hold everywhere.

    Caps are grouped by alignment and only *neighbouring* caps are paired, so
    bubbles standing 25 pt apart never merge into one blob.
    """
    caps_wide, caps_tall = [], []
    for d in pc.drawings():
        items = d["items"]
        if not items or any(i[0] != "c" for i in items):
            continue
        r = d["bbox"]
        w, h = r.width, r.height
        if w <= 0 or h <= 0:
            continue
        short, long_ = min(w, h), max(w, h)
        if not lay.cap_span[0] <= long_ <= lay.cap_span[1]:
            continue
        if not lay.cap_ratio[0] <= long_ / short <= lay.cap_ratio[1]:
            continue
        (caps_tall if h > w else caps_wide).append(r)

    h_seg: dict[float, list] = collections.defaultdict(list)
    v_seg: dict[float, list] = collections.defaultdict(list)
    for a, b in pc.segments():
        if abs(a.y - b.y) < 0.4 and abs(a.x - b.x) > 1.0:
            h_seg[round(a.y, 1)].append((min(a.x, b.x), max(a.x, b.x)))
        elif abs(a.x - b.x) < 0.4 and abs(a.y - b.y) > 1.0:
            v_seg[round(a.x, 1)].append((min(a.y, b.y), max(a.y, b.y)))

    steps = [round(i * 0.1, 1) for i in range(-8, 9)]

    def spans(index, coord, lo, hi) -> bool:
        for d in steps:
            for s0, s1 in index.get(round(coord + d, 1), ()):
                if s0 <= lo + lay.side_slack and s1 >= hi - lay.side_slack:
                    return True
        return False

    bubbles: list[pymupdf.Rect] = []

    # Horizontal stadiums: tall caps sharing a y extent, sides run horizontally.
    groups: dict[tuple, list] = collections.defaultdict(list)
    for r in caps_tall:
        groups[(round(r.y0, 1), round(r.y1, 1))].append(r)
    for g in groups.values():
        g.sort(key=lambda r: r.x0)
        for a, b in zip(g, g[1:]):
            if spans(h_seg, a.y0, a.x1, b.x0) and spans(h_seg, a.y1, a.x1, b.x0):
                bubbles.append(pymupdf.Rect(a.x0, a.y0, b.x1, b.y1))

    # Vertical stadiums: wide caps sharing an x extent, sides run vertically.
    groups = collections.defaultdict(list)
    for r in caps_wide:
        groups[(round(r.x0, 1), round(r.x1, 1))].append(r)
    for g in groups.values():
        g.sort(key=lambda r: r.y0)
        for a, b in zip(g, g[1:]):
            if spans(v_seg, a.x0, a.y1, b.y0) and spans(v_seg, a.x1, a.y1, b.y0):
                bubbles.append(pymupdf.Rect(a.x0, a.y0, b.x1, b.y1))

    return bubbles


def bubble_sizes(bubbles) -> collections.Counter:
    """Distribution of bubble dimensions, for reporting what a page actually uses."""
    return collections.Counter(
        (round(max(b.width, b.height), 1), round(min(b.width, b.height), 1))
        for b in bubbles
    )


class Mark(NamedTuple):
    """One vendor mark occurrence.  `stars` is how many asterisks it carries."""
    x: float
    y: float
    stars: int
    form: str            # GLYPH | TEXT


MARK_TEXT_RE = re.compile(r"^\(?(\*{1,3})\)?")


# 잉크와 종이.  팔레트가 아니라 **도면이 자기 표시에 쓰는 두 색**이고, 검사는
# "이 둘 중 어느 것도 아닌 색으로 그려졌는가" 다.  `detect_all._INK` 과 같은
# 값이고 같은 뜻이다 — 그쪽은 검토자가 칠한 형광을 가르는 데 쓰고, 여기서는
# 개정 클라우드처럼 도면 위에 덧그려진 빨간 표기를 가르는 데 쓴다.
_INK = ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))


def _is_ink(d) -> bool:
    """이 path 가 잉크(또는 종이)로만 그려졌는가."""
    for key in ("color", "fill"):
        c = d.get(key)
        if c is not None and tuple(round(v, 2) for v in c) not in _INK:
            return False
    return True


def _is_stroke_glyph(d) -> bool:
    """이 path 가 별표를 이루는 획인가 — **칠 없는 곧은 선**.

    16회차 실측.  이 문서의 별표는 획 여섯 개(가로 5.7 · 세로 5.7 · 대각
    4.02x4.02 두 개가 각각 두 번)로 그려지고 **전부 `fill=None` 이며 항목이
    전부 직선(`l`)** 이다.  근거는 범례다 — NOTES 정의줄이 인쇄한 별표
    **38개가 38개 다** 그 모양이다 (`*` 가 무엇인지 도면 스스로가 말하는
    자리이므로 이보다 확실한 표본이 없다).

    걸러지는 것은 밸브의 검은 점 같은 **칠한 원**이다: 곡선 네 개(`c`)로
    그린 지름 4.26 원 + 해칭 슬라이버들이라 크기만 보면 별표와 구분되지
    않는다.  실측으로 p9 의 체크밸브 점이 그 옆 패키지 상자의 테두리 띠에
    들어가 상자의 별표를 `*`(HRSG) 에서 `**`(ST SUPPLIER) 로 바꿔 놓고
    있었다.  전 도면: 마크 986 → 795 (칠했거나 곡선인 191개 제외) ·
    범례를 읽은 장 27 그대로 · 상자 78 그대로.
    """
    if d.get("fill") is not None:
        return False
    return all(it[0] == "l" for it in d["items"])


def in_mark_window(rect, x, y, lay: Layout = LAYOUT) -> bool:
    """마크 중심 `(x, y)` 가 이 사각형의 **마크 자리**에 있는가.

    ★ 19회차 — **판정하는 곳을 여기 하나로 모았다.**  이 창은 그 전까지 세
    군데(`read_vendor_mark` · `drawn_mark_sizes` · 소유자 가르기)에 같은 식이
    베껴져 있었고, 그중 하나만 고치면 갈린다.  그리고 **18회차의 감사 시험도
    같은 식을 네 번째로 베껴 갖고 있었다** — 그래서 감사가 판정기와 **같은
    눈**으로 보게 되어, 크기 축은 독립이었는데 **자리 축은 독립이 아니었다.**
    별표 SCOPE 지적이 세 번 반복된 이유가 그것이다.

    **사각형 하나다.**  두 갈래로 쪼개 놓았다가 p52 에서 걸렸다 — 별표가
    버블 위 테두리선에 **정확히 걸쳐** 찍혀서 중심이 `y0` 보다 0.00002pt
    위에 있었고, 그것이 "위" 도 "옆" 도 아니게 됐다.  두 자리는 같은 자리의
    두 얼굴이므로 경계를 만들지 않는다.

        가로   `x0 - mark_side` ~ `x1 + mark_side`   (10.0 — 빈 띠 8.58~10.59)
        세로   `y0 - mark_above` ~ `y1`              (25.0 — 11회차 실측)

    **아래는 넣지 않는다.  이번엔 근거가 있다.**  25pt 안에서 버블 아래에
    찍힌 마크를 전부 렌더로 확인했더니 **한 개도 그 버블의 것이 아니었다**:

        p7  (+8.4pt)   `**` 가 PCV·MOV 의 **액추에이터**(돔 · M 원) 옆에 있다
                       — 11회차 [B] 가 이미 잰 자리다.  버블에도 붙이면
                       같은 별표를 두 번 세는 것이다
        p33 (+7.2pt)   `*` 가 LG 버블이 아니라 옆 **사각 심볼**의 것이다
        p20 (+17.1pt)  `*` 가 오른쪽 **밸브**의 것이다
        p26·p27 (+49.6pt)  액추에이터 스템 **해칭**이다 (마크가 아니다)

    아래 방향을 열면(B=8) 이 다섯 장에서 18건이 붙고 그중 옳은 것은 0 이다.
    """
    return (rect.x0 - lay.mark_side <= x <= rect.x1 + lay.mark_side
            and rect.y0 - lay.mark_above <= y <= rect.y1)


def _glyph_clusters(pc, lay: Layout = LAYOUT):
    """Small square-ish vector blobs, merged into single glyphs.

    The asterisk is drawn differently on different sheets — one 4.0 pt path on
    page 6, four 2.6 pt paths on page 49 — so adjacent fragments are clustered
    rather than matched against a fixed size.  Which cluster size actually
    counts as a mark is decided per page from that page's own legend.
    """
    lo, hi, gap = lay.mark_blob, lay.mark_glyph_span, lay.mark_cluster_gap
    seen, blobs = set(), []
    for d in pc.drawings():
        # 16회차 — **도면이 자기 표시에 쓰는 색은 잉크와 종이 둘뿐이다.**
        # `detect_all._INK` 이 이미 쓰고 있는 개념 그대로다: 그 밖의 색으로
        # 칠해진 것은 도면의 표시가 아니라 위에 덧그린 것이다.  개정 클라우드와
        # 개정 삼각형은 빨강(1,0,0)으로 그려지고 그 호가 별표와 같은 크기라,
        # 이 걸림이 없으면 개정 표시가 벤더 별표로 읽힌다 (실측: p35 의 TIT 가
        # 별표 없이 `VENDOR(PUMP SUPPLIER)` 가 된 것이 그것이다).
        # 전 도면 실측: 글리프 마크 1,031개 중 잉크가 아닌 것 118개.
        # 그리고 별표는 **칠 없는 곧은 선**이다 (`_is_stroke_glyph`) — 범례가
        # 인쇄한 38개가 38개 다 그렇다.  이 걸림이 없으면 밸브의 검은 점이
        # 같은 크기의 마크로 잡힌다.
        if not _is_ink(d) or not _is_stroke_glyph(d):
            continue
        r = d["bbox"]
        w, h = r.width, r.height
        if not (lo[0] <= max(w, h) <= lo[1]) or min(w, h) <= 0.5:
            continue
        if not 0.55 <= w / h <= 1.8:
            continue
        key = (round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1))
        if key in seen:
            continue
        seen.add(key)
        blobs.append(+r)

    grid = collections.defaultdict(list)
    for i, r in enumerate(blobs):
        grid[(int(r.x0 // 8), int(r.y0 // 8))].append(i)
    parent = list(range(len(blobs)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for (gx, gy), idxs in grid.items():
        cand = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cand += grid.get((gx + dx, gy + dy), [])
        for i in idxs:
            for j in cand:
                if i >= j:
                    continue
                a, b = blobs[i], blobs[j]
                if (a.x0 <= b.x1 + gap and b.x0 <= a.x1 + gap
                        and a.y0 <= b.y1 + gap and b.y0 <= a.y1 + gap):
                    ra, rb = find(i), find(j)
                    if ra != rb:
                        parent[rb] = ra

    groups = collections.defaultdict(list)
    for i in range(len(blobs)):
        groups[find(i)].append(blobs[i])

    out = []
    for g in groups.values():
        bb = pymupdf.Rect(min(r.x0 for r in g), min(r.y0 for r in g),
                          max(r.x1 for r in g), max(r.y1 for r in g))
        if not hi[0] <= max(bb.width, bb.height) <= hi[1]:
            continue
        if not 0.75 <= bb.width / bb.height <= 1.35:
            continue
        out.append(bb)
    return out


def _notes_lines(pc, lay: Layout = LAYOUT):
    """The NOTES column, reassembled into lines."""
    x0, y0, x1, y1 = lay.notes_area
    sel = [(r, t) for r, t in pc.words if x0 <= r.x0 <= lay.notes_text_x_max
           and y0 <= r.y0 <= y1]
    rows = collections.defaultdict(list)
    for r, t in sel:
        rows[round(r.y0 / 7)].append((r, t))
    lines = []
    for key in sorted(rows):
        items = sorted(rows[key], key=lambda rt: rt[0].x0)
        lines.append({
            "y": min(r.y0 for r, _ in items),
            "y1": max(r.y1 for r, _ in items),
            "x0": items[0][0].x0,
            "words": [t for _, t in items],
            "text": " ".join(t for _, t in items),
        })
    return lines


def read_mark_dictionary(pc, lay: Layout = LAYOUT):
    """Page-scoped mark legend: {asterisk count -> meaning}.

    Returns (dictionary, glyph_size).  `glyph_size` is the cluster size this
    page uses for a drawn asterisk, or None when the page writes its marks as
    text.  Both notations occur, and several spellings of each:

        p6   [glyph]  DENOTES EQUIPMENT WILL BE SUPPLIED BY HRSG.
        p49  [glyph]  TO BE SUPPLIED BY PUMP VENDOR.
        p26  4. (*) SYMBOL INDICATES COMPONENTS FURNISHED BY / <cont.>
        p32  1. (*)MARKED ITEMS TO BE PROVIDED BY FUEL OIL PUMP / SUPPLIER.
        p46  * TO BE SUPPLIED BY WATER TREATMENT SUPPLIER
        p51  1. MARKED WITH * TO BE SUPPLIED BY PUMP VENDOR.

    Nothing is inferred from other pages: docs/design.md §10.1 requires the
    dictionary to be page-scoped because the same glyph means different things
    on different sheets.
    """
    lines = _notes_lines(pc, lay)
    clusters = [c for c in _glyph_clusters(pc, lay)
                if lay.notes_area[0] <= c.x0 <= lay.notes_text_x_max]

    entries = []            # (line_index, stars, text_after_mark, glyph_size)
    for i, ln in enumerate(lines):
        stars, size, rest = 0, None, None

        # glyph marks sitting to the left of the line's text
        on_line = [c for c in clusters
                   if ln["y"] - 4 <= (c.y0 + c.y1) / 2 <= ln["y1"] + 4
                   and (c.x0 + c.x1) / 2 < ln["x0"]]
        if on_line:
            stars = len(on_line)
            size = (round(on_line[0].width, 1), round(on_line[0].height, 1))
            rest = ln["text"]
        else:
            for j, w in enumerate(ln["words"]):
                m = MARK_TEXT_RE.match(w)
                if m:
                    stars = len(m.group(1))
                    tail = w[m.end():]
                    rest = " ".join(([tail] if tail else []) + ln["words"][j + 1:])
                    break
        if stars:
            entries.append({"line": i, "stars": stars, "text": rest, "size": size})

    dictionary, glyph_size = {}, None
    entry_lines = {e["line"] for e in entries}
    for e in entries:
        text = e["text"]
        prev_y = lines[e["line"]]["y"]
        for k in range(e["line"] + 1, len(lines)):
            ln = lines[k]
            # A wrapped note continues on the very next line, indented, with no
            # mark of its own.  The y gate keeps unrelated stamps further down
            # the column (e.g. "FOR INTERNAL USE") out of the definition.
            if k in entry_lines or ln["y"] - prev_y > lay.note_line_gap:
                break
            if re.match(r"^\d+\.", ln["text"]) or ln["x0"] <= lines[e["line"]]["x0"] + 2:
                break
            text += " " + ln["text"]
            prev_y = ln["y"]
        text = text.strip()
        if text and e["stars"] not in dictionary:
            dictionary[e["stars"]] = text
        if e["size"] and glyph_size is None:
            glyph_size = e["size"]
    return dictionary, glyph_size


def drawn_mark_sizes(pc, lay: Layout = LAYOUT, bubbles=None):
    """이 장이 **도면에** 별표를 어느 크기로 그렸나 — 그 장에서 잰다 (18회차).

    ★ 왜 필요한가.  `find_marks` 는 그 장 NOTES 정의줄이 인쇄한 별표 크기
    (`glyph_size`)만 인정했다.  **그런데 정의줄의 크기와 도면의 크기가 같을
    이유가 없다.**  실측 (27장 · 마크 자리의 뭉치 274개):

        26장   정의줄 4.0 ↔ 도면 4.0  ·  정의줄 5.2 ↔ 도면 5.2   (같다)
        p35    정의줄 **4.0** ↔ 도면 **7.8**                      (다르다)

    그래서 p35 의 별표 5개가 전부 버려졌고, 그 장 NOTES 가 정의한
    `1★ → SUPPLIED BY PUMP SUPPLIER` 가 아무 행에도 안 붙었다.  §3 의
    "범례 형상으로 도면 기기 검출" 실패가 이미 가르친 것과 같은 이야기다 —
    **범례는 뜻을 정하지 축척을 정하지 않는다** (그때 실측이 ×0.42~×2.00).

    재는 방법은 **자리**다.  별표는 버블 둘레의 정해진 창에 찍히고
    (`in_mark_window` — 판정기와 **같은 창**을 쓴다), 그 창에 들어온 잉크 획
    글리프는 별표 말고 올 것이 없다.  그 자리에서 **두 번 이상** 나온 크기만
    인정한다 — 한 번뿐인 것은 얼룩일 수 있다.

    ⚠ 순환이 아니다.  버블은 마크와 무관하게 기하로 찾고, 창은 config 의
      실측값이다.  그리고 **가산이다** — 지금 인정되는 크기를 빼지 않는다.

    실측 효과: 27장 중 **p35 한 장만** 달라진다 (7.8×7.8 · 7.9×7.8 추가).
    한 번뿐이라 기각되는 것은 p3 (5.2×5.8) · p4 · p40 · p41 이고, 그 중
    p40 · p41 은 범례가 없어 `allow_sizes` 로 이미 인정되므로 잃는 것이 없다.
    """
    if bubbles is None:
        bubbles = find_bubbles(pc, lay)
    if not bubbles:
        return []
    seen = collections.Counter()
    for c in _glyph_clusters(pc, lay):
        if c.x1 > lay.drawing_area[2]:
            continue
        cx, cy = (c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2
        in_mark_position = any(in_mark_window(b, cx, cy, lay) for b in bubbles)
        if in_mark_position:
            seen[(round(c.width, 1), round(c.height, 1))] += 1
    return [k for k, n in seen.items() if n >= 2]


def find_marks(pc, lay: Layout = LAYOUT, glyph_size=None, allow_sizes=(),
               bubbles=None):
    """Vendor marks in the drawing area, in whichever notation the page uses.

    A drawn asterisk is accepted when it matches a size this page actually
    uses: the one its own legend prints (`glyph_size`), **or** the one it draws
    marks at (`drawn_mark_sizes`, 18회차).  Without such a check every small
    square blob on the sheet — and there are hundreds — would read as a mark.
    `allow_sizes` is the fallback for pages with no legend: sizes seen in other
    pages' legends are used to *notice* a mark, never to interpret it, which is
    what produces VENDOR_MARK_UNDEFINED.
    """
    out = []
    sizes = [glyph_size] if glyph_size else list(allow_sizes)
    # 18회차 — 가산이다.  정의줄 크기를 빼지 않고 그 장이 실제로 그린 크기를
    # 더한다.  뜻(별 개수 → 공급자)은 여전히 그 장 NOTES 에서만 온다 (§10.1).
    for s in drawn_mark_sizes(pc, lay, bubbles):
        if not any(abs(s[0] - w) <= 0.6 and abs(s[1] - h) <= 0.6 for w, h in sizes):
            sizes.append(s)
    if sizes:
        for c in _glyph_clusters(pc, lay):
            if c.x1 > lay.drawing_area[2]:
                continue
            for w, h in sizes:
                if abs(c.width - w) <= 0.6 and abs(c.height - h) <= 0.6:
                    out.append(Mark((c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2, 1, "GLYPH"))
                    break
    for r, t in pc.words:
        m = MARK_TEXT_RE.match(t)
        if m and r.x1 <= lay.drawing_area[2] and t.strip("()*") == "":
            out.append(Mark((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, len(m.group(1)), "TEXT"))
    return out


def find_package_boxes(pc, lay: Layout = LAYOUT):
    """Dashed package boundary rectangles.

    Page 6 showed that a vendor mark can be attached to the corner of a package
    box instead of to each bubble inside it, so the box has to be found before
    the marks can be attributed.
    """
    h = broken_runs(pc, "h", lay)
    v = broken_runs(pc, "v", lay)
    boxes = []
    for i in range(len(v)):
        for j in range(i + 1, len(v)):
            x1, ya1, yb1, _ = v[i]
            x2, ya2, yb2, _ = v[j]
            if x2 < x1:
                x1, x2, ya1, ya2, yb1, yb2 = x2, x1, ya2, ya1, yb2, yb1
            if abs(ya1 - ya2) > 3 or abs(yb1 - yb2) > 3 or x2 - x1 < 30:
                continue
            width = x2 - x1
            need = lay.box_edge_cover * width
            top = [r for r in h if abs(r[0] - ya1) <= 3
                   and r[1] >= x1 - 3 and r[2] <= x2 + 3 and r[2] - r[1] >= need]
            bot = [r for r in h if abs(r[0] - yb1) <= 3
                   and r[1] >= x1 - 3 and r[2] <= x2 + 3 and r[2] - r[1] >= need]
            if top and bot:
                boxes.append(pymupdf.Rect(x1, ya1, x2, yb1))
    return boxes


def broken_runs(pc, axis: str, lay: Layout = LAYOUT) -> list[tuple]:
    """Runs of broken line (dashed pipe / chain-dashed scope boundary).

    Returns (coord, start, end, n_marks).  Both line styles on this sheet — the
    even dash of a not-in-contract pipe and the dash-dot-dot of a scope
    boundary — are chains of short collinear marks with small gaps, so one
    detector covers both.  Gaps up to `brk_bridge` are bridged so a run
    survives a symbol drawn across it.
    """
    buckets = collections.defaultdict(list)
    x0a, y0a, x1a, y1a = lay.drawing_area
    for a, b in pc.segments():
        if axis == "h" and abs(a.y - b.y) < 0.4 and abs(a.x - b.x) >= 1.0:
            if y0a <= a.y <= y1a:
                buckets[round(a.y, 1)].append((min(a.x, b.x), max(a.x, b.x)))
        elif axis == "v" and abs(a.x - b.x) < 0.4 and abs(a.y - b.y) >= 1.0:
            if x0a <= a.x <= x1a:
                buckets[round(a.x, 1)].append((min(a.y, b.y), max(a.y, b.y)))

    out = []
    for key, intervals in buckets.items():
        marks = [m for m in sorted(set(intervals)) if m[1] - m[0] <= lay.brk_max_mark]
        if len(marks) < lay.brk_min_marks:
            continue
        chains, cur = [], [marks[0]]
        for m in marks[1:]:
            if m[0] - cur[-1][1] <= lay.brk_max_gap:
                cur.append(m)
            else:
                chains.append(cur)
                cur = [m]
        chains.append(cur)

        merged: list[list] = []
        for ch in chains:
            if merged and ch[0][0] - merged[-1][-1][1] <= lay.brk_bridge:
                merged[-1].extend(ch)
            else:
                merged.append(list(ch))

        for ch in merged:
            span = ch[-1][1] - ch[0][0]
            if len(ch) >= lay.brk_min_marks and span >= lay.brk_min_span:
                out.append((key, ch[0][0], ch[-1][1], len(ch)))
    return out


# --------------------------------------------------------------------------
# SCT supplier scope regions
# --------------------------------------------------------------------------
@dataclass
class ScopeRegion:
    kind: str                       # BOX | PIPE_BREAK
    label: str                      # e.g. 'SCT SUPPLIER', 'SCT HRSG'
    rect: pymupdf.Rect | None = None
    run: tuple | None = None        # (y, x0, x1, n_marks) for PIPE_BREAK
    anchor: tuple = (0.0, 0.0)      # the SCT text position


def find_sct_scopes(pc, lay: Layout = LAYOUT) -> list[ScopeRegion]:
    """Locate every supplier scope region marked by 'SCT' text."""
    h_runs = broken_runs(pc, "h", lay)
    v_runs = broken_runs(pc, "v", lay)

    scopes: list[ScopeRegion] = []
    for r, t in pc.words:
        if t != "SCT" or not _inside(r.x0, r.y0, lay.drawing_area):
            continue
        sx, sy = r.x0, (r.y0 + r.y1) / 2

        # Partner label naming the counterparty (HRSG / SUPPLIER / ...).  It is
        # set just below the 'SCT' text, so search downward and ignore the
        # one- and two-character annotations that litter the pipe runs.
        partner, best = "", None
        for r2, t2 in pc.words:
            if t2 == "SCT" or not t2.isalpha() or len(t2) < 4:
                continue
            dx = abs((r2.x0 + r2.x1) / 2 - (r.x0 + r.x1) / 2)
            dy = (r2.y0 + r2.y1) / 2 - sy
            if dx > 80 or not 0 < dy < 70:
                continue
            d = dx + dy
            if best is None or d < best:
                best, partner = d, t2
        label = f"SCT {partner}".strip()

        # A closed chain-dashed rectangle whose edge passes by the SCT text.
        #
        # The label may sit on either side of the box, so with
        # `sct_scope.box_from_both_edges` the box is built from the two horizontal
        # runs that close it rather than from the vertical the label happens to
        # stand next to.  Reading the vertical as the left edge is what a sheet
        # with all its labels on the left teaches, and it collapses a box to zero
        # width the first time a label is set on the right - 2 of the 5 labels on
        # SADARA's turbine sheet, and 8 of AL NOUF1's own 13 boxes.
        #
        # It stays opt-in, and AL NOUF1 does not take it.  The geometry is right
        # there too - all 8 of its zero-width boxes are genuinely closed on four
        # chain-dashed sides, and each carries the two-arrow marker that says which
        # side is whose (`SCT ->` outward, `<- SUPPLIER` into the box), checked by
        # eye on p14, p24, p42 and p58.  What the widened boxes would change is the
        # Description axis, and that was adjudicated against the client's list:
        #
        #   p14  the box closes round #10 CLEAN DRAIN TANK and holds the sheet's
        #        only two LIT - which are xls rows 136-137, Descriptions written.
        #   p42  the box holds the whole compressed-air sheet, 12 detections, and
        #        the client has 0 rows for that drawing - but it has 0 rows for 15
        #        other sheets that carry no box at all, so it says nothing here.
        #
        # One sheet can adjudicate and it says the instruments stay described.  The
        # answer was to stop the span deciding that axis (`SUPPLIER_SPAN_SKIPS`),
        # not to widen the boxes: AL NOUF1's fingerprint and F1 are unchanged, and
        # a project whose labels stand on the right still gets a closed box.
        box = None
        for vx, vy0, vy1, _ in v_runs:
            if abs(vx - sx) > lay.scope_text_tol or not (vy0 - 5 <= sy <= vy1 + 5):
                continue
            # The corner: a horizontal run must reach the vertical one's x.  Both
            # ends are dashed, so the last mark stops short of the true corner by
            # up to a line weight - `brk_corner_tol` is that allowance, and like
            # the dash lengths it is a distance on paper, so it moves with the
            # sheet (see `_layout_from_config`).
            ct = lay.brk_corner_tol
            tops = [h for h in h_runs
                    if abs(h[0] - vy0) < ct and h[1] - ct <= vx <= h[2] + ct]
            bots = [h for h in h_runs
                    if abs(h[0] - vy1) < ct and h[1] - ct <= vx <= h[2] + ct]
            if tops and bots:
                x1 = max(max(h[2] for h in tops), max(h[2] for h in bots))
                if not lay.scope_box_both_edges:
                    box = pymupdf.Rect(vx, vy0, x1, vy1)
                    break
                x0 = min(min(h[1] for h in tops), min(h[1] for h in bots))
                box = pymupdf.Rect(min(x0, vx), vy0, max(x1, vx), vy1)
                break
        if box is not None:
            scopes.append(ScopeRegion("BOX", label, rect=box, anchor=(sx, sy)))
            continue

        # Otherwise a scope break: a broken pipe run ending at the SCT text.
        for hy, hx0, hx1, n in h_runs:
            if abs(hx1 - sx) <= 12.0 and 0 <= hy - sy <= 60.0:
                scopes.append(ScopeRegion("PIPE_BREAK", label, run=(hy, hx0, hx1, n),
                                          anchor=(sx, sy)))
                break
    # Several labels can name one span - SADARA's turbine box carries three - and
    # a span is one scope however many times it is labelled.  Identical regions are
    # folded and the labels kept together, so the count on screen is a count of
    # spans rather than of words.
    if not lay.scope_box_both_edges:
        return scopes
    folded: list[ScopeRegion] = []
    for sc in scopes:
        same = next((o for o in folded if o.kind == sc.kind
                     and _same_region(o, sc)), None)
        if same is None:
            folded.append(sc)
        elif sc.label and sc.label not in same.label:
            same.label = f"{same.label} / {sc.label}"
    return folded


def _same_region(a, b) -> bool:
    """Two scope regions that are the same span, however they were labelled."""
    if a.rect is not None and b.rect is not None:
        return (abs(a.rect.x0 - b.rect.x0) < 1 and abs(a.rect.y0 - b.rect.y0) < 1
                and abs(a.rect.x1 - b.rect.x1) < 1 and abs(a.rect.y1 - b.rect.y1) < 1)
    if a.run is not None and b.run is not None:
        return all(abs(x - y) < 1 for x, y in zip(a.run[:3], b.run[:3]))
    return False


def vertical_index(pc) -> dict:
    """Vertical segments bucketed by x, so drop-line tests stay cheap.

    These sheets carry ~150k segments each; scanning them per detection per
    scope would dominate a 52-page run.
    """
    idx: dict[float, list] = collections.defaultdict(list)
    for a, b in pc.segments():
        if abs(a.x - b.x) < 0.4 and abs(a.y - b.y) > 0.5:
            idx[round(a.x, 1)].append((min(a.y, b.y), max(a.y, b.y)))
    return idx


def lands_on_run(pc, bubble: pymupdf.Rect, run: tuple, lay: Layout = LAYOUT,
                 v_index: dict | None = None) -> bool:
    """True if the instrument's drop line lands on this broken pipe run.

    The drop line hangs from the bubble centre straight down onto the pipe, so
    the test is: a vertical segment at the bubble's centre x whose lower end
    sits on the run's y, with that x inside the run's span.  It is the drop
    line's landing point — not mere proximity — that decides scope, which is
    what separates the two instruments just right of the break from the five
    just left of it.
    """
    ry, rx0, rx1, _ = run
    cx = (bubble.x0 + bubble.x1) / 2
    if not rx0 <= cx <= rx1 or bubble.y1 > ry:
        return False
    if v_index is None:
        v_index = vertical_index(pc)
    step = 0.1
    n = int(lay.drop_x_tol / step)
    for i in range(-n, n + 1):
        for lo, hi in v_index.get(round(cx + i * step, 1), ()):
            if abs(hi - ry) <= lay.drop_end_tol and lo >= bubble.y1 - 2:
                return True
    return False


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------
@dataclass
class Detection:
    anchor: str
    bbox: pymupdf.Rect
    center: tuple
    excel_type: str | None = None
    category: str = ""              # FIELD_INSTRUMENT | VALVE | OTHER
    included: bool = True
    exclude_rule: str = ""          # the rule reported as primary
    rules_hit: list = field(default_factory=list)   # every rule that applies
    evidence: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "anchor": self.anchor,
            "excel_type": self.excel_type,
            "category": self.category,
            "included": self.included,
            "exclude_rule": self.exclude_rule,
            "rules_hit": self.rules_hit,
            "bbox": [round(v, 1) for v in (self.bbox.x0, self.bbox.y0, self.bbox.x1, self.bbox.y1)],
            "center": [round(self.center[0], 1), round(self.center[1], 1)],
            "evidence": self.evidence,
        }


def package_box_marks(boxes, marks, lay: Layout = LAYOUT) -> list:
    """`[(box, stars)]` — 경계에 찍힌 마크는 상자 **안 전체**에 걸린다.

    (page 6 marks the HRSG flow package that way, not its bubbles.)
    """
    out = []
    m = lay.box_mark_margin
    for b in boxes:
        outer = pymupdf.Rect(b.x0 - m, b.y0 - m, b.x1 + m, b.y1 + m)
        inner = pymupdf.Rect(b.x0 + 5, b.y0 + 5, b.x1 - 5, b.y1 - 5)
        stars = sum(k.stars for k in marks
                    if outer.x0 <= k.x <= outer.x1 and outer.y0 <= k.y <= outer.y1
                    and not (inner.x0 <= k.x <= inner.x1 and inner.y0 <= k.y <= inner.y1))
        if stars:
            out.append((b, stars))
    return out


def _mark_gap(rect, x: float, y: float) -> float:
    """마크 `(x, y)` 가 이 사각형에서 얼마나 떨어져 있나 (안이면 0).

    ★ 19회차 — **두 축을 다 본다.**  16회차의 `_x_gap` 은 가로만 봤고,
    그때는 창도 가로로만 애매해서 그것으로 충분했다.  창이 세로로도 뻗자
    **세로로 쌓인 버블**을 가르지 못하게 됐다 (p9: 버블 5개가 한 줄로 서고
    가로 간격이 전부 5.64pt 로 같다).

    그리고 **체비쇼프(max)로는 안 된다** — 두 경우가 서로 반대를 요구한다:

        p25  나란한 PT·TT 사이의 별표.  세로 간격이 5.67 로 **같고**
             가로가 0.09 ↔ 2.85 로 갈린다        → 가로가 답해야 한다
        p9   세로로 쌓인 버블 옆의 `**`.  가로가 5.64 로 **같고**
             세로가 0.0 ↔ 21.9 로 갈린다          → 세로가 답해야 한다

    `max` 는 각각의 경우에서 갈리는 축을 **버린다** (p25 는 둘 다 5.67,
    p9 는 둘 다 5.64 → 무승부 → 둘 다 가져간다).  유클리드는 두 축을 다
    쓰므로 둘 다 맞는다.  실측: 전 도면 `UNDEFINED` 가 가로만 20 · 체비쇼프
    16 · **유클리드 15** 이고, 렌더로 확인한 p25(별 1개) · p9(별 2개)를
    동시에 맞히는 것은 유클리드뿐이다.
    """
    dx = max(rect.x0 - x, x - rect.x1, 0.0)
    dy = max(rect.y0 - y, y - rect.y1, 0.0)
    return math.hypot(dx, dy)


def read_vendor_mark(rect, marks, box_marks, mark_dict, lay: Layout = LAYOUT,
                     others=()):
    """이 사각형에 걸린 벤더 마크 → `(rules_hit, evidence)`.  없으면 `([], None)`.

    11회차에 `detect()` 안에서 꺼냈다.  움직인 것은 **위치뿐**이고 판정은 한
    글자도 바뀌지 않았다 (계기 지문 3a57b6b2 가 그대로인 것이 증거다).
    꺼낸 이유는 밸브 행의 SCOPE 를 같은 규칙으로 채우기 위해서다 — 밸브용으로
    한 벌 더 쓰면 다음 회차에 두 규칙이 갈린다.

    의미는 **그 페이지 NOTES 에서만** 온다 (docs/design.md §10.1).  같은 글리프가
    시트마다 다른 것을 뜻하므로, 그 장이 정의하지 않은 마크는 판단을 미루고
    `VENDOR_MARK_UNDEFINED` 로 표시만 한다 — 추측하지 않는다.
    """
    cx, cy = (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2
    near = [k for k in marks if in_mark_window(rect, k.x, k.y, lay)]
    # 16회차 — **한 마크는 버블 하나에만 붙는다.**  창이 좌우로 늘어나 있어서
    # 나란히 선 두 버블의 창이 겹치고, 그 사이에 찍힌 마크가 **둘 다에**
    # 세어졌다.  실측: p25 의 PT 는 자기 별표 1개 + 옆 TT 의 별표 1개를 합쳐
    # `**` 가 되고, 그 장 NOTES 는 `*` 만 정의하므로 `UNDEFINED` 로 떨어졌다.
    # 그래서 **더 가까운 버블이 따로 있으면 그 마크는 이 사각형의 것이 아니다.**
    # 창을 좁히지 않는다 — 좁히면 자기 별표가 떨어져 나가는 버블이 생긴다.
    # 19회차 — 그 "가깝다" 를 **두 축으로** 잰다 (`_mark_gap`).  가로만 보면
    # 세로로 쌓인 p9 의 `**` 다섯 쌍이 위 버블 것과 섞여 3★·4★ 가 된다.
    if others:
        near = [k for k in near
                if not any(_mark_gap(o, k.x, k.y) < _mark_gap(rect, k.x, k.y)
                           and in_mark_window(o, k.x, k.y, lay)
                           for o in others)]
    stars = sum(k.stars for k in near)
    source, forms = "SYMBOL", {k.form for k in near}
    if not stars:
        for b, st in box_marks:
            if b.x0 <= cx <= b.x1 and b.y0 <= cy <= b.y1:
                stars, source, forms = st, "PACKAGE_BOX", {"BOX"}
                break
    if not stars:
        return [], None
    meaning = mark_dict.get(stars)
    evidence = {"stars": stars, "source": source,
                "meaning": meaning or "UNDEFINED ON THIS PAGE"}
    if meaning is None:
        return ["VENDOR_MARK_UNDEFINED"], evidence
    return ["VENDOR_MARK_BOX" if source == "PACKAGE_BOX"
            else "VENDOR_MARK_TEXT" if "TEXT" in forms
            else "VENDOR_MARK_GLYPH"], evidence


def detect(pc, lay: Layout = LAYOUT, rules: Ruleset = RULESET_V3,
           disabled: frozenset | None = None, allow_glyph_sizes=KNOWN_GLYPH_SIZES):
    bubbles = find_bubbles(pc, lay)
    mark_dict, glyph_size = read_mark_dictionary(pc, lay)
    marks = find_marks(pc, lay, glyph_size, allow_sizes=allow_glyph_sizes,
                       bubbles=bubbles)
    boxes = find_package_boxes(pc, lay)
    scopes = find_sct_scopes(pc, lay)
    v_index = vertical_index(pc)

    box_marks = package_box_marks(boxes, marks, lay)

    if disabled is None:
        disabled = rules.disabled

    detections: list[Detection] = []
    unverified: list[dict] = []

    for r, t in pc.words:
        if t not in rules.anchors:
            continue
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2

        if not _inside(cx, cy, lay.drawing_area):
            continue  # title block / notes column — never a symbol

        # -- geometry verification -------------------------------------
        hit = [
            b for b in bubbles
            if b.x0 - lay.anchor_slack <= cx <= b.x1 + lay.anchor_slack
            and b.y0 - lay.anchor_slack <= cy <= b.y1 + lay.anchor_slack
        ]
        if len(hit) != 1:
            unverified.append({"anchor": t, "center": [round(cx, 1), round(cy, 1)],
                               "bubbles_matched": len(hit)})
            continue
        bubble = hit[0]
        det = Detection(anchor=t, bbox=bubble, center=(cx, cy))

        # -- category / type mapping -----------------------------------
        if t in rules.valves:
            det.category = "VALVE"
            det.included = False
            det.exclude_rule = "VALVE"
            det.rules_hit.append("VALVE")
            det.evidence["note"] = "valve deliverable, not the field instrument list"
        elif t in rules.not_field:
            det.category = "OTHER"
            det.included = False
            det.exclude_rule = "NOT_FIELD_INSTRUMENT"
            det.rules_hit.append("NOT_FIELD_INSTRUMENT")
            det.evidence["note"] = f"{t} never appears in the field instrument list"
        else:
            det.category = "FIELD_INSTRUMENT"
            det.excel_type = rules.field_type_map[t]

        # -- vendor mark (page-scoped meaning) -------------------------
        # 이름은 `mark_rules` 다 — `rules` 는 이 함수의 **매개변수**(Ruleset)이고,
        # 여기서 덮으면 다음 낱말에서 `rules.anchors` 가 터진다 (실제로 그랬다).
        mark_rules, vmark = read_vendor_mark(bubble, marks, box_marks,
                                             mark_dict, lay,
                                             others=[b for b in bubbles
                                                     if b is not bubble])
        if vmark:
            det.evidence["vendor_mark"] = vmark
            det.rules_hit.extend(mark_rules)
            for rule in mark_rules:
                if (rule != "VENDOR_MARK_UNDEFINED" and det.included
                        and rule not in disabled):
                    det.included = False
                    det.exclude_rule = rule

        # -- SCT supplier scope ----------------------------------------
        for sc in scopes:
            inside = False
            if sc.kind == "BOX" and sc.rect is not None:
                inside = sc.rect.x0 <= cx <= sc.rect.x1 and sc.rect.y0 <= cy <= sc.rect.y1
            elif sc.kind == "PIPE_BREAK" and sc.run is not None:
                inside = lands_on_run(pc, bubble, sc.run, lay, v_index)
            if inside:
                det.evidence["sct_scope"] = {
                    "label": sc.label,
                    "kind": sc.kind,
                    "region": ([round(v, 1) for v in sc.rect] if sc.rect
                               else [round(v, 1) for v in sc.run[:3]]),
                }
                det.rules_hit.append("SCT_SUPPLIER_SCOPE")
                if det.included and "SCT_SUPPLIER_SCOPE" not in disabled:
                    det.included = False
                    det.exclude_rule = "SCT_SUPPLIER_SCOPE"
                break

        detections.append(det)

    # Diagnostic only, never a detection rule: tokens that sit inside a verified
    # bubble but that the anchor dictionary does not cover.  These are the
    # candidates for TYPE_MAPPING_MISS when a drawing comes up short.
    unmapped: list[dict] = []
    for r, t in pc.words:
        if t in rules.anchors or not ISA_LIKE_RE.match(t):
            continue
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        if not _inside(cx, cy, lay.drawing_area):
            continue
        hit = [
            b for b in bubbles
            if b.x0 - lay.anchor_slack <= cx <= b.x1 + lay.anchor_slack
            and b.y0 - lay.anchor_slack <= cy <= b.y1 + lay.anchor_slack
        ]
        if len(hit) == 1:
            unmapped.append({"token": t, "center": [round(cx, 1), round(cy, 1)]})

    detections.sort(key=lambda d: (round(d.center[1] / 15), d.center[0]))
    return detections, scopes, mark_dict, unverified, unmapped, boxes


# --------------------------------------------------------------------------
# Excel comparison
# --------------------------------------------------------------------------
def load_excel_rows(path: Path, drawing_no: str) -> list[dict]:
    try:
        import openpyxl
    except ImportError:  # pragma: no cover
        sys.exit("openpyxl is required for --compare:  pip install openpyxl")

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["2.0_Instrument List"]
    rows = []
    for i in range(8, ws.max_row + 1):
        pid = ws.cell(i, 7).value
        if pid and str(pid).strip() == drawing_no:
            rows.append({
                "row": i,
                "no": ws.cell(i, 1).value,
                "type": ws.cell(i, 8).value,
                "qty": ws.cell(i, 9).value,
                "description": ws.cell(i, 10).value,
            })
    return rows


# --------------------------------------------------------------------------
# Overlay
# --------------------------------------------------------------------------
COLORS = {
    "included": (0.0, 0.55, 0.0),
    "VENDOR_MARK_GLYPH": (0.85, 0.35, 0.0),
    "VENDOR_MARK_TEXT": (0.95, 0.6, 0.0),
    "VENDOR_MARK_BOX": (0.6, 0.2, 0.6),
    "SCT_SUPPLIER_SCOPE": (0.85, 0.0, 0.0),
    "NOT_FIELD_INSTRUMENT": (0.45, 0.45, 0.45),
    "VALVE": (0.0, 0.35, 0.85),
}


def write_overlay(pc, detections, scopes, path: Path, zoom: float = 1.6) -> None:
    page = pc.page
    for sc in scopes:
        if sc.kind == "BOX" and sc.rect is not None:
            page.draw_rect(sc.rect, color=(0.85, 0, 0), width=2.0, dashes="[8 5] 0")
            page.insert_text((sc.rect.x0 + 4, sc.rect.y0 - 6), sc.label,
                             fontsize=13, color=(0.85, 0, 0))
        elif sc.run is not None:
            y, x0, x1, _ = sc.run
            page.draw_line(pymupdf.Point(x0, y), pymupdf.Point(x1, y),
                           color=(0.85, 0, 0), width=2.5)
            page.insert_text((x0 + 4, y - 6), f"{sc.label} (not in contract)",
                             fontsize=13, color=(0.85, 0, 0))

    for d in detections:
        color = COLORS["included"] if d.included else COLORS.get(d.exclude_rule, (0.5, 0.5, 0.5))
        page.draw_rect(d.bbox, color=color, width=1.8)
        label = d.excel_type if (d.included and d.excel_type) else d.anchor
        page.insert_text((d.bbox.x0, d.bbox.y0 - 3), label, fontsize=11, color=color)

    legend = [("detected (in list)", COLORS["included"]),
              ("excluded: vendor mark (glyph)", COLORS["VENDOR_MARK_GLYPH"]),
              ("excluded: vendor mark (text)", COLORS["VENDOR_MARK_TEXT"]),
              ("excluded: vendor mark (package box)", COLORS["VENDOR_MARK_BOX"]),
              ("excluded: SCT supplier scope", COLORS["SCT_SUPPLIER_SCOPE"]),
              ("excluded: not a field instrument", COLORS["NOT_FIELD_INSTRUMENT"]),
              ("excluded: valve", COLORS["VALVE"])]
    for i, (text, color) in enumerate(legend):
        y = 80 + i * 26
        page.draw_rect(pymupdf.Rect(70, y, 100, y + 16), color=color, width=3)
        page.insert_text((110, y + 13), text, fontsize=15, color=color)

    path.parent.mkdir(parents=True, exist_ok=True)
    page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(str(path))


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
def report(pc, drawing_no, detections, scopes, mark_dict, unverified, excel_rows):
    print(f"\n=== Symbol detection — page {pc.page_no}  {drawing_no} ===\n")

    print("page-scoped mark dictionary (from this page's NOTES, §10.1):")
    for n, meaning in sorted(mark_dict.items()):
        print(f"  {'*' * n:<4} {meaning}")
    if not mark_dict:
        print("  (none defined on this page)")

    print("\nSCT supplier scope regions found:")
    for sc in scopes:
        if sc.kind == "BOX":
            r = sc.rect
            print(f"  {sc.label:<14} BOX         ({r.x0:.0f},{r.y0:.0f})-({r.x1:.0f},{r.y1:.0f})")
        else:
            y, x0, x1, n = sc.run
            print(f"  {sc.label:<14} PIPE_BREAK  broken pipe y={y:.1f} x={x0:.1f}..{x1:.1f} "
                  f"({n} dashes), break at x={x1:.1f}")

    included = [d for d in detections if d.included]
    excluded = [d for d in detections if not d.included]

    print(f"\nanchors verified as symbols: {len(detections)}"
          f"   (geometry-unverified: {len(unverified)})")
    counts = collections.Counter(d.anchor for d in detections)
    print("  by anchor: " + ", ".join(f"{k}x{v}" for k, v in sorted(counts.items())))

    print(f"\nexcluded: {len(excluded)}")
    print("\n  rule coverage (rules overlap; each counts every symbol it catches):")
    for rule in ("SCT_SUPPLIER_SCOPE", "VENDOR_MARK_GLYPH", "VENDOR_MARK_TEXT",
                 "VENDOR_MARK_BOX", "VENDOR_MARK_UNDEFINED",
                 "NOT_FIELD_INSTRUMENT", "VALVE"):
        hit = [d for d in detections if rule in d.rules_hit]
        only = [d for d in hit if d.rules_hit == [rule]]
        print(f"    {rule:<22} catches {len(hit):>2}   (uniquely: {len(only)})")

    by_rule = collections.defaultdict(list)
    for d in excluded:
        by_rule[d.exclude_rule].append(d)
    for rule, ds in sorted(by_rule.items()):
        print(f"\n  [{rule}] {len(ds)}")
        for d in ds:
            why = ""
            if rule == "VENDOR_MARK":
                vm = d.evidence["vendor_mark"]
                why = f"{'*' * vm['stars']} [{vm['source']}] = {vm['meaning']}"
            elif rule == "SCT_SUPPLIER_SCOPE":
                sc = d.evidence["sct_scope"]
                why = f"{sc['label']} [{sc['kind']}] {sc['region']}"
            else:
                why = d.evidence.get("note", "")
            also = [r for r in d.rules_hit if r != rule]
            extra = f"   [also: {', '.join(also)}]" if also else ""
            print(f"    {d.anchor:<4} ({d.center[0]:7.1f},{d.center[1]:7.1f})  {why}{extra}")

    # --- comparison ---------------------------------------------------
    det_counts = collections.Counter(d.excel_type for d in included)
    exp_counts = collections.Counter(str(r["type"]).strip() for r in excel_rows)
    all_types = sorted(set(det_counts) | set(exp_counts))

    print(f"\n{'-' * 52}\nExcel comparison — {len(excel_rows)} rows for {drawing_no}\n")
    print(f"  {'TYPE':<8} {'detected':>9} {'excel':>7} {'diff':>6}")
    tp = 0
    for t in all_types:
        dcount, ecount = det_counts.get(t, 0), exp_counts.get(t, 0)
        tp += min(dcount, ecount)
        flag = "" if dcount == ecount else "   <<<"
        print(f"  {t:<8} {dcount:>9} {ecount:>7} {dcount - ecount:>+6}{flag}")
    n_det, n_exp = len(included), len(excel_rows)
    print(f"  {'TOTAL':<8} {n_det:>9} {n_exp:>7} {n_det - n_exp:>+6}")

    recall = tp / n_exp if n_exp else 0.0
    precision = tp / n_det if n_det else 0.0
    print(f"\n  recall    = {tp}/{n_exp} = {recall:6.1%}   (target >= 90%, docs/design.md §15)")
    print(f"  precision = {tp}/{n_det} = {precision:6.1%}")

    if unverified:
        print("\nanchors rejected by geometry verification:")
        for u in unverified:
            print(f"  {u['anchor']:<4} {u['center']}  bubbles_matched={u['bubbles_matched']}")

    mismatch = [t for t in all_types if det_counts.get(t, 0) != exp_counts.get(t, 0)]
    print("\n" + "-" * 52)
    if mismatch:
        print("MISMATCHES:")
        for t in mismatch:
            print(f"  {t}: detected {det_counts.get(t,0)} vs excel {exp_counts.get(t,0)}")
            for d in included:
                if d.excel_type == t:
                    print(f"     detected at ({d.center[0]:.1f}, {d.center[1]:.1f})")
    else:
        print(f"MATCH: detected set equals the Excel {n_exp} rows by TYPE.")
    print()
    return {"recall": recall, "precision": precision, "tp": tp,
            "detected": n_det, "expected": n_exp, "mismatch_types": mismatch}


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 0 spike 2 — symbol detection, one page")
    ap.add_argument("--pdf", default="data/pid_total.pdf")
    ap.add_argument("--page", type=int, default=6, help="1-based PDF page (spike scope: 6)")
    ap.add_argument("--compare", default="data/CZE_Field_Instrument.xlsx")
    ap.add_argument("--json", default="out/detect_page006.json")
    ap.add_argument("--png", default="out/detect_page006.png")
    ap.add_argument("--enable-rule", default="", metavar="RULE",
                    help="re-enable a rule that is off by default "
                         "(currently SCT_SUPPLIER_SCOPE; see DEFAULT_DISABLED)")
    ap.add_argument("--without", default="",
                    help="comma-separated exclusion rules to disable, to measure "
                         "what each one contributes (e.g. --without VENDOR_MARK)")
    args = ap.parse_args()

    doc, pages = load_pages(args.pdf)
    if not 1 <= args.page <= len(pages):
        sys.exit(f"page {args.page} out of range (1..{len(pages)})")
    pc = pages[args.page - 1]

    # Drawing number straight from the title block (spike 1 territory).
    drawing_no = next(
        (t for r, t in pc.words
         if r.x0 > 1950 and 1560 < r.y0 < 1600 and t.count("-") == 3),
        "",
    )

    enabled = {r.strip() for r in args.enable_rule.split(",") if r.strip()}
    disabled = (RULESET_V3.disabled - enabled) | frozenset(
        r.strip() for r in args.without.split(",") if r.strip())
    if disabled:
        print(f"\n   exclusion rules off for this run: {', '.join(sorted(disabled))}")
    detections, scopes, mark_dict, unverified, unmapped, boxes = detect(pc, disabled=disabled)
    excel_rows = load_excel_rows(Path(args.compare), drawing_no) if args.compare else []
    metrics = report(pc, drawing_no, detections, scopes, mark_dict, unverified, excel_rows)

    payload = {
        "page_no": pc.page_no,
        "drawing_no": drawing_no,
        "source_rotation": pc.source_rotation,
        "analysis_scope": pc.analysis_scope,
        "mark_dictionary": {"*" * k: v for k, v in sorted(mark_dict.items())},
        "sct_scopes": [
            {"label": s.label, "kind": s.kind,
             "rect": [round(v, 1) for v in s.rect] if s.rect else None,
             "run": [round(v, 1) for v in s.run] if s.run else None,
             "anchor": [round(v, 1) for v in s.anchor]}
            for s in scopes
        ],
        "metrics": metrics,
        "excel_rows": excel_rows,
        "detections": [d.to_json() for d in detections],
        "geometry_unverified": unverified,
        "unmapped_in_bubble": unmapped,
    }
    out_json = Path(args.json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.png:
        write_overlay(pc, detections, scopes, Path(args.png))

    print(f"wrote {out_json}" + (f" and {args.png}" if args.png else ""))
    return 0 if not metrics["mismatch_types"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
