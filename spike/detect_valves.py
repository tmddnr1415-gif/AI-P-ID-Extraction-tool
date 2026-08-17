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
# Which deliverable covers which body family (config V5).  The GATE/GLOBE file
# also carries ball-bodied MOVs, which is why its family is not just its title.
DELIVERABLES = [
    (str(d["tag"]), Path(str(d["path"])), tuple(str(b) for b in d["bodies"]))
    for d in CFG.get("valves.deliverables")
]

# The master valve list.  Present only when the client has supplied it; it is
# the only file carrying BODY / ACTUATOR / OPERATION MODE per row, so the
# gate-vs-globe confusion matrix and the self-acting exclusion depend on it.
MASTER = Path("data/Valve_List_2512xx.xlsx")

# The four deliverables a detected valve can end up in, per the client's own
# split.  This is a *deliverable* classification, not a symbol one - two valves
# with the same body go to different packages depending on what drives them.
CLASS_BFV = "BFV"          # butterfly with an actuator
CLASS_MOV = "MOV"          # motor-operated gate / globe / ball
CLASS_CV = "CV"            # modulating pneumatic control valve
CLASS_XV = "XV"            # on-off pneumatic / solenoid valve
CLASS_EXCLUDED = "EXCLUDED"  # nothing drawn on the stem - manual or self-acting

# Tags that separate a modulating control valve from an on-off shutoff valve.
# LEGEND page 3: FCV / LCV / PCV / TCV sit in the CONTROL DEVICE column, while
# XV / HV are shutoff tags on page 4.
CV_TAGS = frozenset(str(t) for t in CFG.get("valves.cv_tags"))
XV_TAGS = frozenset(str(t) for t in CFG.get("valves.xv_tags"))


def deliverable_class(body: "Body") -> str:
    """Which valve deliverable this detection belongs to."""
    if body.actuator in ("NONE", "UNREAD"):
        return CLASS_EXCLUDED
    if body.kind == "BUTTERFLY":
        return CLASS_BFV
    if body.actuator == "MOTOR" and body.kind in ("GATE", "GLOBE", "BALL"):
        return CLASS_MOV
    if body.actuator == "SOLENOID":
        return CLASS_XV
    if body.actuator == "PNEUMATIC":
        return CLASS_XV if body.tag in XV_TAGS else CLASS_CV
    if body.actuator == "HYDRAULIC":
        return CLASS_MOV
    return CLASS_EXCLUDED


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

    # Actuator sits on the stem, on the axis perpendicular to flow.  Both
    # bounds are PROJECT (out/valve_project_deps.md V1, V2) and come from
    # config; the defaults here are only so the dataclass is constructible.
    act_reach: float = 90.0
    act_offaxis: float = 12.0
    # Legend page 3 draws its actuator enclosures at 14.2 pt across (the motor
    # and E/H circles) and page 26 strokes its hydraulic box at 11.3.  The
    # lower bound sits below both and above the 7.1 pt globe waist disc, which
    # would otherwise read as an unlabelled circle standing on the stem.
    act_box: tuple = (9.0, 34.0)        # side of an actuator circle / box

    # Tag bubble attached by a leader.
    tag_reach: float = 190.0


# Rules that can be switched off one at a time so each one's contribution is
# measurable (`--without NAME`), the same way the instrument spikes measure
# theirs.  Nothing here is a tuning knob: each name is a whole decision that is
# either made or skipped.
#
#   WAIST_DISC     legend p2 - the disc at a bowtie's waist makes it a GLOBE.
#                  Off: every bowtie is a GATE.
#   VANE_TICK      legend p2 - the vane ticks make a circle-body a BUTTERFLY.
#                  Off: every circle between bars is a BALL.
#   END_BARS       legend p2 - a line valve is closed off by a bar at each end.
#                  Off: one bar is enough.
#   STROKE_LETTER  read an actuator letter drawn as strokes rather than text.
#                  Off: those enclosures stay UNREAD.
#   ACT_CLEARANCE  an actuator stands clear of the body it drives.
#                  Off: a shape overlapping the body may claim it.
#                  Measured contribution is now zero: ACT_STEM rejects every
#                  case this rule used to catch, because a shape sitting on top
#                  of the body has no stem drawn to it either.  Kept because it
#                  states a different fact and costs nothing, but it is no
#                  longer load-bearing and the report says so.
#   ACT_STEM       legend p3/p4 - the actuator is joined to the body by a drawn
#                  stem.  Off: proximity on the stem axis is enough.
ALL_RULES = ("WAIST_DISC", "VANE_TICK", "END_BARS", "STROKE_LETTER",
             "ACT_CLEARANCE", "ACT_STEM")


def _layout(cfg=CFG) -> ValveLayout:
    """Take every PROJECT-judged value from config.

    What stays as a dataclass default is the LEGEND geometry: the bowtie
    proportions, the waist disc, the vane ticks, the end-bar spacing and the
    actuator enclosure size are all measured off legend pages 2 and 3 and cited
    at the point of use, so they do not move with the project.
    """
    return ValveLayout(
        drawing_area=cfg.rect("regions.drawing_area"),
        act_reach=float(cfg.get("valves.actuator_reach")),
        act_offaxis=float(cfg.get("valves.actuator_offaxis")),
        tag_reach=float(cfg.get("valves.tag_reach")),
    )


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


def find_bodies(pc, lay: ValveLayout = LAYOUT,
                disabled=frozenset()) -> list[Body]:
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
        if mask != 3 and ("END_BARS" not in disabled or mask == 0):
            continue

        state = "CLOSED" if _triangles_filled(box, fills) else "OPEN"

        if len(slopes) < 2:
            # Half a bowtie with both bars: legend page 2 CHECK.
            bodies.append(Body("CHECK", pymupdf.Rect(*box), axis, state=state,
                               evidence={"diagonals": 1, "bars": mask}))
            claimed.add(box)
            continue

        disc, filled = (None, False) if "WAIST_DISC" in disabled else \
            _waist_object(box, axis, rounds, fills, lay)
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
                                           diag, claimed, spent, lay, disabled))
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
                             spent, lay: ValveLayout,
                             disabled=frozenset()) -> list[Body]:
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
                if "END_BARS" not in disabled or (left is None and right is None):
                    continue
                left = right = left if left is not None else right
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
        ticks = 0 if "VANE_TICK" in disabled else _vane_ticks(diag, cx, cy, radius, lay)
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


