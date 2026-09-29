"""What the sheet says about its own layout, measured instead of configured.

The project profile used to carry the drawing's geometry: where the frame is,
where the title block's cells are, how long a dash is, whether the vendor mark is
drawn or typed.  None of that is a fact about the *client* - it is a fact about
the sheet in front of us, and the sheet states all of it.  So it is read here,
once, from the pages themselves, and the profile keeps only what a drawing cannot
say: the client's Excel template, the words its finished list uses, the letters
its deliverable puts in a TYPE column.

Each value comes back with its source and the measurement behind it:

    DERIVED       read off these pages; `evidence` says from what
    CONFIG        the derivation found nothing and the profile supplied it
    UNAVAILABLE   neither; the caller leaves the field empty and says so

The rule everywhere below is the one the rest of this codebase already follows:
a number is either something the document prints or something counted in the
client's list.  Nothing here is a tolerance someone picked - where a bound is
needed it is a rule the sheet draws, a distribution the sheet's own marks form,
or a count over the pages.
"""

from __future__ import annotations

import collections
import re
import statistics
import sys

import pymupdf
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# How much of a page a rule must span to count as the sheet's frame.  Not a
# tolerance on a measurement: the frame is drawn corner to corner and everything
# else on the sheet is an order of magnitude shorter, so any fraction between a
# half and one selects the same lines.  Stated once here rather than repeated.
FRAME_SPAN = 0.85
# How many pages must agree before a line is taken as the sheet's form rather
# than as something one drawing happens to contain.  A form is on every page; a
# drawing's own content is not.  Again a majority, not a threshold on a value.
FORM_PAGES = 0.8


@dataclass
class Item:
    """One derived value, with what it was read from."""

    key: str
    value: object
    source: str = "DERIVED"          # DERIVED | CONFIG | UNAVAILABLE
    evidence: str = ""

    def as_dict(self) -> dict:
        return {"key": self.key, "value": self.value,
                "source": self.source, "evidence": self.evidence}


@dataclass
class Layout:
    items: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)

    def add(self, key, value, evidence, source="DERIVED"):
        self.items[key] = Item(key, value, source, evidence)

    def values(self) -> dict:
        """`{dotted key: value}` for everything that was derived."""
        return {k: it.value for k, it in self.items.items()
                if it.source == "DERIVED"}

    def as_dict(self) -> dict:
        return {"items": [it.as_dict() for it in self.items.values()],
                "notes": list(self.notes)}


# --------------------------------------------------------------------------
# Rules the sheet draws
# --------------------------------------------------------------------------
def _rules(pc):
    """Straight rules on one page, merged per coordinate: (v_runs, h_runs).

    A run is `(coordinate, from, to)`.  Segments that touch are joined, because a
    frame line arrives as many collinear pieces.
    """
    V, H = collections.defaultdict(list), collections.defaultdict(list)
    for a, b in pc.segments():
        if abs(a.x - b.x) < 0.5 and abs(a.y - b.y) > 2:
            V[round(a.x, 1)].append((min(a.y, b.y), max(a.y, b.y)))
        elif abs(a.y - b.y) < 0.5 and abs(a.x - b.x) > 2:
            H[round(a.y, 1)].append((min(a.x, b.x), max(a.x, b.x)))

    def merge(d):
        out = []
        for c, ss in d.items():
            ss.sort()
            lo, hi = ss[0]
            for s, e in ss[1:]:
                if s <= hi + 2:
                    hi = max(hi, e)
                else:
                    out.append((c, lo, hi))
                    lo, hi = s, e
            out.append((c, lo, hi))
        return out

    return merge(V), merge(H)


