"""Constants measured off the legend sheets at run time.

Two rules stayed in the cross-validation's blinded set because their numbers had
been read off drawing pages rather than derived: VANE_TICK (what tells a
butterfly from a ball) and ACT_STEM (what joins an actuator to the body it
drives).  Saying "the legend defines these" is not the same as deriving them, so
this module does the measuring.

Each derivation returns its value *and* where the value came from.  When the
legend cannot be read the caller is told so and falls back to
`valves.legend_fallback` in the project config, with the reason logged - it
never guesses and never silently keeps a stale number.

What is derived
---------------

`butterfly` - legend page 2, the BUTTERFLY row of LINE VALVES.  The symbol is a
circle between two end bars with two short vane ticks on opposite points of its
rim; the BALL row above it is the same circle with no ticks, which is why the
ticks carry the whole distinction.  Measured from the row itself: the tick
length, how far a tick sits from the circle centre in radii, and how far the end
bars stand off, also in radii.  The BALL row is measured too, because it sets
the *closer* bar spacing the detector has to accept.

`actuator_stem` - legend page 3, the VALVES ACTUATORS column.  Every row draws
the actuator enclosure with a stem running out of it towards the valve.  What is
measured is the convention rather than a distance: whether the stem starts on the
enclosure's edge, whether it runs on the enclosure's centre line, and whether it
spans the whole gap.  Those three facts are what `_actuator_stem` tests, and they
are what separate a valve actuator from a pump motor standing the same distance
away with nothing drawn between.

No LLM, no NOTES prose.
"""

from __future__ import annotations

import bisect
import collections
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pidcache  # noqa: E402
import projectconfig  # noqa: E402


# Headings that identify the sheets these rules are measured from.  The
# headings are the legend's own wording, printed on the sheet.
LINE_VALVE_HEADING = "LINE VALVES"
ACTUATOR_HEADING = "VALVES ACTUATORS"

# Row labels, again the legend's own.
BUTTERFLY_LABEL = "BUTTERFLY"
BALL_LABEL = "BALL"
PNEUMATIC_LABEL = "PNEUMATIC"

# How far left of a row label its symbol is drawn, and how tall a row is.  These
# only bound the search for the symbol belonging to a label that has already
# been found by name; they are not measurements of anything.
SYMBOL_BAND = 220.0
ROW_HALF_HEIGHT = 14.0

# 56회차 - 실린더 상자의 크기 창을 **그 문서 범례가 그린 돔**에 맨다.
#
# `closed_boxes` 의 기본 창 (9.0, 40.0) pt 는 AL NOUF1 (A1 용지) 범례에서 잰
# 값이다.  A3 로 그린 도면은 같은 실린더 상자를 절반 크기로 그리므로 (TC2 7.08
# ↔ AL NOUF1 14.22) 그 창의 **하한 9.0 아래로 떨어져** 범례에서 실린더를 한 개도
# 못 찾고, `cylinder_side` 가 비면 `detect_valves._pneumatic_cylinders` 가 통째로
# 꺼져 도면의 파일럿/실린더 상자 액추에이터를 **한 개도** 세우지 못한다
# (실측: TC2 의 XV 10행 · FCV 3행이 `actuator=NONE` 으로 검토 탭에 남았다).
#
# 고치는 방법은 47회차 `ACT_BOX_BAND` 와 같다 - 절대 pt 를 그 문서가 같은
# 시트에 그린 돔의 배수로 바꾼다.  AL NOUF1 의 돔은 14.22 이고 9.0/14.22 ·
# 40.0/14.22 를 되곱하면 (9.0, 40.0) 이 **소수점까지 그대로** 나오므로 그 문서는
# 구조적으로 움직이지 않는다.  돔을 못 재면 기본 창을 그대로 쓴다 - 없는 기준을
# 지어내지 않는다.
ENCLOSURE_SIDES = (9.0, 40.0)
ENCLOSURE_BASIS = 14.22
ENCLOSURE_BAND = (ENCLOSURE_SIDES[0] / ENCLOSURE_BASIS,
                  ENCLOSURE_SIDES[1] / ENCLOSURE_BASIS)


@dataclass
class Derived:
    """One measured value set, with its provenance."""

    values: dict = field(default_factory=dict)
    source: str = "LEGEND"
    note: str = ""
    evidence: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.source == "LEGEND"


