"""Equipment on the drawings, found by the shapes the legend draws for it.

The client's Description names equipment far more often than it names a line -
`GT FUEL OIL FORWARDING PUMP A SUCTION STRAINER DIFFERENTIAL PRESSURE` is about a
pump, not about a pipe - so this finds the equipment first and the pipe second.

Everything about a shape is measured off legend page 2's EQUIPMENT table at run
time.  The table is laid out as a column of labels with each symbol drawn to their
left, so:

  * the label column is the x offset that repeats down the page - the table aligns
    its own labels, and that alignment is the measurement
  * a row is a run of label lines closer together than the table's own row pitch
  * the symbol for a row is every path in the band left of the label column,
    minus the paths that are glyph outlines of the words printed there (found by
    the page's own text boxes, not by a size rule)
  * the *anchor* is that symbol's largest path, with its width, height and the
    kinds of items it is drawn from

Then a drawing is scanned for paths matching an anchor.  No shape name is written
here and no dictionary of equipment types exists: the names are whatever the
legend prints, and a shape the legend does not draw is not equipment.

This module does not use `pipe_graph`.  Connectivity was measured last round at a
13% trace rate, and the two-axis rule this serves - equipment first, line second -
is geometric on both axes.
"""

from __future__ import annotations

import collections
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import legend_rules  # noqa: E402

# The legend heading that marks the table.
EQUIPMENT_HEADING = "EQUIPMENT"


@dataclass
class EquipSymbol:
    """One row of the legend's equipment table."""

    name: str
    page_no: int
    anchor: tuple = ()          # (w, h) of the row's largest path
    kinds: tuple = ()           # sorted (item kind, count) of that path
    footprint: tuple = ()       # (w, h) of the whole symbol
    paths: int = 0

    def key(self) -> tuple:
        return (round(self.anchor[0], 1), round(self.anchor[1], 1), self.kinds)


@dataclass
class Equipment:
    """One instance found on a drawing."""

    kind: str                   # the legend's own words
    rect: tuple
    page_no: int
    label: str = ""
    label_rect: tuple = ()
    label_distance: float = 0.0
    count_note: str = ""        # `(3X50%)` and the like, kept apart from the name
    ordinal: str = ""           # A / B / C within a labelled group
    group: int = -1
    evidence: dict = field(default_factory=dict)


def derive_symbols(pages, cfg=None) -> list:
    """Read the equipment table off whichever legend sheet prints it.

    The sheet lays four tables side by side and names them in one heading row at
    the top - `EQUIPMENT | EQUIPMENT (CONT.) | PROCESS PIPING (CONT.) | LINE VALVES
    (CONT.)` - so a column is claimed by the heading token that sits above it, and
    only the columns headed EQUIPMENT are read.  Both the column positions and the
    headings come off the page; nothing is positioned by hand.
    """
    pc = _equipment_page(pages)
    if pc is None:
        return []
    words = [(r, t) for r, t in pc.words]
    heading_y = min((r.y0 for r, t in words if t.upper() == EQUIPMENT_HEADING),
                    default=None)
    if heading_y is None:
        return []
    heading = sorted((r.x0, t) for r, t in words if abs(r.y0 - heading_y) < 6)

    # The label columns: x offsets the tables repeat down the page.
    xs = collections.Counter(round(r.x0, 1) for r, _t in words
                             if r.y0 > heading_y + 20)
    columns = sorted(x for x, n in xs.items() if n >= 10)
    if not columns:
        return []
    # The heading row on this sheet reads `EQUIPMENT | EQUIPMENT (CONT.) | PROCESS
    # PIPING (CONT.) | ...`, but the column under the second heading is not
    # equipment at all - its labels are `BURIED PIPE`, `CONCENTRIC REDUCER`,
    # `BLIND FLANGE`.  The sheet's own headings and its content disagree, so only
    # the column headed EQUIPMENT *without* a continuation marker is read, and the
    # disagreement is reported rather than papered over (see `heading_mismatch`).
    out = []
    for i, label_x in enumerate(columns):
        left = columns[i - 1] if i else 0.0
        titles = [t for x, t in heading if left < x <= label_x]
        if not titles or titles[0].upper() != EQUIPMENT_HEADING:
            continue
        if len(titles) > 1 and titles[1].upper().startswith("(CONT"):
            continue
        out += _table_rows(pc, words, label_x, left, heading_y)
    return out


