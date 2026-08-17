"""Run the Phase 0 engine over one PDF and return rows, overlays and evidence.

This is orchestration only.  Every detection decision is made by
`app/engine/*`, which arrived here unchanged from `spike/`; nothing in this
file interprets geometry, and the call order is the same one the spike CLIs
use so their published numbers reproduce.

What it produces, per the scope agreed for the MVP:

    P&ID No.      title block (spike 1)
    Type          anchor -> Excel TYPE map (spike 2)
    Q'ty          symbol count x unit multiplier derived from legend p5 (spike 3)
    System        Excel SYSTEM matched to the drawing title (spike 2)
    Valve Type    body + actuator (spike 4)
    Vendor Supply page-scoped vendor mark (spike 2)
    Scope         supplier / package scope (spike 2)
    Description   left empty - needs line tracing, which is Phase 2
    Tag No.       left empty - the drawings carry `.....` placeholders

Rows carry their own evidence, because a reviewer's first question about any
row is "why".
"""

from __future__ import annotations

import collections
import contextlib
import hashlib
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ENGINE = Path(__file__).resolve().parent / "engine"
if str(ENGINE) not in sys.path:
    # The engine modules import each other by bare name through the sys.path
    # insert each one already carries.  Loading them the same way here keeps a
    # single copy of every module-level LAYOUT and of the config singleton;
    # importing them as `app.engine.x` as well would create a second set.
    sys.path.insert(0, str(ENGINE))

import pidcache            # noqa: E402
import projectconfig       # noqa: E402
import legend_rules        # noqa: E402
import extract_titleblocks as tb   # noqa: E402
import detect_symbols as ds        # noqa: E402
import detect_all as da            # noqa: E402
import detect_valves as dv         # noqa: E402
import parse_notes as pn           # noqa: E402
import pipe_graph                  # noqa: E402
import isa_table                   # noqa: E402
import describe as desc            # noqa: E402
import describe_candidates as dcand  # noqa: E402
import describe_llm                # noqa: E402

CFG = projectconfig.load()

# The exclusion set Phase 0 scored on.  `included_under` takes the rules that
# are *active* - not the ones that are disabled - and passing
# `detect_symbols.DEFAULT_DISABLED` here meant the three vendor-mark rules were
# never applied, so every vendor-supply symbol came through as a deliverable
# row.  This is the `v3_glyph_text_box` variant, the one out/failure_report.md
# calls the baseline at 97.0 / 87.0; SCT stays out of it for the reason
# detect_symbols.DEFAULT_DISABLED records.
ACTIVE_SCOPE = da.active_scope(da.BASELINE_SCOPE_NAME)

# Valve rules to switch off for this project, by name from `detect_valves
# .ALL_RULES`.  Empty by default: every measured rule applies.  This exists so a
# rule can be withdrawn from a delivery without editing the engine - and so the
# result records which rules were actually applied rather than implying all of
# them.  An unknown name is an error, not a no-op.
VALVE_DISABLED = frozenset(str(r) for r in
                           (CFG.data.get("valves") or {}).get("disabled_rules") or ())
_unknown = VALVE_DISABLED - set(dv.ALL_RULES)
if _unknown:
    raise SystemExit(f"config valves.disabled_rules: unknown rule(s) "
                     f"{', '.join(sorted(_unknown))}; "
                     f"known: {', '.join(dv.ALL_RULES)}")

# Which grid tab a row belongs to.  These are the four deliverables the client
# splits its packages by, plus the review queue.
TAB_FIELD = "FIELD"
TAB_BFV = "BFV"
TAB_MOV = "MOV"
TAB_PNEUMATIC = "PNEUMATIC"
TAB_REVIEW = "REVIEW"

# Where a row's drawing stands, reported per row so a reviewer can decide what
# to ship - the tool does not decide for them.
#
#   DRAWING       it is in the PDF.  Nothing else is claimed, and this is what
#                 every page is in normal use
#   REVISION_GAP  the drawing carries revision markup (out/revision_gap.md).
#                 Read off the drawing, so it needs no other input
#   MATCHED       verification mode only: the answer key covers this drawing,
#                 and this is the only set the Phase 0 accuracy numbers were
#                 ever measured on
#   PDF_ONLY      verification mode only: the answer key has no row for it
#
# A page can be both MATCHED and REVISION_GAP; the gap wins in the column
# because it is the one that changes what a reviewer should do about the row.
ORIGIN_DRAWING = "DRAWING"
ORIGIN_MATCHED = "MATCHED"
ORIGIN_PDF_ONLY = "PDF_ONLY"
ORIGIN_REVISION_GAP = "REVISION_GAP"


@dataclass
class Row:
    """One line of a deliverable, with the evidence that produced it."""

    key: str                       # stable identity across re-analysis
    tab: str
    page_no: int
    drawing_no: str
    origin: str = ""               # DRAWING | REVISION_GAP | (verify: MATCHED | PDF_ONLY)
    type: str = ""
    qty: object = None
    system: str = ""
    valve_type: str = ""
    vendor_supply: str = ""
    scope: str = ""
    description: str = ""          # Phase 2
    tag_no: str = ""               # not assigned on these drawings
    # Whether this row needs a Description at all.  A separate axis from `scope`:
    # `scope` decides whether the row is in the list, this decides whether a
    # sentence will ever be written for it.  See `_description_skip`.
    description_needed: bool = True
    description_note: str = ""
    # How much of the Description is evidenced, and what the reviewer must do
    # about it.  See GRADES.
    description_grade: str = ""
    remark: str = ""
    needs_review: str = ""         # engine uncertainty, empty when fine
    annotation: str = ""           # reviewer markup on the drawing, page-level
    rect: tuple = ()
    evidence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d["rect"] = [round(v, 1) for v in self.rect] if self.rect else []
        return d


def instrument_kind(row: dict) -> str:
    """FIELD or VALVE, from which detector produced the row."""
    return "VALVE" if row.get("evidence", {}).get("body") else "FIELD"


def _key(*parts) -> str:
    """Stable row identity: same drawing, same place, same kind.

    Built from the detection's own coordinates so that re-analysing the same
    PDF gives every row the same key, which is what lets a reviewer's edits
    survive a re-run.
    """
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


class Timings:
    """Wall clock per stage and per page.

    "The analysis is slower than I expected" is not answerable without knowing
    which stage the time went to, so every stage is timed, printed as it
    finishes and returned with the result.  Times are deliberately kept out of
    `fingerprint()` and out of every row: they are the one part of the result
    that legitimately differs between two runs of the same PDF.
    """

    def __init__(self, log=None):
        self.stages: dict[str, float] = collections.defaultdict(float)
        self.pages: dict[int, dict[str, float]] = {}
        self.log = log if log is not None else (lambda m: print(m, flush=True))

    @contextlib.contextmanager
    def stage(self, name: str, page_no: int = None):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            dt = time.perf_counter() - t0
            self.stages[name] += dt
            if page_no is not None:
                self.pages.setdefault(page_no, {})[name] = dt

    def page_done(self, page_no: int) -> None:
        per = self.pages.get(page_no, {})
        if not per:
            return
        parts = " ".join(f"{k} {v:.2f}s" for k, v in sorted(
            per.items(), key=lambda kv: -kv[1]))
        self.log(f"  page {page_no:>3}  {sum(per.values()):6.2f}s   {parts}")

    def report(self) -> dict:
        total = sum(self.stages.values())
        return {
            "total_s": round(total, 2),
            "by_stage": {k: round(v, 2) for k, v in sorted(
                self.stages.items(), key=lambda kv: -kv[1])},
            "by_page": {str(p): {k: round(v, 2) for k, v in per.items()}
                        for p, per in sorted(self.pages.items())},
            "slowest_pages": [
                {"page_no": p, "seconds": round(sum(per.values()), 2)}
                for p, per in sorted(self.pages.items(),
                                     key=lambda kv: -sum(kv[1].values()))[:5]],
        }

    def summary_lines(self) -> list[str]:
        r = self.report()
        out = [f"analysis took {r['total_s']:.1f}s, by stage:"]
        for name, secs in r["by_stage"].items():
            share = 100 * secs / r["total_s"] if r["total_s"] else 0
            out.append(f"  {name:<22} {secs:8.2f}s  {share:5.1f}%")
        if r["slowest_pages"]:
            worst = ", ".join(f"p{s['page_no']} {s['seconds']:.1f}s"
                              for s in r["slowest_pages"])
            out.append(f"  slowest pages: {worst}")
        return out


