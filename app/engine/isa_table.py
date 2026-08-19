"""The ISA letter table, read off the legend sheet that prints it.

Legend page 3 carries the identification matrix: a `FIRST LETTER` column listing
each letter against the variable it measures (`T  TEMPERATURE`, `PD  PRESSURE
DIFFERENTIAL`, ...) and a `SUCCEEDING LETTERS` block whose columns name what the
following letter does (`E  PRIMARY ELEMENT`, `T  TRANSMITTER`, ...).

Why this module exists: the client's Description column is written in those very
words - `UNIT #11 HP STEAM **PRESSURE** A`, `... **LEVEL** HIGH HIGH` - so the
word for a tag's variable is not something to guess at or keep in a dictionary
here.  The drawing set states it, on a sheet this tool already reads, and that is
where it is taken from.  Nothing in this file interprets prose: it reads a table
by its own column geometry.

No LLM, no hardcoded letter dictionary.  A letter the table does not print stays
unknown, and callers are expected to leave the word out rather than invent it.
"""

from __future__ import annotations

import collections
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import legend_rules  # noqa: E402

# The words the table prints as its own headings.
FIRST_ROW = "FIRST"
LETTER_ROW = "LETTER"
SUCCEEDING_ROW = "SUCCEEDING"

# The table joins alternative readings of one letter with this word: `PRESSURE OR
# VACUUM`, `MOISTURE OR HUMIDITY`, `DENSITY (MASS) OR SPECIFIC GRAVITY`.  Keeping
# it lets the alternatives stay apart instead of being run together into a phrase
# the legend never prints.
ALT = "OR"


@dataclass
class IsaTable:
    """Letter -> the words the legend prints for it."""

    first: dict = field(default_factory=dict)        # 'T' -> ('TEMPERATURE',)
    succeeding: dict = field(default_factory=dict)   # 'E' -> ('PRIMARY', 'ELEMENT')
    page_no: int = 0
    source: str = "LEGEND"
    note: str = ""

    def readings_for(self, tag: str) -> list:
        """Every reading the table prints for this tag's first letter.

        `PRESSURE OR VACUUM` is two readings, not a two-word phrase, so they are
        kept apart: `[('PRESSURE',), ('VACUUM',)]`.  A caller measuring where a word
        came from should accept any of them; a caller writing a line takes the
        first, which is the one the table names first.
        """
        for n in (2, 1):
            head = tag[:n].upper()
            if head in self.first:
                out, cur = [], []
                for w in self.first[head]:
                    if w == ALT:
                        if cur:
                            out.append(tuple(cur))
                        cur = []
                    else:
                        cur.append(w)
                if cur:
                    out.append(tuple(cur))
                return out
        return []

    def words_for(self, tag: str) -> tuple:
        """The variable words for an instrument tag, longest letter match first.

        `PDIT` reads as `PD` + `IT` and `TIT` as `T` + `IT`, so the two-letter
        first-letter entries the legend prints (`PD`) are tried before the single
        letters.

        Only the *first* letter's variable is returned.  The succeeding-letter
        columns are read and reported, but they are not used here: the legend heads
        the `E` column with four words (`PRIMARY ELEMENT` over `SENSING DEVICE`),
        and this client's Description writes one of them (`ELEMENT`, in 18 of its
        557 lines).  Choosing which of the four to keep is not something the legend
        answers, and choosing it by what matches the client's list would be fitting
        to the answer key.  So the word is left out and the miss is counted.
        """
        readings = self.readings_for(tag)
        return readings[0] if readings else ()

    def as_dict(self) -> dict:
        return {"page_no": self.page_no, "source": self.source, "note": self.note,
                "first": {k: list(v) for k, v in sorted(self.first.items())},
                "succeeding": {k: list(v) for k, v in sorted(self.succeeding.items())}}