def _page_with(pages, heading: str):
    """The legend sheet carrying a heading, by its printed words.

    ⚠ 한 조각이 여러 낱말을 담을 수 있다 (28회차) — 획 글꼴로 그린 범례는
    `VALVES ACTUATORS` 를 주석 하나로 싣는다.  `pidcache.tokens` 가 조각 안을
    낱말로 읽는다 (자리는 조각의 것).
    """
    want = heading.split()
    for pc in pages:
        if not pc.analysis_scope:
            continue
        if _line_with(pc, want) is not None:
            return pc
    return None


def _line_with(pc, want):
    """그 머리말이 **한 줄에 나란히** 인쇄된 자리 — 없으면 None.

    낱말이 그 장 아무 데나 있으면 되는 것으로 두면 안 된다 (28회차 실측):
    UAD 는 p2 에 `FIRST ISSUE`, p3 에 `OF OTHER LETTER SYMBOLS)` 가 있어
    `FIRST LETTER` 를 **p3** 에서 찾은 것으로 치고, 정작 표가 있는 p4 를
    건너뛰었다.  머리말은 한 줄에 이어 인쇄된 낱말들이다.

    같은 줄은 **글자 높이의 절반**으로 묶는다 — 그 줄에 인쇄된 글자 자신이
    답하는 값이라 문서가 달라도 따라간다 (절대 pt 를 새로 적지 않는다).
    """
    rows = {}
    for r, t in pidcache.tokens(pc.words):
        half = max(r.height, 1.0) / 2
        key = round((r.y0 + r.y1) / 2 / half)
        rows.setdefault(key, []).append((r.x0, t, r))
    for items in rows.values():
        items.sort(key=lambda it: it[0])
        texts = [t for _x, t, _r in items]
        for i in range(len(texts) - len(want) + 1):
            if texts[i:i + len(want)] == want:
                return items[i][2]
    return None


def _label(pc, text: str):
    """그 라벨이 인쇄된 자리.  조각이 여러 낱말이면 **조각의 사각형**을 준다 —
    그 안 어디인지는 도면이 말하지 않고, 심볼은 라벨 조각의 왼쪽에 그려진다."""
    for r, t in pc.words:
        if t == text:
            return r
    for r, t in pidcache.tokens(pc.words):
        if t == text:
            return r
    return None


def _row_shapes(pc, label_rect, band=SYMBOL_BAND, half=ROW_HALF_HEIGHT):
    """Vector paths drawn on the same row as a label, to its left."""
    yc = (label_rect.y0 + label_rect.y1) / 2
    out = []
    for d in pc.drawings():
        b = d["bbox"]
        if not (label_rect.x0 - band <= b.x0 and b.x1 <= label_rect.x0 - 8):
            continue
        if yc - half <= (b.y0 + b.y1) / 2 <= yc + half:
            out.append(d)
    return out


def _circle_of(shapes):
    """The largest curve-only path with a roughly square box: the disc."""
    best = None
    for d in shapes:
        items = d["items"]
        if not items or any(i[0] != "c" for i in items):
            continue
        b = d["bbox"]
        if b.width <= 0 or b.height <= 0:
            continue
        if min(b.width, b.height) / max(b.width, b.height) < 0.85:
            continue
        if best is None or b.width > best.width:
            best = b
    return best


def _straight_items(d, stroke_only: bool = False, m=None):
    """Straight segments of a path, as ((x0,y0),(x1,y1)).

    `stroke_only` keeps just single-segment unfilled paths.  A filled disc is
    rasterised into dozens of four-sided scanline slivers whose sides are also
    `l` items, and without this filter those slivers swamp the two vane ticks
    they surround - the legend's BUTTERFLY row yields 36 candidate "ticks"
    instead of 2.

    ★ `m` 은 그 쪽의 `rotation_matrix` 다 (41회차).  `d["items"]` 의 점은 **회전
    전** 좌표이고 `d["bbox"]` 와 낱말은 표시 좌표라, 270° 로 회전된 문서
    (SADARA · TC2 · UAD)에서는 원 중심(표시 좌표)과 획(회전 전 좌표)이 서로
    다른 자리에 있었다 — 그래서 끝막대를 못 찾고 멀리 있는 표 괘선을 잡아
    `bar_reach_radii` 가 87 · 84 · 116 (AL NOUF1 2.8) 이 됐고, 그 값이
    `_find_discs_between_bars` 의 거리 조건을 사실상 꺼서 유령 원형 몸체
    TC2 534 · UAD 228 · SADARA 8 을 만들었다.  회전 0 문서는 항등 행렬이라
    한 점도 안 움직인다.
    """
    if stroke_only and (d.get("fill") is not None or len(d["items"]) != 1):
        return []
    out = []
    for it in d["items"]:
        if it[0] == "l":
            if m is not None:
                a, b = pymupdf.Point(it[1]) * m, pymupdf.Point(it[2]) * m
                out.append(((a.x, a.y), (b.x, b.y)))
            else:
                out.append((it[1], it[2]))
    return out


