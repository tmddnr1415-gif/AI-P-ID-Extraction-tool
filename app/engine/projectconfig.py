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


def load(path: str | Path = None) -> ProjectConfig:
    p = Path(path or os.environ.get("PID_PROJECT_CONFIG") or DEFAULT_CONFIG)
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
    p = Path(path)
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


# --------------------------------------------------------------------------
# Unit multiplier, derived from the legend
# --------------------------------------------------------------------------
HEADING = ("UNIT", "IDENTIFICATION", "NUMBERS")
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
            "LEGEND", table, scopes, labels,
            note=(f"legend p{pc.page_no}: "
                  + ", ".join(f"{sc}x{n}" for sc, n in sorted(counts.items()))))

    fallback = cfg.data.get("unit_multiplier_fallback") or {}
    return UnitMultipliers(
        "CONFIG_FALLBACK", {str(k): int(v) for k, v in fallback.items()}, {}, {},
        note="legend UNIT IDENTIFICATION NUMBERS table not found; "
             "using unit_multiplier_fallback from the project config")