def derive(pages, cfg=None) -> IsaTable:
    """Read the identification matrix off whichever legend sheet prints it."""
    pc = legend_rules._page_with(pages, f"{FIRST_ROW} {LETTER_ROW}")
    if pc is None:
        return IsaTable(source="MISSING",
                        note=f"no legend sheet prints '{FIRST_ROW} {LETTER_ROW}'")
    head = None
    for r, t in pc.words:
        if t != FIRST_ROW:
            continue
        row = [w for _r, w in pc.words
               if abs((_r.y0 + _r.y1) / 2 - (r.y0 + r.y1) / 2) < 6]
        if LETTER_ROW in row:
            head = r
            break
    if head is None:
        return IsaTable(source="MISSING",
                        note=f"'{FIRST_ROW} {LETTER_ROW}' heading not found")

    # Which column is the FIRST LETTER column.
    #
    # Not by where its tokens fall.  Taking the leftmost cluster of x offsets is
    # what a reader does looking at one sheet, and it breaks on the next one: a
    # sheet that prints its border grid letters outside the frame offers them as a
    # column, and a sheet that sets a `SYMBOL` sub-heading over the column offers
    # that too, 11 pt from the letters it is supposed to find.
    #
    # By what the column *is* instead.  The matrix has one row per first letter and
    # prints each letter once; a succeeding-letter column carries an entry only on
    # the rows where that combination exists, so its set of letters is a subset of
    # the first letters.  The FIRST LETTER column is therefore the column with the
    # most distinct entries, and it is the only one that never repeats one.  Both
    # are properties of the table's own meaning, so there is no tolerance here to
    # widen and nothing tuned to either document: on AL NOUF1's legend the winner
    # holds 25 distinct against 20-21 for the next columns, on SADARA's 25 against
    # 6-21, and the 25 are the same 25 letters.
    succ = next((r for r, t in pc.words if t == SUCCEEDING_ROW), None)
    right_limit = succ.x0 if succ is not None else head.x1 + 700
    body = [(r, t) for r, t in pc.words
            if r.y0 > head.y1 and r.x0 < right_limit]
    if not body:
        return IsaTable(source="MISSING",
                        note=f"nothing printed under the {FIRST_ROW} "
                             f"{LETTER_ROW} heading on p{pc.page_no}")
    column = _letter_column(body)
    if column is None:
        return IsaTable(source="MISSING",
                        note=f"no column under {FIRST_ROW} {LETTER_ROW} on "
                             f"p{pc.page_no} enumerates a set of first letters")
    # A text line belongs to a letter when the line's centre falls inside that
    # letter's own line box.  Not a tolerance: the letter and its meaning are set
    # on one baseline, so the meaning's centre lies within the letter's ascender-
    # to-descender span by construction.  It has to be a span rather than an equal
    # test because the two are different words - on SADARA's sheet `A` centres at
    # 273.2 and `ANALYSIS` at 274.1, a 0.9 pt difference that an exact key misses
    # and that no amount of rounding fixes reliably.
    letter_box = [(r.y0, r.y1, t) for r, t in column]
    letter_x1 = max(r.x1 for r, _t in column)

    def letter_at(y):
        return next((t for y0, y1, t in letter_box if y0 <= y <= y1), None)

    lines = collections.defaultdict(list)
    for r, t in body:
        lines[round((r.y0 + r.y1) / 2, 1)].append((r.x0, r.x1, t))

    # The meaning column starts where the first letter's cell ends: the leftmost
    # word printed to the right of the letter column on a row that has a letter.
    meaning_lo = min((x0 for y, items in lines.items() if letter_at(y)
                      for x0, _x1, t in items
                      if x0 > letter_x1 and any(c.isalpha() for c in t)),
                     default=None)
    if meaning_lo is None:
        return IsaTable(source="MISSING",
                        note=f"the matrix on p{pc.page_no} prints no meaning "
                             f"beside its first letters")

    # Where the meaning column ends: the matrix repeats each row's letter at the
    # head of its first tag column (`A ANALYSIS ... A E ...`), so the leftmost such
    # repeat marks the edge.  Read off the table's own content rather than set as a
    # width, because a meaning runs to several words (`PRESSURE DIFFERENTIAL`,
    # `MOISTURE OR HUMIDITY`) and cutting it short silently loses them.
    meaning_hi = None
    for y, items in lines.items():
        letter = letter_at(y)
        if letter is None:
            continue
        for x0, _x1, t in sorted(items):
            if x0 > meaning_lo + 8 and t.upper().startswith(letter) and len(t) <= 5:
                meaning_hi = x0 if meaning_hi is None else min(meaning_hi, x0)
                break
    if meaning_hi is None:
        return IsaTable(source="MISSING",
                        note=f"the matrix on p{pc.page_no} never repeats a row's "
                             f"letter, so the meaning column has no measurable end")

    # Letter rows, and the meaning lines that wrap without a letter of their own.
    keyed = []
    for y in sorted(lines):
        items = sorted(lines[y])
        letter = letter_at(y)
        words = [t for x0, _x1, t in items
                 if meaning_lo - 8 <= x0 < meaning_hi - 8
                 and any(c.isalpha() for c in t)
                 # a parenthetical gloss - `(MASS)`, `(EMF)`, `(MANUAL INITIATED)` -
                 # explains the variable rather than naming it
                 and "(" not in t and ")" not in t]
        if letter or words:
            keyed.append({"y": y, "letter": letter, "words": words})

    # `DENSITY (MASS) OR SPECIFIC / D / GRAVITY` is one entry printed over three
    # lines.  A meaning line with no letter belongs to the nearest letter row, and
    # "nearest" is measured against the table's own row pitch rather than a chosen
    # tolerance: half the median distance between consecutive letter rows.
    #
    # Both the pitch and each row's position come from the letter column itself,
    # not from the text lines.  A letter's line box can hold more than one text
    # line - on SADARA's sheet the composed tags sit 1.1 pt below the letter and
    # key as their own line - and counting those as rows collapses the median gap
    # from a row pitch to a line spacing, which switches the wrap off entirely and
    # loses `D DENSITY OR SPECIFIC GRAVITY`.  The letter column has exactly one
    # entry per row by definition, so it is the thing to measure.
    letter_ys = [(r.y0 + r.y1) / 2 for r, _t in column]
    pitch = 0.0
    if len(letter_ys) > 2:
        gaps = sorted(letter_ys[i + 1] - letter_ys[i]
                      for i in range(len(letter_ys) - 1))
        pitch = gaps[len(gaps) // 2]
    first: dict = {}
    order = {t: (r.y0 + r.y1) / 2 for r, t in column}
    for k in keyed:
        if k["letter"]:
            first.setdefault(k["letter"], [])
            first[k["letter"]] += k["words"]
    for k in keyed:
        if k["letter"] or not k["words"]:
            continue
        near = min(order.items(), key=lambda kv: abs(kv[1] - k["y"]), default=None)
        if near and abs(near[1] - k["y"]) <= pitch / 2:
            # above the letter row keeps its reading order, below follows it
            if k["y"] < near[1]:
                first[near[0]] = k["words"] + first[near[0]]
            else:
                first[near[0]] += k["words"]

    # The succeeding-letter columns.  Each is headed by its letter in the row the
    # legend labels `TYPICAL SYMBOL`, and the column's meaning is printed above
    # that row, centred over the column - so a word joins the column whose header
    # letter is nearest its own centre.
    succeeding: dict = {}
    header = next((r for r, t in pc.words
                   if t == "TYPICAL" and head.y1 < r.y0 < head.y1 + 120), None)
    if header is not None:
        hy = (header.y0 + header.y1) / 2
        heads = sorted((r.x0 + r.x1) / 2, ) if False else sorted(
            ((r.x0 + r.x1) / 2, t) for r, t in pc.words
            if len(t) == 1 and t.isalpha() and t.isupper()
            and abs((r.y0 + r.y1) / 2 - hy) < 6 and r.x0 >= meaning_hi - 8)
        pitches = [heads[i + 1][0] - heads[i][0] for i in range(len(heads) - 1)]
        span = (sorted(pitches)[len(pitches) // 2] / 2) if pitches else 0.0
        for r, t in pc.words:
            cy = (r.y0 + r.y1) / 2
            if not (head.y1 < cy < hy) or len(t) < 3 or not t.isalpha():
                continue
            cx = (r.x0 + r.x1) / 2
            best = min(heads, key=lambda h: abs(h[0] - cx), default=None)
            if best and abs(best[0] - cx) <= span:
                succeeding.setdefault(best[1], [])
                if t not in succeeding[best[1]]:
                    succeeding[best[1]].append(t)
    return IsaTable(first={k: tuple(v) for k, v in first.items() if v},
                    succeeding={k: tuple(v) for k, v in succeeding.items()},
                    page_no=pc.page_no,
                    note=f"legend p{pc.page_no} identification matrix: "
                         f"{len(first)} first letters, "
                         f"{len(succeeding)} succeeding letters")


def _letter_column(body) -> list | None:
    """The FIRST LETTER column of the matrix: `[(rect, letter), ...]`, top to bottom.

    A candidate entry is a one- or two-character upper-case token, which is what
    the column holds and nothing else does - the matrix's first letters are A..Z
    plus the one two-letter row `PD`, while a sub-heading like `SYMBOL` is six
    characters and a composed tag in a later column is three or more (`AAL`,
    `PDAH`).

    Candidates are grouped into columns by their centres, allowing one character
    width - measured off the candidates themselves, not chosen.  A cell centres
    its letter, so one column's centres vary by a fraction of a character, while
    two columns of this table stand 250 pt apart; the allowance is therefore not a
    threshold anything turns on.

    The winner is the column with the most distinct letters.  That is the
    definition of the column rather than a property of these sheets: the matrix
    prints one row per first letter, so the FIRST LETTER column enumerates them
    all, and every succeeding-letter column holds a letter only on the rows where
    that combination exists.  A tie goes to the leftmost, because the table's own
    heading puts the first letter first.
    """
    cand = [(r, t) for r, t in body
            if 1 <= len(t) <= 2 and t.isalpha() and t.isupper()]
    if not cand:
        return None
    widths = sorted(r.width for r, _t in cand)
    allow = widths[len(widths) // 2]
    groups: list = []
    for r, t in sorted(cand, key=lambda rt: (rt[0].x0 + rt[0].x1) / 2):
        cx = (r.x0 + r.x1) / 2
        if groups and cx - groups[-1][0] <= allow:
            groups[-1][1].append((r, t))
        else:
            groups.append((cx, [(r, t)]))
    best = None
    for cx, members in groups:
        distinct = len({t for _r, t in members})
        if best is None or distinct > best[0]:
            best = (distinct, cx, members)
    if best is None or best[0] < 2:
        return None
    return sorted(best[2], key=lambda rt: rt[0].y0)


def _columns(xs, slack: float = 8.0) -> list:
    """Column positions from a list of token x offsets: clusters, left to right.

    A column is a run of x values within `slack` of each other, and `slack` is the
    stroke index's own coordinate allowance rather than a new number.
    """
    slack = legend_rules.INDEX_SLACK * 10 if slack is None else slack
    out = []
    for x in sorted(xs):
        if out and x - out[-1][-1] <= slack:
            out[-1].append(x)
        else:
            out.append([x])
    # A column of one stray token is not a column; the table repeats every row.
    return [round(min(c), 1) for c in out if len(c) >= 3]


if __name__ == "__main__":
    import pidcache

    _doc, _pages = pidcache.load_pages(Path("data/pid_total.pdf"))
    t = derive(_pages)
    print(t.note)
    for k, v in sorted(t.first.items()):
        print(f"  {k:<3} {' '.join(v)}")
    print("succeeding:")
    for k, v in sorted(t.succeeding.items()):
        print(f"  {k:<3} {' '.join(v)}")
    for tag in ("TIT", "PIT", "PDIT", "LSHH", "FE", "RO", "FIT", "LIT"):
        print(f"  {tag:<6} -> {t.words_for(tag)}")