# --------------------------------------------------------------------------
# Shapes that are not one path
# --------------------------------------------------------------------------
#
# A box in these drawings is often not a single path.  Legend page 3 draws its
# PNEUMATIC CYLINDER as six separate one-segment paths, page 12 draws the same
# symbol with the left side split into two touching halves, and the legend's
# HYDRAULIC CYLINDER puts the box and its stem in one path, so the path's
# bounding box is 14.2 x 34.0 and not the 14.2 x 14.2 box a reader sees.  A
# path-shaped search misses all three.  These helpers work from the strokes
# instead, and the same code measures the legend and reads the drawings - which
# is the point: the rule cannot drift away from what it was measured on.

def stroke_index(segments, tol: float = 0.4, min_len: float = 0.9):
    """Axis-parallel runs bucketed to 0.1 pt: `(horizontals, verticals)`.

    `horizontals[y]` is a list of `(x0, x1)`, `verticals[x]` of `(y0, y1)`.
    """
    horiz = collections.defaultdict(list)
    vert = collections.defaultdict(list)
    for p0, p1 in segments:
        x0, y0 = (p0.x, p0.y) if hasattr(p0, "x") else (p0[0], p0[1])
        x1, y1 = (p1.x, p1.y) if hasattr(p1, "x") else (p1[0], p1[1])
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        if dy < tol and dx > min_len:
            horiz[round(y0, 1)].append((min(x0, x1), max(x0, x1)))
        elif dx < tol and dy > min_len:
            vert[round(x0, 1)].append((min(y0, y1), max(y0, y1)))
    for index in (horiz, vert):
        for runs in index.values():
            runs.sort()
    return horiz, vert


# Slack already inherent in the stroke index, which buckets coordinates to 0.1pt
# and searches +-8 buckets.  The same value `detect_valves.INDEX_SLACK` documents,
# kept here so callers of these helpers do not have to import that module for it.
INDEX_SLACK = 0.8


def covers(index, coord: float, lo: float, hi: float, cover: float = 1.2) -> bool:
    """Is `lo..hi` drawn at `coord`, allowing the side to be in pieces?

    The single-run version of this test is `detect_valves._covers`; this one
    also accepts a side drawn as several touching segments, which is how page 12
    draws the left wall of its pneumatic cylinder.
    """
    segs = []
    for step in range(-8, 9):
        segs.extend(index.get(round(coord + step * 0.1, 1), ()))
    reach = lo + cover
    for s0, s1 in sorted(segs):
        if s0 > reach:
            break                      # a gap wider than the slack
        reach = max(reach, s1 + cover)
        if reach >= hi:
            return True
    return reach >= hi


def closed_boxes(index, sides=(9.0, 40.0), square=(0.75, 1.34),
                 cover: float = 1.2):
    """Axis-parallel boxes whose four sides are drawn, each possibly in pieces.

    Yields `(x0, y0, x1, y1, dividers)` where `dividers` are the fractions of
    the box height at which a full-width straight run crosses it - the piston
    line that legend page 3 draws across a cylinder and does not draw on the
    plain letter boxes.
    """
    horiz, vert = index
    ys = sorted(horiz)
    for i, top in enumerate(ys):
        for x0, x1 in horiz[top]:
            side = x1 - x0
            if not sides[0] <= side <= sides[1]:
                continue
            lo = bisect.bisect_left(ys, top + side * square[0])
            hi = bisect.bisect_right(ys, top + side * square[1])
            for bottom in ys[lo:hi]:
                if not any(a <= x0 + cover and b >= x1 - cover
                           for a, b in horiz[bottom]):
                    continue
                if not (covers(vert, x0, top, bottom, cover)
                        and covers(vert, x1, top, bottom, cover)):
                    continue
                height = bottom - top
                dividers = [round((y - top) / height, 3)
                            for y in ys[i + 1:lo]
                            if any(a <= x0 + cover and b >= x1 - cover
                                   for a, b in horiz[y])]
                yield (x0, top, x1, bottom, dividers)
                break                  # the nearest closing bottom is the box