_STROKE_SIGS = CFG.get("valves.stroked_letters")


def _read_stroked_letter(strokes, sigs=None):
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
    sigs = _STROKE_SIGS if sigs is None else sigs
    if not strokes:
        return None
    axial = [s for s in strokes if s[2] < 0.4 or s[3] < 0.4]
    diagonal = [s for s in strokes if s[2] >= 0.4 and s[3] >= 0.4]
    if "X" in sigs and len(strokes) == 2 and len(diagonal) == 2:
        return "X"
    if "H" in sigs and len(axial) == 3 and not diagonal:
        horiz = [s for s in axial if s[3] < 0.4]
        vert = [s for s in axial if s[2] < 0.4]
        if (len(horiz), len(vert)) in ((2, 1), (1, 2)):
            return "H"
    if "M" in sigs and len(strokes) == 4 and len(axial) == 2 and len(diagonal) == 2:
        sig = sigs["M"]
        vertical = axial[0][2] < 0.4
        if vertical != (axial[1][2] < 0.4):
            return None                  # the two stems are not parallel
        stem = max(s[3] if vertical else s[2] for s in axial)
        for s in diagonal:
            long_, cross = (s[3], s[2]) if vertical else (s[2], s[3])
            if (abs(long_ - stem) > stem * float(sig["diagonal_length_tol"])
                    or cross > long_ * float(sig["diagonal_lean_max"])):
                return None
        return "M"
    return None


def _actuator_stem(horiz, vert, rect, body: Body, lay: ValveLayout) -> bool:
    """Is the actuator joined to the body by a stem drawn on the flow normal?"""
    br = body.rect
    if body.axis == "H":                 # flow horizontal, stem vertical
        coord = (rect.x0 + rect.x1) / 2
        if rect.y1 <= br.y0:
            lo, hi = rect.y1, br.y0
        elif rect.y0 >= br.y1:
            lo, hi = br.y1, rect.y0
        else:
            return True                  # already touching
        return lo >= hi - 0.5 or _stem_links(vert, coord, lo, hi, lay)
    coord = (rect.y0 + rect.y1) / 2
    if rect.x1 <= br.x0:
        lo, hi = rect.x1, br.x0
    elif rect.x0 >= br.x1:
        lo, hi = br.x1, rect.x0
    else:
        return True
    return lo >= hi - 0.5 or _stem_links(horiz, coord, lo, hi, lay)


def find_actuators(pc, lay: ValveLayout = LAYOUT, disabled=frozenset(),
                   sigs=None):
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
        letter = (None if "STROKE_LETTER" in disabled
                  else _read_stroked_letter(_strokes_in(pc, b, lay), sigs))
        if letter is not None:
            out.append((ACT_LETTERS[letter], centre, rect,
                        f"stroked '{letter}' in {shape}"))
        else:
            n = len(_strokes_in(pc, b, lay))
            # Split the two reasons an enclosure stays unread, because they are
            # different problems: nothing drawn inside means the shape is
            # probably not an actuator at all, while strokes that match no
            # signature mean a letter this module cannot yet name.
            out.append(("UNREAD", centre, rect,
                        f"empty {shape}, no strokes inside" if n == 0 else
                        f"{shape} with {n} strokes, no letter signature"))
    # I/P positioners are written as text on the stem with no enclosure
    # (legend page 3, PNEUMATIC DIAPHRAGM WITH POSITIONER).
    for r, t in words:
        if t in ("I/P", "IP"):
            out.append(("PNEUMATIC", pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2),
                        pymupdf.Rect(r), "I/P positioner on stem"))
    return out


def _stem_links(index, coord, lo, hi, lay: ValveLayout) -> bool:
    """Is there a drawn run at `coord` spanning lo..hi?

    LEGEND pages 3 and 4 never float an actuator next to a valve: it is always
    joined to the body by a stem.  Requiring the stem is what separates a valve
    actuator from a *pump* motor, which is the same M-in-a-circle sitting the
    same distance away on the same axis - page 46 has three of them, each 75 pt
    from a closed globe valve with nothing drawn in between.
    """
    span = hi - lo
    for step in range(-8, 9):
        for s0, s1 in index.get(round(coord + step * 0.1, 1), ()):
            if s0 <= lo + span * 0.25 and s1 >= hi - span * 0.25:
                return True
    return False


def attach_actuators(pc, bodies: list[Body], lay: ValveLayout = LAYOUT,
                     disabled=frozenset(), sigs=None) -> None:
    """Assign each actuator mark to the body it stands over.

    Legend pages 3 and 4 both draw the actuator on the stem, on the axis
    perpendicular to flow, so the search is a narrow band on that axis.  A
    named actuator outranks an UNREAD one for the same body, so an enclosure
    whose letter could not be read never displaces a letter that could.
    """
    marks = find_actuators(pc, lay, disabled, sigs)
    marks.sort(key=lambda m: m[0] == "UNREAD")
    horiz, vert, _ = _index_segments(pc, lay)
    for kind, pt, rect, why in marks:
        best, best_d = None, None
        for b in bodies:
            # An actuator stands clear of the body on the stem.  This was
            # load-bearing before ACT_STEM existed - the globe's own waist disc
            # read as an unlabelled circle sitting exactly on the valve, giving
            # every globe an UNREAD actuator.  ACT_STEM now rejects the same
            # cases, so `--without ACT_CLEARANCE` moves nothing.
            if "ACT_CLEARANCE" not in disabled and rect.intersects(b.rect):
                continue
            cx, cy = (b.rect.x0 + b.rect.x1) / 2, (b.rect.y0 + b.rect.y1) / 2
            if b.axis == "H":
                off, along = abs(pt.x - cx), abs(pt.y - cy)
            else:
                off, along = abs(pt.y - cy), abs(pt.x - cx)
            if off > lay.act_offaxis or along > lay.act_reach:
                continue
            if "ACT_STEM" not in disabled and not _actuator_stem(
                    horiz, vert, rect, b, lay):
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

