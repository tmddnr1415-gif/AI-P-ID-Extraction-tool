"""Project configuration loader, and the legend-derived unit multiplier table.

Two jobs:

1. **Load the project-dependent values** (out/project_deps.md, items P1..P18)
   from a YAML file, with no defaults anywhere.  A lookup that misses does not
   fall back to a plausible value — it returns "undefined" and the caller is
   expected to record NEEDS_REVIEW with a reason and leave the field empty.
   A wrong quantity is worse than a blank one on an instrument list
   (docs/design.md §8.3), and a default is a wrong quantity that looks right.

2. **Derive the unit-code multiplier from the Symbol & Legend sheet** rather
   than from configuration.  Legend page 5 prints a UNIT IDENTIFICATION NUMBERS
   table that states the plant's breakdown outright:

       POWER PLANT COMMON                              0
       FIRST GROUP COMMON (INCL. FIRST GROUP STG)     10
       FIRST GROUP #1 GTG / HRSG                      11
       FIRST GROUP #2 GTG / HRSG                      12
       SECOND GROUP COMMON (INCL. SECOND GROUP STG)   20
       SECOND GROUP #1 GTG / HRSG                     21
       SECOND GROUP #2 GTG / HRSG                     22

   Counting the rows at each scope gives the multiplier directly: one plant
   scope (x1), two group-common scopes (x2), four unit scopes (x4).  A plant
   with three groups would print more rows and the same code would produce x3
   and x6 without anyone editing a constant.  The configured table is a
   fallback for when the legend cannot be parsed, and using it is logged.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

UNDEFINED = object()


class ConfigError(RuntimeError):
    """Raised when the config file itself is unusable — never for a missing key."""


@dataclass
class ProjectConfig:
    path: Path
    data: dict
    misses: list = field(default_factory=list)

    def get(self, dotted: str):
        """Fetch a configured value, or raise if the config omits it.

        Used for values the pipeline cannot run without (sheet geometry, Excel
        column numbers).  Failing loudly at start-up beats detecting nothing and
        reporting a clean zero.
        """
        node = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                raise ConfigError(
                    f"{self.path.name}: required setting '{dotted}' is missing")
            node = node[part]
        return node

    def lookup(self, dotted: str, key):
        """Fetch one entry of a configured mapping.

        Returns UNDEFINED when the key is absent.  Callers must branch on that
        and emit NEEDS_REVIEW; they must not substitute a value.
        """
        try:
            table = self.get(dotted)
        except ConfigError:
            self.misses.append(f"{dotted} (table absent)")
            return UNDEFINED
        if not isinstance(table, dict) or key not in table:
            self.misses.append(f"{dotted}[{key!r}]")
            return UNDEFINED
        return table[key]

    def get_or(self, dotted: str, default):
        """The configured value, or the caller's own, with the miss recorded.

        For the layout readers, which are built at import - before any document
        has been opened - from a profile that may deliberately leave the sheet's
        geometry out, because the sheet states it and `derive_layout` reads it.
        The default here is the reader's own measured constant, and the pipeline
        overwrites it once the pages are open; either way `misses` says the
        profile was silent, so nothing is guessed without a record.
        """
        try:
            return self.get(dotted)
        except ConfigError:
            self.misses.append(f"{dotted} (not stated; measured from the sheet)")
            return default

    def overlay(self, values: dict) -> list:
        """Write measured values over the profile, and say which moved.

        Used when the profile loaded is not this document's - the geometry in it
        then describes someone else's sheet, and what the sheet in hand states
        about itself is the better answer.  Returns `[(key, was, now)]`.
        """
        moved = []
        for dotted, value in values.items():
            parts = dotted.split(".")
            node = self.data
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            was = node.get(parts[-1], UNDEFINED)
            if was != value:
                moved.append((dotted, None if was is UNDEFINED else was, value))
            node[parts[-1]] = value
        return moved

    def rect(self, dotted: str) -> tuple:
        v = self.get(dotted)
        if not (isinstance(v, list) and len(v) == 4):
            raise ConfigError(f"{self.path.name}: '{dotted}' must be [x0,y0,x1,y1]")
        return tuple(float(x) for x in v)

    def pair(self, dotted: str) -> tuple:
        v = self.get(dotted)
        if not (isinstance(v, list) and len(v) == 2):
            raise ConfigError(f"{self.path.name}: '{dotted}' must be a 2-element list")
        return tuple(float(x) for x in v)


# Which project profile a run uses.  Every module reads its config at import
# time and there is no argument to thread through them, so the choice is an
# environment variable and the default is unchanged - with `PID_PROJECT_CONFIG`
# unset this loads exactly the file it always loaded.  Selecting a profile is
# not the same thing as having one: a second project still has to supply every
# value, because nothing in this file falls back.
DEFAULT_CONFIG = "config/project_alnouf1.yaml"


def _bundled(rel: str) -> Path:
    """A shipped file, found whether this is a checkout or a packaged exe.

    A relative path is relative to the *build*, not to wherever the user happened
    to double-click from, so it is resolved against the resource root.  An
    absolute path - which is what `PID_PROJECT_CONFIG` gives - is left alone.
    """
    p = Path(rel)
    if p.is_absolute() or p.exists():
        return p
    from app import paths                      # local: keeps engine/ importable alone
    return paths.resource(*p.parts)


def load(path: str | Path = None) -> ProjectConfig:
    p = _bundled(str(path or os.environ.get("PID_PROJECT_CONFIG") or DEFAULT_CONFIG))
    if not p.exists():
        raise ConfigError(f"project config not found: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError(f"{p}: expected a mapping at the top level")
    return ProjectConfig(p, data)


def load_standard(path: str | Path = "config/plant_standard_abbr.yaml") -> dict:
    """The trade dictionary: abbreviations that hold on any power plant.

    Kept in its own file and loaded separately from the project config, because it
    is the one part of the configuration meant to be carried to the next project
    unchanged.  Missing is not an error - a project that has not been given one
    simply applies no aliases.
    """
    p = _bundled(str(path))
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


# --------------------------------------------------------------------------
# Unit multiplier, derived from the legend
# --------------------------------------------------------------------------
HEADING = ("UNIT", "IDENTIFICATION", "NUMBERS")

# 승수표가 **이 도면에서** 나왔는가 아닌가.  이름이 한 곳에 있어야 파이프라인이
# "이 값은 남의 도면에서 왔다" 를 문자열 비교로 묻지 않는다 (26회차).
SOURCE_LEGEND = "LEGEND"
SOURCE_CONFIG = "CONFIG_FALLBACK"
_CODE_RE = re.compile(r"^\d{1,2}$")

# How a row's label maps to a replication scope.  These three phrasings are the
# legend's own vocabulary, not project data: the table names a plant level, a
# group-common level and a per-unit level.
_PLANT = re.compile(r"PLANT\s+COMMON")
_GROUP = re.compile(r"GROUP\s+COMMON")
_UNIT = re.compile(r"#\s*\d")


@dataclass
class UnitMultipliers:
    source: str                    # LEGEND | CONFIG_FALLBACK
    table: dict                    # code -> multiplier
    scopes: dict                   # code -> scope name
    labels: dict                   # code -> legend label
    note: str = ""

    def multiplier(self, code: str):
        """Multiplier for a unit code, or UNDEFINED if the legend never named it."""
        return self.table.get(code, UNDEFINED)


def _rows_near_heading(pc, y_span=260.0):
    """The label/code rows under a UNIT IDENTIFICATION NUMBERS heading."""
    words = pc.words
    head = None
    for r, t in words:
        if t != HEADING[0]:
            continue
        line = sorted([(rr, tt) for rr, tt in words
                       if abs(rr.y0 - r.y0) < 6 and rr.x0 >= r.x0 - 2],
                      key=lambda z: z[0].x0)
        if [tt for _, tt in line[:3]] == list(HEADING):
            head = r
            break
    if head is None:
        return []

    # The code column is the right-most short numeric token under the heading.
    band = [(r, t) for r, t in words
            if head.y0 < r.y0 < head.y0 + y_span and abs(r.x0 - head.x0) < 700]
    codes = [(r, t) for r, t in band if _CODE_RE.match(t)]
    if not codes:
        return []
    code_x = max(r.x0 for r, _ in codes)
    codes = [(r, t) for r, t in codes if abs(r.x0 - code_x) < 6]

    rows = []
    for r, t in sorted(codes, key=lambda z: z[0].y0):
        # Bound the label on the left as well: the legend prints an unrelated
        # piping-material list in the neighbouring column at the same heights.
        label = " ".join(tt for rr, tt in sorted(band, key=lambda z: z[0].x0)
                         if abs(rr.y0 - r.y0) < 6
                         and r.x0 - 320 < rr.x0 < r.x0 - 4)
        rows.append((t, label.strip()))
    return rows


# ---------------------------------------------------------------------------
# 그 장 NOTES 가 말하는 "이 도면은 유닛 몇 개에 같이 쓰인다" (27회차)
# ---------------------------------------------------------------------------
#
# 도면이 스스로 말하는 자리다 (§9 ②).  실측 문형 넷 — 전부 같은 뜻이다:
#
#   AL NOUF1  THIS P&ID IS FOR GROUP #10, CONFIGURATION IS IDENTICAL FOR GROUP #20.
#   AL NOUF1  THIS P&ID IS FOR UNIT#11, CONFIGURATION IS IDENTICAL FOR UNIT#12,21,22.
#   TC2       THIS P&ID IS FOR UNIT 3-1. AND, SIMILAR SCHEME IS APPLICABLE TO
#             UNIT 3-2, UNIT 4-1, … UNIT 6-2.
#   TC2       … INSTRUMENTS SHALL BE IDENTICAL TO UNIT 3-1 AS SHOWN IN THIS P&ID.
#
# **세는 것이지 해석하지 않는다** — 그 문단이 열거한 유닛 표기의 개수가 곧 배수다.
# 문장 모양으로 찾지 않는 이유는 위 넷이 서로 다르기 때문이고, `IDENTICAL` 과
# `SIMILAR` 를 같게 보는 것은 사용자가 실무 기준으로 확인해 준 것이다.
#
# ⚠ 이 값은 **범례 표가 답하지 못할 때만** 쓴다 (`pipeline._field_rows`).
# AL NOUF1 은 대조 가능한 24장 중 23장에서 노트와 범례가 같고 p15 한 장만
# 어긋난다 (노트 4 ↔ 범례 2) — 어느 쪽이 옳은지는 도면이 두 말을 하므로,
# 이미 답이 있는 문서의 판정을 흔들지 않는다.
_SAME_WORD = re.compile(r"\b(IDENTICAL|SIMILAR|SAME)\b")
_UNIT_NUM = r"\d{1,2}(?:\s*-\s*\d{1,2})?"
# 낱말 뒤의 **꼬리까지** 읽는다 — `UNIT#12,21,22` 에서 꼬리를 버리면 4를 2로 센다
# (옛 스파이크 `parse_notes.GROUP_REF` 의 주석이 경고해 둔 자리다).
_UNIT_HEAD = re.compile(r"(?:GROUP|UNIT|TRAIN)S?\s*(?:NO\.?|#)?\s*(%s)" % _UNIT_NUM)
_UNIT_TAIL = re.compile(r"\s*(?:,|&|AND)\s*#?\s*(%s)" % _UNIT_NUM)
# 낱말 없이 이어지는 목록.  실측 두 문형 —
#   `… TYPICAL FOR UNIT 3-1 & 3-2, SIMILAR … APPLICABLE FOR 4-1 & 4-2, 5-1 & 5-2 AND 6-1 & 6-2`
#   `… COMMON FOR UNITS NO.3-1 & 3-2. … DUPLICATED FOR UNIT 4-1 & 4-2, 5-1 & 5-2, 6-1 & 6-2`
# 앞의 것은 뒤 여섯이 낱말 없이 나오고 뒤의 것은 앞 둘이 그렇다.  **낱말에 걸린
# 표기가 `3-1` 꼴일 때만** 같은 꼴을 더 줍는다 — 두 자리 맨숫자(`20 DIAMETERS`
# ·`ONE (1)`)까지 주우면 아무 숫자나 유닛이 된다.  한 자리-한 자리로 좁혀서
# 도면번호(`M05-0002`)와 날짜(`2026-08-21`)에 걸리지 않는다.
_UNIT_BARE = re.compile(r"(?<![\w-])(\d-\d)(?![\w-])")
_NUMBERED = re.compile(r"^\d+\.")


def _unit_tokens(text: str) -> list:
    """그 문단이 열거한 유닛 표기 (등장 순서, 중복 포함)."""
    out = []
    for m in _UNIT_HEAD.finditer(text):
        out.append(m.group(1))
        pos = m.end()
        while True:
            t = _UNIT_TAIL.match(text, pos)   # `^` 를 쓰면 안 된다 — match(pos) 가 그 자리다
            if not t:
                break
            out.append(t.group(1))
            pos = t.end()
    out = [re.sub(r"\s+", "", t) for t in out]
    if any(_UNIT_BARE.fullmatch(t) for t in out):
        out += _UNIT_BARE.findall(text)
    return out


def _note_paragraphs(pc, area, x_max) -> list:
    """그 장 NOTES 를 문단으로.

    줄은 **같은 y** 끼리만 묶는다 — `detect_symbols._notes_lines` 의 7pt 버킷은
    줄 간격이 9.3~11.2pt 인 문서에서도 **두 줄을 한 줄로 묶어** 낱말을 섞는다
    (TC2 p7 실측: `5. UNIT THIS 5-2, P&ID UNIT IS FOR 6-1, …`).  같은 자리에
    같은 낱말이 또 있으면 덧인쇄이므로 하나로 본다 (TC2 p10·p12 는 NOTES 를
    **두 번** 인쇄한다).
    """
    x0, y0, _x1, y1 = area
    rows, seen = {}, set()
    for r, t in pc.words:
        if not (x0 <= r.x0 <= x_max and y0 <= r.y0 <= y1):
            continue
        key = (round(r.x0, 1), round(r.y0, 1), t)
        if key in seen:
            continue
        seen.add(key)
        rows.setdefault(round(r.y0, 1), []).append((r.x0, t))
    paras, cur = [], ""
    for y in sorted(rows):
        line = " ".join(t for _x, t in sorted(rows[y]))
        if _NUMBERED.match(line.strip()):
            if cur:
                paras.append(cur)
            cur = line
        elif cur:
            cur += " " + line
        else:
            cur = line
    if cur:
        paras.append(cur)
    return paras


def note_unit_span(pc, area, x_max):
    """`(배수, 유닛 표기, 그 문단)` — 그 장 NOTES 가 말하지 않으면 `(None, [], "")`."""
    best = (None, [], "")
    for para in _note_paragraphs(pc, area, x_max):
        up = re.sub(r"\s+", " ", para.upper())
        if not _SAME_WORD.search(up):
            continue
        toks = list(dict.fromkeys(_unit_tokens(up)))
        if len(toks) >= 2 and (best[0] is None or len(toks) > best[0]):
            best = (len(toks), toks, up.strip())
    return best


def derive_unit_multipliers(pages, cfg: ProjectConfig, legend_kinds=("LEGEND",),
                            page_kinds: dict | None = None) -> UnitMultipliers:
    """Read the legend's unit table; fall back to config only if that fails."""
    candidates = [pc for pc in pages
                  if page_kinds is None or page_kinds.get(pc.page_no) in legend_kinds]
    for pc in candidates or pages:
        rows = _rows_near_heading(pc)
        if len(rows) < 3:
            continue

        scopes, labels = {}, {}
        for code, label in rows:
            code = code.zfill(2)          # the table prints plant common as '0'
            up = label.upper()
            if _PLANT.search(up):
                scopes[code] = "PLANT"
            elif _GROUP.search(up):
                scopes[code] = "GROUP"
            elif _UNIT.search(up):
                scopes[code] = "UNIT"
            else:
                continue
            labels[code] = label

        if not scopes:
            continue
        counts: dict[str, int] = {}
        for sc in scopes.values():
            counts[sc] = counts.get(sc, 0) + 1
        table = {code: counts[sc] for code, sc in scopes.items()}
        return UnitMultipliers(
            SOURCE_LEGEND, table, scopes, labels,
            note=(f"legend p{pc.page_no}: "
                  + ", ".join(f"{sc}x{n}" for sc, n in sorted(counts.items()))))

    fallback = cfg.data.get("unit_multiplier_fallback") or {}
    return UnitMultipliers(
        SOURCE_CONFIG, {str(k): int(v) for k, v in fallback.items()}, {}, {},
        note="legend UNIT IDENTIFICATION NUMBERS table not found; "
             "using unit_multiplier_fallback from the project config")