def derive_butterfly(pages, cfg) -> Derived:
    """Measure the vane-tick rule off the legend's BUTTERFLY row."""
    pc = _page_with(pages, LINE_VALVE_HEADING)
    if pc is None:
        return _fallback(cfg, "butterfly",
                         f"no legend sheet prints '{LINE_VALVE_HEADING}'")
    lab = _label(pc, BUTTERFLY_LABEL)
    if lab is None:
        return _fallback(cfg, "butterfly",
                         f"'{BUTTERFLY_LABEL}' not found on the {LINE_VALVE_HEADING} sheet")

    shapes = _row_shapes(pc, lab)
    circle = _circle_of(shapes)
    if circle is None:
        return _fallback(cfg, "butterfly",
                         "no disc found on the BUTTERFLY row")
    cx, cy = (circle.x0 + circle.x1) / 2, (circle.y0 + circle.y1) / 2
    radius = max(circle.width, circle.height) / 2
    m = pc.page.rotation_matrix            # 획을 표시 좌표로 (41회차)

    # Ticks: short slanted strokes whose midpoint sits just off the rim.
    # ★ 행 띠에 이웃 심볼의 사선이 섞일 수 있으므로(UAD 범례는 띠 안에 도형
    # 96개) 테두리에 **가장 가까운 둘**만 그 심볼의 틱으로 본다.
    ticks = []
    for d in shapes:
        for p0, p1 in _straight_items(d, stroke_only=True, m=m):
            dx, dy = abs(p1[0] - p0[0]), abs(p1[1] - p0[1])
            if dx < 0.3 or dy < 0.3:
                continue                       # axial: an end bar, not a tick
            length = math.hypot(dx, dy)
            if length > radius * 3:
                continue
            mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            ticks.append((length, math.hypot(mx - cx, my - cy)))
    if len(ticks) < 2:
        return _fallback(cfg, "butterfly",
                         f"BUTTERFLY row has {len(ticks)} vane ticks, expected 2")
    ticks = sorted(ticks, key=lambda t: abs(t[1] - radius))[:2]

    # End bars: axial runs standing off the circle on both sides.  ★ 심볼의
    # 끝막대는 원 **밖**에 · 원의 높이 **안**에 서고, 양쪽에서 **가장 가까운**
    # 것이다 (`_find_discs_between_bars` 의 `_nearest_bars` 와 같은 뜻).  `max`
    # 로 잡으면 같은 띠의 표 괘선이 끝막대가 된다.
    sides: dict = {"L": [], "R": [], "U": [], "D": []}
    for d in shapes:
        for p0, p1 in _straight_items(d, stroke_only=True, m=m):
            dx, dy = abs(p1[0] - p0[0]), abs(p1[1] - p0[1])
            mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            if dx < 0.3 and dy > radius:
                off = mx - cx
                if abs(off) > radius and abs(my - cy) <= radius:
                    sides["R" if off > 0 else "L"].append(abs(off))
            elif dy < 0.3 and dx > radius:
                off = my - cy
                if abs(off) > radius and abs(mx - cx) <= radius:
                    sides["D" if off > 0 else "U"].append(abs(off))
    bars = []
    for a, b in (("L", "R"), ("U", "D")):
        if sides[a] and sides[b]:
            bars = [min(sides[a]), min(sides[b])]
            break
    if len(bars) < 2:
        return _fallback(cfg, "butterfly",
                         f"BUTTERFLY row has {len(bars)} end bars, expected 2")

    # The BALL row sets the closer bar spacing the detector must still accept.
    ball_ratio = None
    ball_lab = _label(pc, BALL_LABEL)
    if ball_lab is not None:
        ball_shapes = _row_shapes(pc, ball_lab)
        ball_circle = _circle_of(ball_shapes)
        if ball_circle is not None:
            bcx = (ball_circle.x0 + ball_circle.x1) / 2
            brad = max(ball_circle.width, ball_circle.height) / 2
            bcy = (ball_circle.y0 + ball_circle.y1) / 2
            ball_bars = [abs((p0[0] + p1[0]) / 2 - bcx)
                         for d in ball_shapes
                         for p0, p1 in _straight_items(d, stroke_only=True, m=m)
                         if abs(p1[0] - p0[0]) < 0.3 and abs(p1[1] - p0[1]) > brad
                         and abs((p0[0] + p1[0]) / 2 - bcx) > brad        # 원 밖
                         and abs((p0[1] + p1[1]) / 2 - bcy) <= brad]      # 원 높이 안
            if ball_bars:
                ball_ratio = min(ball_bars) / brad

    tick_len = sorted(t[0] for t in ticks)
    tick_off = sorted(t[1] for t in ticks)
    bar_ratio = max(bars) / radius
    closest = min([bar_ratio] + ([ball_ratio] if ball_ratio else []))

    return Derived(
        values={
            "tick_length": round(sum(tick_len) / len(tick_len), 3),
            "tick_reach_radii": round(max(tick_off) / radius, 3),
            "bar_reach_radii": round(max(bar_ratio, ball_ratio or 0), 3),
            "bar_min_radii": round(closest, 3),
            "circle_diameter": round(radius * 2, 3),
        },
        evidence={
            "page_no": pc.page_no,
            "circle": [round(v, 2) for v in (circle.x0, circle.y0, circle.x1, circle.y1)],
            "tick_lengths": [round(v, 3) for v in tick_len],
            "tick_offsets": [round(v, 3) for v in tick_off],
            "bar_offsets": [round(v, 3) for v in sorted(bars)],
            "ball_bar_radii": round(ball_ratio, 3) if ball_ratio else None,
        })


