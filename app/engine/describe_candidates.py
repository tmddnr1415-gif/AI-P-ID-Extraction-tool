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


def collect(pc, rows, equipment, drawing_area, pos, limit: float = None) -> dict:
    """`{row_key: [candidate, ...]}` for the instruments on one page.

    `rows` is `[(key, rect, type)]`; `equipment` is what `describe_equipment.find_labels`
    found on this page, already grouped and numbered.
    """
    conns = _connector_lines(pc, drawing_area)
    labels = _line_text(pc, drawing_area)
    out = {}
    for key, rect, _type in rows:
        cx = (rect[0] + rect[2]) / 2
        cy = (rect[1] + rect[3]) / 2
        cands = []
        # --- axis 1: equipment ------------------------------------------
        for e in equipment:
            d = max(abs((e.rect[0] + e.rect[2]) / 2 - cx),
                    abs((e.rect[1] + e.rect[3]) / 2 - cy))
            if limit and d > limit:
                continue
            side = side_of(rect, e.rect)
            cands.append({
                "text": e.label, "kind": EQUIPMENT, "distance": round(d, 1),
                "direction": side, "rect": list(e.rect),
                "equipment": {"noun": e.kind, "ordinal": e.ordinal,
                              "count_note": e.count_note,
                              "position_word": position_word(e, side, pos),
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
        cands.sort(key=lambda c: (c["kind"] != EQUIPMENT, c["distance"]))
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


def instrument_ordinals(rows, cands) -> dict:
    """A, B, C for instruments of one type that share a subject.

    The client puts an ordinal in two places, and which one it uses is settled by
    its own lines: after an equipment noun 172 times (`PUMP A SUCTION ...`), and at
    the very end 117 times (`... PRESSURE A`).  The first is the equipment's
    number and comes from `describe_equipment.group`; this is the second - it
    numbers instruments that would otherwise read identically.

    Ordering is by the drawing's own layout, the same rule the equipment grouping
    uses: down the page when the group is a column, across when it is a row.
    """
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
        for i, (key, _r) in enumerate(members):
            if i < 26:
                out[key] = chr(ord("A") + i)
    return out