def _page_origins(pages, tb_rows, per_page, reference: Path = None) -> dict:
    """page_no -> DRAWING | MATCHED | PDF_ONLY, overridden by REVISION_GAP.

    `reference` is a *finished* instrument list - the answer key Phase 0 scored
    against.  In real use it does not exist: what a user has is the PDF and an
    empty output form, and if they already had a filled-in list they would not
    need this tool.  So it defaults to None and every drawing is DRAWING, which
    is all that can honestly be said about it.

    Given an answer key (verification mode) the MATCHED / PDF_ONLY split is
    `detect_all.attribute_rows`, unchanged: a drawing number appearing on several
    sheets is attributed by matching the Excel SYSTEM value against the drawing
    title, which is what stopped 52 phantom over-detections being counted in
    Phase 0.

    REVISION_GAP needs no key at all - it is `detect_all.review_annotations`
    finding revision markup in the drawing body - so it is decided either way.
    """
    keyed = reference is not None and Path(reference).exists()
    origins = {p: (ORIGIN_PDF_ONLY if keyed else ORIGIN_DRAWING) for p in per_page}
    if keyed:
        excel, _total, _spare = da.load_excel(Path(reference))
        pages_by_drawing: dict[str, list] = collections.defaultdict(list)
        for pno, info in per_page.items():
            pages_by_drawing[info["drawing_no"]].append(pno)
        owned, _ = da.attribute_rows(excel, pages_by_drawing, per_page)
        for pno in per_page:
            if owned.get(pno):
                origins[pno] = ORIGIN_MATCHED
    for pno, info in per_page.items():
        if any(a["where"] == "DRAWING" for a in info["annotations"]):
            origins[pno] = ORIGIN_REVISION_GAP
    return origins


def analyse(pdf_path: Path, progress=None, timings: "Timings" = None,
            reference: Path = None) -> dict:
    """Full analysis of one PDF.  `progress(done, total, message)` is optional.

    `reference` turns on verification mode: it is a finished instrument list to
    attribute drawings against, and it is the only thing in this pipeline that
    needs one.  Real runs pass nothing.
    """
    def say(done, total, msg):
        if progress:
            progress(done, total, msg)

    clock = timings or Timings()

    with clock.stage("open_pdf"):
        doc, pages = pidcache.load_pages(pdf_path)
    total = len(pages) + 6
    say(1, total, "reading title blocks")

    with clock.stage("titleblock_glyphs"):
        library = tb.build_glyph_library(pages)
    with clock.stage("titleblocks"):
        tb_rows = {r["page_no"]: r
                   for r in (tb.extract_page(pd, library) for pd in pages)}

    say(2, total, "measuring rules off the legend sheets")
    with clock.stage("legend_rules"):
        dv.LAYOUT, legend_derived = dv.derive_layout(pages)
        pipe_style = pipe_graph.derive_line_styles(pages, CFG)
        legend_derived["line_styles"] = pipe_style
        # The off-page connector is not in the legend, so how far its text sits
        # from the pipe is measured off this document instead - see
        # `pipe_graph.derive_connector_reach`, which says so in its provenance.
        reach = pipe_graph.derive_connector_reach(
            pages, pipe_style.values, CFG.rect("regions.drawing_area"), CFG)
        legend_derived["connector_reach"] = reach
        pipe_style.values.update(reach.values)
        # The words for each tag's measured variable, off legend p3's own
        # identification matrix - the Description column is written in them.
        isa = isa_table.derive(pages)
        pattern = desc.derive_pattern(CFG)

    page_kinds = {p: r["page_kind"] for p, r in tb_rows.items()}
    say(3, total, "deriving unit multipliers from legend page 5")
    with clock.stage("unit_multipliers"):
        mult = projectconfig.derive_unit_multipliers(pages, CFG, page_kinds)

    targets = [pc for pc in pages
               if tb_rows[pc.page_no]["page_kind"] == "PID" and pc.analysis_scope]

    rows: list[Row] = []
    layers: dict[int, dict] = {}
    per_page: dict[int, dict] = {}

    for i, pc in enumerate(targets, 1):
        say(3 + i, total, f"page {pc.page_no} of {len(pages)}")
        meta = tb_rows[pc.page_no]
        with clock.stage("instruments", pc.page_no):
            dets, scopes, mark_dict, unverified, unmapped, boxes = ds.detect(
                pc, rules=ds.RULESET_V3)
        with clock.stage("annotations", pc.page_no):
            annotations = da.review_annotations(pc)
        # The same body-text scan parse_notes.py does: a scope keyword says some
        # items on this drawing take a different multiplier from the rest of it.
        body_text = " ".join(t for r, t in pc.words
                             if r.x0 < CFG.rect("regions.drawing_area")[2]).upper()
        scope_keywords = [k for k in SCOPE_OVERRIDES if k in body_text]
        per_page[pc.page_no] = {
            "drawing_no": meta["drawing_no"],
            "title": meta["drawing_title"],
            "unit_code": meta["unit_code"],
            "detections": dets,
            "annotations": annotations,
            "scope_keywords": scope_keywords,
            "page_cache": pc,
        }
        rows.extend(_field_rows(pc, meta, dets, mult, annotations, scope_keywords,
                                isa=isa, pat=pattern))
        layers.setdefault(pc.page_no, collections.defaultdict(list))
        clock.page_done(pc.page_no)

    say(total - 2, total, "valve bodies and actuators")

    def valve_step(page_no, name, dt):
        """Timing hook for the valve stage, which runs all pages in one call."""
        clock.stages["valves." + name] += dt
        if page_no is not None:
            clock.pages.setdefault(page_no, {})["valves." + name] = dt

    valve_results, glyphs = dv.analyse_all(pages, VALVE_DISABLED,
                                           on_step=valve_step)
    for page_no, res in valve_results.items():
        meta = tb_rows.get(page_no)
        if not meta or meta["page_kind"] != "PID":
            continue
        rows.extend(_valve_rows(page_no, meta, res, mult))

    origins = _page_origins(pages, tb_rows, per_page, reference)
    for r in rows:
        r.origin = origins.get(r.page_no, ORIGIN_DRAWING)

    # Bubbles the drawing stacks edge-to-edge.  Flagged, never merged.
    signal_groups = _signal_groups(rows)

    say(total - 1, total, "building overlays")
    for r in rows:
        if not r.rect:
            continue
        layers.setdefault(r.page_no, collections.defaultdict(list))
        scope = (SCOPE_REVIEW if r.needs_review else
                 SCOPE_SCT if r.scope == "SCT" else
                 SCOPE_VENDOR if r.vendor_supply == "VENDOR" else SCOPE_INCLUDED)
        layers[r.page_no][r.tab].append({
            "key": r.key, "rect": [round(v, 1) for v in r.rect],
            "label": r.type or r.valve_type, "needs_review": bool(r.needs_review),
            "scope": scope,
            "kind": KIND_VALVE if r.evidence.get("body") else KIND_INSTRUMENT,
            "row": True,
            "reason": r.needs_review,
            "description_needed": r.description_needed,
        })
    # And the symbols that were excluded, which have no row to hang off.
    for pno, info in per_page.items():
        marks = _excluded_marks(info["page_cache"], tb_rows[pno], info["detections"])
        if marks:
            layers.setdefault(pno, collections.defaultdict(list))
            layers[pno]["EXCLUDED"].extend(marks)

    # Pipe connectivity.  Every row gets what it is connected to, or the fact
    # that it could not be traced.  No sentence is written from it - Description
    # stays empty, and this is the input a later pass would need.
    say(total - 1, total, "tracing pipe connectivity")
    with clock.stage("pipe_graph"):
        trace_stats = _trace_rows(rows, per_page, pipe_style.values, clock)

    # Description: choose a middle where the drawing offers candidates, grade
    # every row, and say in the Remark what the reviewer has to do about it.
    say(total - 1, total, "assembling descriptions")
    with clock.stage("description"):
        selector = describe_llm.build(CFG)
        examples = _client_examples(reference, tb_rows, pattern)
        desc_stats = _finish_descriptions(rows, per_page, isa, pattern,
                                          selector, examples)

    alarms = _glyph_alarms(glyphs)
    # Findings that belong to the document rather than to any one row.  They are
    # returned alongside the rows so the review count on screen is the whole
    # review load, not just the part that happens to have a rectangle.
    job_review = []
    for u in glyphs.unlabeled:
        job_review.append({"kind": u["kind"], "detail": u,
                           "pages": u.get("pages", [])})
    for a in alarms:
        job_review.append({"kind": a["kind"], "detail": a,
                           "pages": a.get("pages", [])})
    if reference is not None and not Path(reference).exists():
        # Verification mode was asked for and its answer key is not there.  That
        # is a missing *input*, and saying so is the difference between "these
        # drawings are not in the client's list" and "we never looked".  A normal
        # run passes no reference and never reaches this branch.
        job_review.append({
            "kind": "ORIGIN_REFERENCE_MISSING",
            "pages": [],
            "detail": {"expected": str(reference),
                       "reason": "검증 모드로 요청됐지만 대조용 계기 리스트가 그 "
                                 "경로에 없습니다. 귀속은 전 페이지 DRAWING 으로 "
                                 "남았습니다."}})
    for pno, info in sorted(per_page.items()):
        if info.get("scope_keywords"):
            job_review.append({
                "kind": "SCOPE_OVERRIDE_UNRESOLVED",
                "pages": [pno],
                "detail": {"drawing_no": info["drawing_no"],
                           "keywords": info["scope_keywords"],
                           "reason": "scope keyword found; which items it covers "
                                     "needs line tracing (Phase 2)"}})
    say(total, total, "done")
    for line in clock.summary_lines():
        clock.log(line)
    applied = {
        "instrument_ruleset": ds.RULESET_V3.name,
        "exclusion_scope_name": da.BASELINE_SCOPE_NAME,
        "exclusion_rules_active": sorted(ACTIVE_SCOPE),
        "exclusion_rules_inactive": sorted(
            set(da.SCOPE_RULES) - set(ACTIVE_SCOPE)),
        "valve_rules_active": sorted(set(dv.ALL_RULES) - VALVE_DISABLED),
        "valve_rules_disabled": sorted(VALVE_DISABLED),
        "anchor_map_entries": len(ds.RULESET_V3.field_type_map),
        "not_field": sorted(ds.RULESET_V3.not_field),
    }
    return {
        "applied_rules": applied,
        # Wall clock, not a finding: excluded from `fingerprint()` on purpose,
        # because it is the one key that must differ between two runs.
        "timings": clock.report(),
        "pipe_trace": trace_stats,
        # The two axes, counted separately on purpose.  `scope` is what is in the
        # list; this is what will carry a Description.
        # What the Description column carries, and on what authority.  Reported
        # with the accuracy it was measured at, so nobody reads the column as
        # finished text: see DESCRIPTION_PARTIAL.
        "description_build": {
            "written": sum(1 for r in rows if r.description),
            "blank": sum(1 for r in rows if not r.description),
            "isa_table": isa.as_dict(),
            "pattern": {"template": pattern.evidence.get("template"),
                        "measured_on": pattern.evidence.get("measured_on"),
                        "source": pattern.source, "note": pattern.note},
            "measured_accuracy": {
                "lines_compared": 536,
                "exact": 1,
                "token_precision": 57.3,
                "token_recall": 37.6,
                "with_near_text_160pt": {"token_precision": 20.2,
                                         "token_recall": 47.9},
                "with_near_text_240pt": {"token_precision": 17.6,
                                         "token_recall": 62.8},
            },
        },
        "description_grades": desc_stats,
        "description_scope": {
            "needed": sum(1 for r in rows if r.description_needed),
            "skipped": sum(1 for r in rows if not r.description_needed),
            "by_reason": dict(collections.Counter(
                r.description_note for r in rows if not r.description_needed)),
            "supplier_span_label": SUPPLIER_SPAN_LABEL,
            "supplier_span_party": SUPPLIER_SPAN_PARTY,
        },
        "signal_groups": signal_groups,
        "pdf": str(pdf_path),
        "pages": [
            {"page_no": p.page_no, "width": p.width, "height": p.height,
             "drawing_no": tb_rows[p.page_no]["drawing_no"],
             "title": tb_rows[p.page_no]["drawing_title"],
             "page_kind": tb_rows[p.page_no]["page_kind"],
             "in_scope": bool(p.analysis_scope),
             "scope_reason": p.scope_reason}
            for p in pages],
        "titleblocks": [tb_rows[p.page_no] for p in pages],
        "rows": [r.as_dict() for r in rows],
        "layers": {str(k): {kk: vv for kk, vv in v.items()} for k, v in layers.items()},
        "multipliers": {
            "source": mult.source, "note": mult.note,
            "table": {k: v for k, v in sorted(mult.table.items())},
        },
        "legend": {k: {"source": d.source, "note": d.note, "values": d.values}
                   for k, d in legend_derived.items()},
        "job_review": job_review,
        "origins": origins,
        "glyphs": {
            "letters": dict(sorted(glyphs.letters.items())),
            "clusters": glyphs.clusters,
            "unlabeled": glyphs.unlabeled,
            "alarms": alarms,
        },
    }