# hotfix20 — 아래 액추에이터 기둥 측정의 pt 값들(원 크기 창 8~40 · 기둥 폭 260 ·
# 스템 탐색 2.0/4.0/…)은 AL NOUF1 범례에서 정한 값이다.  그 문서 범례의 **나비
# 원 지름**(`derive_butterfly` · AL NOUF1 6.06pt)을 자로 삼아 곱한다 — AL NOUF1
# 은 1.0 이라 소수점까지 그대로이고, A3 로 그린 범례(원 7.08pt)는 창 하한 8.0 에
# 걸려 AL NOUF1 의 값으로 떨어지던 것이 제 범례에서 잰다.
BUTTERFLY_CIRCLE_BASIS = 6.06


LEGEND_HEADINGS = (LINE_VALVE_HEADING, ACTUATOR_HEADING, "FIRST LETTER")


def _majority_paper(pages) -> tuple:
    """가장 많은 장이 쓰는 쪽 크기 (hotfix28 `_form_pages` 와 같은 생각 · 다수가 곧 양식)."""
    groups: dict = {}
    for pc in pages:
        k = (round(float(pc.width), 1), round(float(pc.height), 1))
        groups[k] = groups.get(k, 0) + 1
    return max(groups, key=lambda k: (groups[k], k)) if groups else (0.0, 0.0)


