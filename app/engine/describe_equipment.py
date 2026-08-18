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
COUNT_NOTE = re.compile(r"\(?\s*\d+\s*X\s*\d+\s*%\s*\)?")
# Whatever else the drawing puts in brackets - a size, a capacity - the
# client leaves out: 0 of its 557 lines carry a bracket.
BRACKET = re.compile(r"\([^)]*\)?")
# `FEEDWATER PUMP FOR HRSG UNIT #11` names a pump; the client writes 1 `FOR` in
# its 557 lines, so the tail is where the drawing says which unit, not the name.
FOR_TAIL = re.compile(r"\bFOR\b.*$")

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


def derive_component_words(pages) -> dict:
    """The line components the legend names, for the middle of a description.

    The client writes `... PUMP A SUCTION STRAINER DIFFERENTIAL PRESSURE` - a thing
    that sits between the instrument and the equipment - in 13 of its 557 lines, and
    the words it uses (`STRAINER`) are ones the legend's own tables print.  So the
    vocabulary is read off the legend rather than listed here.

    Measured limit, reported rather than worked around: the drawings print
    `STRAINER` on 6 sheets (13, 22, 30, 32, 49, 55) and *not* on p33, which is
    where the client writes it six times.  There it is drawn as a symbol with no
    text, and matching the legend's strainer shape returns glyph-sized noise - the
    same failure this round measured for equipment shapes.  So this finds the ones
    the drawing names and reports the rest as unavailable.
    """
    out = {}
    for pc in pages:
        if not pc.analysis_scope:
            continue
        for _r, t in pc.words:
            u = t.upper().strip(".,()")
            if u in ("STRAINER", "FILTER", "TRAP"):
                out.setdefault(u, "LEGEND" if pc.page_no <= 5 else "DRAWING")
    return out


def find_components(pc, words: dict, drawing_area) -> list:
    """Where the drawing prints one of those component words."""
    out = []
    for r, t in pc.words:
        u = t.upper().strip(".,()")
        base = u[:-1] if u.endswith("S") and u[:-1] in words else u
        if base not in words:
            continue
        if not (drawing_area[0] <= r.x0 and r.x1 <= drawing_area[2]):
            continue
        out.append({"text": base,
                    "rect": (round(r.x0, 1), round(r.y0, 1),
                             round(r.x1, 1), round(r.y1, 1))})
    return out


def derive_aliases(standard: dict, choice: dict) -> dict:
    """`{printed form: the form to write}` for the sets a person has confirmed.

    Two layers meet here.  `standard` is trade vocabulary - on any power plant a
    feedwater pump is a boiler feedwater pump - and is meant to be carried to the
    next project unchanged, so it fixes no direction.  `choice` is this client's
    habit, measured on its own list, and names which member of a set it writes.
    A set with no choice recorded is not applied at all.
    """
    out = {}
    for name, forms in (standard or {}).items():
        want = str((choice or {}).get(name) or "").upper().strip()
        if not want:
            continue
        for form in forms:
            f = " ".join(str(form).upper().split())
            if f and f != want:
                out[f] = want
    return out


def apply_alias(name: str, aliases: dict) -> tuple:
    """`(name, the form it was written under)` - only when the alias is the head.

    A short form in front of another noun is a modifier, not the thing itself, and
    the client writes it differently there: it names the pump `BOILER FEED WATER
    PUMP` on all 33 lines where the pump is the subject, and `BFP` on all 24 where
    something else is - `BFP A/B COOLER`, `BFP A/B MOTOR COOLER`.  Rewriting a
    modifier as well cost 1.5 F1 when it was measured, so the match has to end the
    name.  The longest match wins.
    """
    up = " ".join(str(name).upper().split())
    for form in sorted(aliases, key=len, reverse=True):
        if re.search(rf"(?<![A-Z]){re.escape(form)}$", up):
            return (up[:len(up) - len(form)] + aliases[form]).strip(), form
    return name, ""


def _modifier_ok(text: str, head: str, modifiers: dict) -> bool:
    """Whether the word in front of a noun is one the client uses with it.

    Some nouns name equipment only in company: the client writes `BYPASS VALVE`
    54 times, `LETDOWN` 3, `CONTROL` 3, `MODULATING` 2 - and never `BRETHER`,
    `OFF`, `VENT` or `SHUTOFF`, which is what the drawings put in front of VALVE
    42, 59, 29 and 34 times.  The same for HEADER: `DISCHARGE` 16, `STEAM` 6,
    `SEAL` 4, `RING` 3 against the drawings' `DRAIN HEADER` 39.  Without this the
    word pulls in pipe annotations that outrank the real equipment by distance -
    measured: `WASTE OIL TANK LEVEL` became `FUEL OIL SUPPLY DRAIN HEADER LEVEL`.
    """
    allowed = modifiers.get(head)
    if not allowed:
        return True
    words = re.findall(r"[A-Z]+", text.upper())
    for i, w in enumerate(words):
        if w == head and i and words[i - 1] in allowed:
            return True
    return False