def analyse(pc, lay: ValveLayout = LAYOUT, disabled=frozenset(),
            sigs=None) -> dict:
    bodies = find_bodies(pc, lay, disabled)
    attach_actuators(pc, bodies, lay, disabled, sigs)
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


def load_master_rows(path: Path) -> list[dict]:
    """Read the master valve list, which alone carries BODY / ACTUATOR.

    The header row is located by name rather than by index: the master is a
    different template from the two filtered cuts (those put VALVE TYPE in
    column 3 and have no body column at all), and hard-coding a column number
    for a file this module has never seen would be a guess.  A column the
    header does not name is left empty and the row is reported rather than
    filled in.
    """
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    sheet = next((n for n in wb.sheetnames if "valve list" in n.lower()),
                 wb.sheetnames[0])
    ws = wb[sheet]

    want = {
        "no": ("no",),
        "pid_no": ("p&id no", "pid no", "p&id"),
        "body": ("body",),
        "actuator": ("actuator", "act"),
        "operation_mode": ("operation mode", "operation"),
        "valve_type": ("valve type",),
        "qty": ("q'ty", "qty"),
        "system": ("system",),
        "description": ("description",),
    }
    header_row, cols = None, {}
    for i in range(1, min(ws.max_row, 30) + 1):
        found = {}
        for c in range(1, ws.max_column + 1):
            v = ws.cell(i, c).value
            if not isinstance(v, str):
                continue
            norm = " ".join(v.split()).lower()
            for key, names in want.items():
                if key in found:
                    continue
                if norm in names or any(norm.startswith(n) for n in names):
                    found[key] = c
        if "pid_no" in found and ("body" in found or "valve_type" in found):
            header_row, cols = i, found
            break
    if header_row is None:
        raise ValueError(f"{path}: no header row naming P&ID NO. found")

    rows, missing = [], sorted(set(want) - set(cols))
    for i in range(header_row + 1, ws.max_row + 1):
        no = ws.cell(i, cols["no"]).value if "no" in cols else i
        if not isinstance(no, int):
            continue
        rec = {"row": i, "no": no, "missing_columns": missing}
        for key, c in cols.items():
            v = ws.cell(i, c).value
            rec[key] = v if key == "qty" else " ".join(str(v).split()) if v else ""
        rows.append(rec)
    return rows


# How the master's own BODY / ACTUATOR values map onto what this module reads
# off the drawing.  Kept as a table rather than fuzzy matching so that a value
# the master uses and this table does not know shows up as UNMAPPED instead of
# being silently bucketed.
MASTER_BODY = {
    "BUTTERFLY": "BUTTERFLY", "GATE": "GATE", "GLOBE": "GLOBE",
    "BALL": "BALL", "ANGLE": "ANGLE", "CHECK": "CHECK",
    "DIAPHRAGM": "DIAPHRAGM", "NEEDLE": "NEEDLE", "PLUG": "PLUG",
}
MASTER_ACTUATOR = {
    "MOTOR": "MOTOR", "MOTOR OPERATED": "MOTOR", "ELECTRIC": "MOTOR",
    "PNEUMATIC": "PNEUMATIC", "HYDRAULIC": "HYDRAULIC",
    "SELF ACTING": "NONE", "SELF-ACTING": "NONE", "SELF ACTUATED": "NONE",
    "MANUAL": "NONE", "HAND": "NONE",
}


def master_class(row: dict) -> str:
    """The deliverable a master row belongs to, from its own columns."""
    act = MASTER_ACTUATOR.get(str(row.get("actuator", "")).upper().strip())
    body = MASTER_BODY.get(str(row.get("body", "")).upper().strip())
    if act in (None, "NONE"):
        return CLASS_EXCLUDED
    if body == "BUTTERFLY":
        return CLASS_BFV
    if act == "MOTOR":
        return CLASS_MOV
    if act == "HYDRAULIC":
        return CLASS_MOV
    mode = str(row.get("operation_mode", "")).upper()
    return CLASS_XV if ("ON" in mode and "OFF" in mode) else CLASS_CV


# `VALVE TYPE` in the deliverables is an operation mode, not a body type.
# MOV / MOV_I are motor-operated, HOV hydraulic, CV a control valve.
TYPE_ACTUATOR = {str(k): str(v)
                 for k, v in CFG.get("valves.valve_type_actuator").items()}


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


def analyse_all(pages, disabled=frozenset(), sigs=None) -> dict:
    return {pc.page_no: analyse(pc, LAYOUT, disabled, sigs)
            for pc in pages if pc.analysis_scope}


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


# --------------------------------------------------------------------------
# Failure typing
# --------------------------------------------------------------------------
#
# The same discipline the instrument spikes use: name a small closed set of
# reasons, count them, and measure each rule's contribution by switching the
# rule off rather than by arguing about it.
FAILURE_TYPES = (
    "DRAWING_NO_MISMATCH",   # title block and deliverable disagree on the number
    "ANNOTATION_TEXT",       # the page carries review markup changing the count
    "ACT_UNREAD_STROKE",     # enclosure holds strokes matching no letter signature
    "ACT_UNREAD_EMPTY",      # enclosure holds nothing - probably not an actuator
    "ACT_MISSING",           # the deliverable lists more actuated valves than found
    "DELIVERABLE_SCOPE",     # a real actuated valve the deliverable does not list
)


def annotated_pages() -> dict:
    """Pages carrying reviewer markup, read back from the instrument spike."""
    out = {}
    path = OUT / "revision_gap.md"
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| p"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        try:
            out[int(cells[0][1:])] = cells[3]
        except (ValueError, IndexError):
            continue
    return out