def legend_paper_scale(pages) -> tuple:
    """범례 장의 종이 → 양식(본 도면) 종이 배율 `(scale, why)` (hotfix48 [B]).

    범례에서 잰 길이(별표 창 · 액추에이터 원 · 나비 짧은 변 · 스템 · 돔)는 **범례
    장의 축척**으로 적힌 값이다.  범례 장이 본 도면과 같은 종이면 그대로 본문의
    길이이고(네 기준 문서 전부), 다른 종이면 그 값은 본문에서 그 배율만큼 커진다 —
    QFE 는 범례 5장을 A3(1191x842)로, 도면 88장을 A1(2384x1684)로 냈고 범례의
    M 원 7.08 · 버블 11.4 가 본문에서 14.2 · 22.6 이다 (배율 2.0 = 종이 비 2.0017).
    그 배율을 안 곱하면 별표 창(`vendor_marks.side` 10.0 x 0.495 = 4.95)이 본문
    별표(액추에이터 원에서 5.06pt)를 놓친다 — 사용자 지적의 둘째 원인이다.

    규칙은 종이 크기 둘뿐이고 새 상수가 없다: 범례 장이 양식 종이와 같으면 1.0 ·
    가로·세로 비가 서로 다르면(비례 축소가 아니면) 1.0 과 사유 · 범례 장끼리 종이가
    다르면 1.0 과 사유.  **축척으로 분기하는 것이 아니다** — 같은 문서 안에서 자가
    둘(범례 종이 · 도면 종이)인 것을 하나로 맞추는 것이다 (§9 ⑥ 의 반증은 다른
    문서의 절대 pt 를 종이로 나눈 것이었다).
    """
    if not pages:
        return 1.0, "no pages"
    form = _majority_paper(pages)
    legend = {}
    for h in LEGEND_HEADINGS:
        pc = _page_with(pages, h)
        if pc is not None:
            legend[pc.page_no] = (round(float(pc.width), 1), round(float(pc.height), 1))
    if not legend:
        return 1.0, "no legend sheet found by its headings - legend lengths used as written"
    sizes = set(legend.values())
    if len(sizes) > 1:
        return 1.0, (f"legend sheets are on different papers {sorted(sizes)} - not scaled")
    lw, lh = next(iter(sizes))
    fw, fh = form
    if abs(lw - fw) <= 1.0 and abs(lh - fh) <= 1.0:
        return 1.0, f"legend sheet is on the form paper {fw}x{fh} pt"
    if not (lw > 0 and lh > 0):
        return 1.0, "legend sheet has no size"
    sx, sy = fw / lw, fh / lh
    if abs(sx - sy) > 0.01 * max(sx, sy):
        return 1.0, (f"legend paper {lw}x{lh} is not proportional to the form paper "
                     f"{fw}x{fh} (x{sx:.3f} vs x{sy:.3f}) - not scaled")
    scale = round((sx + sy) / 2, 4)
    return scale, (f"legend sheet {lw}x{lh} pt, form sheets {fw}x{fh} pt "
                   f"({len(pages) - len(legend)} of {len(pages)}) - legend lengths x{scale}")


def legend_unit(bf) -> float:
    """그 문서 범례의 길이 단위 (AL NOUF1 = 1.0).  나비 원을 못 재면 1.0."""
    cd = float((bf.values or {}).get("circle_diameter") or 0.0) if bf is not None else 0.0
    return round(cd / BUTTERFLY_CIRCLE_BASIS, 4) if cd > 0 else 1.0


def derive_actuator_stem(pages, cfg, unit: float = 1.0) -> Derived:
    """Measure the actuator-to-body stem convention off legend page 3."""
    pc = _page_with(pages, ACTUATOR_HEADING)
    if pc is None:
        return _fallback(cfg, "actuator_stem",
                         f"no legend sheet prints '{ACTUATOR_HEADING}'")

    head = _label(pc, "ACTUATORS")
    column = (head.x0 - 260 * unit, head.x0 + 40 * unit) if head else (0.0, 1e9)

    # Enclosures in the symbol column: circles and closed boxes of actuator size.
    enclosures = []
    for d in pc.drawings():
        b = d["bbox"]
        if not (column[0] <= b.x0 and b.x1 <= column[1]):
            continue
        if not (8.0 * unit <= min(b.width, b.height) <= 40.0 * unit):
            continue
        items = d["items"]
        if items and all(i[0] == "c" for i in items):
            if min(b.width, b.height) / max(b.width, b.height) >= 0.85:
                enclosures.append(b)

    verticals = []
    m = pc.page.rotation_matrix            # 획을 표시 좌표로 (41회차)
    for d in pc.drawings():
        for p0, p1 in _straight_items(d, m=m):
            if abs(p1[0] - p0[0]) < 0.2 * unit and abs(p1[1] - p0[1]) > 1.0 * unit:
                verticals.append((p0[0], min(p0[1], p1[1]), max(p0[1], p1[1])))

    stems = []
    for b in enclosures:
        cx = (b.x0 + b.x1) / 2
        best = None
        for x, y0, y1 in verticals:
            if abs(x - cx) > 2.0 * unit:
                continue
            gap = y0 - b.y1
            if -0.3 * unit <= gap <= 4.0 * unit and (y1 - y0) > 2.0 * unit:      # starts on the edge
                if best is None or (y1 - y0) > best[0]:
                    best = (y1 - y0, abs(x - cx), gap)
        if best is not None:
            stems.append(best)

    if len(stems) < 2:
        return _fallback(cfg, "actuator_stem",
                         f"only {len(stems)} enclosure(s) on the "
                         f"{ACTUATOR_HEADING} sheet have a stem that can be measured")

    lengths = sorted(s[0] for s in stems)
    offsets = sorted(s[1] for s in stems)
    gaps = sorted(s[2] for s in stems)
    return Derived(
        values={
            # The stem leaves the enclosure edge: no gap is drawn between them.
            "stem_gap": round(max(gaps), 3),
            # It runs on the enclosure's centre line.
            "stem_offaxis": round(max(offsets), 3),
            # Longest stem the legend itself draws, enclosure edge to valve.
            "stem_length": round(max(lengths), 3),
            # Centre-to-body distance the legend uses for its own layout.
            "centre_to_body": round(max(lengths) + max(
                min(b.width, b.height) for b in enclosures) / 2, 3),
        },
        evidence={
            "page_no": pc.page_no,
            "enclosures": len(enclosures),
            "stems": len(stems),
            "stem_lengths": [round(v, 2) for v in lengths],
            "stem_offsets": [round(v, 2) for v in offsets],
            "stem_gaps": [round(v, 2) for v in gaps],
        })


