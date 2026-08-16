"""Spike 4 - valve detection (docs/design.md appendix A, valve deliverable).

The field-instrument spikes could lean on text: every instrument carries a
bubble with a function-letter tag in it, so an anchor existed for almost every
row.  Valves are the opposite case.  Most of them are drawn and never labelled,
so this spike has to answer a different question first:

    how far do text anchors actually reach, and where does geometry have to
    take over?

`--reach` answers exactly that and nothing else.  The rest of the module is the
geometry that has to cover the remainder.

Everything the classifier keys on is read off the legend sheets, and every rule
below cites the sheet it came from:

  page 2 `LINE VALVES`   - body shapes.  Measured from the legend rows rather
                           than described in prose:

      GATE       bowtie  (two crossing diagonals in a 17.0 x 9.9 box, end bars
                          at both ends) and nothing at the waist
      GLOBE      the same bowtie *plus a filled disc at the waist*, 7.1 across
                 - 0.72 of the body's short side, aspect 1.0
      NEEDLE     the same bowtie plus a filled wedge at the waist, 2.3 x 7.1
                 - aspect 0.32, so the disc test separates the two on shape,
                 not on size
      DIAPHRAGM  bowtie plus an unfilled arc sitting above the body
      BUTTERFLY  *no diagonals*: a circle between the end bars carrying two
                 short vane ticks at opposite points of its rim
      BALL       no diagonals, a circle between the end bars and no ticks
      CHECK      half a bowtie - one diagonal, not two
      ANGLE      a single closed triangle with the stem on the perpendicular

    Gate and globe are the pair the user flagged as look-alike, and they are:
    the outline is identical.  The whole distinction is the disc at the waist,
    which is why this module tests for a centred round path there - page 6
    draws 46 of them and 12 bare bowties.

  page 2 `VALVE OPERATION` - and this is the trap in the block above.  Solid
    black does *not* mean a body type:

      open bowtie         OPEN DURING NORMAL OPERATION (all valves except butterfly)
      solid black bowtie  CLOSED DURING NORMAL OPERATION (all valves except butterfly)
      open circle         OPEN DURING NORMAL OPERATION (BUTTERFLY ONLY)
      solid black circle  CLOSED DURING NORMAL OPERATION (BUTTERFLY ONLY)

    So fill is *state*, and a butterfly drawn open is an open circle - exactly
    what a ball valve looks like.  Reading fill as body type would have called
    every open butterfly a ball; page 26's hydraulic CW pump discharge valves
    are drawn as open circles and are butterflies.  Fill is therefore recorded
    as `state`, and body type comes from the vane ticks alone.  The globe disc
    survives this because it is a *centred round path at the waist of a
    bowtie*, while `CLOSED` fills the two triangles off-centre.

  page 3 `VALVES ACTUATORS` - actuator judgement:

      circle with M      ROTARY MOTOR (shown typically with electric signal)
      box with H         HYDRAULIC CYLINDER SINGLE-ACTING
      circle with E/H    ELECTRO OR HYDRAULIC
      box with S         SINGLE SOLENOID
      dome / cylinder    PNEUMATIC DIAPHRAGM / PNEUMATIC CYLINDER
      I/P               PNEUMATIC DIAPHRAGM WITH POSITIONER
      plain T bar        HAND ACTUATOR
      box with X         UNCLASSIFIED

    A body with none of these has no actuator drawn on it.  That is reported as
    `NONE`, not as a guess about what operates it: page 3 keeps SELF-ACTUATED
    DEVICES (PSV / PRV / BPRV) as their own group with their own symbols, so
    "nothing on the stem" and "self-acting" are different findings and this
    module does not merge them.

  page 4 `VALVE BODY WITH ACTUATOR` - MOV / HOV tags sit in an ordinary
    instrument bubble with a leader down to the body, which is why the tag
    search reuses `detect_symbols.find_bubbles`.

No LLM, no NOTES prose.

Comparison data
---------------
The master valve list named in the request (`data/Valve_List_2512xx.xlsx`,
194 rows with BODY and ACTUATOR columns) is not in the repository.  What exists
is two *filtered* deliverables cut from it:

    data/CZI_Butterfly_Valve.xlsx   I&C Butterfly Valve   21 rows
    data/CZH_MOV_Gate_Globe.xlsx    MOV (GATE & GLOBE)    63 rows

Their `NO` column still carries the master's numbering (CZH 1..174, CZI
89..178), so they really are row subsets of the same list - but neither has a
BODY or an ACTUATOR column.  Body type is only recoverable at *file* level from
the deliverable's own DESCRIPTION line, and gate-vs-globe is not recoverable at
all: CZH mixes both under one heading.  `--compare` therefore measures what
these two files can support and states what it cannot; see out/valve_report.md.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pidcache          # noqa: E402
import projectconfig     # noqa: E402
import detect_symbols as ds   # noqa: E402

CFG = projectconfig.load()

PDF = Path("data/pid_total.pdf")
OUT = Path("out")

# Valve deliverables, keyed by the body family their DESCRIPTION line declares.
DELIVERABLES = [
    ("CZI", Path("data/CZI_Butterfly_Valve.xlsx"), ("BUTTERFLY",)),
    ("CZH", Path("data/CZH_MOV_Gate_Globe.xlsx"), ("GATE", "GLOBE")),
]


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ValveLayout:
    """Geometry tolerances.

    These describe legend page 2's own drawing, not this project: the bowtie
    there is 17.0 x 9.9 with a 7.1 disc, and the bounds below are wide windows
    around those proportions so a page that draws valves at another scale still
    passes.  Nothing here is a size taken from one drawing page.
    """

    drawing_area: tuple = (38.0, 35.0, 1960.0, 1650.0)

    seg_span: tuple = (1.0, 60.0)       # segment lengths worth looking at
    body_short: tuple = (5.0, 30.0)     # short side of a valve body
    body_ratio: tuple = (1.4, 2.8)      # long / short of a bowtie body
    bar_axis_tol: float = 0.8           # how close an end bar is to the end
    bar_cover: float = 1.2              # how far a bar may fall short

    centre_tol: float = 2.0             # waist object off-centre allowance
    waist_ratio: tuple = (0.35, 1.05)   # waist object vs body short side
    disc_aspect: tuple = (0.70, 1.45)   # a disc is round, a needle wedge is not
    arc_above: float = 6.0              # diaphragm arc clearance above the body

    # Butterfly vane ticks: two short strokes on opposite points of the rim.
    tick_span: tuple = (1.5, 6.0)
    tick_reach: float = 1.3             # multiples of the circle radius
    # Legend page 2 draws the butterfly's 6.1 circle between bars 17.0 apart
    # (2.79 radii) and the ball's 7.2 circle between bars 17.0 apart (2.36).
    bar_reach: float = 3.4              # how far an end bar may sit, in radii
    bar_min: float = 1.1                # ...and how close, also in radii: the
                                        # end bar is drawn clear of the circle,
                                        # never through it

    # Actuator sits on the stem, on the axis perpendicular to flow.
    act_reach: float = 90.0
    act_offaxis: float = 12.0
    # Legend page 3 draws its actuator enclosures at 14.2 pt across (the motor
    # and E/H circles) and page 26 strokes its hydraulic box at 11.3.  The
    # lower bound sits below both and above the 7.1 pt globe waist disc, which
    # would otherwise read as an unlabelled circle standing on the stem.
    act_box: tuple = (9.0, 34.0)        # side of an actuator circle / box

    # Tag bubble attached by a leader.
    tag_reach: float = 190.0


def _layout(cfg=CFG) -> ValveLayout:
    """Only the sheet split is project-dependent; the rest is legend geometry."""
    return ValveLayout(drawing_area=cfg.rect("regions.drawing_area"))


LAYOUT = _layout()

# Valve tags that can appear in a bubble.  LEGEND: page 3 lists FCV / LCV / PCV
# / TCV in the CONTROL DEVICE column and PSV / PRV / BPRV under SELF-ACTUATED
# DEVICES; page 4 draws MOV / HOV / HV / XV under VALVE BODY WITH ACTUATOR.
TAG_ANCHORS = frozenset(ds.VALVE_ANCHORS)

# Actuator letters, legend page 3.  'E/H' and 'I/P' arrive from the text layer
# already joined; the single letters are matched only inside an enclosing shape.
ACT_LETTERS = {
    "M": "MOTOR",
    "H": "HYDRAULIC",
    "E/H": "HYDRAULIC",
    "S": "SOLENOID",
    "X": "UNCLASSIFIED",
    "I/P": "PNEUMATIC",
    "IP": "PNEUMATIC",
}


# --------------------------------------------------------------------------
# Body detection
# --------------------------------------------------------------------------

@dataclass
class Body:
    kind: str                       # GATE | GLOBE | BUTTERFLY | ...
    rect: pymupdf.Rect
    axis: str                       # H (flow horizontal) | V
    state: str = "OPEN"             # legend p2 VALVE OPERATION; fill = CLOSED
    actuator: str = "NONE"
    actuator_evidence: str = ""
    tag: str = ""                   # MOV / HOV / ... when a bubble is attached
    tag_rect: tuple = ()
    evidence: dict = field(default_factory=dict)

    def as_json(self) -> dict:
        r = self.rect
        return {
            "kind": self.kind,
            "rect": [round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1)],
            "axis": self.axis,
            "state": self.state,
            "actuator": self.actuator,
            "actuator_evidence": self.actuator_evidence,
            "tag": self.tag,
            "tag_rect": [round(v, 1) for v in self.tag_rect] if self.tag_rect else [],
            "evidence": self.evidence,
        }


def _in_area(r, area) -> bool:
    return area[0] <= r.x0 and r.x1 <= area[2] and area[1] <= r.y0 and r.y1 <= area[3]


def _index_segments(pc, lay: ValveLayout):
    """Short segments, split into horizontal / vertical / diagonal."""
    horiz: dict[float, list] = collections.defaultdict(list)
    vert: dict[float, list] = collections.defaultdict(list)
    diag: list = []
    a0, b0, a1, b1 = lay.drawing_area
    lo, hi = lay.seg_span
    for p0, p1 in pc.segments():
        if not (a0 <= min(p0.x, p1.x) and max(p0.x, p1.x) <= a1
                and b0 <= min(p0.y, p1.y) and max(p0.y, p1.y) <= b1):
            continue
        dx, dy = abs(p1.x - p0.x), abs(p1.y - p0.y)
        length = (dx * dx + dy * dy) ** 0.5
        if not lo <= length <= hi:
            continue
        if dy < 0.4 and dx > 1.0:
            horiz[round(p0.y, 1)].append((min(p0.x, p1.x), max(p0.x, p1.x)))
        elif dx < 0.4 and dy > 1.0:
            vert[round(p0.x, 1)].append((min(p0.y, p1.y), max(p0.y, p1.y)))
        elif dx > 1.0 and dy > 1.0:
            diag.append((p0, p1))
    return horiz, vert, diag


def _covers(index, coord, lo, hi, lay: ValveLayout) -> bool:
    """Is there a straight run at `coord` spanning lo..hi (within slack)?"""
    for step in range(-8, 9):
        for s0, s1 in index.get(round(coord + step * 0.1, 1), ()):
            if s0 <= lo + lay.bar_cover and s1 >= hi - lay.bar_cover:
                return True
    return False


def _end_bars(horiz, vert, box, axis, lay: ValveLayout) -> int:
    """Bit mask of which of the two end bars of a body are drawn.

    LEGEND page 2: every line-valve symbol is closed off by a bar at each end,
    perpendicular to the pipe.  This is what keeps a random pair of crossing
    lines from reading as a valve.
    """
    x0, y0, x1, y1 = box
    mask = 0
    if axis == "H":
        if _covers(vert, x0, y0, y1, lay):
            mask |= 1
        if _covers(vert, x1, y0, y1, lay):
            mask |= 2
    else:
        if _covers(horiz, y0, x0, x1, lay):
            mask |= 1
        if _covers(horiz, y1, x0, x1, lay):
            mask |= 2
    return mask


def _filled_paths(pc, lay: ValveLayout):
    out = []
    for d in pc.drawings():
        if d.get("fill") is None:
            continue
        b = d["bbox"]
        if _in_area(b, lay.drawing_area):
            out.append(b)
    return out


def _round_paths(pc, lay: ValveLayout):
    """Curve-only paths: circles, discs and arcs."""
    out = []
    for d in pc.drawings():
        items = d["items"]
        if not items or any(i[0] != "c" for i in items):
            continue
        b = d["bbox"]
        if b.width <= 0 or b.height <= 0:
            continue
        if _in_area(b, lay.drawing_area):
            out.append(b)
    return out


def _waist_object(box, axis, rounds, fills, lay: ValveLayout):
    """What sits at the waist of a body, and whether it is filled.

    Returns (rect, filled) or (None, False).  This is the gate/globe test.
    """
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    short = min(box[2] - box[0], box[3] - box[1])
    best = None
    for b in rounds:
        if abs((b.x0 + b.x1) / 2 - cx) > lay.centre_tol:
            continue
        if abs((b.y0 + b.y1) / 2 - cy) > lay.centre_tol:
            continue
        span = max(b.width, b.height)
        if not lay.waist_ratio[0] * short <= span <= lay.waist_ratio[1] * short:
            continue
        if best is None or span > max(best.width, best.height):
            best = b
    if best is None:
        return None, False
    filled = any(abs((f.x0 + f.x1) / 2 - cx) <= lay.centre_tol
                 and abs((f.y0 + f.y1) / 2 - cy) <= lay.centre_tol
                 and f.width <= best.width + 0.6 and f.height <= best.height + 0.6
                 for f in fills)
    return best, filled


def _wedge_at_waist(box, fills, lay: ValveLayout):
    """A filled non-round shape at the waist - legend page 2's NEEDLE plug."""
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    short = min(box[2] - box[0], box[3] - box[1])
    for f in fills:
        if abs((f.x0 + f.x1) / 2 - cx) > lay.centre_tol:
            continue
        if abs((f.y0 + f.y1) / 2 - cy) > lay.centre_tol:
            continue
        w, h = f.width, f.height
        if w < 0.5 or h < 0.5:
            continue
        span = max(w, h)
        if not lay.waist_ratio[0] * short <= span <= lay.waist_ratio[1] * short:
            continue
        aspect = min(w, h) / max(w, h)
        if aspect < lay.disc_aspect[0]:
            return f
    return None