def _frame(pages) -> tuple:
    """The sheet's border and the title-block column edge.

    The border is the pair of full-height rules and the pair of full-width rules
    that every page draws.  The title-block column is the innermost full-height
    rule on the right of the sheet that is not the border - the line the form
    draws between the drawing and its title block.
    """
    W, H = pages[0].width, pages[0].height
    # Counted to the point, kept to the tenth.  A form's line is in the same place
    # on every page but the export does not repeat its coordinate to the decimal,
    # so counting on the rounded value is what groups one line's occurrences; the
    # value reported is the median of what was actually measured.
    vx, hy = [], []
    for i, pc in enumerate(pages):
        V, Hh = _rules(pc)
        vx += [(x, i) for x, lo, hi in V if hi - lo > FRAME_SPAN * H]
        hy += [(y, i) for y, lo, hi in Hh if hi - lo > FRAME_SPAN * W]
    need = FORM_PAGES * len(pages)

    def keep(vals):
        """One line's occurrences, gathered across pages and kept if most agree.

        Grouped by proximity rather than by a rounded coordinate: a form's line
        lands within a point of itself from page to page, and rounding splits one
        line into two buckets when it happens to straddle a whole number - which
        is what lost SADARA's left border, drawn at 80.7 on some pages and 83.5 on
        others.  The width allowed is a single point, which is finer than any two
        lines of a title block are apart.
        """
        out = []
        for v, page in sorted(vals):
            if out and v - out[-1][0][-1] <= 1.0:
                out[-1][0].append(v)
                out[-1][1].add(page)
            else:
                out.append(([v], {page}))
        return sorted(g[len(g) // 2] for g, seen in out if len(seen) >= need)

    xs, ys = keep(vx), keep(hy)
    if len(xs) < 2 or len(ys) < 2:
        return None
    # The border is the outermost pair; the drawing sits inside it.
    left, right = xs[0], xs[-1]
    top, bottom = ys[0], ys[-1]
    # The title-block column: the innermost of the rules right of centre that is
    # not the border itself.  On a sheet that draws none, the border stands in.
    inner = [x for x in xs if 0.5 * W < x < right - 1]
    column = min(inner) if inner else right
    return left, top, right, bottom, column, xs, ys


# --------------------------------------------------------------------------
# The title block, found by the captions it prints
# --------------------------------------------------------------------------
# The form's own words.  Not project data: they are printed on the sheet, and
# finding a cell by the caption above it is what a person does reading the block.
CAPTIONS = {
    "project_name": ("PROJECT", "NAME"),
    "title": ("DRAWING", "TITLE"),
    "dwg_no": ("PROJECT", "DWG", "NO."),
    "project_no": ("PROJECT", "NO."),
    "history": ("REV.", "DATE", "DESCRIPTION"),
}


def _column_lines(pages, column) -> list:
    """Text lines inside the title-block column, as `(y, [(x, text, height)])`.

    Built from the page that has the most of them, so a sheet whose block is
    partly empty does not decide the geometry for the set.
    """
    best = None
    for pc in pages:
        lines = collections.defaultdict(list)
        seen = set()
        for r, t in pc.words:
            # 낱말이 그 열 **안에 있는가** — 왼쪽 모서리가 아니라 **중심**으로 가른다
            # (28회차).  UAD 는 캡션을 세로 괘선에 바짝 붙여 인쇄해서 `PROJECT DWG
            # NO.` 의 x0 가 984.0 · 괘선이 984.1 이다.  모서리로 가르면 **0.1pt**
            # 차이로 표제란 캡션 셋이 통째로 빠지고(실측: 찾은 캡션 1개),
            # 허용치를 더하면 그 숫자가 곧 임의값이 된다 (§2.2).
            if (r.x0 + r.x1) / 2 < column:
                continue
            # Duplicates are dropped here whatever the cache is set to do: this
            # measurement runs before that setting is known, and a caption stamped
            # four times reads as `PROJECT PROJECT PROJECT PROJECT NAME`.
            key = (round(r.x0, 2), round(r.y0, 2), t)
            if key in seen:
                continue
            seen.add(key)
            lines[round((r.y0 + r.y1) / 2, 1)].append(
                (r.x0, t, r.height, r.y0, r.y1, r.x1))
        if best is None or len(lines) > len(best[1]):
            best = (pc, lines)
    if best is None:
        return []
    return sorted((y, sorted(items)) for y, items in best[1].items())


def _caption_rows(lines) -> dict:
    """Where each caption line sits: `{name: (y_top, y_bottom)}`.

    ⚠ 한 조각이 여러 낱말을 담을 수 있다 (28회차).  획(SHX) 글꼴로 그린 글자는
    PDF 에 주석 하나로 들어오고 그 주석은 `PROJECT DWG NO.` 를 **통째로** 담는다
    — 쪼개 놓으면 그 자리는 지어낸 값이 되므로 쪼개지 않고 여기서 낱말로 읽는다.
    """
    out = {}
    for y, items in lines:
        words = [w.upper() for _x, t, *_rest in items for w in t.split()]
        for name, caption in CAPTIONS.items():
            if name in out:
                continue
            # the caption's words, in order, at the head of the line
            if words[:len(caption)] == list(caption):
                y0 = min(it[3] for it in items)
                y1 = max(it[4] for it in items)
                out[name] = (y0, y1)
    return out


# 2차 — 캡션 **어휘** (hotfix29).  1차(`CAPTIONS` 정확 일치)가 못 찾은 이름만 여기로
# 온다.  양식마다 같은 칸을 `DWG. NO.` · `DRAWING NUMBER` · `DOC NO` · `SHEET TITLE` 로
# 달리 부르고, 값을 캡션 **아래**가 아니라 **같은 줄 오른쪽**(`DWG NO. : XXXX`)에 두는
# 양식도 있다.  `need` 의 묶음마다 낱말 하나씩이 줄 머리에 나와야 하고, `allow` 는 그
# 사이에 끼어도 되는 낱말이다.  머리 뒤에 남는 낱말이 있으면 그것이 **같은 줄의 값**이다.
# 낱말은 양식의 것이지 프로젝트 데이터가 아니다 (`CAPTIONS` 와 같은 자격).
CAPTION_VOCAB = {
    "dwg_no": ([{"DWG", "DWG.", "DRAWING", "DRG", "DRG.", "DOC", "DOC.", "DOCUMENT"},
                {"NO", "NO.", "NO:", "NUMBER", "N°", "#"}],
               {"PROJECT", "CLIENT", "CONTRACTOR", "OWNER", ":", "-"}),
    "history": ([{"REV", "REV.", "REVISION"}, {"DATE"}, {"DESCRIPTION"}],
                {"NO", "NO.", "BY", "CHK", "CHK.", "CHECKED", "APP", "APP.", "APPROVED",
                 "DRAWN", "DRN", ":"}),
    "project_no": ([{"PROJECT", "JOB", "CONTRACT"}, {"NO", "NO.", "NO:", "NUMBER", "#"}], {":"}),
    "project_name": ([{"PROJECT"}, {"NAME", "TITLE"}], {":"}),
    "title": ([{"TITLE"}], {"DRAWING", "DWG", "DWG.", "SHEET", "DOCUMENT", "DOC", "DOC.", ":"}),
    "rev": ([{"REV", "REV.", "REV:", "REVISION"}], {"NO", "NO.", ":"}),
    "sheet": ([{"SHEET", "SH", "SH.", "SHT", "SHT.", "SHEET:"}], {"NO", "NO.", ":"}),
}


def _vocab_match(words, name):
    """줄 머리가 `name` 의 캡션인가 — (캡션 낱말 수, 값 낱말들) 또는 None."""
    need, allow = CAPTION_VOCAB[name]
    hit = [False] * len(need)
    n = 0
    for w in words:
        k = next((i for i, g in enumerate(need) if w in g and not hit[i]), None)
        if k is not None:
            hit[k] = True
        elif w in allow:
            pass
        else:
            break
        n += 1
    if not all(hit):
        return None
    return n, words[n:]


def _caption_rows_vocab(lines, taken: dict) -> dict:
    """2차 — 어휘로 찾은 캡션 `{name: (y_top, y_bottom, x_after, inline_words)}`.

    1차가 찾은 이름(`taken`)은 건드리지 않고, 1차가 이미 쓴 줄도 다시 쓰지 않는다 —
    그래서 1차가 전부 찾는 문서(AL NOUF1 · TC2 · UAD · SADARA)는 여기서 아무 것도
    바뀌지 않는다.  한 줄은 한 이름에만 간다 (`PROJECT TITLE` 은 project_name 이지
    title 이 아니다 — 순서가 그것을 정한다).
    """
    used_y = {v[0] for v in taken.values()}
    out = {}
    for y, items in lines:
        y0 = min(it[3] for it in items)
        if y0 in used_y:
            continue
        toks = [(w.upper(), it) for it in items for w in it[1].split()]
        words = [w for w, _it in toks]
        for name in ("dwg_no", "history", "project_no", "project_name", "title", "rev", "sheet"):
            if name in taken or name in out:
                continue
            m = _vocab_match(words, name)
            if m is None:
                continue
            n, rest = m
            # 캡션의 마지막 낱말이 든 조각의 오른쪽 끝 — 같은 줄 값은 그 뒤다.
            # 값은 캡션보다 큰 글자로 찍히기 일쑤라 y 중심이 달라 **다른 줄로 묶여**
            # 있을 수 있다 — 캡션의 세로 띠와 겹치고 오른쪽에 있는 낱말은 전부 값이다.
            x_after = max(it[5] for _w, it in toks[:n])
            y1 = max(it[4] for it in items)
            beside = [it for yy, its in lines for it in its
                      if it[0] >= x_after - 0.5 and it[4] > y0 and it[3] < y1 and it is not None
                      and not (yy == y and it in items[:0])]
            beside = [it for it in beside if not (it in items and it[0] < x_after)]
            if beside:
                rest = [w for it in sorted(beside) for w in it[1].split()]
                y0 = min(y0, min(it[3] for it in beside))
                y1 = max(y1, max(it[4] for it in beside))
            out[name] = (y0, y1, x_after, rest)
            break
    return out


def _cell(caps, lines, name, right):
    """The band a caption owns: from its own top to the next caption's top."""
    if name not in caps:
        return None
    y0 = caps[name][0]
    below = sorted((v[0], v[1]) for k, v in caps.items() if v[0] > caps[name][1])
    # Down to the *bottom* of the next caption, not its top: a value that wraps
    # descends past the caption's own top, and the caption itself is excluded by
    # size rather than by position.
    y1 = below[0][1] if below else max(y for y, _items in lines)
    return (y0, y1)


def _title_block(pages, column, right_edge) -> dict:
    """The cells the title block prints a caption for.

    Every cell is bounded by its own caption above and the next caption below,
    which is how the form is laid out and how it reads.  The value inside a cell
    is separated from the caption by size - the caption is set small and the value
    large - and the boundary is measured per cell rather than configured: it is
    the midpoint between the caption's own height and the tallest line under it.
    """
    lines = _column_lines(pages, column)
    if not lines:
        return {}
    caps = _caption_rows(lines)
    out = {"_captions": {k: [round(v[0], 1), round(v[1], 1)]
                         for k, v in caps.items()}}
    # `SHEET` and `REV.` are captioned on the drawing-number row itself, to the
    # right of it, so each owns the column from its own caption across to the next
    # one.  Their band is the drawing number's band.
    if "dwg_no" in caps:
        y0, y1 = _cell(caps, lines, "dwg_no", right_edge)
        # Every line that overlaps the caption's own band, not just the one whose
        # centre matches it: `SHEET` and `REV.` are set larger than
        # `PROJECT DWG NO.` and centre a few points lower, so they key as their
        # own line while sitting on the same row of the form.
        heads = [(it[0], it[5], it[1].upper()) for y, items in lines
                 if caps["dwg_no"][0] <= y <= caps["dwg_no"][1] for it in items]
        for want, key in (("SHEET", "sheet_box"), ("REV.", "rev_box")):
            hit = next((h for h in heads if h[2] == want), None)
            if hit is None:
                continue
            after = sorted(x for x, _x1, t in heads if x > hit[0])
            out[key] = [round(hit[0], 1), round(y0, 1),
                        round(after[0] if after else right_edge, 1), round(y1, 1)]
    for name in ("project_name", "title", "dwg_no"):
        band = _cell(caps, lines, name, right_edge)
        if band is None:
            continue
        y0, y1 = band
        out[f"{name}_region"] = [round(column, 1), round(y0, 1),
                                 round(right_edge, 1), round(y1, 1)]
        # The caption/value size split, from this cell's own lettering.
        cap_h = max((it[2] for y, items in lines
                     if caps[name][0] <= y <= caps[name][1] for it in items),
                    default=0.0)
        val_h = max((it[2] for y, items in lines if caps[name][1] < y < y1
                     for it in items), default=0.0)
        if val_h > cap_h > 0:
            out[f"{name}_min_height"] = round((cap_h + val_h) / 2, 1)
    # hotfix29 — 2차: 1차가 못 찾은 이름만 어휘로.  1차가 찾은 칸은 위에서 이미
    # 정해졌고 여기서 바뀌지 않는다.
    vocab = _caption_rows_vocab(lines, caps)
    if vocab:
        out["_captions_vocab"] = {k: [round(v[0], 1), round(v[1], 1)] for k, v in vocab.items()}
        allcaps = dict(caps)
        allcaps.update({k: (v[0], v[1]) for k, v in vocab.items()})
        for name in ("project_name", "title", "dwg_no"):
            if name in caps or name not in vocab:
                continue
            y0, y1, x_after, rest = vocab[name]
            if rest:                       # 값이 같은 줄 오른쪽에
                h = y1 - y0
                out[f"{name}_region"] = [round(x_after, 1), round(y0 - h / 2, 1),
                                         round(right_edge, 1), round(y1 + h / 2, 1)]
                out[f"{name}_inline"] = True
                if name != "dwg_no":
                    out[f"{name}_min_height"] = 0.0
                continue
            band = _cell(allcaps, lines, name, right_edge)
            if band is None:
                continue
            by0, by1 = band
            # 아래에 캡션이 없으면 마지막 글줄의 **바닥**까지 (`_cell` 은 그 줄의 중심에서
            # 끊는다 — 1차 문서는 그대로 두고 2차에서만 바닥까지 편다)
            if not any(v[0] > y1 for v in allcaps.values()):
                by1 = max(it[4] for yy, its in lines for it in its)
            out[f"{name}_region"] = [round(column, 1), round(by0, 1),
                                     round(right_edge, 1), round(by1, 1)]
            cap_h = max((it[2] for y, items in lines if y0 <= y <= y1 for it in items), default=0.0)
            val_h = max((it[2] for y, items in lines if y1 < y < by1 for it in items), default=0.0)
            if val_h > cap_h > 0:
                out[f"{name}_min_height"] = round((cap_h + val_h) / 2, 1)
        # REV · SHEET — 1차는 도면번호 줄의 `REV.`/`SHEET` 머리만 봤다.  2차는 어휘로
        # 찾은 캡션 줄에서: 같은 줄에 값이 있으면 그 오른쪽, 아니면 캡션 아래 띠.
        for name, key in (("rev", "rev_box"), ("sheet", "sheet_box")):
            if key in out or name not in vocab:
                continue
            y0, y1, x_after, rest = vocab[name]
            h = y1 - y0
            if rest:
                out[key] = [round(x_after, 1), round(y0 - h / 2, 1),
                            round(right_edge, 1), round(y1 + h / 2, 1)]
            else:
                band = _cell(allcaps, lines, name, right_edge)
                if band is None:
                    continue
                b1 = band[1]
                if not any(v[0] > y1 for v in allcaps.values()):
                    b1 = max(it[4] for yy, its in lines for it in its)
                cx0 = min(it[0] for y, items in lines if y0 <= y <= y1 for it in items)
                out[key] = [round(cx0, 1), round(y1, 1), round(right_edge, 1), round(b1, 1)]
    return out


# --------------------------------------------------------------------------
# Dash geometry
# --------------------------------------------------------------------------
def _equal_gap_runs(ys, rel_tol=0.02):
    """간격이 서로 같은 괘선이 연달아 있는 구간들 — `(y0, y1, 행높이, 행수)`.

    `rel_tol` 은 **비율**이다 (절대 pt 가 아니다).  같은 표의 행은 같은 높이로
    그려지고, 다른 종이에서도 비율은 그대로이기 때문이다 (23회차 §6 — 절대 pt
    규칙은 A1→A3 에서 전부 걸렸고 비율·모양 규칙은 넘었다).

    ★ 값 2%는 **분포의 빈 띠**에서 왔다 (§8).  세 문서에서 띠 안의 간격을
    최빈값과 견주어 전수로 세면 (`spike/hist_gaps.py`):

        개정 행   0.0% 626 · 0.1% 4 · 0.4% 174 · 1.4% 85       ← 최대 1.4%
        (빈 띠)   1.4% 와 2.8% 사이에 간격이 **하나도 없다**
        머리글 행 2.8% 1(TC2 p37) · 3.9% 2 · 4.2% 59 · 4.3% 13 · 4.4% 4 · 4.7% 48

    그 사이 어디에 두어도 답이 같으므로 임의값이 아니다 (16회차 `brk_max_mark`
    25.9~28.3 · 17회차 C-4 41.4~190.8 과 같은 근거).

    ★ 5%로 두었을 때 실제로 틀렸다: `REV. DATE DESCRIPTION` 머리글 행이 개정
    행보다 4.2~4.7% 높을 뿐이라 띠 안으로 들어왔고, `build_glyph_library` 가
    그 행을 rank 0 으로 세어 **개정 문자 A 를 B 로 이름 붙였다** (TC2 60장 ·
    SADARA 9장 전수).  손으로 적은 AL NOUF1 띠 [1200, 1390] 도 그 행을
    빼 두고 있다 — 유도가 손입력값을 재현하려면 빼야 한다.
    """
    out, i = [], 0
    gaps = [ys[k + 1] - ys[k] for k in range(len(ys) - 1)]
    while i < len(gaps):
        j = i
        while j + 1 < len(gaps) and abs(gaps[j + 1] - gaps[i]) <= rel_tol * gaps[i]:
            j += 1
        if j > i:                       # 간격 둘 = 괘선 셋 = 행 둘
            out.append((ys[i], ys[j + 1],
                        statistics.median(gaps[i:j + 1]), j - i + 1))
        i = j + 1
    return out


def _history_table(pages, column, edge, inset) -> dict:
    """개정 이력 표 — **표의 모양이 말한다.**

    이 여섯 칸은 20회차까지 AL NOUF1 실측값이 코드에 박혀 있었고, 그래서 종이가
    다른 문서에서는 좌표 띠가 통째로 종이 밖이 되어 이력 행을 한 줄도 못 찾았다
    (TC2 REV 0/60).  여기서 그 도면이 답하게 한다.

    무엇으로 찾는가 — 셋 다 모양이고 절대 pt 가 없다:

    ① 이력 띠   타이틀블록 열을 가로지르는 괘선 중 **간격이 서로 같은 띠**,
                그중 **행이 더 촘촘한 쪽**.  세 문서 모두 그 열에 띠가 둘이고
                (이력 표 + 서명란) 행 높이가 2~3배 갈린다:
                AL NOUF1 16.77 ↔ 44.52 · SADARA 24.04 ↔ 63.81 · TC2 8.52 ↔ 22.56.
    ② 열        그 띠를 세로로 가로지르는 괘선.  1열이 REV, 2열이 DATE 다.
                캡션을 인쇄하는 문서에서는 캡션이 그 열 안에 들어가 서로를
                확인해 준다 (SADARA `REV.` 2735.7~2757.9 ⊂ 1열 2726.7~2766.8 ·
                TC2 967.0~974.8 ⊂ 963.8~978.0).
    ③ 오른쪽 끝 시트 가장자리가 **아니라** 노트 열의 안쪽 괘선이다 — AL NOUF1 의
                이력 괘선은 2330.3 에서 멈추고 시트는 2345.3 이다.

    ★ 캡션으로 찾지 않는 이유: **AL NOUF1 은 `REV. DATE DESCRIPTION` 을 인쇄하지
    않는다** (그 문서가 찾는 캡션은 dwg_no · project_name · project_no · title 넷).
    캡션을 1차로 삼으면 기준선 문서가 빠진다.

    장마다 재고 **가장 흔한 답**을 쓴다 — 한 장이 비어도 표는 같기 때문이다.
    """
    seen: dict = {}
    for pc in pages:
        ys = sorted({round(r.y0, 2) for r in pc.rects()
                     if abs(r.height) < 1.0
                     and r.x0 <= column + inset and r.x1 >= edge - inset})
        runs = _equal_gap_runs(ys)
        if not runs:
            continue
        y0, y1, gap, _n = min(runs, key=lambda b: b[2])      # 촘촘한 쪽
        vx = sorted({round(r.x0, 2) for r in pc.rects()
                     if abs(r.width) < 1.0
                     and r.y0 <= y0 + gap and r.y1 >= y1 - gap
                     and column - inset <= r.x0 <= edge + inset})
        if len(vx) < 3:
            continue
        key = (round(y0, 2), round(y1, 2), round(gap, 2),
               tuple(round(v, 2) for v in vx))
        seen[key] = seen.get(key, 0) + 1
    if not seen:
        return {}
    (y0, y1, gap, vx), votes = max(seen.items(), key=lambda kv: kv[1])
    return {"y0": y0, "y1": y1, "gap": gap, "vx": list(vx),
            "votes": votes, "pages": len(pages)}


def _dash_geometry(pages, drawing_area, unit: float = 1.0) -> dict:
    """The dash geometry of the lines that matter: the scope boundaries.

    Measuring every collinear run on the sheet does not work - hatching, a table's
    ruling and a tessellated curve all look like a dashed line at that distance,
    and the longest "mark" comes back at 55 pt where a real chain-dash is 26.
    What the filter is for is finding the boundary a scope label stands on, so the
    thing to measure is the runs that pass a scope label.  The label is the
    document's own pointer at the line, which is why it can be used to find it.
    """
    x0, y0, x1, y1 = drawing_area
    anchors = []
    for i, pc in enumerate(pages):
        for r, t in pc.words:
            if t == "SCT" and x0 <= r.x0 <= x1 and y0 <= r.y0 <= y1:
                anchors.append((i, (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
    if not anchors:
        return {}
    # How near is near: the label is set beside the line it names, so a distance
    # of one line of its own lettering is what "beside" means here.
    reach = max(r.height for pc in pages for r, t in pc.words if t == "SCT") * 4
    marks, gaps = [], []
    for i, pc in enumerate(pages):
        near = [(ax, ay) for j, ax, ay in anchors if j == i]
        if not near:
            continue
        for axis in (0, 1):
            by = collections.defaultdict(list)
            for a, b in pc.segments():
                if axis == 0:
                    if abs(a.y - b.y) >= 0.4 * unit or not (0.2 * unit < abs(a.x - b.x) < 120 * unit):
                        continue
                    key, lo, hi, other = round(a.y, 1), min(a.x, b.x), max(a.x, b.x), a.y
                else:
                    if abs(a.x - b.x) >= 0.4 * unit or not (0.2 * unit < abs(a.y - b.y) < 120 * unit):
                        continue
                    key, lo, hi, other = round(a.x, 1), min(a.y, b.y), max(a.y, b.y), a.x
                by[key].append((lo, hi, other))
            for c, ss in by.items():
                if len(ss) < 6:
                    continue
                ss = sorted((lo, hi) for lo, hi, _o in ss)
                lo_all, hi_all = ss[0][0], ss[-1][1]
                if axis == 0:
                    hit = any(abs(ay - c) <= reach and lo_all - reach <= ax <= hi_all + reach
                              for ax, ay in near)
                else:
                    hit = any(abs(ax - c) <= reach and lo_all - reach <= ay <= hi_all + reach
                              for ax, ay in near)
                if not hit:
                    continue
                g = [round(ss[k + 1][0] - ss[k][1], 2) for k in range(len(ss) - 1)]
                g = [v for v in g if v > 0]
                if len(g) < 5 or max(g) - min(g) > 1.0 * unit:
                    continue
                m = [round(b - a, 2) for a, b in ss]
                # A dash pattern repeats: a plain dash is one mark length, a chain
                # dash is a long one and a dot.  A run whose marks take many
                # lengths is not a pattern, it is a line that happens to be broken
                # up - which is how a 49 pt "mark" got in beside 3 pt ones.
                if len({round(v / unit) for v in m}) > 2:
                    continue
                marks += m
                gaps += g
    if not marks:
        return {}
    marks.sort()
    gaps.sort()
    return {"brk_max_mark": round(marks[-1] + 0.5, 1),
            "brk_max_gap": round(gaps[-1] + 0.5, 1),
            "_marks": len(marks), "_longest": marks[-1], "_widest_gap": gaps[-1],
            "_anchors": len(anchors)}


# --------------------------------------------------------------------------
# Notation: what this document actually uses
# --------------------------------------------------------------------------
MARK_TEXT = re.compile(r"^\(?\*{1,3}\)?$")


def _vendor_notation(pages, layout) -> dict:
    """The sizes at which this document draws its vendor mark, if it draws one.

    Each page whose NOTES define a mark also prints that mark beside the
    definition, and `read_mark_dictionary` measures it there.  A size that turns
    up on more than one page is the document's; a size seen once is that page's
    own mark drawn slightly differently, and taking it would widen the filter on
    the strength of a single sample.
    """
    import detect_symbols as ds
    seen = collections.Counter()
    typed = 0
    for pc in pages:
        _md, gs = ds.read_mark_dictionary(pc, layout)
        if gs:
            seen[(round(gs[0], 1), round(gs[1], 1))] += 1
        for r, t in pc.words:
            if MARK_TEXT.match(t) and layout.drawing_area[0] <= r.x0 <= layout.drawing_area[2]:
                typed += 1
    sizes = sorted(k for k, n in seen.items() if n > 1)
    return {"typed": typed, "glyph_sizes": [list(k) for k in sizes],
            "seen": seen.most_common()}


def _systematic_duplicates(pages) -> dict:
    """Whether the export stamps its own furniture more than once.

    A CAD export that draws the frame twice repeats the *same words at the same
    coordinates on every page*.  A drawing that happens to print a word twice does
    not.  So the test is per-page repetition that holds across the set, which is a
    count over pages rather than a threshold on one.
    """
    per_page, pages_with = [], 0
    for pc in pages:
        # The page as PyMuPDF returns it, not the cache: the cache may already
        # have had duplicates removed, and measuring that would only confirm the
        # setting that removed them.
        raw = [(pymupdf.Rect(w[:4]) * pc.page.rotation_matrix, w[4])
               for w in pc.page.get_text("words")]
        c = collections.Counter((round(r.x0, 2), round(r.y0, 2),
                                 round(r.x1, 2), round(r.y1, 2), t)
                                for r, t in raw)
        dup = sum(v - 1 for v in c.values() if v > 1)
        per_page.append(dup)
        pages_with += dup > 0
    return {"pages_with_duplicates": pages_with, "pages": len(pages),
            "systematic": pages_with >= FORM_PAGES * len(pages),
            "median_per_page": sorted(per_page)[len(per_page) // 2]}


def _markup_script(pages, drawing_area) -> dict:
    """Which script the reviewers write in, and whether it needs the highlight.

    A drawing is set in one script; a note added over it may be in another.  So a
    script that appears on the sheet *only inside a highlight* is the reviewers',
    and a script the drawing itself uses needs the highlight to tell the two
    apart.  Both are counted here rather than assumed.
    """
    ranges = {"HANGUL": re.compile("[가-힣]"), "LOWER": re.compile("[a-z]")}
    out = {}
    for name, rx in ranges.items():
        inside = outside = 0
        for pc in pages:
            boxes = _highlights(pc)
            for r, t in pc.words:
                if not rx.search(t) or not (drawing_area[0] <= r.x0 <= drawing_area[2]):
                    continue
                cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
                if any(b.x0 <= cx <= b.x1 and b.y0 <= cy <= b.y1 for b in boxes):
                    inside += 1
                else:
                    outside += 1
        out[name] = {"in_highlight": inside, "elsewhere": outside}
    return out


_INK = ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))


def _highlights(pc) -> list:
    """Rectangles filled with neither the drawing's ink nor its paper."""
    import pymupdf
    out = []
    m = pc.page.rotation_matrix
    for dr in pc.page.get_drawings():
        fill = dr.get("fill")
        if fill is None or tuple(round(v, 2) for v in fill) in _INK:
            continue
        out.append(pymupdf.Rect(dr["rect"]) * m)
    return out


def _scope_label_side(pages, drawing_area) -> dict:
    """Whether any scope label stands to the right of the span it marks.

    The box is built from the vertical the label stands beside.  If every label is
    on the left that vertical is the left edge and the box closes; if one is on
    the right it is the right edge and the box has to be built from the two
    horizontal edges instead.  Which of the two applies is a fact about the sheet,
    so it is read: a label is on the right when the dashed run beside it has more
    of its own row to the *left* than to the right.
    """
    right = left = 0
    for pc in pages:
        V, H = _rules(pc)
        for r, t in pc.words:
            if t != "SCT" or not (drawing_area[0] <= r.x0 <= drawing_area[2]):
                continue
            sy = (r.y0 + r.y1) / 2
            near = [x for x, lo, hi in V if abs(x - r.x0) < 60 and lo - 5 <= sy <= hi + 5]
            if not near:
                continue
            vx = min(near, key=lambda x: abs(x - r.x0))
            spans = [(lo, hi) for y, lo, hi in H if lo - 5 <= vx <= hi + 5]
            if not spans:
                continue
            to_left = sum(1 for lo, hi in spans if hi - 5 <= vx)
            to_right = sum(1 for lo, hi in spans if lo + 5 >= vx)
            if to_left > to_right:
                right += 1
            else:
                left += 1
    return {"labels_on_left": left, "labels_on_right": right}


# --------------------------------------------------------------------------
# The whole measurement
# --------------------------------------------------------------------------
def _history_rev_marks(pages, hist, inset, cfg) -> set[str]:
    """이력 표 REV 열이 **활자로** 인쇄한 개정 표기들.

    머리글 행을 섞지 않으려고 같은 행의 DATE 열이 날짜인 행만 받는다.
    획으로 그린 문서(AL NOUF1 · TC2 · SADARA)는 빈 집합을 돌려준다 — 그러면
    설정값이 그대로 쓰인다 (§9 ⑤: 못 읽으면 지어내지 않는다).
    """
    date_re = None
    if cfg is not None:
        try:
            date_re = re.compile(cfg.get("formats.date"))
        except Exception:
            date_re = None
    if date_re is None:
        return set()
    y0, y1, gap, vx = hist["y0"], hist["y1"], hist["gap"], hist["vx"]
    if len(vx) < 3:
        return set()
    rev = (vx[0] + inset, vx[1] - inset)
    date = (vx[1] + inset, vx[2] - inset)
    out: set[str] = set()
    for pd in pages:
        rows: dict[int, dict] = {}
        for r, t in pd.words:
            cy = (r.y0 + r.y1) / 2
            if not (y0 - gap <= cy <= y1 + gap):
                continue
            band = int(round((cy - y0) / gap)) if gap else 0
            cx = (r.x0 + r.x1) / 2
            if rev[0] <= cx <= rev[1]:
                rows.setdefault(band, {}).setdefault("rev", []).append(t)
            elif date[0] <= cx <= date[1]:
                rows.setdefault(band, {}).setdefault("date", []).append(t)
        for cell in rows.values():
            if not any(date_re.match(t) for t in cell.get("date", ())):
                continue
            for t in cell.get("rev", ()):
                out.add(t)
    return out


def _drawing_no_shapes(pages, region) -> dict:
    """도면번호 칸에 인쇄된 낱말의 **모양** → {모양: 장 집합} (37회차).

    모양은 붙임표로 나눈 자리마다 (글자 L · 숫자 D · 섞임 A) + 길이다 —
    `D02J-00GEN00-M05-0001` → `A4-A7-A3-D4`.  칸 안에서 붙임표와 숫자를 가진
    낱말만 본다.  네 문서 실측(`spike/dwgno_survey.py`)에서 그 칸에는 도면번호
    말고 다른 낱말이 없었다.
    """
    x0, y0, x1, y1 = region
    seen: dict = {}
    for pc in pages:
        for r, t in pc.words:
            xm = (r.x0 + getattr(r, "x1", r.x0)) / 2
            if not (x0 <= xm <= x1 and y0 <= r.y0 <= y1):
                continue
            if "-" not in t or not any(c.isdigit() for c in t):
                continue
            segs = t.split("-")
            if len(segs) < 2 or not all(s.isalnum() for s in segs):
                continue
            shape = "-".join(("D" if s.isdigit() else "L" if s.isalpha() else "A") + str(len(s)) for s in segs)
            seen.setdefault(shape, set()).add(pc.page_no)
    return seen


def _drawing_no_pattern(shapes: dict, min_sheets: int = 2) -> str | None:
    """읽은 모양들을 그대로 받는 정규식 — 넓히지 않는다 (37회차).

    **두 장 이상**에서 인쇄된 모양만 받는다 (18회차 규칙 — 한 장의 낱말 하나는
    모양이 아니라 사고일 수 있다).  AL NOUF1 · SADARA 는 모양이 하나(A4-A7-A3-D4),
    TC2 는 둘(56장 + `D02J-31PGB0-M05-0001` 4장)이다.  읽지 않은 모양을 추측으로
    더하지 않는다 (§2.1 ③).  config 의 표기와 같은 글자(`[A-Z0-9]`·`\\d`)를 쓴다.
    """
    kinds = {"L": "[A-Z]", "D": "\\d", "A": "[A-Z0-9]"}
    keep = sorted((k for k, pg in shapes.items() if len(pg) >= min_sheets),
                  key=lambda k: (-len(shapes[k]), k))
    if not keep:
        return None
    alts = []
    for shape in keep:
        alts.append("-".join("%s{%s}" % (kinds[seg[0]], seg[1:]) for seg in shape.split("-")))
    return "^%s$" % "|".join(alts) if len(alts) == 1 else "^(?:%s)$" % "|".join(alts)


def _form_pages(pages) -> tuple:
    """이 문서의 **양식 종이** — 가장 많은 장이 쓰는 쪽 크기의 장들 (hotfix28).

    한 PDF 에 표지·목록·범례를 다른 크기로 섞어 낸 문서가 온다 (현장: A3 5장 +
    A1 88장).  종이가 다르면 괘선의 자리도 다르므로 한 좌표로 잴 수 없고, 첫 장이
    표지이면 `pages[0]` 의 크기로 잰 문턱이 본 도면과 어긋난다.  **다수가 곧
    양식**이고(`FORM_PAGES` 와 같은 생각), 소수 장은 재지 않고 이름만 남긴다.
    """
    groups: dict = {}
    for pc in pages:
        groups.setdefault((round(float(pc.width), 1), round(float(pc.height), 1)), []).append(pc)
    size = max(groups, key=lambda k: (len(groups[k]), k))
    sizes = {k: len(v) for k, v in groups.items()}
    return groups[size], sizes


def _code_shape(t: str) -> str | None:
    """`_drawing_no_shapes` 와 같은 판정 — 붙임표·숫자를 가진 낱말의 모양, 아니면 None."""
    if "-" not in t or not any(c.isdigit() for c in t):
        return None
    segs = t.split("-")
    if len(segs) < 2 or not all(s.isalnum() for s in segs):
        return None
    return "-".join(("D" if s.isdigit() else "L" if s.isalpha() else "A") + str(len(s))
                    for s in segs)


def _recurring_numbers(pages) -> list:
    """캡션 없이 도면번호 칸을 찾는다 — **장마다 같은 자리에 되풀이되는 번호** (hotfix28).

    양식이 `PROJECT DWG NO.` 캡션을 인쇄하지 않으면 `_title_block` 은 그 칸을 못
    찾고, 그러면 AL NOUF1 의 좌표가 그대로 쓰여 한 장도 안 읽힌다 (현장: QFE 93장).
    캡션 낱말을 더 외우는 대신 **구조**를 본다 — 도면번호는 (가) 붙임표·숫자를 가진
    코드 낱말이고 (나) 양식이 정한 **같은 자리**에 장마다 인쇄되며 (다) 그 값이
    장마다 **다르다**.  프로젝트 번호·문서 번호는 (가)(나)를 만족하지만 값이 같고,
    오프페이지 커넥터의 도면번호는 (가)(다)를 만족하지만 자리가 장마다 다르다.

    자리 묶음은 `_frame.keep` 과 같은 폭(한 점)이고, 가로는 그 낱말 자신의 높이
    안이면 같은 자리다 (가운데 맞춤이면 길이에 따라 조금 움직인다).  상수는 새로
    두지 않는다 — 다수 조건은 `FORM_PAGES` 그대로다.

    돌려주는 것: 후보 목록, 좋은 것부터 — {rect, pages, values, shapes, y}.
    순위는 ① 장마다 값이 다른 정도(distinct/pages · 같은 번호를 두 장이 쓰는
    문서도 1에 가깝다) ② 인쇄된 장 수 ③ 아래쪽.  둘 이상이면 첫째를 쓰되 나머지를
    근거에 적는다.
    """
    entries = []          # (yc, x0, shape, text, page_no, rect, height)
    for pc in pages:
        for r, t in pc.words:
            shape = _code_shape(t)
            if shape is None:
                continue
            entries.append(((r.y0 + r.y1) / 2, r.x0, shape, t, pc.page_no,
                            (r.x0, r.y0, r.x1, r.y1), r.y1 - r.y0))
    if not entries:
        return []
    entries.sort()
    rows = []
    for e in entries:
        if rows and e[0] - rows[-1][-1][0] <= 1.0:
            rows[-1].append(e)
        else:
            rows.append([e])
    need = FORM_PAGES * len(pages)
    out = []
    for row in rows:
        row.sort(key=lambda e: e[1])
        cols = []
        for e in row:
            if cols and e[1] - cols[-1][-1][1] <= e[6]:
                cols[-1].append(e)
            else:
                cols.append([e])
        for col in cols:
            by_page: dict = {}
            for e in col:
                by_page.setdefault(e[4], []).append(e)
            if len(by_page) < need or any(len(v) > 1 for v in by_page.values()):
                continue
            values = {e[3] for e in col}
            if len(values) < 2:
                continue
            xs0 = [e[5][0] for e in col]; ys0 = [e[5][1] for e in col]
            xs1 = [e[5][2] for e in col]; ys1 = [e[5][3] for e in col]
            h = max(e[6] for e in col)
            out.append({
                "rect": [round(min(xs0) - h, 1), round(min(ys0) - h / 2, 1),
                         round(max(xs1) + h, 1), round(max(ys1) + h / 2, 1)],
                "pages": sorted(by_page), "values": len(values),
                "shapes": {e[2] for e in col}, "y": round(col[0][0], 1),
                "unique": round(len(values) / len(by_page), 3),
            })
    out.sort(key=lambda c: (-c["unique"], -len(c["pages"]), -c["y"]))
    return out


def _recurring_title(pages, column, right, dwg_rect=None) -> dict | None:
    """캡션 없는 양식의 제목 칸 — 되풀이 자리 · 장마다 다른 값 · 가장 큰 글자 (hotfix29).

    표제란 열의 글줄을 장마다 y(1pt 묶음)로 모아, 다수 장에 있고 값이 둘 이상인 줄만
    남긴다 (프로젝트명·캡션은 값이 같고, 날짜·개정은 작지만 다르다).  그중 글자가
    가장 큰 줄이 제목이고, 같은 높이의 이웃 줄(두 줄 제목)을 같은 칸에 넣는다.
    도면번호 칸과 겹치는 줄은 뺀다.  값의 문턱은 없다 — 제목의 높이와 그 다음으로
    큰 되풀이 글줄 높이의 중간이 `title_min_height` 다 (캡션 규칙과 같은 정의).
    """
    rows: dict = {}
    for pc in pages:
        lines: dict = {}
        for r, t in pc.words:
            if (r.x0 + r.x1) / 2 < column:
                continue
            if dwg_rect and dwg_rect[0] <= (r.x0 + r.x1) / 2 <= dwg_rect[2] \
                    and dwg_rect[1] <= (r.y0 + r.y1) / 2 <= dwg_rect[3]:
                continue
            lines.setdefault(round((r.y0 + r.y1) / 2), []).append((r, t))
        for yk, ws in lines.items():
            ws.sort(key=lambda w: w[0].x0)
            text = " ".join(t for _r, t in ws)
            h = max(r.y1 - r.y0 for r, _t in ws)
            rows.setdefault(yk, []).append((pc.page_no, text, h, min(r.y0 for r, _t in ws), max(r.y1 for r, _t in ws)))
    need = FORM_PAGES * len(pages)
    cand = []
    for yk, ents in rows.items():
        pgs = {e[0] for e in ents}
        if len(pgs) < need:
            continue
        vals = {e[1] for e in ents}
        if len(vals) < 2:
            continue
        if all(_code_shape(e[1]) for e in ents):
            continue
        cand.append((yk, statistics.median(e[2] for e in ents), len(pgs),
                     min(e[3] for e in ents), max(e[4] for e in ents)))
    if not cand:
        return None
    top = max(cand, key=lambda c: (round(c[1], 1), c[2]))
    band = [c for c in cand if abs(c[1] - top[1]) <= 0.1 * top[1]
            and abs(c[0] - top[0]) <= 3 * top[1]]
    y0 = min(c[3] for c in band); y1 = max(c[4] for c in band)
    smaller = [c[1] for c in cand if c[1] < top[1] - 0.1 * top[1]]
    min_h = round((max(smaller) + top[1]) / 2, 1) if smaller else 0.0
    h = top[1]
    return {"rect": [round(column, 1), round(y0 - h / 2, 1), round(right, 1), round(y1 + h / 2, 1)],
            "height": round(h, 1), "min_height": min_h, "pages": top[2]}


def _revision_pattern(marks: set[str]) -> str:
    """읽은 표기들을 그대로 받아들이는 정규식 — 넓히지 않는다.

    모양(글자·숫자 달리기)이 하나면 그 모양만 받고, 여럿이면 읽은 표기를
    그대로 나열한다.  **읽지 않은 모양을 추측으로 더하지 않는다** (§2.1 ③).
    """
    shapes = {("".join("D" if c.isdigit() else "L" if c.isalpha() else "X"
                       for c in m)) for m in marks}
    if shapes == {"D"}:
        return r"^[0-9]$"
    if shapes == {"L"}:
        return r"^[A-Z]$"
    if shapes == {"D", "DD"} or shapes == {"DD"}:
        return r"^[0-9]{1,2}$"
    return "^(?:%s)$" % "|".join(re.escape(m) for m in sorted(marks))


def derive(pages, cfg=None) -> Layout:
    """Everything the sheet states about its own layout."""
    lay = Layout()
    if not pages:
        return lay
    # hotfix28 — 종이가 섞인 문서는 **다수 크기의 장**으로 잰다.  나머지는 재지
    # 않고 이름만 남긴다 (그 장들은 도면번호 칸이 종이 밖이라 대상에서 빠진다).
    all_pages = pages
    pages, sizes = _form_pages(pages)
    W, H = pages[0].width, pages[0].height
    same = (f"page rectangle, identical on all {len(pages)} pages" if len(sizes) == 1
            else f"page rectangle of the {len(pages)} of {len(all_pages)} pages that share "
                 f"the majority size; the others are " + ", ".join(
                     f"{k[0]}x{k[1]} pt x{v}" for k, v in sorted(sizes.items()) if k != (round(float(W), 1), round(float(H), 1))))
    lay.add("sheet.width_pt", round(W, 1), same)
    lay.add("sheet.height_pt", round(H, 1), same)
    if len(sizes) > 1:
        lay.notes.append("mixed page sizes: " + ", ".join(
            f"{k[0]}x{k[1]} pt x{v}" for k, v in sorted(sizes.items(), key=lambda t: -t[1]))
            + f"; measured on the {len(pages)} majority-size pages only")

    fr = _frame(pages)
    if fr is None:
        lay.notes.append("no border rule spans this sheet on a majority of its "
                         "pages, so the drawing area could not be measured")
        return lay
    left, top, right, bottom, column, xs, ys = fr
    lay.add("regions.drawing_area",
            [round(left, 1), round(top, 1), round(column, 1), round(bottom, 1)],
            f"border rules at x {left:.1f}/{right:.1f} and y {top:.1f}/{bottom:.1f}; "
            f"the title block's column edge is the innermost full-height rule "
            f"right of centre, at x {column:.1f}")
    lay.add("regions.notes_area",
            [round(column, 1), round(top, 1), round(W, 1), round(bottom, 1)],
            f"the column right of x {column:.1f}, between the border rules")
    # The notes text stops at the column's own inner rule where the form draws
    # one; otherwise at the sheet edge.
    inner = [x for x in xs if column < x < right]
    lay.add("regions.notes_text_x_max", round(inner[-1] if inner else right, 1),
            (f"inner rule of the notes column at x {inner[-1]:.1f}" if inner
             else f"no inner rule; the sheet edge at x {right:.1f}"))

    tb = _title_block(pages, column, right)
    vocab_found = tb.get("_captions_vocab") or {}
    for name, key in (("project_name", "title_block.project_name_region"),
                      ("title", "title_block.title_region"),
                      ("dwg_no", "title_block.dwg_no_region")):
        if f"{name}_region" in tb:
            if name in vocab_found:
                why = (f"the value printed on the same line, right of the form's "
                       f"`{name}` caption (matched by caption vocabulary)"
                       if tb.get(f"{name}_inline") else
                       f"the cell under the form's `{name}` caption matched by caption "
                       f"vocabulary (not the exact `{' '.join(CAPTIONS[name])}`), down "
                       f"to the next caption")
            else:
                why = (f"the cell under the form's own `{' '.join(CAPTIONS[name])}` "
                       f"caption, down to the next caption")
            lay.add(key, tb[f"{name}_region"], why)
        if f"{name}_min_height" in tb and name != "dwg_no":
            lay.add(f"title_block.{name}_min_height", tb[f"{name}_min_height"],
                    "midway between the caption's lettering and the value's, "
                    "measured in this cell" if tb[f"{name}_min_height"] else
                    "the value shares the caption's line, so no size split applies")
    # 37회차 — **도면번호의 모양도 도면이 말한다.**  `formats.drawing_no` 는
    # AL NOUF1 에서 옮겨 적은 값이라 TC2 의 `D02J-31PGB0-M05-0001`(둘째 자리가
    # 6자 · 4장)을 안 받았고, 그 네 장은 행 0 이었다 (25·26회차가 적어 둔 자리).
    # 읽는 곳은 위에서 캡션으로 찾은 **도면번호 칸 자신**이다 — 그 칸이 곧 이
    # 문서가 쓰는 도면번호의 목록이다.
    # hotfix28 — 캡션이 없는 양식.  `PROJECT DWG NO.` 를 안 찍는 양식에서는 위가
    # 빈 채로 남고 AL NOUF1 좌표가 그대로 쓰여 한 장도 안 읽힌다.  캡션 낱말을 더
    # 외우지 않고 **구조**로 찾는다 — 장마다 같은 자리에 되풀이되는 코드 번호 중
    # 값이 장마다 다른 것 (`_recurring_numbers`).  캡션이 찾은 문서는 여기 안 온다.
    if "dwg_no_region" not in tb:
        cands = _recurring_numbers(pages)
        if cands:
            best = cands[0]
            tb["dwg_no_region"] = best["rect"]
            tb["_dwg_no_by"] = "recurrence"
            lay.add("title_block.dwg_no_region", best["rect"],
                    f"no DWG NO. caption is printed; taken as the cell where a "
                    f"hyphenated number recurs at one position on {len(best['pages'])} "
                    f"of {len(pages)} sheets with {best['values']} distinct values "
                    f"(shapes {', '.join(sorted(best['shapes']))})"
                    + (f"; {len(cands) - 1} other recurring number cell(s) ranked below "
                       f"it at y " + ", ".join(str(c['y']) for c in cands[1:4])
                       if len(cands) > 1 else ""))
        else:
            lay.notes.append("title block: no DWG NO. caption, and no hyphenated "
                             "number recurs at one position on a majority of sheets "
                             "with per-sheet values — the drawing-number cell could "
                             "not be found by caption or by structure")
    if "dwg_no_region" in tb:
        shapes = _drawing_no_shapes(pages, tb["dwg_no_region"])
        pat = _drawing_no_pattern(shapes)
        if pat:
            lay.add("formats.drawing_no", pat,
                    "the shapes this document prints in its own DWG NO. cell on two "
                    "or more sheets: " + ", ".join(f"{k} x{len(v)}" for k, v in
                                                   sorted(shapes.items(), key=lambda t: -len(t[1]))))
        else:
            lay.notes.append("formats.drawing_no is not derived: no hyphenated "
                             "number appears in the DWG NO. cell on two sheets")
    for key in ("rev_box", "sheet_box"):
        if key in tb:
            lay.add(f"title_block.{key}", tb[key],
                    f"the column under the form's own `{key.split('_')[0].upper()}` "
                    f"caption on the drawing-number row"
                    if key.split("_")[0] not in vocab_found else
                    f"the value beside or under the form's `{key.split('_')[0]}` "
                    f"caption matched by caption vocabulary")
    if tb.get("_captions"):
        lay.notes.append("title block captions found: "
                         + ", ".join(sorted(tb["_captions"])))
    if vocab_found:
        lay.notes.append("title block captions found by vocabulary: "
                         + ", ".join(sorted(vocab_found)))
    # hotfix29 — 3차: 캡션이 아예 없는 양식의 제목·REV 를 **구조**로.  도면번호 칸은
    # 위에서 되풀이로 섰고, 제목은 *장마다 같은 자리에 되풀이되며 값이 장마다 다른
    # 글줄 중 가장 큰 글자*, REV 는 *이력 표가 인쇄한 개정 표기만 값으로 갖는 되풀이
    # 칸*이다.  캡션이 하나라도 그 칸을 찾은 문서는 여기 안 온다.
    if "title_region" not in tb:
        tt = _recurring_title(pages, column, right, tb.get("dwg_no_region"))
        if tt:
            lay.add("title_block.title_region", tt["rect"],
                    f"no title caption is printed; taken as the recurring text row(s) "
                    f"whose value changes from sheet to sheet with the largest lettering "
                    f"({tt['height']} pt) in the title-block column, on {tt['pages']} sheets")
            lay.add("title_block.title_min_height", tt["min_height"],
                    "midway between that lettering and the next smaller recurring text")
        else:
            lay.notes.append("title block: no title caption and no recurring varying "
                             "text row in the column — the title cell is not derived")

    # 개정 이력 표 — 20회차까지 여섯 칸이 전부 AL NOUF1 실측 상수였고, 그래서 종이가
    # 다른 문서에서는 좌표 띠가 통째로 종이 밖이 됐다 (TC2 REV 0/60).  표의 모양이
    # 답하게 한다.  `hist_row_inset` 만은 여기서 정하지 않는다 — 아래 참조.
    inset = 1.2
    if cfg is not None:
        try:
            inset = float(cfg.get("title_block.hist_row_inset"))
        except Exception:
            inset = 1.2
    table_right = inner[-1] if inner else right
    hist = _history_table(pages, column, table_right, inset)
    if not hist:
        lay.notes.append("no revision-history table found in the title-block "
                         "column: no run of equally spaced rules crosses it")
    else:
        y0, y1, gap, vx = hist["y0"], hist["y1"], hist["gap"], hist["vx"]
        rows = int(round((y1 - y0) / gap))
        lay.add("title_block.hist_rule_y",
                [round(y0 - gap / 2, 1), round(y1 + gap / 2, 1)],
                f"the run of equally spaced rules crossing the title-block "
                f"column: {rows + 1} rules {gap:.2f} pt apart, the same on "
                f"{hist['votes']} of {hist['pages']} sheets; widened by half a "
                f"row, which no other rule of this table can be inside")
        lay.add("title_block.hist_rule_x0_max", round((vx[0] + vx[1]) / 2, 1),
                f"midway into the table's first column (the rules start at "
                f"{vx[0]:.1f}, the first vertical rule is at {vx[1]:.1f})")
        lay.add("title_block.hist_rule_x1_min", round((vx[-2] + vx[-1]) / 2, 1),
                f"midway into the table's last column (last vertical rule "
                f"{vx[-2]:.1f}, the table ends at {vx[-1]:.1f})")
        lay.add("title_block.hist_rev_col",
                [round(vx[0] + inset, 1), round(vx[1] - inset, 1)],
                "the table's first column, inset by hist_row_inset so the "
                "vertical rules themselves stay out of the cell")
        lay.add("title_block.hist_date_col",
                [round(vx[1] + inset, 1), round(vx[2] - inset, 1)],
                "the table's second column, inset the same way")
        # `hist_row_inset` 은 유도하지 않는다.  그것은 도면이 그린 것이 아니라
        # **렌더 여백**이다 — 행을 자를 때 괘선 자체가 clip 에 들어가지 않게 하는
        # 값이고, 도면에는 대응하는 선이 없다.  22회차 [7] 과 같은 자리:
        # 재지 못하는 것은 지어내지 않고 이름만 남긴다.
        lay.notes.append("hist_row_inset is not derived: it is a render margin, "
                         "not a drawn feature; the sheet states nothing about it")
        # 30회차 — **개정 표기가 어떻게 생겼는지도 도면이 말한다.**
        # `formats.revision` 은 AL NOUF1 에서 옮겨 적은 값(`^[A-Z][0-9]?$`)이고,
        # UAD 는 개정을 **숫자**로 매긴다.  그래서 REV 칸에 `6` 이 활자로
        # 인쇄돼 있는데도 `has_titleblock_text` 가 못 받아 글리프 경로로
        # 흘렀고, 그 경로는 이력 행을 A·B·C 로 이름 붙이므로 `G1` 이라는
        # 없는 값을 냈다 (32장 전부 신뢰도 LOW → 축3 개정 0/32).
        #
        # 읽는 곳은 **이력 표의 REV 열**이다 — 그 표가 바로 이 문서가 쓰는
        # 개정 표기의 목록이다.  머리글 행(`REV.` · `DATE`)을 섞지 않으려고
        # **DATE 열이 실제 날짜인 행만** 받는다 (`formats.date` 재사용).
        marks = _history_rev_marks(pages, hist, inset, cfg)
        if marks:
            lay.add("formats.revision", _revision_pattern(marks),
                    "the revision marks this document actually prints in the "
                    "history table's REV column, on rows whose DATE column "
                    "holds a date: " + ", ".join(sorted(marks)[:8]))
        else:
            lay.notes.append("formats.revision is not derived: the history "
                             "table's REV column carries no text on any sheet "
                             "(the marks are drawn as strokes)")

    # The dash geometry is measured and reported but NOT adopted.  Every way of
    # picking the runs tried here either lets an ordinary broken line in or
    # excludes the chain dash: over the two documents the same measurement returns
    # 18.6 pt on one and 7.6 pt on the other, where the boundaries they need are
    # 26.3 and 21.3.  A number that is wrong in both directions is not a
    # derivation, so the value stays configured and this records what was seen.
    try:
        import legend_rules as _lr
        _unit = _lr.legend_unit(_lr.derive_butterfly(pages, cfg))
    except Exception:                                      # noqa: BLE001
        _unit = 1.0
    dash = _dash_geometry(pages, (left, top, column, bottom), _unit)
    if dash:
        lay.add("broken_line.brk_max_mark", dash["brk_max_mark"],
                f"marks in runs beside a scope label: longest {dash['_longest']}pt "
                f"over {dash['_marks']}; not adopted - the same rule reads 18.6pt "
                f"on one document and 7.6 on the other while the boundaries need "
                f"26.3 and 21.3, so it isolates neither",
                source="UNAVAILABLE")
        lay.add("broken_line.brk_max_gap", dash["brk_max_gap"],
                f"widest gap in those runs: {dash['_widest_gap']}pt; not adopted, "
                f"same reason", source="UNAVAILABLE")

    dup = _systematic_duplicates(pages)
    lay.add("text.dedup_exact_duplicates", bool(dup["systematic"]),
            f"words repeated at identical coordinates on "
            f"{dup['pages_with_duplicates']} of {dup['pages']} pages "
            f"(median {dup['median_per_page']} per page); the export stamps its "
            f"own furniture when that holds across the set")

    import detect_symbols as ds
    ven = _vendor_notation(pages, ds.LAYOUT)
    lay.add("vendor_marks.glyph_sizes", ven["glyph_sizes"],
            f"sizes this document's own mark legends print, kept where more than "
            f"one page shows them: {ven['seen']}; "
            f"{ven['typed']} marks are typed as text instead")

    scripts = _markup_script(pages, (left, top, column, bottom))
    lay.notes.append("review markup by script: " + "; ".join(
        f"{k} {v['in_highlight']} highlighted / {v['elsewhere']} not"
        for k, v in scripts.items()))
    # The reviewers' script is the one this document only writes on a highlight,
    # or - where the drawing itself never uses it - the one it uses at all.
    ranges = {"HANGUL": "가-힣", "LOWER": "a-z"}
    # The reviewers' script is the one this document writes on a highlight most
    # often - a note is written over the drawing, and a highlight is what "over"
    # looks like.  Chosen by that count rather than by the order they are listed.
    pick = max(scripts, key=lambda k: scripts[k]["in_highlight"])
    picked = scripts[pick]
    if picked["in_highlight"]:
        lay.add("review_markup.script_ranges", [ranges[pick]],
                f"{pick}: {picked['in_highlight']} occurrences on a highlight "
                f"against {picked['elsewhere']} elsewhere; the other script has "
                + ", ".join(f"{k} {v['in_highlight']}/{v['elsewhere']}"
                            for k, v in scripts.items() if k != pick))
        lay.add("review_markup.requires_fill", picked["elsewhere"] > 0,
                f"the drawing writes this script {picked['elsewhere']} times "
                f"outside a highlight, so the script alone would take those for "
                f"notes and the highlight is what separates them"
                if picked["elsewhere"] else
                "the drawing never writes this script outside a highlight, so "
                "the script alone identifies a note")

    side = _scope_label_side(pages, (left, top, column, bottom))
    if side["labels_on_left"] or side["labels_on_right"]:
        lay.add("sct_scope.box_from_both_edges", side["labels_on_right"] > 0,
                f"scope labels: {side['labels_on_left']} beside a left edge, "
                f"{side['labels_on_right']} beside a right edge")
    return lay