def _row_label_lines(pc, column: tuple, band: tuple):
    """Label lines in the legend's text column, as `(rect, text)` per line."""
    lines = collections.defaultdict(list)
    for r, t in pc.words:
        if column[0] <= r.x0 <= column[1] and band[0] <= r.y0 <= band[1]:
            lines[round((r.y0 + r.y1) / 2)].append((r.x0, r, t))
    out = []
    for yc in sorted(lines):
        items = sorted(lines[yc])
        text = " ".join(t for _, _, t in items)
        out.append((items[0][1], text))
    return out


def derive_pneumatic(pages, cfg) -> Derived:
    """Measure the pneumatic actuator shapes off legend page 3.

    The rows are found by their own printed words: everything the VALVES
    ACTUATORS sheet labels PNEUMATIC.  On this document that is PNEUMATIC
    DIAPHRAGM, PNEUMATIC DIAPHRAGM WITH POSITIONER and PNEUMATIC CYLINDER
    SINGLE- / DOUBLE-ACTING, and they draw two shapes:

      * a **dome** - a half circle standing on the stem with its flat side
        drawn as a chord.  It is the chord that separates it from a tag
        bubble's rounded end, which has the same 0.50 aspect and no chord.
      * a **cylinder** - a closed square box with a straight run across the
        middle.  The divider is what separates it from the plain letter boxes
        on the same sheet (H, S, X), which are closed and undivided.

    Neither shape holds a letter, which is why they were never candidates: the
    enclosure search was looking for something to read.  On this document there
    is nothing to read - `I/P` appears only inside equipment names - so the
    shape is the whole evidence.
    """
    pc = _page_with(pages, ACTUATOR_HEADING)
    if pc is None:
        return _fallback(cfg, "pneumatic",
                         f"no legend sheet prints '{ACTUATOR_HEADING}'")

    head = _label(pc, "ACTUATORS")
    if head is None:
        return _fallback(cfg, "pneumatic",
                         f"'{ACTUATOR_HEADING}' sheet has no ACTUATORS label")
    # The labels sit to the right of their symbols on this sheet; the symbol
    # column is the band `_row_shapes` already searches, left of the label.
    labels = [(r, t) for r, t in _row_label_lines(
        pc, (head.x0 - 40, head.x0 + 700), (head.y1, pc.height))
        if PNEUMATIC_LABEL in t]
    if not labels:
        return _fallback(cfg, "pneumatic",
                         f"no row on the {ACTUATOR_HEADING} sheet is labelled "
                         f"{PNEUMATIC_LABEL}")

    index = stroke_index(pc.segments())
    horiz, _vert = index
    rows = [(lab, _row_shapes(pc, lab)) for lab, _t in labels]

    domes = []
    for lab, shapes in rows:
        for d in shapes:
            b = d["bbox"]
            items = d["items"]
            if not items or any(i[0] != "c" for i in items):
                continue
            if b.width <= 0 or b.height <= 0:
                continue
            if b.width <= b.height:      # the legend draws it flat side down
                continue
            if covers(horiz, b.y1, b.x0, b.x1) or covers(horiz, b.y0, b.x0, b.x1):
                domes.append((round(b.width, 2), round(b.height, 2),
                              [round(v, 1) for v in b]))

    # 56회차 - 상자 창은 이 시트가 그린 돔의 배수다 (ENCLOSURE_BAND 주석 참조).
    sides, basis = ENCLOSURE_SIDES, None
    if domes:
        basis = round(sum(w for w, _h, _r in domes) / len(domes), 3)
        sides = (basis * ENCLOSURE_BAND[0], basis * ENCLOSURE_BAND[1])

    cylinders = []
    for lab, _shapes in rows:
        # The cylinder's box is not a path, so it is assembled from strokes
        # inside the row band.
        yc = (lab.y0 + lab.y1) / 2
        for x0, y0, x1, y1, dividers in closed_boxes(index, sides=sides):
            if not (lab.x0 - SYMBOL_BAND <= x0 and x1 <= lab.x0 - 8):
                continue
            if not (yc - ROW_HALF_HEIGHT <= (y0 + y1) / 2 <= yc + ROW_HALF_HEIGHT):
                continue
            if not dividers:
                continue                 # a plain letter box, not a cylinder
            cylinders.append((round(x1 - x0, 2), round(y1 - y0, 2),
                              sorted(dividers)))

    if not domes and not cylinders:
        return _fallback(cfg, "pneumatic",
                         f"the {len(labels)} {PNEUMATIC_LABEL} row(s) on the "
                         f"{ACTUATOR_HEADING} sheet drew neither a domed "
                         f"diaphragm nor a divided cylinder box")

    values = {}
    if domes:
        flats = sorted(w for w, _h, _r in domes)
        depths = sorted(h for _w, h, _r in domes)
        values["dome_flat"] = round(sum(flats) / len(flats), 3)
        values["dome_depth"] = round(sum(depths) / len(depths), 3)
        values["dome_aspect"] = round(values["dome_depth"] / values["dome_flat"], 3)
    if cylinders:
        sides = sorted(w for w, _h, _d in cylinders)
        heights = sorted(h for _w, h, _d in cylinders)
        div = sorted(f for _w, _h, ds in cylinders for f in ds)
        values["cylinder_side"] = round(sum(sides) / len(sides), 3)
        values["cylinder_aspect"] = round(
            (sum(heights) / len(heights)) / (sum(sides) / len(sides)), 3)
        values["cylinder_divider"] = round(sum(div) / len(div), 3) if div else None
    return Derived(
        values=values,
        evidence={
            "page_no": pc.page_no,
            "rows": [t for _r, t in labels],
            "domes": domes,
            "cylinders": cylinders,
            "enclosure_sides": [round(v, 3) for v in sides],
            "enclosure_basis": basis,
        })


