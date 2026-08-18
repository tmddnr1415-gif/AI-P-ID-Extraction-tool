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
    # Sheets whose unit code the client leaves off the line (measured: unit 00).
    unit_prefix_skip: tuple = ()
    # The client's own spelling for a variable, where it differs from the legend's.
    variable_words: dict = field(default_factory=dict)
    # The instrument types whose lines carry a position word in the majority.
    position_word_types: frozenset = frozenset()
    # Equipment nouns whose lines always carry a position word (measured: 115 of
    # the client's 158 sit against a pump).  Kept for the record; the type gate
    # below replaced it, because by noun the rule cost PI and TI 13pp of
    # precision - see `position_word_types`.
    pump_nouns: frozenset = frozenset()
    # The instrument types whose lines end in a letter.  Measured over the 557:
    # PIT 44/106, TIT 36/97, FIT 26/31, PDIT 6/52, LIT 5/29 do; PI 0/111,
    # TI 0/59, LS 0/22, RO 0/19, FE 0/18, LI 0/10, FS 0/3 never do.
    end_ordinal_types: frozenset = frozenset()
    # What a switch's trailing H / L letters read as, off the client's own lines.
    alarm_suffix: dict = field(default_factory=dict)
    # `{(type, side): word}` where the client's own lines have a majority word for
    # an instrument on that side of its subject.
    position_by_side: dict = field(default_factory=dict)
    # `{phrase: abbreviation}` - the drawing title's words as the client writes them.
    system_abbreviations: dict = field(default_factory=dict)
    # `{(system abbreviation, type): word}` - a word a whole system uses.
    position_by_system: dict = field(default_factory=dict)
    # `{noun: word}` - what the client writes against a kind of equipment, with an
    # empty string for a kind it never gives a position word at all.
    position_by_noun: dict = field(default_factory=dict)
    source: str = "CONFIG"
    note: str = ""
    evidence: dict = field(default_factory=dict)


def derive_pattern(cfg=None) -> Pattern:
    cfg = cfg or projectconfig.load()
    d = (cfg.data.get("description") or {})
    skip = tuple(str(c) for c in (d.get("unit_prefix_skip_codes") or ()))
    variables = {str(k).upper(): tuple(str(w).upper() for w in v)
                 for k, v in (d.get("variable_words") or {}).items()}
    pos_types = frozenset(str(t).upper()
                          for t in (d.get("position_word_types") or ()))
    pumps = frozenset(str(t).upper() for t in
                      ((d.get("position_words") or {}).get("pump_nouns") or ()))
    end_types = frozenset(str(t).upper()
                          for t in (d.get("end_ordinal_types") or ()))
    alarms = {str(k).upper(): tuple(str(w).upper() for w in v)
              for k, v in (d.get("alarm_suffix") or {}).items()}
    sides = {}
    for key, word in (d.get("position_by_side") or {}).items():
        type_, _s, side = str(key).upper().partition(" ")
        if side:
            sides[(type_, side)] = str(word).upper()
    abbrev = {" ".join(tokens(str(k))): str(v).upper()
              for k, v in (d.get("system_abbreviations") or {}).items()}
    by_system = {}
    for key, word in (d.get("position_by_system") or {}).items():
        abb, _s, type_ = str(key).upper().rpartition(" ")
        if abb:
            by_system[(abb, type_)] = str(word).upper()
    by_noun = {str(k).upper(): str(v or "").upper()
               for k, v in (d.get("position_by_noun") or {}).items()}
    stop = frozenset(str(w).upper() for w in
                     ((cfg.data.get("matching") or {}).get("stopwords") or ()))
    return Pattern(
        prefix=str(d.get("prefix") or "UNIT"),
        unit_mark=str(d.get("unit_mark") or "#"),
        title_open=tuple(str(w).upper() for w in (d.get("title_open") or ("FOR",))),
        title_close=tuple(str(w).upper() for w in (d.get("title_close") or ("SYSTEM",))),
        stopwords=stop,
        note=str(d.get("note") or ""),
        unit_prefix_skip=skip,
        variable_words=variables,
        position_word_types=pos_types,
        pump_nouns=pumps,
        end_ordinal_types=end_types,
        alarm_suffix=alarms,
        position_by_side=sides,
        system_abbreviations=abbrev,
        position_by_system=by_system,
        position_by_noun=by_noun,
        evidence={"template": d.get("template") or "", "measured_on": d.get("measured_on") or ""})