def classify_failures(results, cmp_data) -> dict:
    """Attribute every per-drawing delta to one of FAILURE_TYPES."""
    marked = annotated_pages()
    counts = collections.Counter()
    detail = []
    for d in cmp_data["deliverables"]:
        for e in d["entries"]:
            delta = e["detected_actuated"] - e["excel_rows"]
            reasons = []
            if e["detected_unread"]:
                for p in e["pages"]:
                    for b in results[p]["bodies"]:
                        if b.actuator != "UNREAD":
                            continue
                        t = ("ACT_UNREAD_EMPTY" if "no strokes" in b.actuator_evidence
                             else "ACT_UNREAD_STROKE")
                        counts[t] += 1
                        reasons.append(t)
            if any(p in marked for p in e["pages"]):
                counts["ANNOTATION_TEXT"] += 1
                reasons.append("ANNOTATION_TEXT")
            if delta > 0:
                counts["DELIVERABLE_SCOPE"] += delta
                reasons.append(f"DELIVERABLE_SCOPE x{delta}")
            elif delta < 0:
                counts["ACT_MISSING"] += -delta
                reasons.append(f"ACT_MISSING x{-delta}")
            if reasons:
                detail.append({"deliverable": d["tag"], "drawing": e["drawing"],
                               "pages": e["pages"], "delta": delta,
                               "reasons": sorted(set(reasons))})
    for m in cmp_data["missing_drawings"]:
        counts["DRAWING_NO_MISMATCH"] += 1
        detail.append({"deliverable": m["deliverable"], "drawing": m["drawing"],
                       "pages": [], "delta": None,
                       "reasons": ["DRAWING_NO_MISMATCH"]})
    return {"counts": counts, "detail": detail}


def rule_contributions(pages, baseline_cmp) -> list[dict]:
    """Re-run with each rule switched off and report what changes.

    A rule that changes nothing when removed is not carrying the result,
    whatever the code suggests; a rule that changes a lot is where the accuracy
    actually comes from.
    """
    base = {}
    for d in baseline_cmp["deliverables"]:
        for e in d["entries"]:
            base[e["drawing"]] = e["detected_actuated"]
    base_total = sum(base.values())
    rows = []
    for rule in ALL_RULES:
        res = analyse_all(pages, frozenset({rule}))
        cmp_ = compare(res, pages)
        got, exact, moved = {}, 0, 0
        for d in cmp_["deliverables"]:
            for e in d["entries"]:
                got[e["drawing"]] = e["detected_actuated"]
                if e["detected_actuated"] == e["excel_rows"]:
                    exact += 1
                if base.get(e["drawing"]) != e["detected_actuated"]:
                    moved += 1
        bodies = sum(len(r["bodies"]) for r in res.values())
        kinds = collections.Counter(b.kind for r in res.values() for b in r["bodies"])
        rows.append({
            "rule": rule,
            "actuated_total": sum(got.values()),
            "delta_vs_baseline": sum(got.values()) - base_total,
            "drawings_changed": moved,
            "exact_drawings": exact,
            "bodies": bodies,
            "kinds": dict(kinds),
        })
    return rows


# --------------------------------------------------------------------------
# Cross-validation
# --------------------------------------------------------------------------
#
# Same construction as spike/crossval.py on the instrument side: rebuild the
# ruleset using only what the Steam drawings could have taught, then apply it to
# the systems that taught the rest and measure the drop.
#
# What each rule was learned from, tracked honestly:
#
#   WAIST_DISC     legend p2 + p6 (LBA, Steam)          -> available
#   END_BARS       legend p2                            -> available
#   ACT_CLEARANCE  p6 (LBA, Steam)                      -> available
#   VANE_TICK      legend p2 + p26 (PAB, not Steam)     -> NOT available
#   ACT_STEM       p46 (GHC, not Steam)                 -> NOT available
#   STROKE_LETTER  p26 (PAB) + p33 (EGD), neither Steam -> NOT available
#
# The Steam drawings write their motor 'M' into the text layer, so no Steam page
# could have taught the stroke signatures at all.  That is the point of the
# exercise: it says which parts of the accuracy are transferable and which were
# bought by looking at the systems being measured.
STEAM_SYSTEMS = ("LBA", "LBC", "LBG", "LCA", "LCM", "LAB", "MAN", "MAJ")
HOLDOUT_SYSTEMS = ("PGB", "PAB", "EGD")

# Rules no Steam drawing could have supplied.
STEAM_BLIND = frozenset({"VANE_TICK", "ACT_STEM", "STROKE_LETTER"})


def _system_of(drawing: str) -> str:
    lo, hi = CFG.get("formats.system_code_chars")
    seg = drawing.split("-")
    return seg[1][int(lo):int(hi)] if len(seg) > 1 else ""


def crossvalidate(pages) -> dict:
    """Full ruleset vs Steam-only ruleset, scored on the holdout systems."""
    full = compare(analyse_all(pages), pages)
    steam = compare(analyse_all(pages, STEAM_BLIND), pages)

    def score(cmp_, systems):
        rows = []
        for d in cmp_["deliverables"]:
            for e in d["entries"]:
                if systems and _system_of(e["drawing"]) not in systems:
                    continue
                rows.append(e)
        want = sum(e["excel_rows"] for e in rows)
        got = sum(e["detected_actuated"] for e in rows)
        hit = sum(min(e["excel_rows"], e["detected_actuated"]) for e in rows)
        return {
            "drawings": len(rows), "excel": want, "detected": got, "matched": hit,
            "recall": 100.0 * hit / want if want else 0.0,
            "precision": 100.0 * hit / got if got else 0.0,
            "exact": sum(1 for e in rows
                         if e["excel_rows"] == e["detected_actuated"]),
        }

    out = {"blinded": sorted(STEAM_BLIND), "groups": []}
    for name, systems in (("STEAM (training)", STEAM_SYSTEMS),
                          ("HOLDOUT PGB/PAB/EGD", HOLDOUT_SYSTEMS),
                          ("ALL", ())):
        a, b = score(full, systems), score(steam, systems)
        out["groups"].append({
            "group": name, "full": a, "steam_only": b,
            "recall_drop": a["recall"] - b["recall"],
            "precision_drop": a["precision"] - b["precision"],
        })
    return out