def _arc_above(box, axis, rounds, lay: ValveLayout):
    """Legend page 2 DIAPHRAGM: an open arc riding on top of the bowtie."""
    cx = (box[0] + box[2]) / 2
    for b in rounds:
        if abs((b.x0 + b.x1) / 2 - cx) > lay.centre_tol + 1.0:
            continue
        if b.height > b.width:          # an arc here is a shallow cap
            continue
        if box[1] - lay.arc_above <= b.y1 <= box[1] + 1.0:
            return b
    return None


def find_bodies(pc, lay: ValveLayout = LAYOUT) -> list[Body]:
    """Every line-valve body on the page, classified per legend page 2."""
    horiz, vert, diag = _index_segments(pc, lay)
    rounds = _round_paths(pc, lay)
    fills = _filled_paths(pc, lay)

    # Diagonals sharing a bounding box are the two halves of a bowtie.
    grouped: dict[tuple, list] = collections.defaultdict(list)
    for p0, p1 in diag:
        key = (round(min(p0.x, p1.x), 1), round(min(p0.y, p1.y), 1),
               round(max(p0.x, p1.x), 1), round(max(p0.y, p1.y), 1))
        grouped[key].append((p0, p1))

    bodies: list[Body] = []
    claimed: set[tuple] = set()
    # Round paths already spoken for as part of a bowtie (the globe's waist
    # disc, the diaphragm's arc).  Without this they would be picked up again
    # as a circle standing between the bowtie's own end bars, and every globe
    # would also be reported as a ball.
    spent: set[int] = set()

    for box, lines in grouped.items():
        w, h = box[2] - box[0], box[3] - box[1]
        short, long_ = min(w, h), max(w, h)
        if not lay.body_short[0] <= short <= lay.body_short[1]:
            continue
        if not lay.body_ratio[0] <= long_ / short <= lay.body_ratio[1]:
            continue
        axis = "H" if w > h else "V"
        slopes = {1 if (p1.x - p0.x) * (p1.y - p0.y) > 0 else -1 for p0, p1 in lines}
        mask = _end_bars(horiz, vert, box, axis, lay)
        if mask != 3:
            continue

        state = "CLOSED" if _triangles_filled(box, fills) else "OPEN"

        if len(slopes) < 2:
            # Half a bowtie with both bars: legend page 2 CHECK.
            bodies.append(Body("CHECK", pymupdf.Rect(*box), axis, state=state,
                               evidence={"diagonals": 1, "bars": mask}))
            claimed.add(box)
            continue

        disc, filled = _waist_object(box, axis, rounds, fills, lay)
        wedge = _wedge_at_waist(box, fills, lay)
        arc = _arc_above(box, axis, rounds, lay)
        for used in (disc, arc):
            if used is not None:
                spent.add(id(used))

        if disc is not None and filled:
            aspect = min(disc.width, disc.height) / max(disc.width, disc.height)
            if lay.disc_aspect[0] <= aspect <= lay.disc_aspect[1]:
                kind, ev = "GLOBE", {"waist": "filled_disc",
                                     "disc": round(max(disc.width, disc.height), 1),
                                     "aspect": round(aspect, 2)}
            else:
                kind, ev = "NEEDLE", {"waist": "filled_wedge",
                                      "aspect": round(aspect, 2)}
        elif wedge is not None:
            kind, ev = "NEEDLE", {"waist": "filled_wedge"}
        elif arc is not None:
            kind, ev = "DIAPHRAGM", {"waist": "arc_above"}
        elif disc is not None:
            kind, ev = "BOWTIE_OTHER", {"waist": "unfilled_disc"}
        else:
            kind, ev = "GATE", {"waist": "none"}
        ev["bars"] = mask
        ev["size"] = [round(w, 1), round(h, 1)]
        bodies.append(Body(kind, pymupdf.Rect(*box), axis, state=state,
                           evidence=ev))
        claimed.add(box)

    bodies.extend(_find_discs_between_bars(pc, horiz, vert, rounds, fills,
                                           diag, claimed, spent, lay))
    return bodies