def heading_mismatch(pages) -> list:
    """Columns the heading row calls EQUIPMENT (CONT.) but that carry other rows.

    Reported so the skip above is visible: it is a fact about this legend sheet,
    not a rule about legends.
    """
    pc = _equipment_page(pages)
    if pc is None:
        return []
    words = [(r, t) for r, t in pc.words]
    heading_y = min((r.y0 for r, t in words if t.upper() == EQUIPMENT_HEADING),
                    default=None)
    heading = sorted((r.x0, t) for r, t in words if abs(r.y0 - heading_y) < 6)
    xs = collections.Counter(round(r.x0, 1) for r, _t in words
                             if r.y0 > heading_y + 20)
    columns = sorted(x for x, n in xs.items() if n >= 10)
    out = []
    for i, label_x in enumerate(columns):
        left = columns[i - 1] if i else 0.0
        titles = [t for x, t in heading if left < x <= label_x]
        if (len(titles) > 1 and titles[0].upper() == EQUIPMENT_HEADING
                and titles[1].upper().startswith("(CONT")):
            labels = [t for r, t in words if abs(r.x0 - label_x) < 1.0][:12]
            out.append({"label_x": label_x, "heading": " ".join(titles[:2]),
                        "first_labels": labels})
    return out


def _equipment_page(pages):
    """The legend sheet whose top heading row names an EQUIPMENT column."""
    best = None
    for pc in pages:
        if not pc.analysis_scope:
            continue
        tops = [r.y0 for r, t in pc.words if t.upper() == EQUIPMENT_HEADING]
        if not tops:
            continue
        y = min(tops)
        row = [t.upper() for r, t in pc.words if abs(r.y0 - y) < 6]
        if row.count(EQUIPMENT_HEADING) >= 2 and (best is None or y < best[0]):
            best = (y, pc)
    return best[1] if best else None