# --------------------------------------------------------------------------
# Master valve list measurements (report items A1..A4)
# --------------------------------------------------------------------------

def measure_against_master(results, pages) -> dict:
    """Everything that needs the master's BODY / ACTUATOR / OPERATION MODE.

    Returns `{"available": False, ...}` when the master is not present, rather
    than substituting the two filtered cuts, which carry no body column.
    """
    if not MASTER.exists():
        return {"available": False, "path": str(MASTER)}
    rows = load_master_rows(MASTER)
    idx = page_index()
    missing_cols = rows[0]["missing_columns"] if rows else []

    by_dwg: dict[str, list] = collections.defaultdict(list)
    for r in rows:
        by_dwg[_norm(r["pid_no"])].append(r)

    body_cm = collections.Counter()      # (excel body, detected body)
    class_cm = collections.Counter()     # (excel class, detected class)
    unmapped = collections.Counter()
    per_drawing = []
    for dwg, rs in sorted(by_dwg.items()):
        pgs = [p for k, v in idx.items() if _norm(k) == dwg for p in v]
        det = [b for p in pgs for b in results.get(p, {"bodies": []})["bodies"]]
        # Bodies the deliverables can contain at all: anything with an actuator,
        # plus the self-acting group the master keeps but the drawing shows as a
        # body with nothing on its stem.
        want_body = collections.Counter()
        want_class = collections.Counter()
        for r in rs:
            b = MASTER_BODY.get(str(r.get("body", "")).upper().strip())
            if b is None:
                unmapped["body:" + str(r.get("body", ""))] += 1
            want_body[b or "UNMAPPED"] += 1
            want_class[master_class(r)] += 1
        got_body = collections.Counter()
        got_class = collections.Counter()
        for b in det:
            cls = deliverable_class(b)
            got_class[cls] += 1
            if cls != CLASS_EXCLUDED:
                got_body[b.kind] += 1
        for kind in set(want_body) | set(got_body):
            n = min(want_body[kind], got_body[kind])
            body_cm[(kind, kind)] += n
        for cls in set(want_class) | set(got_class):
            class_cm[(cls, cls)] += min(want_class[cls], got_class[cls])
        per_drawing.append({
            "drawing": dwg, "pages": pgs,
            "master_rows": len(rs),
            "master_bodies": dict(want_body),
            "master_classes": dict(want_class),
            "detected_bodies": dict(got_body),
            "detected_classes": dict(got_class),
        })
    return {
        "available": True,
        "rows": len(rows),
        "missing_columns": missing_cols,
        "unmapped": dict(unmapped),
        "body_confusion": {f"{a}->{b}": n for (a, b), n in body_cm.items()},
        "class_confusion": {f"{a}->{b}": n for (a, b), n in class_cm.items()},
        "per_drawing": per_drawing,
    }


def rollcall(results, tag: str) -> dict:
    """Walk a deliverable row by row and try to place each one on the drawing.

    Rows carry no coordinates, so a row is matched greedily against the
    detections on its own drawing: first one with the same body family *and*
    the same actuator, then one with the right family but a different actuator,
    then nothing.  That is weaker than a positional match, but it is a per-row
    verdict rather than a count comparison, and it names which rows failed.
    """
    entry = next((d for d in DELIVERABLES if d[0] == tag), None)
    if entry is None or not entry[1].exists():
        return {"available": False}
    _, path, family = entry
    idx = page_index()
    rows = load_valve_rows(path)

    pool: dict[str, list] = {}
    for dwg in {_norm(r["pid_no"]) for r in rows}:
        pgs = [p for k, v in idx.items() if _norm(k) == dwg for p in v]
        pool[dwg] = [b for p in pgs
                     for b in results.get(p, {"bodies": []})["bodies"]
                     if b.kind in family and b.actuator not in ("NONE", "UNREAD")]

    out, verdicts = [], collections.Counter()
    for r in rows:
        dwg = _norm(r["pid_no"])
        want = TYPE_ACTUATOR.get(r["valve_type"], "?")
        cand = pool.get(dwg, [])
        pick = next((b for b in cand if b.actuator == want), None)
        verdict = "MATCHED"
        if pick is None:
            pick = cand[0] if cand else None
            verdict = "ACTUATOR_MISMATCH" if pick else "NOT_FOUND"
        if pick is not None:
            cand.remove(pick)
        verdicts[verdict] += 1
        out.append({
            "no": r["no"], "drawing": dwg, "valve_type": r["valve_type"],
            "expected_actuator": want, "verdict": verdict,
            "detected_kind": pick.kind if pick else "",
            "detected_actuator": pick.actuator if pick else "",
            "rect": [round(v, 1) for v in pick.rect] if pick else [],
            "description": r["description"][:60],
        })
    leftover = sum(len(v) for v in pool.values())
    return {"available": True, "tag": tag, "rows": len(rows),
            "verdicts": dict(verdicts), "unclaimed_detections": leftover,
            "items": out}


def class_scores(results) -> dict:
    """Recall / precision per output deliverable, from the sources available.

    BFV and MOV have exact ground truth in the two filtered files (21 and 63
    rows).  CV, XV and the self-acting exclusion have none without the master,
    and are reported as such rather than scored against a proxy.
    """
    scores = {}
    for tag, cls in (("CZI", CLASS_BFV), ("CZH", CLASS_MOV)):
        rc = rollcall(results, tag)
        if not rc.get("available"):
            continue
        want = rc["rows"]
        matched = rc["verdicts"].get("MATCHED", 0)
        got = matched + rc["verdicts"].get("ACTUATOR_MISMATCH", 0) + \
            rc["unclaimed_detections"]
        scores[cls] = {
            "source": tag, "excel_rows": want, "detected": got,
            "matched": matched,
            "recall": 100.0 * matched / want if want else 0.0,
            "precision": 100.0 * matched / got if got else 0.0,
            "verdicts": rc["verdicts"],
            "unclaimed": rc["unclaimed_detections"],
        }
    counted = collections.Counter()
    for r in results.values():
        for b in r["bodies"]:
            counted[deliverable_class(b)] += 1
    scores["_detected_totals"] = dict(counted)
    return scores


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