def variable_words(tag: str, isa, pat: Pattern) -> tuple:
    """The words the client uses for this tag's variable.

    The legend's matrix is the source, except where the client demonstrably
    spells it differently - `DIFFERENTIAL PRESSURE` 52 lines against the matrix's
    `PRESSURE DIFFERENTIAL` 0 - and for tags the matrix does not carry at all,
    such as `RO`.  Both live in `config description.variable_words` with their
    counts, marked PROJECT because they are the client's wording, not a legend
    derivation.
    """
    up = str(tag).upper()
    base = ()
    for n in (4, 3, 2, 1):
        if up[:n] in pat.variable_words:
            base = pat.variable_words[up[:n]]
            break
    if not base:
        base = tuple(isa.words_for(tag)) if isa is not None else ()
    return tuple(base) + alarm_words(up, base, pat)


def alarm_words(tag: str, base, pat: Pattern) -> tuple:
    """`HIGH HIGH` / `HIGH` off the end of a switch's own tag.

    The legend's succeeding-letter table stops at `S SWITCH` - it defines no `H`
    or `L` modifier at all - so the words come from the client's own list, where
    `LSHH` reads `LEVEL HIGH HIGH` in 11 lines and `LSH` reads `LEVEL HIGH` in 11.
    The drawing already tells us which is which: the bubble is tagged `LSHH`,
    `LSH` or `LSL`, and that tag is what the row carries.
    """
    if not pat.alarm_suffix or not base:
        return ()
    for n in (2, 1):
        if len(tag) > n and tag[-n:] in pat.alarm_suffix:
            return pat.alarm_suffix[tag[-n:]]
    return ()


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
        return _abbreviate(toks[open_i + 1:close_i], pat), "TITLE_BRACKETED"
    rest = [t for t in toks if t not in pat.stopwords and not t.isdigit()]
    return _abbreviate(rest, pat), "TITLE_STOPWORDS"


def _abbreviate(words, pat: Pattern) -> list:
    """The client's own short form for a title phrase, where it has one.

    Found by taking each title phrase's initials and counting both forms in the
    client's lines for that sheet.  Two phrases out of thirty-five come back
    short - `CLOSED COOLING WATER` is `CCW` on 127 lines and never written out,
    `AUX. COOLING WATER` is `ACW` on 4 - and every other title phrase the client
    writes in full: HP STEAM 12 of 12, CRH STEAM 11 of 11, CLEAN DRAIN 9 of 9.
    So this is a two-entry dictionary the counting found, not a rule that
    initials replace phrases.
    """
    short = pat.system_abbreviations.get(" ".join(words))
    return [short] if short else list(words)


# Which way a system phrase already said by the subject is removed.  Both were
# measured; see the note above `assemble`.
DEDUP_WHOLE = True