def _table_rows(pc, words, label_x, left, heading_y) -> list:
    """Every labelled symbol in one column of the table."""
    # A label line is every word on the baseline that *starts* at the column, so
    # `PLATE TYPE HEAT EXCHANGER` stays four words rather than becoming its first.
    by_y = collections.defaultdict(list)
    for r, t in words:
        if r.x0 >= label_x - 1.0 and r.y0 > heading_y + 20:
            by_y[round((r.y0 + r.y1) / 2, 1)].append((r.x0, t))
    label_lines = []
    for y in sorted(by_y):
        items = sorted(by_y[y])
        if abs(items[0][0] - label_x) < 1.0:
            label_lines.append((y, " ".join(t for _x, t in items)))
    if len(label_lines) < 4:
        return []
    # Row pitch: rows are separated by more than the line spacing inside a row, and
    # both come from the table itself.
    gaps = sorted(label_lines[i + 1][0] - label_lines[i][0]
                  for i in range(len(label_lines) - 1))
    line_gap = gaps[0]
    pitch = gaps[len(gaps) // 2]
    split = (line_gap + pitch) / 2

    rows, cur = [], [label_lines[0]]
    for item in label_lines[1:]:
        if item[0] - cur[-1][0] <= split:
            cur.append(item)
        else:
            rows.append(cur)
            cur = [item]
    rows.append(cur)

    # Glyph outlines: paths that sit inside a printed word's own box.
    boxes = [r for r, _t in words]

    def is_glyph(b):
        return any(w.x0 - 1 <= b.x0 and b.x1 <= w.x1 + 1
                   and w.y0 - 1 <= b.y0 and b.y1 <= w.y1 + 1 for w in boxes)

    drawings = [(d["bbox"], collections.Counter(i[0] for i in d["items"]))
                for d in pc.drawings()]
    out = []
    for row in rows:
        y0 = min(y for y, _t in row) - pitch / 2
        y1 = max(y for y, _t in row) + pitch / 2
        name = " ".join(t for _y, t in row).strip()
        band = [(b, k) for b, k in drawings
                if left < b.x0 and b.x1 < label_x - 2 and b.y0 >= y0 and b.y1 <= y1
                and b.width > 2 and b.height > 2 and not is_glyph(b)]
        if not band:
            continue
        anchor, kinds = max(band, key=lambda bk: bk[0].width * bk[0].height)
        out.append(EquipSymbol(
            name=name, page_no=pc.page_no,
            anchor=(round(anchor.width, 1), round(anchor.height, 1)),
            kinds=tuple(sorted(kinds.items())),
            footprint=(round(max(b.x1 for b, _k in band) - min(b.x0 for b, _k in band), 1),
                       round(max(b.y1 for b, _k in band) - min(b.y0 for b, _k in band), 1)),
            paths=len(band)))
    return out


def find(pc, symbols, drawing_area, slack: float = None) -> list:
    """Equipment instances on one drawing: paths matching a legend anchor.

    `slack` defaults to the stroke index's own coordinate allowance, which is the
    tolerance this project already uses for "the same coordinate drawn twice".
    """
    slack = legend_rules.INDEX_SLACK if slack is None else slack
    by_key = collections.defaultdict(list)
    for s in symbols:
        if s.anchor:
            by_key[s.kinds].append(s)
    out = []
    for d in pc.drawings():
        b = d["bbox"]
        if not (drawing_area[0] <= b.x0 and b.x1 <= drawing_area[2]
                and drawing_area[1] <= b.y0 and b.y1 <= drawing_area[3]):
            continue
        kinds = tuple(sorted(collections.Counter(i[0] for i in d["items"]).items()))
        for s in by_key.get(kinds, ()):
            if (abs(b.width - s.anchor[0]) <= slack
                    and abs(b.height - s.anchor[1]) <= slack):
                out.append(Equipment(
                    kind=s.name, page_no=pc.page_no,
                    rect=(round(b.x0, 1), round(b.y0, 1),
                          round(b.x1, 1), round(b.y1, 1)),
                    evidence={"legend": s.name, "anchor": list(s.anchor),
                              "kinds": [list(k) for k in s.kinds]}))
                break
    return _dedupe(out)


def _dedupe(items) -> list:
    """One instance per place: a symbol drawn from two identical paths is one."""
    out, seen = [], set()
    for e in items:
        key = (round(e.rect[0]), round(e.rect[1]), round(e.rect[2]), round(e.rect[3]))
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


# --------------------------------------------------------------------------
# Equipment on a drawing, by the words the drawing prints
# --------------------------------------------------------------------------
#
# Matching the legend's *shapes* on the sheets was measured and does not work: the
# legend draws its horizontal centrifugal pump 40.5 x 38.5 and the sheets draw the
# same pump 46.2 x 44.0, and across 20 pages the size ratios between legend
# symbols and same-signature paths scatter (x2.00, x0.84, x0.42, x1.61 ...) with
# no single scale - the matches at those ratios are instrument bubbles and valve
# circles, not equipment.  So shapes are derived and reported, and instances are
# found by the labels the drawing prints instead, which it does 116 times for
# `PUMP` alone across 30 sheets.

# A count note the drawing writes beside an equipment name.  Stripped from the
# name because the client never writes one: `(3X50%)` and its kind appear in 0 of
# the 557 finished Description lines.
COUNT_NOTE = re.compile(r"\(\s*\d+\s*X\s*\d+\s*%?\s*\)")

# A line the drawing opens with its own preposition is a route, not a name: `TO
# HRSG#12 BD TANK` says where the pipe goes.  Taking it as equipment put an
# ordinal and a position word on a destination - `TO CLEAN DRAIN TANK C INLET` -
# which the client never writes, so those lines are left to the line axis.
ROUTE_RE = re.compile(r"^(TO|FROM)\b")


def derive_vocabulary(symbols, cfg=None, extra=()) -> dict:
    """`{word: source}` - the nouns that name equipment.

    Two sources, both stated:

      LEGEND  every word of the equipment table's own labels.  Always available,
              because the legend sheet ships with the drawings
      CLIENT  nouns the client's finished list puts an ordinal after
              (`... PUMP A ...`, `... COOLER B ...`).  Measured, not chosen: PUMP
              76, COOLER 48, TANK 26, HEATER 9, HEX 9, EXCHANGER 9, SKID 8, CEP 3.
              They live in `config description.equipment_words` because a real run
              has no finished list to derive them from, and `COOLER` matters - the
              drawings print it 50 times and the legend never names it
    """
    out = {}
    for s in symbols:
        for w in re.findall(r"[A-Z]+", s.name.upper()):
            if len(w) >= 3:
                out.setdefault(w, "LEGEND")
    words = list(extra)
    if cfg is not None:
        words += list((cfg.data.get("description") or {}).get("equipment_words") or [])
    for w in words:
        out.setdefault(str(w).upper(), "CLIENT")
    return out


def find_labels(pc, vocab: dict, drawing_area) -> list:
    """Equipment named on one drawing: text lines carrying an equipment noun.

    A line is the words sharing a baseline, joined in reading order - the drawing
    writes `GT FUEL OIL FORWARDING PUMPS (3X50%)` as one line and that whole line
    is the name.
    """
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
        if ROUTE_RE.match(text.upper()):
            continue
        head = _head_noun(text, vocab)
        if not head:
            continue
        x0 = min(r.x0 for _x, r, _t in items)
        y0 = min(r.y0 for _x, r, _t in items)
        x1 = max(r.x1 for _x, r, _t in items)
        y1 = max(r.y1 for _x, r, _t in items)
        name, note = clean_label(text)
        out.append(Equipment(
            kind=head, page_no=pc.page_no,
            rect=(round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)),
            label=name, label_rect=(round(x0, 1), round(y0, 1),
                                    round(x1, 1), round(y1, 1)),
            count_note=note,
            evidence={"raw": text, "noun": head, "noun_source": vocab.get(head, "")}))
    return out