# Scope keywords that override the unit multiplier for individual items
# (config `qty_scope_overrides`).  Phase 0 confirmed the one case on p38 and
# deliberately did not apply it: deciding *which* items belong to the scoped
# equipment needs the dashed equipment box, whose detection depends on
# brk_max_mark - still an UNKNOWN.  So the quantity keeps the sheet multiplier
# and the row says why, which is what SCOPE_OVERRIDE_UNRESOLVED means.
SCOPE_OVERRIDES = {str(k["keyword"]).upper(): int(k["multiplier"])
                   for k in (CFG.data.get("qty_scope_overrides") or [])}

# `IP` is mapped to PNEUMATIC in detect_valves.ACT_LETTERS, but every one of the
# 17 `IP` tokens in this document is part of an equipment name - "IP TURBINE",
# and the label on a BFP discharge line - not an I/P positioner.  None of them
# currently reaches a valve, because the stem test rejects them.  If one ever
# does, the valve it creates is a phantom, so it is flagged rather than trusted.
# The detector is untouched: this only decides what the row says about itself.
IP_TOKEN_EVIDENCE = ("I/P positioner on stem",)


# How a symbol on the drawing relates to our supply scope.  This is what the
# overlay is coloured by, because "why is this one not in my list" is the
# question a reviewer asks of the drawing rather than of the grid - and the
# answer is invisible when every box is the same colour.  The excluded ones are
# not rows at all, so they are carried here or nowhere.
SCOPE_INCLUDED = "INCLUDED"          # our supply, in a deliverable
SCOPE_VENDOR = "VENDOR_EXCLUDED"     # a vendor mark is drawn on the symbol
SCOPE_SCT = "SCT"                    # inside a supplier-scope box
SCOPE_REVIEW = "REVIEW"              # a row whose judgement is held open
KIND_INSTRUMENT = "INSTRUMENT"
KIND_VALVE = "VALVE"

# Which exclusion rule hit, in the words the report uses.
_VENDOR_RULES = ("VENDOR_MARK_GLYPH", "VENDOR_MARK_TEXT", "VENDOR_MARK_BOX")

# What a supplier-interface span is called.
#
# The drawing marks the span with a broken line and the letters `SCT`, and the
# engine's rule is named after those letters - `SCT_SUPPLIER_SCOPE`, untouched,
# because it is verified detection.  What the span *means* is what this corrects.
# The label used to read "SCT 배관 제외", which names our own company as the party
# and says the item is out of the list; a reviewer confirmed that on p20's
# D00P-11LAB00-M05-0001 the pipe and the equipment inside the span are the
# *supplier's* scope, and that the item stays in the list.  The judgement is
# unchanged - only the sentence that explains it.
#
# The legend does not define this span (measured last round: pages 2-5 print no
# row for it), so no rule is derived from it.  Who supplies it is a project fact,
# so `config supplier_interface_span` holds the place and stays blank until a
# project states it.
SUPPLIER_SPAN = CFG.data.get("supplier_interface_span") or {}
SUPPLIER_SPAN_LABEL = str(SUPPLIER_SPAN.get("label")
                          or "공급자 인터페이스 구간 — 배관 및 기기 공급자 범위")
SUPPLIER_SPAN_PARTY = str(SUPPLIER_SPAN.get("supplied_by") or "")

# Rows that stay in the list but get no Description, and why.  This is the second
# axis, deliberately not mixed with `scope`: a confirmed other-party supply item
# is still delivered as a line of the list - the reviewer confirmed that is the
# client's practice - and its Description is left blank, because we do not
# describe a scope we do not supply.  Tracing is skipped for the same reason.
#
# `VENDOR_MARK_UNDEFINED` is deliberately absent: a mark this drawing's NOTES do
# not define is not a confirmation of anything, so those rows keep their
# Description, keep their trace and keep their review flag.
DESCRIPTION_SKIP_RULES = {
    "SCT_SUPPLIER_SCOPE": SUPPLIER_SPAN_LABEL,
    "VENDOR_MARK_GLYPH": "벤더 마크 — 타사 공급 범위",
    "VENDOR_MARK_TEXT": "벤더 마크(텍스트형) — 타사 공급 범위",
    "VENDOR_MARK_BOX": "벤더 패키지 박스 안 — 타사 공급 범위",
}
DESCRIPTION_SKIP_NOTE = "타사 공급 — Description 생략"


def _description_skip(d) -> str:
    """Why this row needs no Description, or "" when it does.

    Read off the same rule hits the scope judgement uses, so the two axes agree on
    the facts while staying separate in what they do about them.
    """
    for rule in getattr(d, "rules_hit", []) or []:
        if rule in DESCRIPTION_SKIP_RULES:
            return f"{DESCRIPTION_SKIP_NOTE} ({DESCRIPTION_SKIP_RULES[rule]})"
    return ""


# Multi-signal bubble groups: several signals off one physical instrument.
#
# A reviewer confirmed that the LSHH / LSH / LSL bubbles drawn edge-to-edge are
# one physical level switch, so the physical quantity should be 1 rather than 3.
# Nothing here acts on that, because nothing in the document says so:
#
#   * legend p3 defines "INSTRUMENT FOR SINGLE MEASURED VARIABLE AND ANY NUMBER OF
#     FUNCTIONS" and draws it as *one* bubble; it draws no stack anywhere, so it
#     does not define this case.
#   * the client's own list writes one row per bubble (22 LS rows against 22 LS
#     bubbles on the five drawings it covers) - but it covers none of the five
#     drawings that carry the stacks, so it never ruled on them either.
#
# So the group is measured, shown and flagged, and the quantity is left alone.
MULTI_SIGNAL_REASON = "다중 신호 버블 — 물리 수량 확인 필요"

