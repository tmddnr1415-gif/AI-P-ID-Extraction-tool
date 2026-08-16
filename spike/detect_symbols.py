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

`NOT_FIELD_INSTRUMENT`  TW (thermowell), FE and FT never appear in the field
                instrument list.

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
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import pymupdf
except ImportError:  # pragma: no cover
    sys.exit("PyMuPDF is required:  pip install pymupdf")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pidcache import load_pages  # noqa: E402


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------
# Drawing anchor -> Excel TYPE.  The drawing uses transmitter letters (TT/PT)
# while the Excel uses indicating-transmitter letters (TIT/PIT).
FIELD_TYPE_MAP = {
    "TT": "TIT", "PT": "PIT", "LT": "LIT", "PDT": "PDIT",
    "TI": "TI", "PI": "PI", "LI": "LI", "FI": "FI",
    "TIT": "TIT", "PIT": "PIT", "LIT": "LIT", "PDIT": "PDIT", "FIT": "FIT",
    "LS": "LS", "FS": "FS", "RO": "RO",
}

# Recognised but never a field instrument row.
NOT_FIELD_INSTRUMENT = {"TW", "FE", "FT"}

# Valve anchors -> the valve deliverables, not this list.
VALVE_ANCHORS = {"MOV", "HOV", "HV", "XV", "CV", "FCV", "TCV", "PCV", "LCV",
                 "NRV", "PSV", "PRV", "BPRV"}

ANCHORS = set(FIELD_TYPE_MAP) | NOT_FIELD_INSTRUMENT | VALVE_ANCHORS


@dataclass(frozen=True)
class Layout:
    # The drawing area; everything to the right is title block and notes.
    drawing_area: tuple = (38.0, 35.0, 1960.0, 1650.0)
    notes_area: tuple = (1960.0, 35.0, 2384.0, 1250.0)

    # Instrument bubble: a stadium of 68.0 x 22.6 pt built from two arc caps.
    cap_long: tuple = (20.0, 26.0)      # cap size along the stadium axis
    cap_short: tuple = (9.0, 14.0)
    cap_separation: tuple = (54.0, 59.0)  # between cap centres
    anchor_slack: float = 3.0

    # Vendor asterisk marks sit just above the bubble.
    mark_size: tuple = (3.5, 4.5)
    mark_above: float = 25.0
    mark_x_slack: float = 6.0
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


LAYOUT = Layout()


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def _inside(x, y, region) -> bool:
    x0, y0, x1, y1 = region
    return x0 <= x <= x1 and y0 <= y <= y1


def find_bubbles(pc, lay: Layout = LAYOUT) -> list[pymupdf.Rect]:
    """Instrument bubbles, from pairs of matching arc caps.

    Adjacent bubbles are only 25.5 pt apart, so caps must be *paired* by
    alignment and separation — taking the union of all nearby caps merges
    neighbouring bubbles into one blob.
    """
    caps_h, caps_v = [], []
    for d in pc.drawings():
        items = d["items"]
        if not items or any(i[0] != "c" for i in items):
            continue
        r = d["bbox"]
        lo_l, hi_l = lay.cap_long
        lo_s, hi_s = lay.cap_short
        if lo_l < r.width < hi_l and lo_s < r.height < hi_s:
            caps_h.append(r)      # top/bottom cap of a vertical stadium
        elif lo_s < r.width < hi_s and lo_l < r.height < hi_l:
            caps_v.append(r)      # left/right cap of a horizontal stadium

    lo_sep, hi_sep = lay.cap_separation
    bubbles = []
    for caps, vertical in ((caps_h, True), (caps_v, False)):
        for a, b in itertools.combinations(caps, 2):
            if vertical:
                if abs(a.x0 - b.x0) > 1 or abs(a.x1 - b.x1) > 1:
                    continue
                sep = abs((a.y0 + a.y1) / 2 - (b.y0 + b.y1) / 2)
            else:
                if abs(a.y0 - b.y0) > 1 or abs(a.y1 - b.y1) > 1:
                    continue
                sep = abs((a.x0 + a.x1) / 2 - (b.x0 + b.x1) / 2)
            if not lo_sep < sep < hi_sep:
                continue
            bubbles.append(pymupdf.Rect(min(a.x0, b.x0), min(a.y0, b.y0),
                                        max(a.x1, b.x1), max(a.y1, b.y1)))
    return bubbles