def write_report(results, cmp_data, path: Path, extra=None) -> None:
    extra = extra or {}
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
    L.append("be named; it is reported rather than guessed.  The two reasons an")
    L.append("enclosure stays unread are different problems, so they are counted")
    L.append("apart:\n")
    unread = collections.Counter()
    for r in results.values():
        for b in r["bodies"]:
            if b.actuator != "UNREAD":
                continue
            unread["ACT_UNREAD_EMPTY" if "no strokes" in b.actuator_evidence
                   else "ACT_UNREAD_STROKE"] += 1
    L.append("| unread reason | count | meaning |")
    L.append("|---|---:|---|")
    L.append(f"| ACT_UNREAD_EMPTY | {unread['ACT_UNREAD_EMPTY']} | enclosure holds "
             "no strokes at all - most likely not an actuator |")
    L.append(f"| ACT_UNREAD_STROKE | {unread['ACT_UNREAD_STROKE']} | strokes are "
             "there but match no signature in `valves.stroked_letters` |")
    L.append("")

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

    fail = extra.get("failures")
    if fail:
        L.append("## 5. Failure types\n")
        L.append("Counted over the drawings the two deliverables name, so the two")
        L.append("`ACT_UNREAD_*` rows are zero here whenever every unread enclosure")
        L.append("in the document sits on some other drawing; section 3 counts those")
        L.append("document-wide.\n")
        L.append("| type | count |")
        L.append("|---|---:|")
        for t in FAILURE_TYPES:
            L.append(f"| {t} | {fail['counts'].get(t, 0)} |")
        L.append("")
        L.append("| deliverable | drawing | pages | delta | reasons |")
        L.append("|---|---|---|---:|---|")
        for d in fail["detail"]:
            L.append(f"| {d['deliverable']} | {d['drawing']} | "
                     f"{','.join(str(x) for x in d['pages'])} | "
                     f"{'' if d['delta'] is None else format(d['delta'], '+d')} | "
                     f"{', '.join(d['reasons'])} |")
        L.append("")

    contrib = extra.get("contributions")
    if contrib:
        L.append("## 6. Rule contributions (`--without`)\n")
        L.append("Each row is the whole document re-run with one rule switched off.")
        L.append("`bodies` is the total body count, which is why a rule can move")
        L.append("nothing in the actuated column and still be load-bearing.\n")
        L.append("| rule removed | actuated | vs baseline | drawings changed "
                 "| exact drawings | bodies |")
        L.append("|---|---:|---:|---:|---:|---:|")
        for r in contrib:
            L.append(f"| {r['rule']} | {r['actuated_total']} | "
                     f"{r['delta_vs_baseline']:+d} | {r['drawings_changed']} | "
                     f"{r['exact_drawings']} | {r['bodies']} |")
        L.append("")

    scores = extra.get("class_scores")
    if scores:
        L.append("## 7. Per-deliverable recall / precision\n")
        L.append("| class | ground truth | rows | detected | matched | recall | precision |")
        L.append("|---|---|---:|---:|---:|---:|---:|")
        for cls in (CLASS_BFV, CLASS_MOV, CLASS_CV, CLASS_XV, CLASS_EXCLUDED):
            sc = scores.get(cls)
            if not sc:
                n = scores["_detected_totals"].get(cls, 0)
                L.append(f"| {cls} | *master needed* | - | {n} | - | - | - |")
                continue
            L.append(f"| {cls} | {sc['source']} | {sc['excel_rows']} | "
                     f"{sc['detected']} | {sc['matched']} | "
                     f"{sc['recall']:.1f}% | {sc['precision']:.1f}% |")
        L.append("")

    for tag, title in (("CZI", "BUTTERFLY roll call (all 21 rows)"),):
        rc = extra.get("rollcall_" + tag)
        if not rc or not rc.get("available"):
            continue
        L.append(f"### {title}\n")
        L.append("| no | drawing | type | expected | detected | verdict | description |")
        L.append("|---:|---|---|---|---|---|---|")
        for it in rc["items"]:
            L.append(f"| {it['no']} | {it['drawing']} | {it['valve_type']} | "
                     f"{it['expected_actuator']} | "
                     f"{it['detected_kind']} {it['detected_actuator']} | "
                     f"{it['verdict']} | {it['description']} |")
        L.append(f"\nUnclaimed butterfly detections on those drawings: "
                 f"**{rc['unclaimed_detections']}** - the file lists only the I&C "
                 f"butterflies, so a drawing may legitimately carry more.\n")

    cv = extra.get("crossval")
    if cv:
        L.append("## 8. Cross-validation - Steam-only ruleset\n")
        L.append(f"Rules no Steam drawing could have taught, switched off: "
                 f"`{'`, `'.join(cv['blinded'])}`.\n")
        L.append("| group | | drawings | excel | detected | matched | recall | precision | exact |")
        L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
        for g in cv["groups"]:
            for label, key in (("full", "full"), ("steam-only", "steam_only")):
                d = g[key]
                L.append(f"| {g['group']} | {label} | {d['drawings']} | {d['excel']} "
                         f"| {d['detected']} | {d['matched']} | {d['recall']:.1f}% "
                         f"| {d['precision']:.1f}% | {d['exact']} |")
            L.append(f"| | **drop** | | | | | **-{g['recall_drop']:.1f}pp** "
                     f"| **-{g['precision_drop']:.1f}pp** | |")
        L.append("")

    master = extra.get("master")
    if master and master.get("available"):
        L.append("## 9. Against the master valve list\n")
        L.append(f"{master['rows']} rows read from `{MASTER.name}`.")
        if master["missing_columns"]:
            L.append(f"Columns the header did not name: "
                     f"`{'`, `'.join(master['missing_columns'])}` - left empty, "
                     f"not guessed.")
        if master["unmapped"]:
            L.append(f"Values this module has no mapping for: {master['unmapped']}")
        L.append("")
        L.append("| body | matched |")
        L.append("|---|---:|")
        for k, v in sorted(master["body_confusion"].items()):
            L.append(f"| {k} | {v} |")
        L.append("")
    elif master:
        L.append("## 9. Against the master valve list\n")
        L.append(f"`{master['path']}` is not present in this checkout, so the")
        L.append("gate-vs-globe confusion matrix, the self-acting exclusion count")
        L.append("and the CV / XV split are still unmeasured. Section 10 below")
        L.append("states what that leaves open. Drop the file in and re-run:")
        L.append("nothing else needs changing - `load_master_rows` locates its")
        L.append("columns by header name.\n")

    L.append("## 10. What this comparison cannot measure\n")
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