def assemble(unit_code: str, title: str, tag: str, isa, pat: Pattern,
             subject: dict = None, suffix: str = "", type_: str = "",
             between: str = "") -> dict:
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
    var = " ".join(variable_words(tag, isa, pat))
    parts = list(base["parts"])
    sources = list(base["sources"])
    middle = ""
    if subject:
        eq = subject.get("equipment") or {}
        bits = [subject.get("text", "").strip()]
        if eq.get("ordinal"):
            bits.append(eq["ordinal"])
        # The client attaches a position word by *type*, not by geometry and not
        # by equipment noun.  Measured over its 557 lines: FS 3/3, PIT 75/106,
        # PDIT 35/52, FIT 13/31, FE 7/18, TIT 31/97 carry one; PI 7/111,
        # TI 7/59, RO 1/19 and LIT / LS / LI 0/61 effectively never do.  Going by
        # the equipment noun instead - "a pump's line always carries one" - put
        # SUCTION on PI and TI rows the client leaves bare, which is why the type
        # decides on its own (config description.position_word_types).
        wants_position = (str(type_).upper() in pat.position_word_types
                          if type_ else True)
        # Geometry answers left and right - a pump's suction is on one side and
        # its discharge on the other.  It says nothing about above and below, and
        # the client mostly writes nothing there.  Where its own lines do have a
        # majority word for a type on a side, that word is used and nothing else
        # is invented (config description.position_by_side, with the counts).
        # A whole system can have its own word: on the closed cooling water
        # sheets every TI the client writes is on the RETURN - 51 lines of 54 -
        # whichever side of the cooler it is drawn on.  Its PI is an even split,
        # 49 SUPPLY against 51 RETURN in every direction, so nothing is attached
        # there (config description.position_by_system, with the counts).
        system = " ".join(system_words(title, pat)[0])
        # A kind of equipment can settle the word on its own, and can settle that
        # there is none: the client writes a position word against 0 of its 59 TANK
        # lines, while a VALVE takes DOWNSTREAM on 30 of 65 and a HEADER DISCHARGE
        # on 16 of 32.  Left and right only name a side; they do not know that a
        # tank has no inlet worth writing down
        # (config description.position_by_noun, with the counts).
        noun = str(eq.get("noun") or "").upper()
        if noun in pat.position_by_noun:
            word = pat.position_by_noun[noun]
        else:
            word = (pat.position_by_system.get((system, str(type_).upper()), "")
                    or eq.get("position_word")
                    or pat.position_by_side.get(
                        (str(type_).upper(),
                         str(subject.get("direction") or "").upper()), ""))
        if word and (wants_position
                     or (system, str(type_).upper()) in pat.position_by_system):
            bits.append(word)
            eq = dict(eq, position_word=word)
        # What sits between the instrument and the equipment - `SUCTION STRAINER`
        # in 13 of the client's lines, always before the variable word.
        if between:
            bits.append(between)
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
    # The client does not repeat itself: only 29 of its 557 lines carry the same
    # word twice.  So a system word already inside the subject - `FUEL OIL SUPPLY`
    # in front of `FUEL OIL STORAGE TANK` - is dropped rather than said twice.
    head = [p for p in parts if p != var]
    if middle:
        # The system name is a phrase, not a bag of words: `FUEL OIL SUPPLY` in
        # front of `FUEL OIL STORAGE TANK` is dropped whole rather than trimmed to
        # `SUPPLY`, which is not something the client ever writes.
        seen = set(tokens(middle))
        # The unit prefix is never dropped: the drawing prints `#10 CLEAN DRAIN
        # TANK` on the label and the client still writes `UNIT #10 CLEAN DRAIN
        # TANK`, so matching on `#10` and dropping the prefix loses a word the
        # client always writes (454 of its 557 lines carry the mark).  The label's
        # own copy of the mark goes instead, so the line reads it once.
        head = [p for p in head
                if p.startswith(pat.prefix) or not (set(tokens(p)) & seen)] \
            if DEDUP_WHOLE else [
                p if p.startswith(pat.prefix)
                else " ".join(w for w in tokens(p) if w not in seen)
                for p in head]
        head = [p for p in head if p]
        marks = {w for p in head if p.startswith(pat.prefix) for w in tokens(p)
                 if w.startswith(pat.unit_mark)}
        if marks:
            middle = " ".join(w for w in middle.split() if w not in marks)
    # A trailing letter is written only by the types that write one.  The client
    # repeats itself rather than disambiguate on PI (0 of 111 lines end in a
    # letter, and 24 of them are exact repeats of another line on the same
    # sheet), so a letter added there is a word the client never wrote.
    if suffix and type_ and pat.end_ordinal_types \
            and str(type_).upper() not in pat.end_ordinal_types:
        suffix = ""
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
    if unit_code and str(unit_code) not in pat.unit_prefix_skip:
        parts.append(f"{pat.prefix} {pat.unit_mark}{unit_code}")
        sources.append(f"UNIT: 도면 타이틀블록 unit code {unit_code} + 템플릿 접두어")
    elif unit_code:
        sources.append(f"UNIT: unit code {unit_code} 는 발주처가 접두어를 쓰지 않는 "
                       f"코드입니다 (실측 98행 중 98행 생략)")
    sysw, how = system_words(title, pat)
    if sysw:
        parts.append(" ".join(sysw))
        sources.append(f"SYSTEM: 도면 제목 “{title}” ({how})")
    else:
        reasons.append(NO_SYSTEM)
    var = variable_words(tag, isa, pat)
    if var:
        parts.append(" ".join(var))
        client = str(tag).upper()[:4] in pat.variable_words or \
            str(tag).upper()[:2] in pat.variable_words
        sources.append(
            (f"VARIABLE: 발주처 표기 — {tag} → {' '.join(var)} "
             f"(config description.variable_words)") if client else
            (f"VARIABLE: 범례 p{getattr(isa, 'page_no', '?')} ISA "
             f"문자표 — {tag[:2]} → {' '.join(var)}"))
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