def find_marks(pc, lay: Layout = LAYOUT) -> list[pymupdf.Point]:
    """Centres of the small asterisk vendor marks (drawn as vector, not text)."""
    lo, hi = lay.mark_size
    seen = set()
    out = []
    for r in pc.rects():
        if lo < r.width < hi and lo < r.height < hi:
            key = (round(r.x0, 1), round(r.y0, 1))
            if key in seen:
                continue
            seen.add(key)
            out.append(pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
    return out


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
# Page-scoped mark dictionary (docs/design.md §10.1)
# --------------------------------------------------------------------------
def read_mark_dictionary(pc, lay: Layout = LAYOUT) -> dict[int, str]:
    """Map asterisk count -> meaning, read from this page's NOTES block.

    The marks in the notes column are the same vector glyphs used on the
    drawing, so counting them on a note line gives the legend directly.
    """
    notes_marks = [p for p in find_marks(pc, lay) if _inside(p.x, p.y, lay.notes_area)]
    rows: dict[float, list] = collections.defaultdict(list)
    for p in notes_marks:
        key = next((k for k in rows if abs(k - p.y) <= lay.note_mark_row_tol), p.y)
        rows[key].append(p)

    dictionary = {}
    for y, marks in rows.items():
        right_of = max(m.x for m in marks)
        words = [
            (r, t) for r, t in pc.words
            if r.x0 > right_of and abs((r.y0 + r.y1) / 2 - y) <= lay.note_mark_row_tol + 4
        ]
        words.sort(key=lambda rt: rt[0].x0)
        text = " ".join(t for _, t in words).strip()
        if text:
            dictionary[len(marks)] = text
    return dictionary


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
        box = None
        for vx, vy0, vy1, _ in v_runs:
            if abs(vx - sx) > lay.scope_text_tol or not (vy0 - 5 <= sy <= vy1 + 5):
                continue
            tops = [h for h in h_runs if abs(h[0] - vy0) < 3 and h[1] <= vx + 3 <= h[2]]
            bots = [h for h in h_runs if abs(h[0] - vy1) < 3 and h[1] <= vx + 3 <= h[2]]
            if tops and bots:
                x1 = max(max(h[2] for h in tops), max(h[2] for h in bots))
                box = pymupdf.Rect(vx, vy0, x1, vy1)
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
    return scopes


def lands_on_run(pc, bubble: pymupdf.Rect, run: tuple, lay: Layout = LAYOUT) -> bool:
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
    for a, b in pc.segments():
        if abs(a.x - b.x) >= 0.4 or abs(a.x - cx) > lay.drop_x_tol:
            continue
        if abs(max(a.y, b.y) - ry) <= lay.drop_end_tol and min(a.y, b.y) >= bubble.y1 - 2:
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


def detect(pc, lay: Layout = LAYOUT, disabled: frozenset = frozenset()):
    bubbles = find_bubbles(pc, lay)
    marks = find_marks(pc, lay)
    mark_dict = read_mark_dictionary(pc, lay)
    scopes = find_sct_scopes(pc, lay)

    detections: list[Detection] = []
    unverified: list[dict] = []

    for r, t in pc.words:
        if t not in ANCHORS:
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
        if t in VALVE_ANCHORS:
            det.category = "VALVE"
            det.included = False
            det.exclude_rule = "VALVE"
            det.rules_hit.append("VALVE")
            det.evidence["note"] = "valve deliverable, not the field instrument list"
        elif t in NOT_FIELD_INSTRUMENT:
            det.category = "OTHER"
            det.included = False
            det.exclude_rule = "NOT_FIELD_INSTRUMENT"
            det.rules_hit.append("NOT_FIELD_INSTRUMENT")
            det.evidence["note"] = f"{t} never appears in the field instrument list"
        else:
            det.category = "FIELD_INSTRUMENT"
            det.excel_type = FIELD_TYPE_MAP[t]

        # -- vendor mark (page-scoped meaning) -------------------------
        near = [
            m for m in marks
            if bubble.x0 - lay.mark_x_slack <= m.x <= bubble.x1 + lay.mark_x_slack
            and bubble.y0 - lay.mark_above <= m.y <= bubble.y0
        ]
        if near:
            det.evidence["vendor_mark"] = {
                "count": len(near),
                "meaning": mark_dict.get(len(near), "UNDEFINED ON THIS PAGE"),
            }
            det.rules_hit.append("VENDOR_MARK")
            if det.included and "VENDOR_MARK" not in disabled:
                det.included = False
                det.exclude_rule = "VENDOR_MARK"

        # -- SCT supplier scope ----------------------------------------
        for sc in scopes:
            inside = False
            if sc.kind == "BOX" and sc.rect is not None:
                inside = sc.rect.x0 <= cx <= sc.rect.x1 and sc.rect.y0 <= cy <= sc.rect.y1
            elif sc.kind == "PIPE_BREAK" and sc.run is not None:
                inside = lands_on_run(pc, bubble, sc.run, lay)
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

    detections.sort(key=lambda d: (round(d.center[1] / 15), d.center[0]))
    return detections, scopes, mark_dict, unverified


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
    "VENDOR_MARK": (0.85, 0.35, 0.0),
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
              ("excluded: vendor mark", COLORS["VENDOR_MARK"]),
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
    for rule in ("SCT_SUPPLIER_SCOPE", "VENDOR_MARK", "NOT_FIELD_INSTRUMENT", "VALVE"):
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
                why = f"{'*' * vm['count']} = {vm['meaning']}"
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

    disabled = frozenset(r.strip() for r in args.without.split(",") if r.strip())
    if disabled:
        print(f"\n!! exclusion rules disabled for this run: {', '.join(sorted(disabled))}")
    detections, scopes, mark_dict, unverified = detect(pc, disabled=disabled)
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