DEPS_DOC = """# 밸브 규칙 프로젝트 종속 값 인벤토리 (스파이크 4)

`out/project_deps.md` 와 같은 기준입니다.

| 판정 | 의미 |
|---|---|
| `LEGEND` | Symbol & Legend(p2~p5)에서 유도 가능 → 코드 유지 |
| `PROJECT` | 도면/NOTES/Excel 양식에서 유도 → config |
| `UNKNOWN` | 출처 불명 → 조사 필요, 튜닝 금지 |

**집계: `LEGEND` 12건 / `PROJECT` 8건 / `UNKNOWN` 5건 (총 25건)**

판정 근거는 전부 실측입니다. "아마 그럴 것 같다"는 UNKNOWN 으로 넘겼습니다.

---

## LEGEND — 코드 유지 (12건)

| # | 항목 | 위치 | 근거 (실측) |
|---|---|---|---|
| VL1 | **나비넥타이 몸체 규칙** (교차 대각선 2 + 양끝 바) | `find_bodies` | 범례 p2 `LINE VALVES` GATE 행: 대각선 2개가 같은 bbox `(895.9,551.3,912.9,561.2)`, 양끝 세로바 `x=895.9`·`912.9`. 크기 17.0×9.9 |
| VL2 | **글로브 = 허리 중앙 원반** | `_waist_object` | 같은 표 GLOBE 행: 나비넥타이는 GATE 와 동일, 추가로 원 `(900.9,592.4,908.0,599.5)` 7.1×7.1, 중심이 몸체 중심과 **정확히 일치**. 7.1/9.9 = **0.72** |
| VL3 | **니들 = 허리의 좁은 쐐기** (종횡비로 원반과 구분) | `_wedge_at_waist`, `disc_aspect` 하한 0.70 | NEEDLE 행의 채움 `(903.3,830.5,905.6,837.6)` = 2.3×7.1, **종횡비 0.32**. 글로브 원반은 1.00. 0.70 은 두 실측값 사이 |
| VL4 | **다이어프램 = 몸체 위 열린 호** | `_arc_above` | DIAPHRAGM 행: 몸체 상단 `y0=926.1`, 그 위에 곡선 `(897.4,923.8,911.5,926.9)` — **2.3pt 돌출** |
| VL5 | **버터플라이 vs 볼 = 베인 틱** | `_vane_ticks` | BUTTERFLY 행: 원 6.1 + 짧은 사선 2개(각 길이 **3.0**), 중심 기준 정반대. BALL 행: 원 7.2, **틱 없음**. p26 실측도 동일(원 6.0, 틱 3.05×2) |
| VL6 | **체크 = 반쪽 나비넥타이** (대각선 1개) | `find_bodies` | CHECK 행에 대각선이 1개뿐 |
| VL7 | **채움 = 몸체 종류가 아니라 개폐 상태** | `Body.state`, `_triangles_filled` | 범례 p2 `VALVE OPERATION`: 빈 나비넥타이 = OPEN DURING NORMAL OPERATION, 검은 나비넥타이 = CLOSED (둘 다 `ALL VALVES EXCEPT BUTTERFLY`), 빈 원 / 검은 원 = 버터플라이 전용 OPEN / CLOSED. 검은 나비넥타이도 대각선 2개는 그대로 있음(`fs` 4장 + `s` 대각선 2) |
| VL8 | **양끝 바 간격 범위** | `bar_reach` 3.4 / `bar_min` 1.1 (반지름 배수) | BUTTERFLY 6.1 원에 바 ±8.5 → **2.79 반지름**, BALL 7.2 원에 바 ±8.5 → **2.36 반지름** |
| VL9 | **액추에이터 어휘** (원 `M` / 상자 `H` / 원 `E/H` / 상자 `S` / 돔·실린더 / `I/P` / 상자 `X` / T바) | `ACT_LETTERS` | 범례 p3 `VALVES ACTUATORS` 가 8종을 라벨과 함께 직접 그림 |
| VL10 | **액추에이터 울타리 크기 하한** | `act_box` 하한 9.0 | 범례 p3 모터·E/H 원 **14.2×14.2**, 유압/솔레노이드/X 상자 **14.2×34.0**. 글로브 허리 원반은 7.1 → 9.0 이 둘 사이 |
| VL11 | **액추에이터는 줄기로 몸체에 연결된다** | `_actuator_stem` | 범례 p3 의 8행 전부, p4 `VALVE BODY WITH ACTUATOR` 의 MOV 도 예외 없이 줄기를 그림 |
| VL12 | **자력식은 별도 그룹** (NONE ≠ SELF ACTING) | `deliverable_class` | 범례 p3 이 `SELF-ACTUATED DEVICES`(PSV/PRV/BPRV)를 고유 심볼로 따로 둠. 줄기에 아무것도 없는 것은 수동 밸브지 자력식이 아님 |

---

## PROJECT — config 이동 완료 (8건)

전부 `config/project_alnouf1.yaml` 의 `valves:` 블록으로 옮겼습니다.

| # | 항목 | config 키 | 근거 |
|---|---|---|---|
| V1 | **액추에이터 도달 거리** 90.0 | `valves.actuator_reach` | 범례가 아니라 도면 실측: p6·p30 은 줄기 26.9pt, p33 은 최대 80pt. 범례는 고정 거리 하나만 그리고 범위를 말하지 않음 |
| V2 | **줄기 축 이탈 허용** 12.0 | `valves.actuator_offaxis` | 위와 동일. 작도 관행 |
| V3 | **태그 버블 도달 거리** 190.0 | `valves.tag_reach` | p6 MOV 버블 실측. 지시선은 길이 제한이 없으므로 규칙이 아니라 관행 |
| V4 | **밸브 Excel 시트·열** (`3.0_Valve List`, NO=1, P&ID=2, TYPE=3, Q'ty=4, SYSTEM=5, DESC=12) | `valves.excel` | 발주처 양식. 계기 리스트(`2.0_Instrument List`)와 시트명도 열 순서도 다름 |
| V5 | **납품서 ↔ 몸체 계열** (CZI=BUTTERFLY, CZH=GATE/GLOBE/**BALL**) | `valves.deliverables` | 각 파일 헤더의 `DESCRIPTION` 줄. CZH 는 제목이 GATE & GLOBE 지만 볼 몸체 MOV 도 담고 있어 계열에 BALL 을 포함해야 함 |
| V6 | **`VALVE TYPE` 어휘** MOV / MOV_I / HOV / CV | `valves.valve_type_actuator` | 이 문자열들은 범례에 없음. 납품서 표기이고 몸체가 아니라 구동 방식 |
| V7 | **CV vs XV 태그 분리** | `valves.cv_tags`, `valves.xv_tags` | 태그 어휘 자체는 범례(p3 CONTROL DEVICE, p4 차단 태그)지만 **두 납품서로 가르는 기준**은 발주처 관행 |
| V8 | **스트로크 글자 서명** (M 4획 / H 3획 / X 2획) | `valves.stroked_letters` | **범례는 M·H·S·X 를 텍스트로 인쇄합니다.** 즉 범례만 봐서는 이 회사 CAD 스트로크 폰트가 글자를 어떻게 조립하는지 알 수 없습니다. 서명은 p26(H)·p33(M) 도면에서 읽었으므로 PROJECT |

---

## UNKNOWN — 조사 필요, 이번에 튜닝하지 않음 (5건)

| # | 항목 | 위치 | 왜 UNKNOWN 인가 |
|---|---|---|---|
| VU1 | **세그먼트 길이 상한** 60.0 | `seg_span` | 범례 최대 밸브 치수는 34.0(유압 실린더 상자). 60 은 여유값이고 유도 근거가 없음. 성능 필터라 결과에 영향은 없지만 근거는 없음 |
| VU2 | **바 커버리지 여유** 1.2 / **끝단 허용** 0.8 | `bar_cover`, `bar_axis_tol` | 1pt 미만의 작도 정밀도 여유. 범례에서 유도되지 않음 |
| VU3 | **허리 중심 허용 오차** 2.0 | `centre_tol` | 범례 글로브 원반은 중심 오차 **0.0**. 2.0 이 어디서 왔는지 근거 없음 |
| VU4 | **범례 실측값 주변 창 폭** (`body_short`, `body_ratio`, `waist_ratio`, `tick_span`, `tick_reach`) | `ValveLayout` | 창의 **중심값**은 전부 범례 실측(17.0×9.9, 0.72, 3.0 …)이지만 **폭**은 유도된 것이 아님. 다른 축척으로 그린 도면을 통과시키려는 의도지만 검증되지 않음 |
| VU5 | **닫힘 판정 면적 임계** 0.30 | `_triangles_filled` | 검은 나비넥타이의 `fs` 4장이 몸체 bbox 의 몇 %를 덮는지 범례에서 계산하지 않았음 |

**UNKNOWN 은 이번에도 손대지 않았습니다.** 계기 쪽 UNKNOWN 5건과 함께 Phase 3 조사
대상입니다.

---

## 승수 예외 1건 — 보류 유지 (NEEDS_REVIEW)

`D00P-10PGB10-M05-0004`(p38) `(PLANT COMMON)` 건은 그대로 둡니다. 귀속 판정에
필요한 설비 점선 박스 검출이 `brk_max_mark`(UNKNOWN) 튜닝을 요구하므로 건드리지
않았고, `out/qty_report.md` 의 NEEDS_REVIEW 로 남습니다. 영향 Q'ty 3 / 1120 = 0.3%.
"""


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
    ap.add_argument("--without", default="",
                    help="disable rules for this run, e.g. ACT_STEM,VANE_TICK")
    ap.add_argument("--contributions", action="store_true",
                    help="re-run once per rule and report each one's contribution")
    ap.add_argument("--crossval", action="store_true",
                    help="score a Steam-only ruleset on PGB/PAB/EGD")
    ap.add_argument("--deps", default="",
                    help="write the valve project-dependency inventory here")
    args = ap.parse_args()

    doc, pages = pidcache.load_pages(PDF)
    if args.pages:
        want = {int(x) for x in args.pages.split(",")}
        pages = [p for p in pages if p.page_no in want]

    disabled = frozenset(x.strip() for x in args.without.split(",") if x.strip())
    unknown = disabled - set(ALL_RULES)
    if unknown:
        ap.error(f"unknown rule(s): {', '.join(sorted(unknown))}; "
                 f"known: {', '.join(ALL_RULES)}")
    if disabled:
        print("rules disabled:", ", ".join(sorted(disabled)))
    results = analyse_all(pages, disabled)

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
    if args.deps:
        Path(args.deps).write_text(DEPS_DOC, encoding="utf-8")
        print("wrote", args.deps)
    if args.report:
        extra = {
            "failures": classify_failures(results, cmp_data),
            "class_scores": class_scores(results),
            "rollcall_CZI": rollcall(results, "CZI"),
            "master": measure_against_master(results, pages),
        }
        if args.contributions:
            extra["contributions"] = rule_contributions(pages, cmp_data)
        if args.crossval:
            extra["crossval"] = crossvalidate(pages)
        write_report(results, cmp_data, Path(args.report), extra)
        print("wrote", args.report)
        print(json.dumps({k: v for k, v in extra.items()
                          if k in ("class_scores", "crossval")}, indent=1)[:3000])
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
