"""What an instrument's Description is about: equipment first, line second.

The reviewer settled the rule this implements:

    is there equipment near the instrument?
      yes -> describe it against the equipment
               left of it  = INLET / SUCTION
               right of it = OUTLET / DISCHARGE
               several of the same name -> A, B, C down the page
      no  -> describe it against the line: the FROM / TO connector text
               several instruments of one type on a line -> a suffix tells them apart

    equipment wins when both are present.  `GT FUEL OIL FORWARDING PUMP A SUCTION
    STRAINER DIFFERENTIAL PRESSURE` is written against the pump, not the pipe.

Which words each side takes is not assumed either; it is counted in the client's
own 557 finished lines (`config description.position_words`):

    PUMP  -> SUCTION 45 / DISCHARGE 70      (115 of 115, no counter-example)
    other -> INLET   27 / OUTLET    30      (57 of 57: WATERBOX, EXCHANGER, SKID,
                                             HEATER, HEX, COOLER, CONDENSER)

This module does not use `pipe_graph`.  Both axes are geometric: equipment is
found by the words the drawing prints (`describe_equipment`), and the line axis
reads the `TO` / `FROM` text the drawing prints beside the run the instrument sits
on.  Nothing is ranked by preference - every candidate carries its distance, its
side and where it came from, and the caller grades it.
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import describe_equipment as de  # noqa: E402
import legend_rules  # noqa: E402

# Where a candidate came from.
EQUIPMENT = "EQUIPMENT"      # a named piece of equipment on this sheet
CONNECTOR = "CONNECTOR"      # a `TO ...` / `FROM ...` line
PIPE_LABEL = "PIPE_LABEL"    # text on the run beside the instrument
UNIT_MARK = "UNIT_MARK"      # `HRSG#11`
NAMED_KINDS = (EQUIPMENT, CONNECTOR)

UNIT_MARK_CHAR = "#"
CONNECTOR_RE = re.compile(r"^(TO|FROM)\b(.+)$")

# The sides, in the drawing's own axes.
LEFT, RIGHT, ABOVE, BELOW = "LEFT", "RIGHT", "ABOVE", "BELOW"


def derive_position_words(cfg=None) -> dict:
    """`{noun class: {side: word}}`, from the counts recorded in config."""
    words = ((cfg.data.get("description") or {}).get("position_words")
             if cfg is not None else None) or {}
    pump = words.get("pump") or {}
    other = words.get("other") or {}
    return {
        "pump": {LEFT: str(pump.get("left") or "SUCTION"),
                 RIGHT: str(pump.get("right") or "DISCHARGE")},
        "other": {LEFT: str(other.get("left") or "INLET"),
                  RIGHT: str(other.get("right") or "OUTLET")},
        "pump_nouns": tuple(str(w).upper() for w in (words.get("pump_nouns")
                                                     or ("PUMP", "CEP", "BFP"))),
    }


def side_of(instr_rect, equip_rect) -> str:
    """Which side of the equipment the instrument sits on, by their centres."""
    ix = (instr_rect[0] + instr_rect[2]) / 2
    iy = (instr_rect[1] + instr_rect[3]) / 2
    ex = (equip_rect[0] + equip_rect[2]) / 2
    ey = (equip_rect[1] + equip_rect[3]) / 2
    if abs(ix - ex) >= abs(iy - ey):
        return RIGHT if ix > ex else LEFT
    return BELOW if iy > ey else ABOVE


def position_word(equipment, side: str, pos: dict) -> str:
    """`SUCTION` / `DISCHARGE` for a pump, `INLET` / `OUTLET` for anything else."""
    if side not in (LEFT, RIGHT):
        return ""
    cls = "pump" if equipment.kind.upper() in pos["pump_nouns"] else "other"
    return pos[cls][side]


def distance_limit(distances, quantile: float = 0.9) -> float:
    """How far equipment may be and still be this instrument's subject.

    Taken from the measured distribution of instrument-to-nearest-equipment
    distances on this document rather than chosen, and reported with the
    distribution so the cut is visible.
    """
    if not distances:
        return 0.0
    ordered = sorted(distances)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * quantile))], 1)


def local_runs(pc, style) -> list:
    """The pipe runs on one page, merged - one step of connectivity, no graph.

    This is deliberately not `pipe_graph`: nothing here walks from junction to
    junction.  It answers one question per instrument - which run does its leader
    land on - and the run's own extent is then used to see what it touches.  The
    minimum run length is the legend's, untouched.
    """
    horiz, vert = legend_rules.stroke_index(pc.segments(), min_len=1.0)
    slack = style["join_slack"]
    out = []
    for axis, index in (("H", horiz), ("V", vert)):
        for coord, lo, hi in _merge(index, style["min_run"], slack):
            out.append((axis, coord, lo, hi))
    # leaders are shorter than a pipe run: an instrument bubble hangs off one
    leaders = []
    for axis, index in (("H", horiz), ("V", vert)):
        for coord, lo, hi in _merge(index, style["dash_len"], slack):
            leaders.append((axis, coord, lo, hi))
    return out, leaders


def _merge(index, min_len, slack) -> list:
    """Collinear pieces unioned into runs.  Local: one page, one pass."""
    out = []
    for coord, pieces in index.items():
        pieces = sorted(pieces)
        lo, hi = pieces[0]
        for a, b in pieces[1:]:
            if a - hi <= slack:
                hi = max(hi, b)
            else:
                if hi - lo >= min_len:
                    out.append((coord, lo, hi))
                lo, hi = a, b
        if hi - lo >= min_len:
            out.append((coord, lo, hi))
    return out


def _run_touches_rect(run, rect, slack) -> bool:
    axis, coord, lo, hi = run
    if axis == "H":
        return (rect[1] - slack <= coord <= rect[3] + slack
                and lo - slack <= rect[2] and hi + slack >= rect[0])
    return (rect[0] - slack <= coord <= rect[2] + slack
            and lo - slack <= rect[3] and hi + slack >= rect[1])


def derive_equipment_reach(pages, equipment_by_page, style) -> object:
    """How far an equipment label sits from the pipe run that serves it, measured.

    A pipe run touches the equipment *symbol*; the name is printed beside it, and
    the gap between the two is a habit of this drawing set, not a number anyone
    can pick.  So it is measured the same way `pipe_graph.derive_connector_reach`
    measures a connector's flag: every equipment label in the document, the
    distance to its nearest run, and the high end of that distribution.  A label
    printed further out than that stays unconnected and the caller falls back to
    distance, which is the honest outcome.
    """
    seen = []
    for pc in pages:
        equipment = equipment_by_page.get(pc.page_no) or ()
        if not equipment:
            continue
        runs, _leaders = local_runs(pc, style)
        for e in equipment:
            best = None
            for axis, coord, lo, hi in runs:
                if axis == "H":
                    d = max(max(e.rect[1] - coord, coord - e.rect[3], 0.0),
                            max(lo - e.rect[2], e.rect[0] - hi, 0.0))
                else:
                    d = max(max(e.rect[0] - coord, coord - e.rect[2], 0.0),
                            max(lo - e.rect[3], e.rect[1] - hi, 0.0))
                if best is None or d < best:
                    best = d
            if best is not None:
                seen.append(best)
    if not seen:
        return legend_rules.Derived(
            values={"equipment_reach": (style or {}).get("join_slack", 0.8)},
            source="FALLBACK",
            note="no equipment label and pipe run share a page")
    seen.sort()
    reach = seen[int(len(seen) * 0.9)]
    hist = collections.Counter(int(d // 10) * 10 for d in seen)
    return legend_rules.Derived(
        values={"equipment_reach": round(reach, 1)},
        source="MEASURED",
        note=f"the label is printed beside the symbol, so this is measured from "
             f"{len(seen)} equipment labels in this document",
        evidence={"labels": len(seen), "min": round(seen[0], 1),
                  "median": round(seen[len(seen) // 2], 1),
                  "p90": round(reach, 1), "max": round(seen[-1], 1),
                  "histogram_10pt": dict(sorted(hist.items()))})


def subject_by_connection(rect, runs, leaders, equipment, slack,
                          reach: float = None) -> tuple:
    """`(equipment, how)` - the equipment the instrument's own run reaches.

    Two steps and no more, which is what "local" means here:

      1. the run the instrument sits on, or the run its leader lands on
      2. the equipment whose label that run touches

    A run reaching several pieces of equipment picks the nearest along the run;
    a run reaching none returns nothing and the caller falls back to distance.
    """
    mine = [r for r in runs if _run_touches_rect(r, rect, slack)]
    how = "on the run"
    if not mine:
        # follow the leader one step: a short run with one end inside the symbol
        for axis, coord, lo, hi in leaders:
            p0 = (lo, coord) if axis == "H" else (coord, lo)
            p1 = (hi, coord) if axis == "H" else (coord, hi)
            ins = [_inside(p, rect, slack) for p in (p0, p1)]
            if ins[0] == ins[1]:
                continue
            far = p1 if ins[0] else p0
            box = (far[0] - slack, far[1] - slack, far[0] + slack, far[1] + slack)
            mine = [r for r in runs if _run_touches_rect(r, box, slack)]
            if mine:
                how = "leader"
                break
    if not mine:
        return None, ""
    cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    best, best_d = None, None
    # The run has to reach the *symbol*; the label is printed beside it, so the
    # tolerance here is the measured label-to-run gap, not the stroke join slack.
    near = slack if reach is None else reach
    for e in equipment:
        for run in mine:
            if _run_touches_rect(run, e.rect, near):
                d = max(abs((e.rect[0] + e.rect[2]) / 2 - cx),
                        abs((e.rect[1] + e.rect[3]) / 2 - cy))
                if best_d is None or d < best_d:
                    best, best_d = e, d
    return (best, how) if best else (None, "")


def _inside(p, rect, slack) -> bool:
    return (rect[0] - slack <= p[0] <= rect[2] + slack
            and rect[1] - slack <= p[1] <= rect[3] + slack)


def between_symbol(rect, equip_rect, components, slack: float = 0.0) -> str:
    """A component the drawing names on the path between instrument and equipment.

    Strictly between the two, in the band they share - nothing is searched for in
    open space.  Returns "" when the drawing prints no such word, which on p33 is
    every case (see `describe_equipment.derive_component_words`).
    """
    ix, iy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    ex, ey = (equip_rect[0] + equip_rect[2]) / 2, (equip_rect[1] + equip_rect[3]) / 2
    lo_x, hi_x = sorted((ix, ex))
    lo_y, hi_y = sorted((iy, ey))
    best, best_d = "", None
    for c in components:
        cx = (c["rect"][0] + c["rect"][2]) / 2
        cy = (c["rect"][1] + c["rect"][3]) / 2
        if not (lo_x - slack <= cx <= hi_x + slack
                and lo_y - slack <= cy <= hi_y + slack):
            continue
        d = max(abs(cx - ix), abs(cy - iy))
        if best_d is None or d < best_d:
            best, best_d = c["text"], d
    return best


def collect(pc, rows, equipment, drawing_area, pos, limit: float = None,
            style: dict = None, components=(), reach: float = None,
            between_types=()) -> dict:
    """`{row_key: [candidate, ...]}` for the instruments on one page.

    `rows` is `[(key, rect, type)]`; `equipment` is what `describe_equipment.find_labels`
    found on this page, already grouped and numbered.
    """
    conns = _connector_lines(pc, drawing_area)
    labels = _line_text(pc, drawing_area)
    slack = (style or {}).get("join_slack", 0.8)
    runs, leaders = local_runs(pc, style) if style else ([], [])
    out = {}
    between_types = frozenset(str(t).upper() for t in between_types)
    for key, rect, _type in rows:
        # Only the types that write an intermediate symbol are offered one.  The
        # client names one on 13 of its 557 lines and every one of them is a PDIT
        # reading `SUCTION STRAINER`; on any other type the word is something it
        # never wrote (config description.between_symbol_types).
        wants_between = (not between_types
                         or str(_type).upper() in between_types)
        cx = (rect[0] + rect[2]) / 2
        cy = (rect[1] + rect[3]) / 2
        cands = []
        # --- axis 1: equipment ------------------------------------------
        # The run this instrument sits on decides first; distance only breaks a
        # tie or fills in when no run reaches any equipment.
        connected, how = (subject_by_connection(rect, runs, leaders, equipment,
                                                slack, reach)
                          if style else (None, ""))
        for e in equipment:
            d = max(abs((e.rect[0] + e.rect[2]) / 2 - cx),
                    abs((e.rect[1] + e.rect[3]) / 2 - cy))
            if limit and d > limit:
                continue
            side = side_of(rect, e.rect)
            cands.append({
                "text": e.label, "kind": EQUIPMENT, "distance": round(d, 1),
                "connected": e is connected, "connected_by": how if e is connected else "",
                "direction": side, "rect": list(e.rect),
                "equipment": {"noun": e.kind, "ordinal": e.ordinal,
                              "count_note": e.count_note,
                              "position_word": position_word(e, side, pos),
                              "between": (between_symbol(rect, e.rect, components)
                                          if wants_between else ""),
                              "evidence": e.evidence},
            })
        # --- axis 2: the line -------------------------------------------
        for rct, text in conns:
            d = max(abs((rct[0] + rct[2]) / 2 - cx), abs((rct[1] + rct[3]) / 2 - cy))
            cands.append({"text": text, "kind": CONNECTOR, "distance": round(d, 1),
                          "direction": side_of(rect, rct), "rect": list(rct)})
        for rct, text in labels:
            d = max(abs((rct[0] + rct[2]) / 2 - cx), abs((rct[1] + rct[3]) / 2 - cy))
            if UNIT_MARK_CHAR in text:
                cands.append({"text": text, "kind": UNIT_MARK, "distance": round(d, 1),
                              "direction": side_of(rect, rct), "rect": list(rct)})
        # connected equipment first, then equipment by distance, then the line
        cands.sort(key=lambda c: (c["kind"] != EQUIPMENT,
                                  not c.get("connected"), c["distance"]))
        out[key] = cands[:12]
    return out


def _connector_lines(pc, drawing_area) -> list:
    """`TO ...` / `FROM ...` lines, which is how this drawing set names a route."""
    out = []
    for rect, text in _lines(pc, drawing_area):
        if CONNECTOR_RE.match(text.upper()):
            out.append((rect, text))
    return out


def _line_text(pc, drawing_area) -> list:
    return _lines(pc, drawing_area)


def _lines(pc, drawing_area) -> list:
    lines = collections.defaultdict(list)
    for r, t in pc.words:
        if not (drawing_area[0] <= r.x0 and r.x1 <= drawing_area[2]
                and drawing_area[1] <= r.y0 and r.y1 <= drawing_area[3]):
            continue
        lines[round((r.y0 + r.y1) / 2, 1)].append((r.x0, r, t))
    out = []
    for y in sorted(lines):
        items = sorted(lines[y], key=lambda it: it[0])
        text = " ".join(t for _x, _r, t in items).strip()
        if not text:
            continue
        rect = (round(min(r.x0 for _x, r, _t in items), 1),
                round(min(r.y0 for _x, r, _t in items), 1),
                round(max(r.x1 for _x, r, _t in items), 1),
                round(max(r.y1 for _x, r, _t in items), 1))
        out.append((rect, text))
    return out


def instrument_ordinals(rows, cands, equipment=()) -> dict:
    """`{row_key: (ordinal, where)}` - A, B, C, and which half of the line it sits in.

    The client puts an ordinal in two places and its own lines settle which:

      middle, after the equipment noun - 172 lines.  `GT FUEL OIL FORWARDING PUMP A
        SUCTION STRAINER DIFFERENTIAL PRESSURE`: three pumps, one instrument each,
        so the letter numbers the *pump*
      end, after the variable - 117 lines.  `GT FUEL OIL FORWARDING PUMP DISCHARGE
        PRESSURE A`: one pump set, two instruments on the common discharge, so the
        letter numbers the *instrument*

    What separates them is measurable on the drawing: the equipment label carries a
    duty note (`3X50%`, `2X100%`) saying how many units it covers.  When a type has
    exactly that many instruments on the equipment, each belongs to one unit and the
    letter goes in the middle; otherwise it numbers instruments and goes at the end.

    Ordering is the drawing's own layout, the same rule the equipment grouping uses.
    """
    counts = {}
    for e in equipment:
        n = _count_of(e.count_note)
        if n:
            counts[e.label.upper()] = n
    groups = collections.defaultdict(list)
    for key, rect, type_ in rows:
        best = next((c for c in (cands.get(key) or [])
                     if c["kind"] in NAMED_KINDS), None)
        subject = (best or {}).get("text", "")
        groups[(type_, subject)].append((key, rect))
    out = {}
    for (_type, subject), members in groups.items():
        if len(members) < 2 or not subject:
            continue
        xs = [(r[0] + r[2]) / 2 for _k, r in members]
        ys = [(r[1] + r[3]) / 2 for _k, r in members]
        vertical = (max(ys) - min(ys)) >= (max(xs) - min(xs))
        members.sort(key=lambda kr: (kr[1][1], kr[1][0]) if vertical
                     else (kr[1][0], kr[1][1]))
        where = "MIDDLE" if counts.get(subject.upper()) == len(members) else "END"
        for i, (key, _r) in enumerate(members):
            if i < 26:
                out[key] = (chr(ord("A") + i), where)
    return out


def _count_of(note: str) -> int:
    """How many units a duty note covers: `3X50%` -> 3, `2X100%` -> 2."""
    m = re.search(r"(\d+)\s*X\s*\d+\s*%", str(note).upper())
    return int(m.group(1)) if m else 0