def _triangles_filled(box, fills) -> bool:
    """Legend page 2 VALVE OPERATION: a solid black bowtie is CLOSED.

    The fill arrives as quarter-tiles offset from the waist, not as one shape,
    so this asks whether the body's area is covered rather than looking for a
    single path.
    """
    x0, y0, x1, y1 = box
    area = (x1 - x0) * (y1 - y0)
    covered = 0.0
    for f in fills:
        ix0, iy0 = max(f.x0, x0), max(f.y0, y0)
        ix1, iy1 = min(f.x1, x1), min(f.y1, y1)
        if ix1 <= ix0 or iy1 <= iy0:
            continue
        if f.width > (x1 - x0) * 1.1 or f.height > (y1 - y0) * 1.1:
            continue
        covered += (ix1 - ix0) * (iy1 - iy0)
    return covered >= area * 0.30


def _nearest_bars(index, coord, lo, hi, mind, maxd, lay: ValveLayout):
    """Distance to the closest covering run on each side of `coord`."""
    left = right = None
    for key, runs in index.items():
        d = key - coord
        if abs(d) > maxd or abs(d) < mind:
            continue
        if not any(s0 <= lo + lay.bar_cover and s1 >= hi - lay.bar_cover
                   for s0, s1 in runs):
            continue
        if d < 0 and (left is None or -d < left):
            left = -d
        elif d > 0 and (right is None or d < right):
            right = d
    return left, right


