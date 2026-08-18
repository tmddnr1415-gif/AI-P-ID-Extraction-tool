"""Build a Description from the drawing, with rules only.

The Description column has to be delivered, and pipe tracing reaches 13% of rows,
so this asks a different question: how much of the client's own wording can be
assembled without following a pipe at all?  Every part comes from a source that
was measured first (see README "Description — 토큰 출처"):

    UNIT #<n>   the title block's unit code.  The word `UNIT` itself is printed on
                no drawing; it is the client's own fixed prefix, so it comes from
                the template below rather than from the sheet
    <system>    the drawing title, between the words the titles themselves use to
                bracket it (`P&ID FOR` ... `SYSTEM`)
    <variable>  legend page 3's identification matrix, via `isa_table`
    <suffix>    NOT produced.  `A` / `B` / `C` (129 instances) and `HIGH` /
                `HIGH HIGH` (22) appear nowhere on the page the row belongs to, so
                there is nothing to read them from

What this deliberately does **not** do: invent the middle of the sentence.  The
client's middle segment runs 5-6 tokens on average and names equipment
("GENERATOR HYDROGEN GAS COOLER CCW RETURN"); measured against the drawing title,
49.7% of middles have *no* word in common with it and only 2.9% are fully
contained in it.  Where that text sits on the sheet was measured too: half the
tokens need a 240 pt radius around the symbol and 91% need 480 pt, which on a
2384 pt sheet is a fifth of the drawing - a radius that wide collects hundreds of
unrelated words.  So a line assembled from proximity would be a guess dressed as
a measurement, and this module reports `NEEDS_REVIEW` instead of writing one.

No LLM.  No NOTES prose.  No radius that was not measured.
"""

from __future__ import annotations

import collections
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import projectconfig  # noqa: E402

TOKEN_RE = re.compile(r"[A-Z0-9#&/\-\.]+")

# What a row is missing when no line can be written for it.
NO_VARIABLE = "ISA 문자표에 없는 태그 — 변수어를 유도할 수 없습니다"
NO_SYSTEM = "도면 제목에서 계통명을 분리할 수 없습니다"
INCOMPLETE = ("근접 텍스트만으로는 중간 서술(대상 기기)을 세울 수 없습니다 — "
              "측정: 발주처 중간 서술의 49.7%가 도면 제목과 한 낱말도 겹치지 않고, "
              "토큰의 절반이 심볼에서 240pt 이상 떨어져 있습니다")


def tokens(s) -> list:
    return [t for t in TOKEN_RE.findall(str(s).upper()) if any(c.isalnum() for c in t)]


@dataclass
class Pattern:
    """The client's sentence shape, as a project fact rather than a guess.

    It is derived from the client's own finished list - 557 Description lines -
    and recorded in `config description`, with the counts that justify each part
    kept beside it there.  It is config and not a runtime derivation because in
    real use there is no finished list to derive it from: what the user has is a
    PDF and an empty form.
    """

    prefix: str = "UNIT"
    unit_mark: str = "#"
    title_open: tuple = ("FOR",)
    title_close: tuple = ("SYSTEM",)
    stopwords: frozenset = frozenset()
    source: str = "CONFIG"
    note: str = ""
    evidence: dict = field(default_factory=dict)


def derive_pattern(cfg=None) -> Pattern:
    cfg = cfg or projectconfig.load()
    d = (cfg.data.get("description") or {})
    stop = frozenset(str(w).upper() for w in
                     ((cfg.data.get("matching") or {}).get("stopwords") or ()))
    return Pattern(
        prefix=str(d.get("prefix") or "UNIT"),
        unit_mark=str(d.get("unit_mark") or "#"),
        title_open=tuple(str(w).upper() for w in (d.get("title_open") or ("FOR",))),
        title_close=tuple(str(w).upper() for w in (d.get("title_close") or ("SYSTEM",))),
        stopwords=stop,
        note=str(d.get("note") or ""),
        evidence={"template": d.get("template") or "", "measured_on": d.get("measured_on") or ""})


def system_words(title: str, pat: Pattern) -> list:
    """The system name out of a drawing title.

    The titles bracket it themselves - `P&ID FOR HP STEAM SYSTEM GROUP 10` - so
    the words between the bracket words are taken, and nothing is trimmed by
    length or position.  A title that does not use those words falls back to its
    own tokens minus the stopword list this project already uses for title
    matching, which is a weaker answer and is reported as one.
    """
    toks = tokens(title)
    open_i = next((i for i, t in enumerate(toks) if t in pat.title_open), None)
    close_i = next((i for i, t in enumerate(toks) if t in pat.title_close), None)
    if open_i is not None and close_i is not None and open_i + 1 < close_i:
        return toks[open_i + 1:close_i], "TITLE_BRACKETED"
    rest = [t for t in toks if t not in pat.stopwords and not t.isdigit()]
    return rest, "TITLE_STOPWORDS"