# Whether to consolidate a group's quantity onto one row.  **Off**, and it stays
# off until the client answers `out/ls_bundle_question.md`: the drawing says the
# three bubbles are one assembly, and the client's list says one row per bubble,
# but the two statements are about different drawings, so neither settles it.
#
# Turned on, the topmost bubble of each group carries the group's whole quantity
# and the rest carry 0, every row keeping its own line, its own evidence and the
# flag.  Which row should hold the quantity is itself part of the question being
# asked, so it is recorded in the evidence rather than presented as the answer.
MULTI_SIGNAL_MERGE = bool((CFG.data.get("multi_signal_bundle") or {})
                          .get("merge_quantity") or False)


def _signal_groups(rows) -> list:
    """Bubbles the drawing stacks edge-to-edge, grouped, with the basis measured.

    The three tests are the ones the drawing itself answers, and none of them is a
    distance someone chose:

      touching       the vertical gap is no more than the stroke index's own slack
                     (`legend_rules.INDEX_SLACK`).  Measured over every
                     horizontally-overlapping pair of bubbles in this document,
                     the pairs that pass are exactly the 34 LSH/LSHH/LSL stacks
                     and their gap is 0.0; the next-closest overlapping pair
                     anywhere is 3 pt apart.  The test reads a discrete fact.
      stacked        their horizontal extents overlap by at least half the
                     narrower bubble - that is what makes it a stack rather than
                     two neighbours side by side.
      same variable  the anchors begin with the same letter, so they are functions
                     on one measured variable.
    """
    by_page = collections.defaultdict(list)
    for r in rows:
        anchor = str(r.evidence.get("anchor") or "")
        if r.rect and anchor:
            by_page[r.page_no].append((anchor, r))
    groups = []
    for pno, members in sorted(by_page.items()):
        parent = list(range(len(members)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                (ai, ri), (aj, rj) = members[i], members[j]
                if ai[0] != aj[0]:
                    continue
                a, b = ri.rect, rj.rect
                overlap = min(a[2], b[2]) - max(a[0], b[0])
                if overlap < 0.5 * min(a[2] - a[0], b[2] - b[0]):
                    continue
                gap = max(a[1], b[1]) - min(a[3], b[3])
                if gap > legend_rules.INDEX_SLACK:
                    continue
                pi, pj = find(i), find(j)
                if pi != pj:
                    parent[pj] = pi
        buckets = collections.defaultdict(list)
        for i in range(len(members)):
            buckets[find(i)].append(i)
        for idxs in buckets.values():
            if len(idxs) < 2:
                continue
            idxs.sort(key=lambda i: members[i][1].rect[1])
            grp = [members[i][1] for i in idxs]
            gaps = [round(grp[k + 1].rect[1] - grp[k].rect[3], 2)
                    for k in range(len(grp) - 1)]
            group = {
                "page_no": pno,
                "drawing_no": grp[0].drawing_no,
                "members": [{"key": r.key, "anchor": r.evidence.get("anchor", ""),
                             "type": r.type,
                             "rect": [round(v, 1) for v in r.rect]} for r in grp],
                "basis": {
                    "touching_gaps_pt": gaps,
                    "slack_pt": legend_rules.INDEX_SLACK,
                    "shared_first_letter": str(
                        grp[0].evidence.get("anchor", ""))[:1],
                    "qty_applied": [r.qty for r in grp],
                },
            }
            groups.append(group)
            for i, r in enumerate(grp):
                r.evidence["signal_group"] = group
                r.needs_review = "; ".join(
                    [s for s in (r.needs_review, MULTI_SIGNAL_REASON) if s])
                if not MULTI_SIGNAL_MERGE:
                    continue
                total = sum(x.qty for x in grp if isinstance(x.qty, (int, float)))
                r.qty = total if i == 0 else 0
                r.evidence["qty_basis"] = (
                    f"다중 신호 버블 묶음 합산 (config multi_signal_bundle."
                    f"merge_quantity) — 묶음 {len(grp)}개 중 "
                    + ("최상단 버블이 묶음 수량 " + str(total) + " 을 가집니다"
                       if i == 0 else "합산되어 0 입니다")
                    + f"; 원래 값 {group['basis']['qty_applied'][i]}")
            group["basis"]["merged"] = MULTI_SIGNAL_MERGE
    return groups


def description_question(result: dict, token_stats: dict = None) -> str:
    """What the client has to tell us before Description can be finished.

    Four questions, each with the number of rows its answer would fill, so the
    client can see what their reply is worth rather than being asked in the
    abstract.  The counts come from the run and from the token decomposition of
    their own finished list; nothing here is estimated.
    """
    rows = result["rows"]
    grades = collections.Counter(r["description_grade"] for r in rows)
    needs = sum(grades[g] for g in (GRADE_PARTIAL, GRADE_LOW, GRADE_NONE))
    tok = token_stats or {}
    L = ["# Description 작성 규칙 확인 요청", ""]
    L.append(f"도면에서 확인되는 조각(단위·계통·변수)만으로 Description 을 세웠고, "
             f"**{needs}행**이 사람 손을 기다리고 있습니다. 아래 네 가지를 알려주시면 "
             f"그만큼이 규칙으로 채워집니다.")
    L.append("")
    L.append("| 등급 | 뜻 | 행 |")
    L.append("|---|---|---:|")
    for g, label, why in (
            (GRADE_CONFIRMED, "확정", "도면이 이름을 대는 것으로 채워짐"),
            (GRADE_LOW, "AI 제안", "후보에서 골랐으나 근거가 약함"),
            (GRADE_PARTIAL, "부분", "중간 서술 미확인"),
            (GRADE_NONE, "없음", "근거 없음"),
            (GRADE_SKIP, "생략", "타사 공급")):
        L.append(f"| {label} | {why} | {grades[g]} |")
    L.append("")
    L.append("## 1. 기기 명명 규칙 — 중간 서술")
    L.append("")
    L.append(f"발주처 문장의 중간 서술(예: `GENERATOR HYDROGEN GAS COOLER CCW RETURN`)은 "
             f"평균 5~6낱말이고 기기를 지목합니다. 도면에서 이 낱말들이 나오는 곳을 "
             f"전수 조사한 결과, 중간 서술의 **49.7%는 도면 제목과 한 낱말도 겹치지 "
             f"않고**, 절반은 심볼에서 240pt 이상 떨어져 있습니다.")
    L.append("")
    L.append("**요청**: COOLER / BOILER / GENERATOR 계열 기기의 명명 규칙 — 도면의 "
             "어떤 표기(장비 태그? 배관 라인 번호? 커넥터 문구?)에서 그 이름을 "
             "가져오는지 한 계통만 예시로 보여주시면 나머지는 규칙으로 확장합니다.")
    L.append(f"")
    L.append(f"**영향**: 중간 서술이 비어 있는 **{grades[GRADE_PARTIAL] + grades[GRADE_NONE]}행**")
    L.append("")
    L.append("## 2. 위치 관계어 — DISCHARGE / SUCTION / INLET / OUTLET")
    L.append("")
    L.append("`DISCHARGE` 57건, `SUCTION` 40건, `OUTLET` 35건, `INLET` 29건이 발주처 "
             "문장에 있으나 **해당 도면 어디에도 인쇄돼 있지 않습니다**. 펌프의 어느 "
             "쪽인지는 배관 방향으로 판정해야 하는데, 이 도면들의 배관 추적률이 13% 라 "
             "규칙으로는 닿지 않습니다.")
    L.append("")
    L.append("**요청**: 펌프·쿨러 기준 흡입/토출 판정을 도면에서 어떻게 읽는지 "
             "(화살표? 기기 좌우? 라인 번호 규칙?)")
    L.append("")
    L.append(f"**영향**: 이 낱말이 들어가는 문장 **{tok.get('position_words', 161)}건**")
    L.append("")
    L.append("## 3. UNIT 접두어와 유닛 번호")
    L.append("")
    L.append("`UNIT` 이라는 낱말은 **어느 도면에도 인쇄되지 않습니다** (발주처 문장 "
             "373건에 등장). 접두어 자체는 문형으로 처리했습니다. 다만 뒤의 번호가 "
             "문제입니다 — 발주처는 한 도면 안에서 `#10` · `#11` · `#12` 를 섞어 쓰는데, "
             "타이틀블록의 unit code 는 도면당 하나(예: 10)입니다.")
    L.append("")
    L.append("**요청**: `UNIT #11` 의 11 은 도면 안의 `HRSG#11` 같은 지역 표기에서 "
             "가져오는 것이 맞는지, 아니면 다른 규칙인지")
    L.append("")
    L.append(f"**영향**: 유닛 번호가 시트 값과 다른 행 — 발주처 리스트 기준 "
             f"{tok.get('unit_mismatch', 204)}행")
    L.append("")
    L.append("## 4. A / B / C 순번")
    L.append("")
    L.append("문장 끝의 `A` 58건, `B` 51건, `C` 8건, 숫자 24건이 도면에 없습니다. "
             "같은 계통에 같은 계기가 여러 개일 때 붙는 순번으로 보입니다.")
    L.append("")
    L.append("**요청**: 순번 부여 기준 — 도면 좌표 순서(좌→우, 상→하)인지, 기기 "
             "번호를 따르는지, 발주처가 별도로 정하는지")
    L.append("")
    L.append(f"**영향**: 접미가 붙는 문장 **{tok.get('suffix_rows', 141)}건**")
    L.append("")
    L.append("## 지금 상태")
    L.append("")
    L.append("답을 받기 전까지 도구는 도면에서 확인되는 조각만 씁니다. 확인되지 않은 "
             "칸은 비워 두고 Remark 에 사유를 적으며, 화면의 `검토필요` 탭에서 "
             "`Description 입력 필요` 그룹으로 묶어 보여줍니다. 후보 텍스트를 클릭해 "
             "넣고, 같은 도면·같은 Type 에 일괄 적용할 수 있습니다.")
    return "\n".join(L) + "\n"


def ls_bundle_question(result: dict) -> str:
    """The client-facing question about multi-signal bubbles, as markdown.

    Written from one run's own measurements so the client is asked with the
    drawing's coordinates in hand rather than a description of them.  It asks a
    question; it does not propose an answer, because the two sources that could
    settle it disagree in scope (see the body).
    """
    groups = result.get("signal_groups") or []
    rows = {r["key"]: r for r in result["rows"]}
    members = [m for g in groups for m in g["members"]]
    per_page = collections.Counter(g["page_no"] for g in groups)
    shapes = collections.Counter(
        " + ".join(m["anchor"] for m in g["members"]) for g in groups)
    qty_now = sum(rows[m["key"]]["qty"] for m in members
                  if isinstance(rows[m["key"]].get("qty"), (int, float)))
    L = ["# 다중 신호 버블 — 물리 수량 확인 요청", ""]
    L.append("도면에서 세로로 **맞닿아** 그려진 계기 버블 묶음이 있습니다. "
             "물리적으로 하나의 기기에서 나오는 여러 신호로 보이지만, "
             "**도구는 수량을 합산하지 않았습니다** — 아래 두 근거가 서로 다른 "
             "도면을 말하고 있어 이 도구가 판단할 수 없습니다.")
    L.append("")
    L.append("## 무엇을 물어보는지")
    L.append("")
    L.append(f"- 묶음 **{len(groups)}건**, 버블 **{len(members)}개**, "
             f"현재 리스트에 **{len(members)}행** · Q'ty 합계 **{qty_now}**")
    L.append(f"- 합산한다면 행이 {len(members)} → **{len(groups)}행** 이 됩니다 "
             f"(수량 합계는 승수에 따라 재계산)")
    L.append("- 현재 상태: 전 행 리스트 유지 + `다중 신호 버블 — 물리 수량 확인 필요` "
             "로 검토 대기")
    L.append("")
    L.append("## 도면이 말하는 것 (측정)")
    L.append("")
    for shape, n in shapes.most_common():
        L.append(f"- `{shape}` 구성 묶음 {n}건")
    gaps = sorted({g for grp in groups for g in grp["basis"]["touching_gaps_pt"]})
    L.append(f"- 버블 사이 세로 간격: **{', '.join(str(g) for g in gaps)}pt** "
             f"(허용치 {groups[0]['basis']['slack_pt'] if groups else '-'}pt, "
             f"`legend_rules.INDEX_SLACK`). 이 문서에서 가로로 겹치는 다른 버블 쌍의 "
             f"최소 간격은 3pt 이고, 맞닿은 것은 이 묶음뿐입니다")
    L.append("- 묶음마다 리드선이 **1개**이고, 그 리드선은 묶음의 버블 중 "
             "**1개**에만 닿습니다")
    L.append("")
    L.append("## 문서가 답하지 않는 것")
    L.append("")
    L.append("- 범례 p3 `INSTRUMENT FOR SINGLE MEASURED VARIABLE AND ANY NUMBER OF "
             "FUNCTIONS` 는 다기능 계기를 **버블 1개**로 그립니다. 범례에는 맞닿은 "
             "묶음 표기가 **없습니다**")
    L.append("- 발주처 계기 리스트는 LS 22행 = 도면 버블 22개로 **버블 1개당 1행**을 "
             "쓰지만, 그 22행이 있는 도면에는 이 묶음이 **없습니다**. 묶음이 있는 "
             "도면 5장은 리스트가 다루지 않습니다")
    L.append("")
    L.append("## 묶음 전체 목록")
    L.append("")
    L.append("| # | 도면 | 페이지 | 구성 | 좌표 (x0, y0, x1, y1) | 간격 pt |")
    L.append("|---:|---|---:|---|---|---|")
    for i, g in enumerate(sorted(groups, key=lambda g: (g["page_no"],
                                                        g["members"][0]["rect"][0])), 1):
        coords = " / ".join("(" + ", ".join(str(round(v)) for v in m["rect"]) + ")"
                           for m in g["members"])
        L.append(f"| {i} | `{g['drawing_no']}` | {g['page_no']} | "
                 f"{' + '.join(m['anchor'] for m in g['members'])} | {coords} | "
                 f"{', '.join(str(v) for v in g['basis']['touching_gaps_pt'])} |")
    L.append("")
    L.append(f"페이지별 묶음 수: "
             f"{', '.join(f'p{p} {n}건' for p, n in sorted(per_page.items()))}")
    L.append("")
    L.append("## 답을 받으면")
    L.append("")
    L.append("`config multi_signal_bundle.merge_quantity` 를 켜면 묶음의 최상단 "
             "버블이 묶음 수량을 갖고 나머지는 0 이 됩니다(행은 모두 유지). "
             "어느 행이 수량을 가져야 하는지도 확인 대상입니다. "
             "현재 값: "
             f"`{'on' if MULTI_SIGNAL_MERGE else 'off'}`.")
    return "\n".join(L) + "\n"


def _excluded_marks(pc, meta, dets) -> list:
    """Symbols the exclusion rules removed, as overlay items with the reason.

    They never become rows - that is the point of excluding them - so without
    this they are simply absent from the drawing view, and a reviewer counting
    boxes against the sheet has no way to tell an exclusion from a miss.
    """
    out = []
    for d in dets:
        if da.excel_type_under(d, ds.RULESET_V3) is None:
            continue                     # not a deliverable symbol in any case
        if da.included_under(d, ds.RULESET_V3, ACTIVE_SCOPE):
            continue
        hits = list(getattr(d, "rules_hit", []) or [])
        rule = getattr(d, "exclude_rule", "") or next(
            (r for r in hits if r in da.SCOPE_RULES), "")
        scope = SCOPE_SCT if rule == "SCT_SUPPLIER_SCOPE" else SCOPE_VENDOR
        r = d.bbox
        out.append({
            "key": _key(meta["drawing_no"], pc.page_no, "X", rule,
                        *[round(v, 1) for v in (r.x0, r.y0, r.x1, r.y1)]),
            "rect": [round(v, 1) for v in (r.x0, r.y0, r.x1, r.y1)],
            "label": getattr(d, "anchor", "") or rule,
            "scope": scope,
            "kind": KIND_INSTRUMENT,
            "needs_review": False,
            "row": False,
            "reason": (f"{rule} — {SUPPLIER_SPAN_LABEL}"
                       if rule == "SCT_SUPPLIER_SCOPE"
                       else f"{rule} — 이 심볼은 제외되어 리스트에 나오지 않습니다"),
            # The sentence this page's NOTES prints about the mark.  For an
            # excluded symbol this *is* the answer to "why is it not in my
            # list", so it travels with the mark rather than living in a row
            # that was never created.
            "notes_text": _notes_quotes(d),
        })
    return out


# What the Description column carries, and what it cannot.
#
# Measured against the client's own 536 attributed Description lines (README
# "Description — 토큰 출처"): the three parts written here - the unit prefix, the
# system name off the drawing title and the variable word off legend p3's ISA
# matrix - reproduce 57.3% of the client's tokens with 37.6% recall, and exactly
# **1** of 536 lines in full.  The rest of each line is the middle segment naming
# the equipment, and it is not on the sheet in any usable place: 49.7% of middles
# share no word with the drawing title, and half the client's tokens sit more than
# 240 pt from the symbol they belong to, on a 2384 pt sheet.
#
# Adding that neighbourhood text was measured too, and it makes the line worse:
# token precision falls 57.3% -> 20.2% at a 160 pt radius and -> 17.6% at 240 pt,
# because what a 240 pt circle actually contains is drawing numbers, DN sizes, grid
# references and ASME codes.  So the middle is not written, the row says so, and
# the reviewer completes it.  Nothing here invents a word.
# The grades, and what each one asks of the reviewer.  A grade is decided by
# counting which pieces of the sentence have evidence - never by a score.
#
#   CONFIRMED     all four pieces sourced, and the middle came from something the
#                 drawing *names*: an off-page connector or an equipment box.  That
#                 is what the client's middle segment is
#   PARTIAL       the three rule pieces are there and the middle is not.  The line
#                 is kept; the Remark says why the middle is missing
#   LOW           a middle was chosen, but from a line label rather than a named
#                 thing - a size or a neighbouring tag can look like a name
#   NONE          nothing can be written: no variable in the ISA table, or the
#                 answer failed the gate.  Description stays blank
#   SKIP          other-party supply; no Description is wanted at all
#   USER_ENTERED  a person typed it.  Set by the edit path, never by the engine
GRADE_CONFIRMED = "CONFIRMED"
GRADE_PARTIAL = "PARTIAL"
GRADE_LOW = "LOW"
GRADE_NONE = "NONE"
GRADE_SKIP = "SKIP"
GRADE_USER = "USER_ENTERED"

REMARK = {
    GRADE_CONFIRMED: "",
    GRADE_PARTIAL: "중간 서술 미확인 — 직접 입력",
    GRADE_LOW: "AI 제안 — 확인 필요",
    GRADE_NONE: "근거 없음 — 직접 입력",
    GRADE_SKIP: "타사 공급 — Description 생략",
    GRADE_USER: "",
}

DESCRIPTION_PARTIAL = (
    "Description 부분 생성 — 단위·계통·변수만 도면에서 확인됨 (중간 서술과 접미는 "
    "도면에 없음). 발주처 문장 기준 토큰 정밀도 57.3% / 재현율 37.6%, 완전 일치 "
    "536행 중 1행. 검토 후 확정 필요")
DESCRIPTION_NONE = "Description 근거 부족 — 공란으로 남겼습니다"


def _describe_row(meta, tag: str, isa, pat) -> tuple:
    """`(text, evidence, reason)` for one row's Description.

    Written only when all three sourced parts are there.  A tag whose letter the
    legend's matrix does not carry gets no line at all rather than a line missing
    its variable, because a Description without the measured variable is the part
    of the sentence a reviewer cannot check.
    """
    d = desc.describe(meta["unit_code"], meta["drawing_title"], tag, isa, pat)
    if len(d["parts"]) < 3:
        return "", {"description_sources": d["sources"],
                    "description_missing": d["reason"]}, DESCRIPTION_NONE
    return d["text"], {"description_sources": d["sources"],
                       "description_missing": d["reason"]}, DESCRIPTION_PARTIAL


def _client_examples(reference, tb_rows, pat) -> dict:
    """`{system core: {drawing_no: [finished lines]}}` to show the client's order.

    Examples come from `config description.examples`, or from a finished list when
    one is supplied (verification mode), and from nowhere else.  They are grouped
    by the system name in the drawing title so a row is shown lines from its own
    kind of system - and `_examples_for` then withholds the row's *own* drawing,
    because measuring a selector against lines it was shown would measure nothing.
    """
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    for item in ((CFG.data.get("description") or {}).get("examples") or []):
        out[str(item.get("system") or "")][""].append(str(item.get("text") or ""))
    if reference is not None and Path(reference).exists():
        excel, _t, _s = da.load_excel(Path(reference))
        core_of = {}
        for meta in tb_rows.values():
            if meta["page_kind"] != "PID":
                continue
            words, _how = desc.system_words(meta["drawing_title"], pat)
            core_of[meta["drawing_no"]] = " ".join(words)
        for dn, rs in excel.items():
            core = core_of.get(dn)
            if core is None:
                continue
            for r in rs:
                if r.get("description"):
                    out[core][dn].append(str(r["description"]))
    return {k: dict(v) for k, v in out.items()}


def _examples_for(examples: dict, core: str, drawing_no: str, limit: int = 10) -> list:
    """Up to `limit` lines from the same kind of system but a different drawing."""
    out = []
    for dn, lines in (examples.get(core) or {}).items():
        if dn == drawing_no:
            continue
        out += lines
        if len(out) >= limit:
            break
    return out[:limit]


def _finish_descriptions(rows, per_page, isa, pat, sel, examples) -> dict:
    """Choose a middle for each row, grade every row, write the Remark.

    The selector is offered a row only when the rules found candidates for it, and
    its answer is re-checked here before it reaches the column - the two halves of
    the same contract, kept together so neither can be skipped.  Rows the selector
    is not offered (no candidates, or no selector configured) are graded exactly as
    the rules alone grade them, which is why turning the selector off changes
    grades but never breaks the column.
    """
    stats = collections.Counter()
    grades = collections.Counter()
    units_by_page = {}
    for pno, info in per_page.items():
        marks = {"".join(ch for ch in t if ch.isdigit())
                 for _r, t in info["page_cache"].words if "#" in t}
        code = str((info.get("unit_code") or "")).strip()
        units_by_page[pno] = {m for m in marks if m} | ({code} if code else set())

    for r in rows:
        if not r.description_needed:
            r.description_grade, r.remark = GRADE_SKIP, REMARK[GRADE_SKIP]
            grades[GRADE_SKIP] += 1
            continue
        ev = r.evidence
        cands = ev.get("candidates") or []
        parts_ok = bool(r.description) and len(ev.get("description_sources") or []) >= 3
        middle, kind, why = "", "", ""
        if not parts_ok:
            why = ev.get("description_missing") or ""
        elif not cands:
            why = "후보 0개"
            stats["no_candidates"] += 1
        else:
            payload = describe_llm.prompt_for(
                {"type": r.type, "variable": isa.words_for(ev.get("anchor") or r.type),
                 "system": desc.system_words(r.system, pat)[0],
                 "unit_code": (per_page.get(r.page_no) or {}).get("unit_code", "")},
                cands,
                _examples_for(examples, " ".join(desc.system_words(r.system, pat)[0]),
                              r.drawing_no))
            answer, reason = describe_llm.select(sel, payload)
            if answer is None:
                # The Remark is read by a reviewer deciding what to type, so it
                # says what is missing in their terms; the configuration detail
                # behind it goes to the evidence panel and the rules report.
                why = ("후보 있음, AI 선택기 미사용" if not sel.enabled
                       else reason)
                ev["description_llm_reason"] = reason
                stats["not_answered"] += 1
            else:
                middle, unit, bad = describe_llm.validate(
                    answer, payload, units_by_page.get(r.page_no, set()))
                if bad:
                    stats["rejected"] += 1
                    sel.stats["rejected"] += 1
                    if len(sel.stats["rejections"]) < 40:
                        sel.stats["rejections"].append(
                            {"page_no": r.page_no, "type": r.type,
                             "answer": answer.get("middle", ""), "reason": bad})
                    middle, why = "", bad
                else:
                    stats["accepted"] += 1
                    sel.stats["accepted"] += 1
                    kind = next((c["kind"] for c in cands
                                 if desc.tokens(c["text"]) == desc.tokens(middle)
                                 or set(desc.tokens(middle)) <= set(desc.tokens(c["text"]))),
                                dcand.PIPE_LABEL)
                    ev["description_selected"] = {
                        "middle": middle, "unit": unit, "kind": kind,
                        "why": answer.get("why", ""), "used": answer.get("used", []),
                    }
                    # The template's own order: unit, system, middle, variable.
                    parts = r.description.split()
                    var = " ".join(isa.words_for(ev.get("anchor") or r.type))
                    head = r.description[:-len(var)].strip() if var else r.description
                    r.description = " ".join(x for x in (head, middle, var) if x)
        r.description_grade, r.remark = _grade(
            parts_ok, middle, kind, False, why)
        if r.description_grade == GRADE_NONE:
            r.description = ""
        grades[r.description_grade] += 1
    return {"grades": dict(grades), "selection": dict(stats),
            "llm": {"enabled": sel.enabled, "reason": sel.reason,
                    "model": sel.model, **sel.stats}}


def _grade(parts_ok: bool, middle: str, middle_kind: str, skipped: bool,
           reason: str) -> tuple:
    """`(grade, remark)` from what has evidence.  No score, no threshold."""
    if skipped:
        return GRADE_SKIP, REMARK[GRADE_SKIP]
    if not parts_ok:
        return GRADE_NONE, REMARK[GRADE_NONE]
    if not middle:
        note = REMARK[GRADE_PARTIAL]
        return GRADE_PARTIAL, f"{note} ({reason})" if reason else note
    if middle_kind in dcand.NAMED_KINDS:
        return GRADE_CONFIRMED, REMARK[GRADE_CONFIRMED]
    return GRADE_LOW, f"{REMARK[GRADE_LOW]} — 근거: {middle_kind} “{middle}”"


def _field_rows(pc, meta, dets, mult, annotations, scope_keywords=(),
                isa=None, pat=None) -> list:
    """Field instrument rows for one drawing (spike 2 + spike 3)."""
    out = []
    unit = meta["unit_code"]
    factor = mult.multiplier(unit)
    undefined = factor is projectconfig.UNDEFINED
    marked = bool(annotations)
    for d in dets:
        type_ = da.excel_type_under(d, ds.RULESET_V3)
        included = da.included_under(d, ds.RULESET_V3, ACTIVE_SCOPE)
        if not included or not type_:
            continue
        # `Detection.bbox`, not `.rect` - a valve Body uses `.rect` and an
        # instrument Detection uses `.bbox`, and reading the wrong one silently
        # gave every field row an empty rectangle, which collapsed 906 rows onto
        # 170 colliding keys and left them out of the overlay entirely.
        r = d.bbox
        rect = (r.x0, r.y0, r.x1, r.y1)
        reasons = []
        # The Description column, from the three sources that were measured.  An
        # item we do not describe at all (other-party supply) gets no draft.
        skip_desc = _description_skip(d)
        if skip_desc:
            description, desc_ev, desc_reason = "", {}, ""
        else:
            description, desc_ev, desc_reason = _describe_row(
                meta, getattr(d, "anchor", "") or type_, isa, pat)
            if desc_reason:
                reasons.append(desc_reason)
        if undefined:
            reasons.append(f"unit code '{unit}' is not in the legend's UNIT "
                           f"IDENTIFICATION NUMBERS table, so no multiplier")
        if "VENDOR_MARK_UNDEFINED" in (getattr(d, "rules_hit", []) or []):
            reasons.append("a vendor mark is drawn on this symbol but this "
                           "drawing's NOTES do not define what it means, so "
                           "whether it is vendor supply is undecided")
        if scope_keywords:
            reasons.append(
                f"SCOPE_OVERRIDE_UNRESOLVED: {', '.join(scope_keywords)} appears "
                f"on this drawing, so some items take a different multiplier "
                f"from the sheet's x{'?' if undefined else factor}; which items "
                f"needs line tracing (Phase 2), so the sheet multiplier stands")
        # Reviewer markup is a fact about the *drawing*, not a doubt about this
        # row: it means the client and the drawing disagree, which is theirs to
        # reconcile (out/revision_gap.md says not to correct it by rule).  It is
        # carried and counted separately instead of pushing every instrument on
        # an annotated sheet into the review queue - on this document that alone
        # would have been 314 of 1004 rows.
        out.append(Row(
            key=_key(meta["drawing_no"], pc.page_no, "F", type_, *[round(v, 1) for v in rect]),
            # The tab is the deliverable, always.  Review is a *view* over
            # `needs_review`, not a fifth deliverable: moving a flagged row into
            # a REVIEW tab would quietly drop it from the Field workbook, which
            # is the opposite of what flagging it is for.
            tab=TAB_FIELD,
            page_no=pc.page_no,
            drawing_no=meta["drawing_no"],
            type=type_,
            qty=None if undefined else factor,
            system=meta["drawing_title"],
            vendor_supply=_vendor_of(d),
            scope=_scope_of(d),
            description=description,
            description_needed=not skip_desc,
            description_note=skip_desc,
            needs_review="; ".join(reasons),
            annotation=("reviewer markup on this drawing" if marked else ""),
            rect=rect,
            evidence={
                "anchor": getattr(d, "anchor", ""),
                # Carried in the evidence as well as on the row: the database
                # stores the editable columns and the evidence, so this is how the
                # second axis reaches the reviewer's screen without pretending to
                # be an editable value.
                "description_needed": not skip_desc,
                "description_note": skip_desc,
                **desc_ev,
                "annotations": [a.get("text", "") for a in annotations][:6],
                "rules_hit": list(getattr(d, "rules_hit", [])),
                "excluded_by": getattr(d, "exclude_rule", ""),
                "detail": dict(getattr(d, "evidence", {}) or {}),
                # The sentence this drawing's NOTES actually prints about the
                # mark on this symbol, quoted rather than interpreted: the tool
                # matched a mark, and the reader reads what the page says it
                # means.  Empty when the page defines no meaning, which is what
                # VENDOR_MARK_UNDEFINED is.
                "notes_text": _notes_quotes(d),
                "qty_basis": (f"1 symbol x {factor} (unit code {unit}, "
                              f"{mult.source})" if not undefined else
                              f"unit code {unit} undefined"),
                "qty_source": f"{mult.source} — {mult.note}" if mult.note else mult.source,
            }))
    return out


SKIPPED = "SKIPPED"        # not traced: this row will never carry a Description


def _trace_rows(rows, per_page, style, clock) -> dict:
    """Attach a pipe trace to every row that will need a Description.

    One graph per page, then one walk per row.  The result goes in the row's
    evidence as `trace` and is classified TRACED / MULTIPLE / FAILED so the
    accuracy of this stage can be counted rather than asserted.

    Rows exempt from Description are not walked at all - there is no sentence to
    write for them, so the walk would be work for nothing - and they are counted
    separately.  That also fixes the denominator: a success rate measured over
    every row understates the stage, because it charges it with rows it was never
    asked about.  Both numbers are reported.
    """
    area = CFG.rect("regions.drawing_area")
    stats = collections.Counter()
    graphs = {}
    traces = {}
    by_page = collections.defaultdict(list)
    skipped = 0
    for r in rows:
        if not r.description_needed:
            r.evidence["trace"] = {"status": SKIPPED, "reason": r.description_note}
            skipped += 1
            continue
        if r.rect:
            by_page[r.page_no].append(r)
    for pno, page_rows in sorted(by_page.items()):
        info = per_page.get(pno)
        if info is None:
            continue
        symbols = [(r.key, tuple(r.rect), r.type or r.valve_type) for r in page_rows]
        with clock.stage("pipe_graph", pno):
            g = pipe_graph.build(info["page_cache"], symbols, style, area)
        graphs[pno] = g.stats()
        by_key = {n.get("row_key"): nid for nid, n in g.nodes.items()
                  if n["kind"] == "SYMBOL"}
        for r in page_rows:
            nid = by_key.get(r.key)
            if nid is None:
                r.evidence["trace"] = {"status": pipe_graph.FAILED,
                                       "reason": "no graph node for this row"}
                stats[pipe_graph.FAILED] += 1
                continue
            tr = pipe_graph.trace(g, nid)
            tr["attached_by"] = g.nodes[nid].get("attached_by", "")
            r.evidence["trace"] = tr
            stats[tr["status"]] += 1
            traces[r.key] = tr
        # The text the drawing prints along those runs: the Description
        # candidates, collected by rule while the graph for this page is in hand.
        cands = dcand.collect(info["page_cache"], g, area, traces)
        for r in page_rows:
            r.evidence["candidates"] = dcand.group_lines(cands.get(r.key) or [])[:12]
    walked = sum(stats.values())
    return {
        "per_status": dict(stats),
        "graphs": graphs,
        # The two denominators, both stated: rows walked because they will need a
        # Description, and rows skipped because they will not.
        "description_needed": walked,
        "skipped_not_needed": skipped,
        "rate_of_needed": round(100 * stats[pipe_graph.TRACED] / walked, 1)
        if walked else 0.0,
        "rate_of_all_rows": round(100 * stats[pipe_graph.TRACED] / (walked + skipped), 1)
        if walked + skipped else 0.0,
    }


def probe_point(pdf_path: Path, page_no: int, x: float, y: float,
                radius: float = 60.0) -> dict:
    """What is drawn around a point, for the correction history.

    Called when a reviewer adds a row the engine missed and says where it is.
    Everything here is a measurement of the drawing - paths and their dimensions,
    the text nearby, and which detections the engine did make within reach, with
    the rules each one hit.  **Nothing decides why the engine missed it**; that
    question needs a body of these records, and answering it now from one would
    be the guess this exists to avoid.
    """
    doc, pages = pidcache.load_pages(pdf_path)
    pc = next((p for p in pages if p.page_no == page_no), None)
    if pc is None:
        return {"error": f"page {page_no} is not in this PDF"}
    box = (x - radius, y - radius, x + radius, y + radius)

    def near(rect):
        return not (rect.x1 < box[0] or rect.x0 > box[2]
                    or rect.y1 < box[1] or rect.y0 > box[3])

    paths = []
    for d in pc.drawings():
        b = d["bbox"]
        if not near(b):
            continue
        kinds = collections.Counter(i[0] for i in d["items"])
        paths.append({
            "rect": [round(v, 1) for v in (b.x0, b.y0, b.x1, b.y1)],
            "w": round(b.width, 1), "h": round(b.height, 1),
            "aspect": round(min(b.width, b.height) / max(b.width, b.height), 3)
            if max(b.width, b.height) else None,
            "items": dict(kinds), "filled": d.get("fill") is not None,
        })
    segs = [[round(p0.x, 1), round(p0.y, 1), round(p1.x, 1), round(p1.y, 1)]
            for p0, p1 in pc.segments()
            if box[0] <= p0.x <= box[2] and box[1] <= p0.y <= box[3]]
    words = [{"text": t, "rect": [round(v, 1) for v in (r.x0, r.y0, r.x1, r.y1)],
              "dist": round(max(abs((r.x0 + r.x1) / 2 - x),
                                abs((r.y0 + r.y1) / 2 - y)), 1)}
             for r, t in pc.words if near(r)]
    words.sort(key=lambda w: w["dist"])

    # What the engine did see here, and under which rules.
    dets, _scopes, _marks, _unver, unmapped, _boxes = ds.detect(pc, rules=ds.RULESET_V3)
    detections = []
    for d in dets:
        if not near(d.bbox):
            continue
        detections.append({
            "anchor": getattr(d, "anchor", ""),
            "excel_type": da.excel_type_under(d, ds.RULESET_V3),
            "included": da.included_under(d, ds.RULESET_V3, ACTIVE_SCOPE),
            "rules_hit": list(getattr(d, "rules_hit", []) or []),
            "exclude_rule": getattr(d, "exclude_rule", ""),
            "rect": [round(v, 1) for v in (d.bbox.x0, d.bbox.y0, d.bbox.x1, d.bbox.y1)],
            "evidence": dict(getattr(d, "evidence", {}) or {}),
        })
    unmapped_near = [u for u in unmapped
                     if abs(u["center"][0] - x) <= radius
                     and abs(u["center"][1] - y) <= radius]
    return {
        "page_no": page_no, "point": [round(x, 1), round(y, 1)], "radius": radius,
        "paths": paths[:120], "path_count": len(paths),
        "segments": segs[:400], "segment_count": len(segs),
        "words": words[:40],
        "detections": detections,
        "unmapped_tokens": unmapped_near,
        # The nearest *word*, not the nearest mark: these drawings write an
        # unassigned tag as `.....`, and keying the countable pattern on a full
        # stop would make every added row look like the same case.
        "nearest_text": next((w["text"] for w in words
                              if any(c.isalnum() for c in w["text"])), ""),
    }


def _notes_quotes(d) -> list:
    """The drawing's own words about this symbol's scope marks."""
    ev = getattr(d, "evidence", {}) or {}
    out = []
    mark = ev.get("vendor_mark") or {}
    if mark.get("meaning"):
        out.append(f"[벤더마크 x{mark.get('stars')}, {mark.get('source')}] "
                   f"{mark['meaning']}")
    sct = ev.get("sct_scope") or {}
    if sct.get("label"):
        # The span's own marking, quoted, under the corrected name: the letters
        # the drawing prints are `SCT`, and what the span means is a supplier
        # interface - the label used to claim the item was excluded as our own
        # piping, which named the wrong party.
        out.append(f"[{SUPPLIER_SPAN_LABEL}] 도면 표기 “{sct['label']}”"
                   f" ({sct.get('kind')})"
                   + (f", 공급: {SUPPLIER_SPAN_PARTY}" if SUPPLIER_SPAN_PARTY else ""))
    return out


def _vendor_of(d) -> str:
    hits = set(getattr(d, "rules_hit", []) or [])
    for tag in ("VENDOR_MARK_GLYPH", "VENDOR_MARK_TEXT", "VENDOR_MARK_BOX"):
        if tag in hits:
            return "VENDOR"
    if "VENDOR_MARK_UNDEFINED" in hits:
        return "UNDEFINED"
    return ""


def _scope_of(d) -> str:
    hits = set(getattr(d, "rules_hit", []) or [])
    return "SCT" if "SCT_SUPPLIER_SCOPE" in hits else ""


# Valve deliverable -> grid tab.
_VALVE_TAB = {dv.CLASS_BFV: TAB_BFV, dv.CLASS_MOV: TAB_MOV,
              dv.CLASS_CV: TAB_PNEUMATIC, dv.CLASS_XV: TAB_PNEUMATIC}

# Body families a deliverable covers, from the client's own files (config V5,
# taken from each one's DESCRIPTION line): BUTTERFLY for CZI, GATE/GLOBE/BALL for
# CZH.  A detection whose body is in none of them cannot be written into any
# deliverable as an actuated valve, and that is the whole authority this flag
# claims - it is not a detection rule, and it removes nothing.
#
# It is not derived from the legend, and that is deliberate: the legend does pair
# its pneumatic actuators with bodies, but only by example, and every example is
# a plain bowtie.  Measured on this document - legend p3 draws 4 domed
# diaphragms, all on bowties (tagged PRV, BPRV, FCV), and legend p4's CONTROL
# VALVE and ON-OFF VALVE rows draw 6 more, again all bowties.  The detector calls
# a plain bowtie GATE and a bowtie with a waist disc GLOBE, so taking the
# legend's examples as the permitted set would say GATE only, and throw away the
# 38 globe and 5 ball bodies the drawings actually put pneumatic actuators on.
# So the legend does not answer this question at the granularity it is asked.
ACTUATED_BODIES = frozenset(
    kind for _tag, _path, families in dv.DELIVERABLES for kind in families)


def _valve_rows(page_no, meta, res, mult) -> list:
    """Valve rows for one drawing (spike 4).

    Bodies with nothing on the stem are manual or self-acting and belong to no
    deliverable, so they are not emitted as rows; an unread actuator is emitted
    into the review queue because it is a valve whose class is unknown.
    """
    out = []
    unit = meta["unit_code"]
    factor = mult.multiplier(unit)
    undefined = factor is projectconfig.UNDEFINED
    for b in res["bodies"]:
        cls = dv.deliverable_class(b)
        unread = b.actuator == "UNREAD"
        if cls == dv.CLASS_EXCLUDED and not unread:
            continue
        rect = (b.rect.x0, b.rect.y0, b.rect.x1, b.rect.y1)
        reasons = []
        if any(m in b.actuator_evidence for m in IP_TOKEN_EVIDENCE):
            reasons.append(
                "an 'I/P' token was taken as this valve's actuator, but every "
                "such token in this document is part of an equipment name "
                "(e.g. 'IP TURBINE'), not a positioner - confirm before shipping")
        if unread:
            reasons.append("actuator enclosure found but its letter could not be "
                           "derived from this document")
        if not unread and b.kind not in ACTUATED_BODIES:
            reasons.append(
                f"a {b.actuator} actuator was read onto a {b.kind} body, and no "
                f"deliverable covers that body family "
                f"({', '.join(sorted(ACTUATED_BODIES))})"
                + (f"; the tag bubble says {b.tag}" if b.tag else "")
                + " - confirm before shipping")
        if undefined:
            reasons.append(f"unit code '{unit}' has no multiplier in the legend")
        out.append(Row(
            key=_key(meta["drawing_no"], page_no, "V", b.kind,
                     *[round(v, 1) for v in rect]),
            tab=_VALVE_TAB.get(cls, TAB_REVIEW),
            page_no=page_no,
            drawing_no=meta["drawing_no"],
            type=b.kind,
            qty=None if undefined else factor,
            system=meta["drawing_title"],
            valve_type=b.actuator if not unread else "",
            needs_review="; ".join(reasons),
            rect=rect,
            evidence={
                "body": b.kind,
                # No Description is written for a valve, and the reason is
                # recorded rather than left as an empty cell: the wording would
                # have to come from the client's valve master list, which has
                # never been supplied, and legend p3's ISA matrix is about
                # instrument tags - it says nothing about a gate or globe body.
                "description_missing":
                    "밸브 Description 문형의 기준이 될 발주처 마스터 밸브 리스트가 "
                    "없습니다. 범례 p3 ISA 문자표는 계기 태그용이라 밸브 몸체에는 "
                    "적용되지 않습니다",
                "description_needed": True,
                "body_basis": dict(b.evidence or {}),
                "state": b.state,
                "actuator": b.actuator,
                "actuator_basis": b.actuator_evidence,
                "tag": b.tag,
                "deliverable": cls,
                "qty_basis": (f"1 symbol x {factor} (unit code {unit}, "
                              f"{mult.source})" if not undefined else
                              f"unit code {unit} undefined"),
                "qty_source": f"{mult.source} — {mult.note}" if mult.note else mult.source,
            }))
    return out


def _glyph_alarms(glyphs) -> list:
    """VU6 guard: one glyph cluster carrying tags that disagree.

    out/valve_project_deps.md rates GLYPH_RADIUS the only high-risk UNKNOWN,
    and its dangerous failure is a radius set too wide, which merges two
    letters into one cluster and hands every member the majority letter.  That
    failure is visible: the cluster ends up holding tags that name different
    actuators.  This raises it rather than tuning the radius.
    """
    out = []
    for c in glyphs.clusters:
        letters = {dv.TAG_LETTER[t] for t in c.get("tags", {}) if t in dv.TAG_LETTER}
        if len(letters) > 1:
            out.append({
                "kind": "MIXED_TAG_GLYPH_CLUSTER",
                "size": c["size"], "pages": c["pages"], "tags": c["tags"],
                "letters": sorted(letters),
                "reason": "one glyph cluster carries tags naming different "
                          "actuators, so GLYPH_RADIUS has merged two letters; "
                          "the cluster's letter is not trustworthy",
            })
    return out


def fingerprint(result: dict) -> str:
    """Hash of everything the engine decided, for the determinism test."""
    payload = {
        "rows": sorted((r["key"], r["tab"], r["type"], r["qty"], r["valve_type"],
                        r["vendor_supply"], r["scope"], r["needs_review"],
                        tuple(r["rect"])) for r in result["rows"]),
        "multipliers": result["multipliers"],
        "legend": result["legend"],
        "glyphs": {"letters": result["glyphs"]["letters"]},
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