def _fallback(cfg, key: str, why: str) -> Derived:
    """Config fallback, always with the reason recorded."""
    values = cfg.lookup("valves.legend_fallback", key)
    if values is projectconfig.UNDEFINED:
        return Derived(values={}, source="NEEDS_REVIEW",
                       note=f"{why}; and no `valves.legend_fallback.{key}` in "
                            f"the project config either, so nothing is assumed")
    return Derived(values=dict(values), source="CONFIG_FALLBACK",
                   note=f"{why}; using valves.legend_fallback.{key}")


def derive_all(pages, cfg=None) -> dict:
    cfg = cfg or projectconfig.load()
    bf = derive_butterfly(pages, cfg)
    return {
        "butterfly": bf,
        "actuator_stem": derive_actuator_stem(pages, cfg, legend_unit(bf)),
        "pneumatic": derive_pneumatic(pages, cfg),
    }


def describe(derived: dict) -> list:
    """Human-readable lines for the report and the console."""
    out = []
    for key, d in derived.items():
        out.append(f"{key}: {d.source}"
                   + (f" - {d.note}" if d.note else ""))
        for k, v in sorted(d.values.items()):
            out.append(f"    {k} = {v}")
        for k, v in sorted(d.evidence.items()):
            out.append(f"    [{k}] {v}")
    return out


def main() -> int:
    import pidcache
    doc, pages = pidcache.load_pages(Path("data/pid_total.pdf"))
    for line in describe(derive_all(pages)):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