def _head_noun(text: str, vocab: dict) -> str:
    """The equipment noun in a line, taking the last one - names are head-final."""
    words = re.findall(r"[A-Z]+", text.upper())
    for w in reversed(words):
        if w in vocab:
            return w
        if w.endswith("S") and w[:-1] in vocab:
            return w[:-1]
    return ""


def clean_label(text: str) -> tuple:
    """`(name, count note)`, by the two rules the client's own list settles.

    * a duty note is dropped - `(3X50%)` appears in 0 of 557 Description lines
    * a plural head noun becomes singular - the client writes PUMP 138 / PUMPS 0,
      TANK 59 / TANKS 0, STRAINER 13 / STRAINERS 0, HEATER 9 / HEATERS 0
    """
    note = " ".join(COUNT_NOTE.findall(text)).strip()
    name = COUNT_NOTE.sub(" ", text)
    name = " ".join(name.split())
    words = name.split()
    if words and words[-1].upper().endswith("S") and len(words[-1]) > 3:
        words[-1] = words[-1][:-1]
    return " ".join(words), note


def group(items) -> list:
    """Number equipment that shares a name: A, B, C down the page or across it.

    The axis is the group's own spread, not an assumption: a column of pumps is
    numbered top to bottom, a row of them left to right.  The count note is used
    as a check, never as the source - `(3X50%)` says three, and if three were
    found the numbering covers them.
    """
    by_name = collections.defaultdict(list)
    for e in items:
        by_name[e.label.upper()].append(e)
    for name, members in by_name.items():
        if len(members) < 2:
            continue
        xs = [(e.rect[0] + e.rect[2]) / 2 for e in members]
        ys = [(e.rect[1] + e.rect[3]) / 2 for e in members]
        vertical = (max(ys) - min(ys)) >= (max(xs) - min(xs))
        members.sort(key=lambda e: (e.rect[1], e.rect[0]) if vertical
                     else (e.rect[0], e.rect[1]))
        for i, e in enumerate(members):
            e.ordinal = chr(ord("A") + i) if i < 26 else ""
            e.group = id(members) % 100000
            e.evidence["ordinal_axis"] = "top-to-bottom" if vertical else "left-to-right"
            e.evidence["group_size"] = len(members)
    return items


if __name__ == "__main__":
    import pidcache
    import projectconfig

    cfg = projectconfig.load()
    _doc, _pages = pidcache.load_pages(Path("data/pid_total.pdf"))
    syms = derive_symbols(_pages, cfg)
    print(f"legend equipment symbols: {len(syms)}")
    for s in syms:
        print(f"  {s.name[:44]:<46} anchor {s.anchor[0]:6.1f}x{s.anchor[1]:<6.1f} "
              f"{dict(s.kinds)}  paths {s.paths}")