def assemble(unit_code: str, title: str, tag: str, isa, pat: Pattern,
             subject: dict = None, suffix: str = "") -> dict:
    """The client's sentence shape, with a subject in the middle when there is one.

    Order is the one counted in the client's 557 lines:

        UNIT #<n>  <system>  <subject> [<ordinal>] [<position word>]  <variable> [<suffix>]

    - 81.3% of lines begin `UNIT #<n>`
    - the equipment's ordinal follows its noun (172 lines: `PUMP A SUCTION ...`)
    - the variable word comes last, and 357 of 538 lines end on it
    - an instrument ordinal goes after the variable (117 lines: `... PRESSURE A`)

    `subject` is a candidate from `describe_candidates`; without one this is the
    rules-only line the previous round produced, unchanged.
    """
    base = describe(unit_code, title, tag, isa, pat)
    var = " ".join(isa.words_for(tag)) if isa is not None else ""
    parts = list(base["parts"])
    sources = list(base["sources"])
    middle = ""
    if subject:
        eq = subject.get("equipment") or {}
        bits = [subject.get("text", "").strip()]
        if eq.get("ordinal"):
            bits.append(eq["ordinal"])
        if eq.get("position_word"):
            bits.append(eq["position_word"])
        middle = " ".join(b for b in bits if b)
        if eq:
            sources.append(
                f"SUBJECT: 도면 기기 라벨 “{subject.get('text','')}”"
                + (f" (순번 {eq['ordinal']}, {eq.get('evidence',{}).get('ordinal_axis','')})"
                   if eq.get("ordinal") else "")
                + (f", 계기가 기기의 {subject.get('direction','')} → "
                   f"{eq['position_word']}" if eq.get("position_word") else "")
                + f", 거리 {subject.get('distance')}pt")
        else:
            sources.append(f"SUBJECT: 라인 표기 “{subject.get('text','')}” "
                           f"({subject.get('kind')}, {subject.get('distance')}pt)")
    # variable last, then the instrument's own ordinal
    head = [p for p in parts if p != var]
    line = " ".join(x for x in (" ".join(head), middle, var, suffix) if x)
    return {
        "text": " ".join(line.split()),
        "parts": parts,
        "middle": middle,
        "suffix": suffix,
        "sources": sources,
        "complete": bool(middle),
        "reason": "" if middle else base["reason"],
    }


def describe(unit_code: str, title: str, tag: str, isa, pat: Pattern) -> dict:
    """One row's Description, or an empty one with the reason it is empty.

    Returns `{"text", "parts", "sources", "complete", "reason"}`.  `complete` is
    False whenever the middle of the client's sentence could not be sourced, which
    on this document is every row - see the module docstring.  The text is still
    returned so a reviewer can see how far the drawing gets on its own, and the
    caller decides whether to ship it; `pipeline` leaves the column blank and
    flags the row.
    """
    parts, sources, reasons = [], [], []
    if unit_code:
        parts.append(f"{pat.prefix} {pat.unit_mark}{unit_code}")
        sources.append(f"UNIT: 도면 타이틀블록 unit code {unit_code} + 템플릿 접두어")
    sysw, how = system_words(title, pat)
    if sysw:
        parts.append(" ".join(sysw))
        sources.append(f"SYSTEM: 도면 제목 “{title}” ({how})")
    else:
        reasons.append(NO_SYSTEM)
    var = isa.words_for(tag) if isa is not None else ()
    if var:
        parts.append(" ".join(var))
        sources.append(f"VARIABLE: 범례 p{getattr(isa, 'page_no', '?')} ISA "
                       f"문자표 — {tag[:2]} → {' '.join(var)}")
    else:
        reasons.append(NO_VARIABLE)
    # The middle is never assembled; see the module docstring for the measurement.
    reasons.append(INCOMPLETE)
    return {
        "text": " ".join(parts),
        "parts": parts,
        "sources": sources,
        "complete": False,
        "reason": "; ".join(reasons),
    }


def coverage(lines, unit_of, title_of, tag_of, isa, pat: Pattern) -> dict:
    """Score generated lines against finished ones, token by token.

    `lines` is `[(key, reference_text)]`; the rest are lookups by key.  Reported as
    exact / partial / miss plus token precision and recall, because on a sentence
    this long an exact-match rate alone hides whether the parts that were produced
    were right.
    """
    stat = collections.Counter()
    tp = fp = fn = 0
    for key, ref in lines:
        got = describe(unit_of(key), title_of(key), tag_of(key), isa, pat)["text"]
        a, b = tokens(got), tokens(ref)
        if a == b:
            stat["exact"] += 1
        elif set(a) & set(b):
            stat["partial"] += 1
        else:
            stat["miss"] += 1
        ca, cb = collections.Counter(a), collections.Counter(b)
        for t in set(ca) | set(cb):
            hit = min(ca[t], cb[t])
            tp += hit
            fp += ca[t] - hit
            fn += cb[t] - hit
    total = sum(stat[k] for k in ("exact", "partial", "miss"))
    return {
        "lines": total, "exact": stat["exact"], "partial": stat["partial"],
        "miss": stat["miss"],
        "token_precision": round(100 * tp / (tp + fp), 1) if tp + fp else 0.0,
        "token_recall": round(100 * tp / (tp + fn), 1) if tp + fn else 0.0,
    }