def find_labels(pc, vocab: dict, drawing_area, line_pitch: float = None,
                modifiers: dict = None, aliases: dict = None) -> list:
    """Equipment named on one drawing, as whole label blocks.

    The drawings write an equipment name over several baselines - p33 prints
    `AUX. FUEL OIL` / `FORWARDING PUMP` / `2X100%` as three lines of one label -
    so lines are joined into a block when they sit within the page's own line
    pitch of each other and their horizontal extents overlap.  Taking a single
    line instead produced `FORWARDING PUMP` where the client writes `AUX FUEL OIL
    FORWARDING PUMP`, which is the difference between a name and a fragment.
    """
    modifiers = {str(k).upper(): {str(w).upper() for w in v}
                 for k, v in (modifiers or {}).items()}
    lines = collections.defaultdict(list)
    for r, t in pc.words:
        if not (drawing_area[0] <= r.x0 and r.x1 <= drawing_area[2]
                and drawing_area[1] <= r.y0 and r.y1 <= drawing_area[3]):
            continue
        lines[round((r.y0 + r.y1) / 2, 1)].append((r.x0, r, t))
    # Two labels printed side by side share a baseline.  What separates them is
    # not a gap - splitting on the word gap was tried and measured, and it cut
    # `#10 ST HYDRAULIC OIL COOLER` in half - it is repetition: a drawing that
    # prints four coolers in a row prints `#10 ST` four times, so a word that has
    # already appeared in the line being built starts the next label.
    # The baseline pitch is measured before any splitting: it is the gap between
    # printed lines, and counting it over the split pieces collapses it to a word
    # gap and stops the block joining that reads a name off three baselines.
    pitch = line_pitch if line_pitch else _line_pitch(
        [_row(y, sorted(lines[y], key=lambda it: it[0])) for y in sorted(lines)])
    rows = []
    for y in sorted(lines):
        pieces = _split_repeats(sorted(lines[y], key=lambda it: it[0]))
        starts = {p[0][2].upper() for p in pieces if p}
        for piece in pieces:
            for part in _split_starts(piece, starts):
                rows.append(_row(y, part))

    blocks = _blocks(rows, pitch)

    out = []
    for b in blocks:
        text = " ".join(b["texts"]).strip()
        if ROUTE_RE.match(text.upper()):
            continue
        head = _head_noun(text, vocab)
        if not head:
            continue
        if not _modifier_ok(text, head, modifiers):
            continue
        name, note = clean_label(text)
        name, alias_of = apply_alias(name, aliases or {})
        rect = (round(b["x0"], 1), round(b["y0"], 1),
                round(b["x1"], 1), round(b["y1"], 1))
        out.append(Equipment(
            kind=head, page_no=pc.page_no, rect=rect, label=name, label_rect=rect,
            count_note=note,
            evidence={"raw": text, "noun": head, "noun_source": vocab.get(head, ""),
                      "alias_of": alias_of,
                      "lines": len(b["texts"]), "line_pitch": round(pitch, 1)}))
    return out


def _split_repeats(items) -> list:
    """One baseline into label-sized pieces, cut where a word repeats.

    Two labels printed side by side share a baseline.  What separates them is not
    a gap - splitting on the word gap was measured and it cut `#10 ST HYDRAULIC
    OIL COOLER` in half - it is repetition: a drawing that prints four coolers in
    a row prints `#10 ST` four times, so a word already used in the piece being
    built starts the next one.
    """
    out, run, seen = [], [], set()
    for it in items:
        word = it[2].upper()
        if word in seen:
            out.append(run)
            run, seen = [], set()
        run.append(it)
        seen.add(word)
    if run:
        out.append(run)
    return out


def _split_starts(items, starts) -> list:
    """Cut again at a word that opens another label on the same baseline.

    `#10` opens three of the four coolers, so the `#10` sitting inside a fourth
    piece is that label's start and not part of the piece before it.
    """
    cut = [i for i in range(1, len(items)) if items[i][2].upper() in starts]
    edges = [0] + cut + [len(items)]
    return [items[a:b] for a, b in zip(edges, edges[1:]) if items[a:b]]


def _row(y, items) -> dict:
    """One printed line: its text and the box the words actually occupy."""
    return {"y": y,
            "text": " ".join(t for _x, _r, t in items).strip(),
            "x0": min(r.x0 for _x, r, _t in items),
            "x1": max(r.x1 for _x, r, _t in items),
            "y0": min(r.y0 for _x, r, _t in items),
            "y1": max(r.y1 for _x, r, _t in items)}