def _vane_ticks(diag_pts, cx, cy, radius, lay: ValveLayout) -> int:
    """Count the butterfly's vane ticks on the rim of a circle.

    LEGEND page 2: the BUTTERFLY row draws two short strokes touching the
    circle at diametrically opposite points; the BALL row draws none.  Since
    `VALVE OPERATION` on the same sheet makes fill mean open/closed, these
    ticks are the only thing that tells the two bodies apart.
    """
    hits = []
    for p0, p1 in diag_pts:
        dx, dy = abs(p1.x - p0.x), abs(p1.y - p0.y)
        length = (dx * dx + dy * dy) ** 0.5
        if not lay.tick_span[0] <= length <= lay.tick_span[1]:
            continue
        mx, my = (p0.x + p1.x) / 2, (p0.y + p1.y) / 2
        d = ((mx - cx) ** 2 + (my - cy) ** 2) ** 0.5
        if radius * 0.5 <= d <= radius * lay.tick_reach + length:
            hits.append((mx - cx, my - cy))
    for i, a in enumerate(hits):
        for b in hits[i + 1:]:
            if a[0] * b[0] + a[1] * b[1] < 0:      # opposite sides of the rim
                return 2
    return len(hits)


def _find_discs_between_bars(pc, horiz, vert, rounds, fills, diag, claimed,
                             spent, lay: ValveLayout) -> list[Body]:
    """Bodies with no diagonals through them - legend page 2 BUTTERFLY / BALL.

    Both are a circle sitting between two end bars.  The vane ticks separate
    them; the fill records whether the valve is open or closed.
    """
    out: list[Body] = []
    for b in rounds:
        if id(b) in spent:
            continue
        w, h = b.width, b.height
        if not lay.body_short[0] * 0.4 <= max(w, h) <= lay.body_short[1]:
            continue
        aspect = min(w, h) / max(w, h)
        if not lay.disc_aspect[0] <= aspect <= lay.disc_aspect[1]:
            continue
        cx, cy = (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2
        span = max(w, h)
        radius = span / 2
        maxd = radius * lay.bar_reach
        mind = radius * lay.bar_min
        found = None
        for axis, index, coord, lo, hi in (
                ("H", vert, cx, cy - radius * 1.1, cy + radius * 1.1),
                ("V", horiz, cy, cx - radius * 1.1, cx + radius * 1.1)):
            left, right = _nearest_bars(index, coord, lo, hi, mind, maxd, lay)
            if left is None or right is None:
                continue
            found = (axis, left, right)
            break
        if found is None:
            continue
        axis, left, right = found
        if axis == "H":
            box = (cx - left, cy - radius, cx + right, cy + radius)
        else:
            box = (cx - radius, cy - left, cx + radius, cy + right)
        key = tuple(round(v, 1) for v in box)
        if key in claimed:
            continue
        claimed.add(key)
        ticks = _vane_ticks(diag, cx, cy, radius, lay)
        filled = any(abs((f.x0 + f.x1) / 2 - cx) <= 1.0
                     and abs((f.y0 + f.y1) / 2 - cy) <= 1.0
                     and f.width <= b.width + 0.6 and f.height <= b.height + 0.6
                     for f in fills)
        out.append(Body("BUTTERFLY" if ticks >= 2 else "BALL",
                        pymupdf.Rect(*box), axis,
                        state="CLOSED" if filled else "OPEN",
                        evidence={"circle": round(span, 1),
                                  "vane_ticks": ticks,
                                  "bar_gap": [round(left, 1), round(right, 1)]}))
    return out


# --------------------------------------------------------------------------
# Actuator judgement (legend page 3, VALVES ACTUATORS)
# --------------------------------------------------------------------------

def _actuator_shells(pc, lay: ValveLayout):
    """Small closed shapes that could hold an actuator letter.

    Legend page 3 always encloses the letter: a circle for ROTARY MOTOR and
    ELECTRO OR HYDRAULIC, a box for HYDRAULIC CYLINDER, SOLENOID and
    UNCLASSIFIED.  Finding the enclosure first - rather than starting from a
    letter - matters because the letter is not always text.  Page 6 writes its
    motor 'M' into the text layer; page 26 strokes its hydraulic 'H' as three
    line segments with no text at all, the same way the title block strokes its
    revision letter.  Enclosure-first lets an unread letter be reported as
    unread instead of silently dropping the actuator.
    """
    shells = []
    for d in pc.drawings():
        items = d["items"]
        if not items:
            continue
        b = d["bbox"]
        if not _in_area(b, lay.drawing_area):
            continue
        if not (lay.act_box[0] <= b.width <= lay.act_box[1]
                and lay.act_box[0] <= b.height <= lay.act_box[1]):
            continue
        ratio = min(b.width, b.height) / max(b.width, b.height)
        if ratio < 0.75:
            continue
        if all(i[0] == "c" for i in items):
            shells.append(("circle", b))
        elif all(i[0] in ("l", "qu", "re") for i in items) and len(items) >= 1:
            shells.append(("box", b))
    return shells


def _strokes_in(pc, rect, lay: ValveLayout):
    """Straight strokes wholly inside a shell - the drawn letter."""
    out = []
    for p0, p1 in pc.segments():
        if not (rect.x0 - 0.3 <= min(p0.x, p1.x) and max(p0.x, p1.x) <= rect.x1 + 0.3
                and rect.y0 - 0.3 <= min(p0.y, p1.y) and max(p0.y, p1.y) <= rect.y1 + 0.3):
            continue
        dx, dy = p1.x - p0.x, p1.y - p0.y
        length = (dx * dx + dy * dy) ** 0.5
        if length < 0.8 or length > max(rect.width, rect.height) * 1.1:
            continue
        out.append((p0, p1, abs(dx), abs(dy), length))
    return out


def _read_stroked_letter(strokes):
    """Name the letter a shell contains from its stroke signature.

    The letters this project strokes are decided on stroke *count and
    orientation*, never on size - page 33 draws the same M at 14.2 pt and at
    19.3 pt, and page 26 draws its H rotated with the vertical pipe, so every
    rule below is stated as parallel/perpendicular rather than up/down:

      M  four strokes - two parallel full-height stems and two diagonals of the
         same length forming the inner V, each leaning by well under its own
         length.
      H  three strokes - two parallel and one perpendicular joining them.
      X  two strokes, both diagonal, crossing.

    Anything else returns None and the caller reports the letter as unread
    rather than guessing.
    """
    if not strokes:
        return None
    axial = [s for s in strokes if s[2] < 0.4 or s[3] < 0.4]
    diagonal = [s for s in strokes if s[2] >= 0.4 and s[3] >= 0.4]
    if len(strokes) == 2 and len(diagonal) == 2:
        return "X"
    if len(axial) == 3 and not diagonal:
        horiz = [s for s in axial if s[3] < 0.4]
        vert = [s for s in axial if s[2] < 0.4]
        if (len(horiz), len(vert)) in ((2, 1), (1, 2)):
            return "H"
    if len(strokes) == 4 and len(axial) == 2 and len(diagonal) == 2:
        vertical = axial[0][2] < 0.4
        if vertical != (axial[1][2] < 0.4):
            return None                  # the two stems are not parallel
        stem = max(s[3] if vertical else s[2] for s in axial)
        for s in diagonal:
            long_, cross = (s[3], s[2]) if vertical else (s[2], s[3])
            if abs(long_ - stem) > stem * 0.25 or cross > long_ * 0.6:
                return None
        return "M"
    return None


def find_actuators(pc, lay: ValveLayout = LAYOUT):
    """Actuator marks: (kind, centre, evidence).

    `kind` is a legend page 3 actuator name, or `UNREAD` when the enclosure is
    there but the letter inside it could not be named.
    """
    words = [(r, t.strip()) for r, t in pc.words if _in_area(r, lay.drawing_area)]
    out = []
    for shape, b in _actuator_shells(pc, lay):
        centre = pymupdf.Point((b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2)
        rect = b
        inside = [t for r, t in words
                  if b.x0 - 1 <= r.x0 and r.x1 <= b.x1 + 1
                  and b.y0 - 1 <= r.y0 and r.y1 <= b.y1 + 1]
        text = "".join(inside).strip()
        kind = ACT_LETTERS.get(text)
        if kind is not None:
            out.append((kind, centre, rect, f"text '{text}' in {shape}"))
            continue
        if text:
            continue                     # a labelled box that is not an actuator
        letter = _read_stroked_letter(_strokes_in(pc, b, lay))
        if letter is not None:
            out.append((ACT_LETTERS[letter], centre, rect,
                        f"stroked '{letter}' in {shape}"))
        else:
            out.append(("UNREAD", centre, rect, f"empty {shape}, letter not read"))
    # I/P positioners are written as text on the stem with no enclosure
    # (legend page 3, PNEUMATIC DIAPHRAGM WITH POSITIONER).
    for r, t in words:
        if t in ("I/P", "IP"):
            out.append(("PNEUMATIC", pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2),
                        pymupdf.Rect(r), "I/P positioner on stem"))
    return out


def attach_actuators(pc, bodies: list[Body], lay: ValveLayout = LAYOUT) -> None:
    """Assign each actuator mark to the body it stands over.

    Legend pages 3 and 4 both draw the actuator on the stem, on the axis
    perpendicular to flow, so the search is a narrow band on that axis.  A
    named actuator outranks an UNREAD one for the same body, so an enclosure
    whose letter could not be read never displaces a letter that could.
    """
    marks = find_actuators(pc, lay)
    marks.sort(key=lambda m: m[0] == "UNREAD")
    for kind, pt, rect, why in marks:
        best, best_d = None, None
        for b in bodies:
            # An actuator stands clear of the body on the stem.  Without this
            # the globe's own waist disc reads as an unlabelled circle sitting
            # exactly on the valve and every globe acquires an UNREAD actuator.
            if rect.intersects(b.rect):
                continue
            cx, cy = (b.rect.x0 + b.rect.x1) / 2, (b.rect.y0 + b.rect.y1) / 2
            if b.axis == "H":
                off, along = abs(pt.x - cx), abs(pt.y - cy)
            else:
                off, along = abs(pt.y - cy), abs(pt.x - cx)
            if off > lay.act_offaxis or along > lay.act_reach:
                continue
            if best_d is None or along < best_d:
                best, best_d = b, along
        if best is None or best.actuator != "NONE":
            continue
        best.actuator = kind
        best.actuator_evidence = f"{why}, {round(best_d, 1)}pt along the stem"


# --------------------------------------------------------------------------
# Tags
# --------------------------------------------------------------------------

def bubble_tags(pc, lay: ValveLayout = LAYOUT):
    """Valve tags carried in an instrument bubble (legend page 4)."""
    out = []
    for bub in ds.find_bubbles(pc, ds.LAYOUT):
        if not _in_area(bub, lay.drawing_area):
            continue
        # The tag glyphs overhang the stadium's top arc slightly (page 6 draws
        # MOV at y0 662.5 in a bubble whose top is 664.5), so the top-line
        # window is a fraction of the bubble rather than a fixed inset.
        top = [(r, t) for r, t in pc.words
               if bub.x0 - 2 <= r.x0 and r.x1 <= bub.x1 + 2
               and bub.y0 - bub.height * 0.25 <= r.y0
               and r.y1 <= bub.y0 + bub.height * 0.7]
        top.sort(key=lambda rt: rt[0].x0)
        text = "".join(t for _, t in top).strip()
        if text in TAG_ANCHORS:
            out.append((text, bub))
    return out


def attach_tags(pc, bodies: list[Body], lay: ValveLayout = LAYOUT) -> list[tuple]:
    """Give each tag bubble to its nearest unclaimed body.

    The leader line from bubble to body is drawn as a plain segment among tens
    of thousands of others, so this spike uses nearest-body instead of tracing
    it, and reports the distance as evidence.
    """
    tags = bubble_tags(pc, lay)
    for text, bub in tags:
        bx, by = (bub.x0 + bub.x1) / 2, (bub.y0 + bub.y1) / 2
        best, best_d = None, None
        for b in bodies:
            if b.tag:
                continue
            cx, cy = (b.rect.x0 + b.rect.x1) / 2, (b.rect.y0 + b.rect.y1) / 2
            d = ((cx - bx) ** 2 + (cy - by) ** 2) ** 0.5
            if d > lay.tag_reach:
                continue
            if best_d is None or d < best_d:
                best, best_d = b, d
        if best is None:
            continue
        best.tag = text
        best.tag_rect = (bub.x0, bub.y0, bub.x1, bub.y1)
        best.evidence["tag_distance"] = round(best_d, 1)
    return tags


# --------------------------------------------------------------------------
# Per-page driver
# --------------------------------------------------------------------------

def analyse(pc, lay: ValveLayout = LAYOUT) -> dict:
    bodies = find_bodies(pc, lay)
    attach_actuators(pc, bodies, lay)
    tags = attach_tags(pc, bodies, lay)
    tagged = sum(1 for b in bodies if b.tag)
    return {
        "page_no": pc.page_no,
        "bodies": bodies,
        "tags": tags,
        "counts": collections.Counter(b.kind for b in bodies),
        "actuators": collections.Counter(b.actuator for b in bodies),
        "tagged": tagged,
    }


# --------------------------------------------------------------------------
# Excel side
# --------------------------------------------------------------------------

def load_valve_rows(path: Path) -> list[dict]:
    """Read a valve deliverable's '3.0_Valve List' sheet.

    Different sheet and column layout from the instrument list, which is why
    the config carries the instrument sheet under `excel:` and this reads its
    own header - the two deliverables are separate templates, not one.
    """
    import openpyxl
    ws = openpyxl.load_workbook(path, data_only=True)["3.0_Valve List"]
    rows = []
    for i in range(8, ws.max_row + 1):
        no = ws.cell(i, 1).value
        if not isinstance(no, int):
            continue                     # note block at the foot of the sheet
        pid = ws.cell(i, 2).value
        rows.append({
            "no": no,
            "pid_no": str(pid).strip() if pid else "",
            "valve_type": (ws.cell(i, 3).value or "").strip(),
            "qty": ws.cell(i, 4).value or 0,
            "system": (ws.cell(i, 5).value or "").strip(),
            "description": (ws.cell(i, 12).value or "").strip(),
        })
    return rows


# `VALVE TYPE` in the deliverables is an operation mode, not a body type.
# MOV / MOV_I are motor-operated, HOV hydraulic, CV a control valve.
TYPE_ACTUATOR = {"MOV": "MOTOR", "MOV_I": "MOTOR", "HOV": "HYDRAULIC",
                 "CV": "PNEUMATIC"}


# --------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------

def page_index() -> dict:
    """drawing_no -> [page numbers], from the title block spike's CSV."""
    import csv
    idx: dict[str, list] = collections.defaultdict(list)
    with open(OUT / "titleblocks.csv", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if row["analysis_scope"] != "True":
                continue
            idx[row["drawing_no"]].append(int(row["page_no"]))
    return idx


def analyse_all(pages) -> dict:
    return {pc.page_no: analyse(pc) for pc in pages if pc.analysis_scope}


def cmd_reach(results) -> dict:
    """Step 1 - how far do text anchors reach, and where must geometry take over?"""
    total = collections.Counter()
    per_page = []
    for page_no, res in sorted(results.items()):
        bodies = res["bodies"]
        if not bodies:
            continue
        per_page.append((page_no, len(bodies), res["tagged"]))
        total["bodies"] += len(bodies)
        total["tagged"] += res["tagged"]
        for k, v in res["counts"].items():
            total["kind:" + k] += v
        for k, v in res["actuators"].items():
            total["act:" + k] += v
    return {"total": total, "per_page": per_page}


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").upper())


def compare(results, pages) -> dict:
    """Match detections against the two valve deliverables, page by page.

    The valve sheets carry an explicit `P&ID NO.` column, so unlike the field
    instrument list there is no title-matching to do - but a drawing number can
    still appear on more than one sheet, so the join goes through the title
    block index and a drawing found on several pages has its detections summed.
    """
    idx = page_index()
    out = {"deliverables": [], "missing_drawings": []}
    for tag, path, family in DELIVERABLES:
        if not path.exists():
            continue
        rows = load_valve_rows(path)
        by_dwg: dict[str, list] = collections.defaultdict(list)
        for r in rows:
            by_dwg[_norm(r["pid_no"])].append(r)
        entries = []
        for dwg, rs in sorted(by_dwg.items()):
            pgs = [p for k, v in idx.items() if _norm(k) == dwg for p in v]
            if not pgs:
                out["missing_drawings"].append({"deliverable": tag, "drawing": dwg})
                continue
            det_family = det_act = det_unread = 0
            kinds = collections.Counter()
            acts = collections.Counter()
            fam_acts = collections.Counter()
            for p in pgs:
                res = results.get(p)
                if not res:
                    continue
                for b in res["bodies"]:
                    kinds[b.kind] += 1
                    if b.kind in family:
                        det_family += 1
                        if b.actuator == "UNREAD":
                            det_unread += 1
                        elif b.actuator != "NONE":
                            det_act += 1
                            fam_acts[b.actuator] += 1
                    acts[b.actuator] += 1
            want_act = collections.Counter(
                TYPE_ACTUATOR.get(r["valve_type"], "?") for r in rs)
            entries.append({
                "drawing": dwg,
                "pages": pgs,
                "excel_rows": len(rs),
                "excel_actuators": dict(want_act),
                "detected_family": det_family,
                "detected_actuated": det_act,
                "detected_family_actuators": dict(fam_acts),
                "detected_unread": det_unread,
                "detected_kinds": dict(kinds),
                "detected_actuators": dict(acts),
            })
        out["deliverables"].append({
            "tag": tag, "path": str(path), "family": list(family),
            "rows": len(rows), "drawings": len(by_dwg), "entries": entries,
        })
    return out


def write_viewer(results, pages, out_dir: Path) -> Path:
    """Feed every page's detections to the JSON-driven overlay viewer."""
    import viewer
    by_no = {pc.page_no: pc for pc in pages}
    titles = {}
    import csv
    with open(OUT / "titleblocks.csv", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            titles[int(row["page_no"])] = row["drawing_no"]
    payload = []
    for page_no, res in sorted(results.items()):
        if not res["bodies"]:
            continue
        layers: dict[str, list] = collections.defaultdict(list)
        for b in res["bodies"]:
            item = b.as_json()
            layers["body:" + b.kind].append(item)
            if b.actuator != "NONE":
                layers["act:" + b.actuator].append(
                    {"rect": item["rect"], "actuator": b.actuator,
                     "evidence": b.actuator_evidence})
            if b.tag:
                layers["tag:" + b.tag].append(
                    {"rect": item["tag_rect"], "tag": b.tag,
                     "body": item["rect"], "kind": b.kind})
        payload.append({
            "page_no": page_no,
            "label": titles.get(page_no, ""),
            "layers": [{"name": k, "items": v} for k, v in sorted(layers.items())],
        })
    return viewer.write(payload, out_dir, by_no)


def write_report(results, cmp_data, path: Path) -> None:
    reach = cmd_reach(results)
    t = reach["total"]
    bodies, tagged = t["bodies"], t["tagged"]
    kinds = sorted(((k[5:], v) for k, v in t.items() if k.startswith("kind:")),
                   key=lambda kv: (-kv[1], kv[0]))
    acts = sorted(((k[4:], v) for k, v in t.items() if k.startswith("act:")),
                  key=lambda kv: (-kv[1], kv[0]))
    L = []
    L.append("# Spike 4 - valve detection\n")
    L.append("Rules are derived from legend pages 2 (LINE VALVES, VALVE OPERATION),")
    L.append("3 (VALVES ACTUATORS) and 4 (VALVE BODY WITH ACTUATOR); see the module")
    L.append("docstring in `spike/detect_valves.py` for each citation.\n")

    L.append("## 1. Text-anchor reach vs geometry\n")
    L.append(f"- valve bodies found on {len(reach['per_page'])} drawings: **{bodies}**")
    pct = 100.0 * tagged / max(bodies, 1)
    L.append(f"- carrying a tag bubble (MOV / HOV / HV / XV / FCV / ...): "
             f"**{tagged} ({pct:.1f}%)**")
    L.append(f"- reachable by geometry only: **{bodies - tagged} ({100 - pct:.1f}%)**\n")
    L.append("Text anchors are not a viable primary route for valves: the tag bubble")
    L.append("is drawn only where a valve is instrumented.  Everything else has to be")
    L.append("found from the symbol.\n")

    L.append("## 2. Body types found\n")
    L.append("| body | count |")
    L.append("|---|---:|")
    for k, v in kinds:
        L.append(f"| {k} | {v} |")
    L.append("")

    L.append("## 3. Actuators found\n")
    L.append("| actuator | count |")
    L.append("|---|---:|")
    for k, v in acts:
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append("`NONE` means no actuator enclosure stands on the stem - a manual valve.")
    L.append("`UNREAD` means an enclosure is there but the letter inside it could not")
    L.append("be named; it is reported rather than guessed.\n")

    L.append("## 4. Against the valve deliverables\n")
    for d in cmp_data["deliverables"]:
        L.append(f"### {d['tag']} - {Path(d['path']).name} "
                 f"({d['rows']} rows, family {'/'.join(d['family'])})\n")
        L.append("| drawing | page | excel rows | excel actuators | bodies in family "
                 "| actuated | detected actuators | unread | delta |")
        L.append("|---|---|---:|---|---:|---:|---|---:|---:|")
        tot_x = tot_d = 0
        for e in d["entries"]:
            delta = e["detected_actuated"] - e["excel_rows"]
            tot_x += e["excel_rows"]
            tot_d += e["detected_actuated"]
            L.append(f"| {e['drawing']} | {','.join(str(p) for p in e['pages'])} "
                     f"| {e['excel_rows']} | "
                     f"{', '.join(f'{k} {v}' for k, v in sorted(e['excel_actuators'].items()))} "
                     f"| {e['detected_family']} | {e['detected_actuated']} | "
                     f"{', '.join(f'{k} {v}' for k, v in sorted(e['detected_family_actuators'].items()))} "
                     f"| {e['detected_unread']} | {delta:+d} |")
        L.append(f"| **total** | | **{tot_x}** | | | **{tot_d}** | | | "
                 f"**{tot_d - tot_x:+d}** |")
        L.append("")
    if cmp_data["missing_drawings"]:
        L.append("Drawings named by a deliverable but absent from the PDF index:\n")
        for m in cmp_data["missing_drawings"]:
            L.append(f"- {m['deliverable']}: {m['drawing']}")
        L.append("")
        L.append("These are the same title-block mismatches `out/revision_gap.md`")
        L.append("already records from the instrument side, not a detection failure:")
        L.append("page 46's title block reads `D00P-00GHC10-M05-0001` while the")
        L.append("deliverables address it as `D00P-00GBL10-M05-0001`.  That is why the")
        L.append("GHC row above spans pages 46 and 47 and carries both drawings'")
        L.append("valves; it is left uncorrected here on purpose - the drawing number")
        L.append("is the client's to reconcile, not a rule to patch around.\n")

    L.append("## 5. What this comparison cannot measure\n")
    L.append("`data/Valve_List_2512xx.xlsx` - the 194-row master with the BODY and")
    L.append("ACTUATOR columns - is not in the repository.  The two files above are")
    L.append("filtered cuts of it (their NO column runs 1..178 with gaps), and neither")
    L.append("carries a body column.  So:\n")
    L.append("- **GATE vs GLOBE confusion matrix: not measurable.**  CZH files gate and")
    L.append("  globe together under one heading and has no per-row body column, so")
    L.append("  there is no ground truth to confuse against.")
    L.append("- **BUTTERFLY 21: partly measurable.**  CZI's 21 rows are all butterfly,")
    L.append("  so their drawings can be checked for butterfly bodies - but CZI holds")
    L.append("  only the *I&C* butterflies, so a drawing may legitimately carry more")
    L.append("  butterflies than the file lists.")
    L.append("- **SELF ACTING 68: not measurable.**  Those rows are in neither file.")
    L.append("  What is reported instead is how many detected bodies have no actuator")
    L.append("  drawn on the stem at all.")
    L.append("- **ANGLE 70 / BALL 4: not measurable.**  Neither file contains them.\n")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pages", default="", help="1-based page list, e.g. 6,26,30")
    ap.add_argument("--reach", action="store_true",
                    help="print the text-anchor reach measurement")
    ap.add_argument("--compare", action="store_true",
                    help="compare against the valve deliverables")
    ap.add_argument("--report", default="", help="write the markdown report here")
    ap.add_argument("--json", default="", help="write detections to this path")
    ap.add_argument("--viewer", default="", help="write the overlay viewer here")
    args = ap.parse_args()

    doc, pages = pidcache.load_pages(PDF)
    if args.pages:
        want = {int(x) for x in args.pages.split(",")}
        pages = [p for p in pages if p.page_no in want]

    results = analyse_all(pages)

    for page_no, res in sorted(results.items()):
        if not res["bodies"]:
            continue
        print(f"p{page_no:>3}  bodies={len(res['bodies']):>3} "
              f"tagged={res['tagged']:>3}  {dict(res['counts'])}  "
              f"{dict(res['actuators'])}")

    if args.reach:
        reach = cmd_reach(results)
        t = reach["total"]
        pct = 100.0 * t["tagged"] / max(t["bodies"], 1)
        print(f"\nvalve bodies            : {t['bodies']}")
        print(f"reached by a text anchor: {t['tagged']} ({pct:.1f}%)")
        print(f"needing geometry only   : {t['bodies'] - t['tagged']} ({100 - pct:.1f}%)")
        for prefix, title in (("kind:", "body kinds"), ("act:", "actuators")):
            print("\n" + title + ":")
            for k, v in sorted(((k[len(prefix):], v) for k, v in t.items()
                                if k.startswith(prefix)), key=lambda kv: (-kv[1], kv[0])):
                print(f"  {k:<14} {v}")

    cmp_data = compare(results, pages) if (args.compare or args.report) else None
    if args.compare:
        print(json.dumps(cmp_data, indent=1)[:4000])
    if args.report:
        write_report(results, cmp_data, Path(args.report))
        print("wrote", args.report)
    if args.json:
        Path(args.json).write_text(json.dumps(
            [{"page_no": n,
              "bodies": [b.as_json() for b in r["bodies"]],
              "counts": dict(r["counts"]),
              "actuators": dict(r["actuators"])}
             for n, r in sorted(results.items())], indent=1), encoding="utf-8")
        print("wrote", args.json)
    if args.viewer:
        print("wrote", write_viewer(results, pages, Path(args.viewer)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
