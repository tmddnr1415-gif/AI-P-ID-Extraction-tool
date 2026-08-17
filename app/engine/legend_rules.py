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

import collections
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import projectconfig  # noqa: E402


# Headings that identify the sheets these rules are measured from.  The
# headings are the legend's own wording, printed on the sheet.
LINE_VALVE_HEADING = "LINE VALVES"
ACTUATOR_HEADING = "VALVES ACTUATORS"

# Row labels, again the legend's own.
BUTTERFLY_LABEL = "BUTTERFLY"
BALL_LABEL = "BALL"

# How far left of a row label its symbol is drawn, and how tall a row is.  These
# only bound the search for the symbol belonging to a label that has already
# been found by name; they are not measurements of anything.
SYMBOL_BAND = 220.0
ROW_HALF_HEIGHT = 14.0


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
    """The legend sheet carrying a heading, by its printed words."""
    want = heading.split()
    for pc in pages:
        if not pc.analysis_scope:
            continue
        words = [t for _, t in pc.words]
        if all(w in words for w in want):
            return pc
    return None


def _label(pc, text: str):
    for r, t in pc.words:
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


def _straight_items(d, stroke_only: bool = False):
    """Straight segments of a path, as ((x0,y0),(x1,y1)).

    `stroke_only` keeps just single-segment unfilled paths.  A filled disc is
    rasterised into dozens of four-sided scanline slivers whose sides are also
    `l` items, and without this filter those slivers swamp the two vane ticks
    they surround - the legend's BUTTERFLY row yields 36 candidate "ticks"
    instead of 2.
    """
    if stroke_only and (d.get("fill") is not None or len(d["items"]) != 1):
        return []
    out = []
    for it in d["items"]:
        if it[0] == "l":
            out.append((it[1], it[2]))
    return out


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

    # Ticks: short slanted strokes whose midpoint sits just off the rim.
    ticks = []
    for d in shapes:
        for p0, p1 in _straight_items(d, stroke_only=True):
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

    # End bars: axial runs standing off the circle on both sides.
    bars = []
    for d in shapes:
        for p0, p1 in _straight_items(d, stroke_only=True):
            dx, dy = abs(p1[0] - p0[0]), abs(p1[1] - p0[1])
            if dx < 0.3 and dy > radius:
                bars.append(abs((p0[0] + p1[0]) / 2 - cx))
            elif dy < 0.3 and dx > radius and abs((p0[1] + p1[1]) / 2 - cy) > radius:
                bars.append(abs((p0[1] + p1[1]) / 2 - cy))
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
            ball_bars = [abs((p0[0] + p1[0]) / 2 - bcx)
                         for d in ball_shapes
                         for p0, p1 in _straight_items(d, stroke_only=True)
                         if abs(p1[0] - p0[0]) < 0.3 and abs(p1[1] - p0[1]) > brad]
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


def derive_actuator_stem(pages, cfg) -> Derived:
    """Measure the actuator-to-body stem convention off legend page 3."""
    pc = _page_with(pages, ACTUATOR_HEADING)
    if pc is None:
        return _fallback(cfg, "actuator_stem",
                         f"no legend sheet prints '{ACTUATOR_HEADING}'")

    head = _label(pc, "ACTUATORS")
    column = (head.x0 - 260, head.x0 + 40) if head else (0.0, 1e9)

    # Enclosures in the symbol column: circles and closed boxes of actuator size.
    enclosures = []
    for d in pc.drawings():
        b = d["bbox"]
        if not (column[0] <= b.x0 and b.x1 <= column[1]):
            continue
        if not (8.0 <= min(b.width, b.height) <= 40.0):
            continue
        items = d["items"]
        if items and all(i[0] == "c" for i in items):
            if min(b.width, b.height) / max(b.width, b.height) >= 0.85:
                enclosures.append(b)

    verticals = []
    for d in pc.drawings():
        for p0, p1 in _straight_items(d):
            if abs(p1[0] - p0[0]) < 0.2 and abs(p1[1] - p0[1]) > 1.0:
                verticals.append((p0[0], min(p0[1], p1[1]), max(p0[1], p1[1])))

    stems = []
    for b in enclosures:
        cx = (b.x0 + b.x1) / 2
        best = None
        for x, y0, y1 in verticals:
            if abs(x - cx) > 2.0:
                continue
            gap = y0 - b.y1
            if -0.3 <= gap <= 4.0 and (y1 - y0) > 2.0:      # starts on the edge
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
    return {
        "butterfly": derive_butterfly(pages, cfg),
        "actuator_stem": derive_actuator_stem(pages, cfg),
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