def derive_line_pitch(pages, drawing_area) -> float:
    """The set's own baseline spacing, measured over every sheet at once.

    Measuring it per page is not safe: a sparse sheet such as p37 prints only 36
    lines and its most frequent gap is 2.0 pt, which is a rounding artefact rather
    than a line pitch, and a pitch that small stops a name being read off the three
    baselines it is printed on.  The drawings are one set in one text style, so the
    gap that repeats across the whole document is the measurement.
    """
    heights = collections.Counter()
    ys_by_page = []
    for pc in pages:
        ys = set()
        for r, _t in pc.words:
            if not (drawing_area[0] <= r.x0 and r.x1 <= drawing_area[2]
                    and drawing_area[1] <= r.y0 and r.y1 <= drawing_area[3]):
                continue
            heights[round(r.y1 - r.y0, 1)] += 1
            ys.add(round((r.y0 + r.y1) / 2, 1))
        ys_by_page.append(sorted(ys))
    if not heights:
        return 12.0
    # A line cannot be closer to the next than the letters are tall, so the text's
    # own height is the floor.  Without it the mode is 0.1 pt - two words on one
    # baseline whose centres round apart - which is not a line pitch.
    floor = max(heights.items(), key=lambda kv: kv[1])[0]
    gaps = collections.Counter()
    for ys in ys_by_page:
        for a, b in zip(ys, ys[1:]):
            g = round(b - a, 1)
            if floor <= g < 60:
                gaps[g] += 1
    return max(gaps.items(), key=lambda kv: (kv[1], -kv[0]))[0] if gaps else 12.0


def _line_pitch(rows) -> float:
    """One page's baseline spacing: the gap that repeats between text lines."""
    gaps = collections.Counter()
    for i in range(len(rows) - 1):
        g = round(rows[i + 1]["y"] - rows[i]["y"], 1)
        if 0 < g < 60:
            gaps[g] += 1
    return max(gaps.items(), key=lambda kv: (kv[1], -kv[0]))[0] if gaps else 12.0


def _blocks(rows, pitch) -> list:
    """Consecutive lines of one label: stacked, centred on each other, not routes.

    Horizontal *overlap* alone was too loose on a dense sheet - it glued a size
    label to the route line under it (`DN25 TO EDG DAY TANK`).  A label's lines are
    centred on one another, so the test is on their centres, and a route line never
    joins anything.
    """
    out = []
    for r in rows:
        joined = False
        if ROUTE_RE.match(r["text"].upper()):
            out.append({"texts": [r["text"]], "x0": r["x0"], "x1": r["x1"],
                        "y0": r["y0"], "y1": r["y1"], "y": r["y"]})
            continue
        for b in out:
            if ROUTE_RE.match(b["texts"][0].upper()):
                continue
            centre_r = (r["x0"] + r["x1"]) / 2
            centre_b = (b["x0"] + b["x1"]) / 2
            narrower = min(r["x1"] - r["x0"], b["x1"] - b["x0"])
            if (0 < r["y"] - b["y"] <= pitch * 1.5
                    and abs(centre_r - centre_b) <= narrower / 2):
                b["texts"].append(r["text"])
                b["x0"] = min(b["x0"], r["x0"])
                b["x1"] = max(b["x1"], r["x1"])
                b["y0"] = min(b["y0"], r["y0"])
                b["y1"] = max(b["y1"], r["y1"])
                b["y"] = r["y"]
                joined = True
                break
        if not joined:
            out.append({"texts": [r["text"]], "x0": r["x0"], "x1": r["x1"],
                        "y0": r["y0"], "y1": r["y1"], "y": r["y"]})
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
    """`(name, count note)`, by the rules the client's own list settles.

    * a duty note is dropped - `(3X50%)` appears in 0 of 557 Description lines
    * a plural head noun becomes singular - the client writes PUMP 138 / PUMPS 0,
      TANK 59 / TANKS 0, STRAINER 13 / STRAINERS 0, HEATER 9 / HEATERS 0
    * anything else in brackets goes with it - the client writes no bracket at
      all: `(` appears in 0 of the 557 lines, so the drawing's `(5m3)` size note
      is not something the client would have written down
    * an abbreviation loses its full stop - `.` appears in 0 of the 557 lines,
      against `AUX.` on the drawing, so `AUX. FUEL OIL` is written `AUX FUEL OIL`
    * a `FOR ...` tail goes with them - the client writes one in 1 of its 557
      lines, against the drawings' `FEEDWATER PUMP FOR HRSG UNIT #11`, where the
      name of the pump is the part in front
    """
    note = " ".join(COUNT_NOTE.findall(text)).strip()
    # Brackets go first, whole: a caption can carry two of them - `(A/B)` and
    # `(2X50% PER HRSG)` - and taking the duty note out first splits the second
    # one, leaving `PER HRSG)` glued to the name.
    name = BRACKET.sub(" ", text)
    name = COUNT_NOTE.sub(" ", name)
    name = name.replace(".", "")
    name = FOR_TAIL.sub(" ", name)
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
