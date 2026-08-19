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
import re
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
import describe_equipment as dequip  # noqa: E402
import describe_llm                # noqa: E402

CFG = projectconfig.load()
# The trade dictionary: power-plant abbreviations that hold on any project, kept
# apart from this client's choices so it can be carried to the next one unchanged.
# Only its `confirmed` sets are applied, and only where the project file says which
# member this client writes.
STANDARD = projectconfig.load_standard()

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
            reference: Path = None, use_prefix: bool = True,
            use_line_gate: bool = True) -> dict:
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
        # The equipment table off legend p2, and the nouns that name equipment.
        equip_symbols = dequip.derive_symbols(pages, CFG)
        equip_vocab = dequip.derive_vocabulary(equip_symbols, CFG)
        component_words = dequip.derive_component_words(pages)
        positions = dcand.derive_position_words(CFG)

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

    # Bubbles the drawing stacks edge-to-edge.  Whether they are one instrument
    # or several is a question about the plant, not about the drawing, so it is
    # answered in config; `_signal_groups` returns the rows the answer folds away.
    signal_groups, folded = _signal_groups(rows)
    if folded:
        rows = [r for r in rows if r.key not in folded]

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

    # Equipment, and the two-axis candidates the reviewer's rule asks for:
    # equipment first, the line second.  No pipe graph is involved on either axis.
    say(total - 1, total, "finding equipment")
    with clock.stage("equipment"):
        equip_by_page, equip_stats = _equipment_pass(per_page, equip_symbols,
                                                     equip_vocab, pattern)
    with clock.stage("candidates"):
        cand_stats = _candidate_pass(rows, per_page, equip_by_page, positions,
                                     pipe_style.values, component_words,
                                     use_prefix=use_prefix,
                                     few_equipment=int(
                                         (CFG.data.get("description") or {})
                                         .get("sole_equipment_sheet_max") or 0))

    # Description: choose a middle where the drawing offers candidates, grade
    # every row, and say in the Remark what the reviewer has to do about it.
    say(total - 1, total, "assembling descriptions")
    with clock.stage("description"):
        selector = describe_llm.build(CFG)
        examples = _client_examples(reference, tb_rows, pattern)
        desc_stats = _finish_descriptions(rows, per_page, isa, pattern,
                                          selector, examples, use_line_gate)

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
        "equipment": equip_stats,
        "candidates": cand_stats,
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

# Whether a group folds to one row.  **On**: the user answered the question in
# `out/ls_bundle_question.md` from plant practice - one switch reporting LSHH, LSH
# and LSL is one device - and that is a fact about the instrument, not about these
# drawings, so it settles what neither the legend nor the client's list could.
#
# The stack keeps its first bubble's row; the rest are dropped, and the row's
# quantity is one device x the sheet multiplier rather than the sum, which would
# have ordered one switch three times.  The signals it stands for are written into
# its evidence and into the workbook's REMARK, so the fold is legible from the
# deliverable and not only from this file.
# What the surviving row is called.  The client's own list settles it: all 22 of
# its level-switch rows put `LS` in the TYPE column and never `LSHH` or `LSH`; the
# high/low distinction is written in the Description instead.
MULTI_SIGNAL_TYPE = str((CFG.data.get("multi_signal_bundle") or {})
                        .get("merged_type") or "")
MULTI_SIGNAL_MERGE = bool((CFG.data.get("multi_signal_bundle") or {})
                          .get("merge_quantity") or False)
# Which signal the folded row's Description speaks for.  `representative` is the
# stack's first bubble - the form the client writes, since all 22 of its
# level-switch rows carry one signal each and none carries two.  `none` drops the
# alarm letters; `all` names every folded signal.  Neither appears in the client's
# list, so both are off and the setting is where a project says otherwise.
MULTI_SIGNAL_DESCRIPTION = str((CFG.data.get("multi_signal_bundle") or {})
                               .get("description_signal") or "representative")
if MULTI_SIGNAL_DESCRIPTION not in ("representative", "none", "all"):
    raise SystemExit("multi_signal_bundle.description_signal must be one of "
                     "representative / none / all, not "
                     f"{MULTI_SIGNAL_DESCRIPTION!r}")


def _signal_groups(rows) -> tuple:
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
    groups, folded = [], set()
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
            signals = " + ".join(str(r.evidence.get("anchor") or r.type)
                                 for r in grp)
            group["basis"]["signals"] = signals
            for i, r in enumerate(grp):
                r.evidence["signal_group"] = group
                if not MULTI_SIGNAL_MERGE:
                    # Left as they are: every bubble is its own row and the
                    # question goes to the reviewer.
                    r.needs_review = "; ".join(
                        [s for s in (r.needs_review, MULTI_SIGNAL_REASON) if s])
                    r.evidence.setdefault("review_codes", []).append(
                        "MULTI_SIGNAL_BUNDLE")
                    continue
                if i:
                    folded.add(r.key)
                    continue
                # One physical switch, so one row.  Its Q'ty is the sheet's own
                # multiplier for one device - the same number a single bubble
                # would carry - not the sum of the signals, which would order one
                # switch three times.
                r.type = MULTI_SIGNAL_TYPE or r.type
                r.evidence["qty_basis"] = (
                    f"맞닿은 신호 버블 {len(grp)}개 = 물리 기기 1개 "
                    f"({signals}); Q'ty 는 1 x 시트 승수 {r.qty} "
                    f"(config multi_signal_bundle.merge_quantity)")
                r.evidence["signal_members"] = [m["anchor"] or m["type"]
                                                for m in group["members"]]
                # Which signal the one surviving Description speaks for.  The
                # client's list cannot settle this - it has no line naming two
                # signals - so the choice is config, and every option is a form
                # that can be written down and read back (see
                # `multi_signal_bundle.description_signal`).
                if MULTI_SIGNAL_DESCRIPTION == "none":
                    # Drop the alarm letters, leaving the bare switch tag: the
                    # sentence then says LEVEL and nothing about high or low.
                    base = str(r.evidence.get("anchor") or r.type)
                    r.evidence["description_tag"] = base.rstrip("HL") or base
                elif MULTI_SIGNAL_DESCRIPTION == "all":
                    r.evidence["description_tags"] = list(
                        r.evidence["signal_members"])
            group["basis"]["merged"] = MULTI_SIGNAL_MERGE
            group["basis"]["folded_rows"] = len(grp) - 1 if MULTI_SIGNAL_MERGE else 0
    return groups, folded


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
            (GRADE_CONFIRMED, "도면 근거 있음",
             "이름·계통·변수를 모두 도면에서 읽음 (발주처 표기와 같다는 뜻은 아님)"),
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
    # Only the surviving rows are in the result - the folded members were dropped
    # - so the quantity is summed over the rows that are actually in the list.
    qty_now = sum(rows[m["key"]]["qty"] for m in members
                  if m["key"] in rows
                  and isinstance(rows[m["key"]].get("qty"), (int, float)))
    L = ["# 다중 신호 버블 — 물리 수량 (답변 받음) 과 문형 (미결)", ""]
    L.append("도면에서 세로로 **맞닿아** 그려진 계기 버블 묶음입니다. 물리 수량은 "
             "실사용자가 확인해 줬고 — 하나의 Level Switch 가 LSHH·LSH·LSL 을 "
             "보고하는 것이므로 기기는 1개 — 그대로 적용했습니다. 남은 질문은 "
             "**한 행이 된 그 행의 Description 문형** 하나입니다.")
    L.append("")
    L.append("## 적용한 것")
    L.append("")
    L.append(f"- 묶음 **{len(groups)}건**, 버블 **{len(members)}개** → "
             f"리스트 **{len(groups)}행** · 그 행들의 Q'ty 합계 **{qty_now}** "
             f"(각 행 1 x 시트 승수)")
    L.append("- 남은 행의 TYPE 은 발주처 리스트가 LS 22행 전부에 쓰는 `LS`")
    L.append("- 접힌 신호는 근거 패널과 산출물 REMARK 열에 그대로 적혀 있어, "
             "도면의 버블 수와 행을 대조할 수 있습니다")
    L.append("")
    L.append("## 남은 질문 — 접힌 행의 Description")
    L.append("")
    L.append("발주처 리스트에는 **한 행이 두 신호를 말하는 문형이 없습니다**. "
             "LS 22행은 11쌍이고, 한 주어에 `... LEVEL HIGH HIGH` 한 행과 "
             "`... LEVEL HIGH` 한 행을 따로 씁니다 (각 Q'ty 2). 즉 발주처가 "
             "직접 쓴 곳에서는 **신호 하나에 한 행**입니다. 그래서 접힌 행은 "
             "묶음의 첫 신호로 쓰고 있습니다 — 셋 중 발주처가 실제로 쓰는 유일한 "
             "형태입니다.")
    L.append("")
    L.append("| 선택지 | 예 | 발주처 557행에서의 사용 |")
    L.append("|---|---|---:|")
    L.append("| `representative` (적용 중) | `... LEVEL HIGH HIGH` | 11행 |")
    L.append("| `all` | `... LEVEL HIGH HIGH HIGH LOW` | 0행 |")
    L.append("| `none` | `... LEVEL` | 0행 |")
    L.append("")
    L.append(f"현재 값: `config multi_signal_bundle.description_signal: "
             f"{MULTI_SIGNAL_DESCRIPTION}`. 다른 것을 원하시면 이 값만 바꾸면 "
             f"됩니다.")
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
    L.append("## 수량 질문에 받은 답")
    L.append("")
    L.append("**답을 받았습니다.** 하나의 물리 Level Switch 에 LSHH·LSH·LSL 신호가 "
             "표기된 것이므로 물리 수량은 1입니다. `config multi_signal_bundle."
             "merge_quantity` 를 켜서 맞닿은 묶음은 **한 행으로 접고**, 그 행의 "
             "TYPE 은 발주처 리스트가 22행 전부에 쓰는 `LS` 로, Q'ty 는 1 x 시트 "
             "승수로 둡니다. 접힌 행은 근거 패널에 원래 구성(예: `LSHH + LSH + "
             "LSL` 3신호 = 물리 1개)을 남깁니다. "
             f"현재 값: `{'on' if MULTI_SIGNAL_MERGE else 'off'}`, TYPE "
             f"`{MULTI_SIGNAL_TYPE or '(변경 없음)'}`.")
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

# What a row's Description still needs, written from the grade the Description
# pass ended with rather than from the draft it started with.  The earlier wording
# was raised while the row was built - before the pass ran - and stayed on 746
# rows the pass then completed, quoting a precision figure from three rounds ago.
DESCRIPTION_REVIEW = {
    GRADE_PARTIAL: ("Description 부분 생성 — 단위·계통·변수까지는 도면에서 "
                    "확인됐고 중간 서술은 확인되지 않았습니다. 검토 후 확정 필요"),
    GRADE_LOW: ("Description 중간 서술을 후보에서 골랐으나 근거가 약합니다 — "
                "확인 필요"),
    GRADE_NONE: "Description 근거 부족 — 공란으로 남겼습니다",
}
DESCRIPTION_NONE = DESCRIPTION_REVIEW[GRADE_NONE]


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
                    "description_missing": d["reason"]}, ""
    return d["text"], {"description_sources": d["sources"],
                       "description_missing": d["reason"]}, ""


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


def _equipment_pass(per_page, symbols, vocab, pat) -> tuple:
    """Equipment named on every drawing, numbered within its own group."""
    out, stats = {}, collections.Counter()
    area = CFG.rect("regions.drawing_area")
    aliases = dequip.derive_aliases(
        (STANDARD or {}).get("confirmed") or {},
        (CFG.data.get("description") or {}).get("equipment_alias_choice") or {})
    stats["aliases"] = len(aliases)
    pitch = dequip.derive_line_pitch(
        [info["page_cache"] for _p, info in sorted(per_page.items())], area)
    stats["line_pitch_pt"] = pitch
    for pno, info in sorted(per_page.items()):
        found = dequip.find_labels(
            info["page_cache"], vocab, area, pitch,
            (CFG.data.get("description") or {}).get("equipment_modifiers"), aliases)
        found = dequip.group(found)
        out[pno] = found
        stats["instances"] += len(found)
        stats["pages_with_equipment"] += 1 if found else 0
        for e in found:
            if (e.evidence or {}).get("alias_of"):
                stats["alias_applied"] += 1
            stats[f"noun:{e.kind}"] += 1
            if e.ordinal:
                stats["numbered"] += 1
            if e.count_note:
                stats["with_count_note"] += 1
    report = {
        "legend_symbols": [{"name": s.name, "anchor": list(s.anchor),
                            "kinds": [list(k) for k in s.kinds]} for s in symbols],
        "vocabulary": vocab,
        "instances": stats["instances"],
        "numbered": stats["numbered"],
        "with_count_note": stats["with_count_note"],
        "pages_with_equipment": stats["pages_with_equipment"],
        "by_noun": {k[5:]: v for k, v in stats.items() if k.startswith("noun:")},
        # Why shapes are not used to find instances - measured, see
        # describe_equipment's module note.
        "shape_matching": "not used: legend symbol sizes do not recur on the "
                          "sheets (pump 40.5x38.5 in the legend, 46.2x44.0 on p26; "
                          "ratios across 20 pages scatter x0.42-x2.00)",
    }
    return out, report


def _candidate_pass(rows, per_page, equip_by_page, positions, style,
                    component_words, use_prefix: bool = True,
                    few_equipment: int = 0) -> dict:
    """Two-axis candidates for every row, and the distance the cut was made at.

    The equipment distance limit is measured, not chosen: every instrument's
    distance to the nearest equipment on its own sheet is collected first, and the
    limit is that distribution's 90th percentile.  Both the limit and the
    distribution are reported.
    """
    area = CFG.rect("regions.drawing_area")
    by_page = collections.defaultdict(list)
    for r in rows:
        if r.rect and r.description_needed:
            by_page[r.page_no].append(r)

    nearest = []
    for pno, page_rows in by_page.items():
        for e in equip_by_page.get(pno, ()):
            pass
        for r in page_rows:
            cx, cy = (r.rect[0] + r.rect[2]) / 2, (r.rect[1] + r.rect[3]) / 2
            ds = [max(abs((e.rect[0] + e.rect[2]) / 2 - cx),
                      abs((e.rect[1] + e.rect[3]) / 2 - cy))
                  for e in equip_by_page.get(pno, ())]
            if ds:
                nearest.append(min(ds))
    limit = dcand.distance_limit(nearest)
    # How far a run may sit from an equipment label and still count as reaching
    # it.  Measured over the whole document, not chosen - see the function.
    reach = dcand.derive_equipment_reach(
        [info["page_cache"] for _p, info in sorted(per_page.items())],
        equip_by_page, style)

    stats = collections.Counter()
    hist = collections.Counter()
    for d in nearest:
        hist[int(d // 100) * 100] += 1
    for pno, page_rows in sorted(by_page.items()):
        info = per_page[pno]
        triples = [(r.key, tuple(r.rect), r.type) for r in page_rows]
        comps = dequip.find_components(info["page_cache"], component_words, area)
        # A sheet that names only one or two pieces of equipment has nothing for
        # the distance limit to choose between: the limit exists to stop an
        # instrument borrowing a name from the far side of a crowded sheet.  On
        # p20 the pump is captioned once at the foot of the sheet, 700 pt from the
        # instruments, and all 33 of the client's lines on it name that pump.
        # Measured on the two sheets that qualify, though - p31's sole label is the
        # bare word `PUMP` and 0 of its 15 lines use it - so this is reported with
        # its own `--without` number rather than assumed.
        page_limit = None if (few_equipment
                              and len({e.label for e in equip_by_page.get(pno, ())})
                              <= few_equipment) else limit
        cands = dcand.collect(info["page_cache"], triples,
                              equip_by_page.get(pno, ()), area, positions, page_limit,
                              style=style, components=comps,
                              reach=reach.values["equipment_reach"],
                              between_types=CFG.data.get("description", {})
                              .get("between_symbol_types") or (),
                              use_prefix=use_prefix)
        stats["component_words"] += len(comps)
        ordinals = dcand.instrument_ordinals(triples, cands,
                                             equip_by_page.get(pno, ()))
        for r in page_rows:
            got = cands.get(r.key) or []
            r.evidence["candidates"] = got
            ordinal, where = ordinals.get(r.key, ("", ""))
            r.evidence["instrument_ordinal"] = ordinal
            r.evidence["ordinal_place"] = where
            kinds = {c["kind"] for c in got}
            stats["rows"] += 1
            stats["equipment_axis"] += 1 if dcand.EQUIPMENT in kinds else 0
            stats["connected"] += 1 if any(c.get("connected") for c in got) else 0
            stats["by_prefix"] += 1 if (got and got[0].get("by_prefix")) else 0
            stats["line_axis"] += 1 if (dcand.EQUIPMENT not in kinds
                                        and dcand.CONNECTOR in kinds) else 0
            stats["no_candidate"] += 1 if not (kinds & set(dcand.NAMED_KINDS)) else 0
    return {
        "rows": stats["rows"],
        "equipment_axis": stats["equipment_axis"],
        "connected_subject": stats["connected"],
        "prefix_subject": stats["by_prefix"],
        "line_axis": stats["line_axis"],
        "no_candidate": stats["no_candidate"],
        "component_words": stats["component_words"],
        "distance_limit_pt": limit,
        "equipment_reach_pt": reach.values["equipment_reach"],
        "equipment_reach": {"source": reach.source, "note": reach.note,
                            **(reach.evidence or {})},
        "distance_note": "instrument-to-nearest-equipment, 90th percentile of "
                         f"{len(nearest)} measured distances",
        "distance_histogram_100pt": dict(sorted(hist.items())),
    }


_UNIT_MARK = re.compile(r"#\s*(\d{1,2})\b")


def _local_unit(cands, marks_on_page, sheet_code: str, skip=()) -> tuple:
    """The unit number printed nearest the instrument, or the sheet's own.

    Only a number this page actually prints as a `#` mark counts, so a pipe size
    or a note number cannot become a unit.  A sheet whose own code the client
    leaves off the line entirely - unit 00, 98 lines of 98 - is never overridden:
    borrowing a `#11` printed on it put a prefix on lines the client writes bare.
    """
    if str(sheet_code) in skip:
        return sheet_code, ""
    for c in sorted((c for c in cands if c["kind"] == dcand.UNIT_MARK),
                    key=lambda c: c["distance"]):
        for num in _UNIT_MARK.findall(str(c["text"])):
            if num in marks_on_page:
                return num, str(c["text"])
    return sheet_code, ""


def _user_input_note(type_, middle: str, noun: str, system: str) -> tuple:
    """Why a row still needs a person, where the drawing is known not to say.

    These are not "we did not manage": each one was measured and the drawing does
    not carry the answer.  The reasons and the counts behind them live in
    `config description.user_input_reasons`, and a row only gets one when it is in
    the class that was measured - a PDIT on a pump for the strainer, a PI on a
    closed-cooling-water sheet for supply against return.
    """
    for rule in ((CFG.data.get("description") or {}).get("user_input_reasons") or ()):
        types = [str(t).upper() for t in (rule.get("types") or ())]
        if types and str(type_).upper() not in types:
            continue
        want_noun = str(rule.get("noun") or "").upper()
        if want_noun and want_noun != str(noun).upper():
            continue
        want_system = str(rule.get("system") or "").upper()
        if want_system and want_system != str(system).upper():
            continue
        if rule.get("needs_subject") and not middle:
            continue
        # The tag is what the review screen groups on.  It is generated, not parsed
        # back out of the sentence, so the grouping cannot drift from the reason.
        tag = str(rule.get("tag") or "").strip()
        reason = " ".join(str(rule.get("reason") or "").split())
        return (str(rule.get("code") or ""),
                f"[{tag}] {reason}" if tag else reason)
    return "", ""


def _finish_descriptions(rows, per_page, isa, pat, sel, examples,
                         use_line_gate: bool = True) -> dict:
    """Write each row's Description from its best candidate, and grade every row.

    The subject is chosen by the reviewer's rule, not by preference: equipment
    when the drawing names equipment near the instrument, the line's `TO` / `FROM`
    text when it does not.  The selector is offered only what is left over - rows
    that have candidates but no equipment - and its answer is still re-validated
    (`describe_llm.validate`) before it reaches the column.
    """
    stats = collections.Counter()
    grades = collections.Counter()
    line_types = frozenset(
        str(t).upper() for t in
        ((CFG.data.get("description") or {}).get("line_phrase_types") or ()))
    if not use_line_gate:
        line_types = None
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
        info = per_page.get(r.page_no) or {}
        # A folded signal stack writes one sentence for several bubbles, and
        # `multi_signal_bundle.description_signal` says which signal it speaks
        # for.  Untouched rows have neither key and read their own anchor.
        tag = ev.get("description_tag") or ev.get("anchor") or r.type
        parts_ok = len(ev.get("description_sources") or []) >= 3
        subject = next((c for c in cands if c["kind"] == dcand.EQUIPMENT), None)
        axis = "EQUIPMENT" if subject else ""
        why, middle_kind = "", ""
        if subject is None:
            # The line phrase is written by one type and no other.  Counted on the
            # client's 557 lines: LS writes `TO ...` on 22 of 22, every other type
            # on 14 of 535 (2.6%) and those 14 are one-off phrases with no shared
            # condition.  Where the drawing names no equipment, the sentence is
            # left without a middle rather than given a route the client would not
            # have written - the same call as the position word, where attaching
            # nothing beat attaching something.
            if line_types is None or str(r.type).upper() in line_types:
                subject = next((c for c in cands
                                if c["kind"] == dcand.CONNECTOR), None)
                axis = "LINE" if subject else ""
            else:
                stats["line_phrase_withheld"] += 1 if any(
                    c["kind"] == dcand.CONNECTOR for c in cands) else 0
        if subject is None:
            why = "후보 0개" if not cands else "이름을 대는 후보 없음"
            stats["no_candidates" if not cands else "no_named_candidate"] += 1
        else:
            middle_kind = subject["kind"]
            stats[axis.lower() + "_axis"] += 1

        # An instrument ordinal goes at the very end, and only when this row would
        # otherwise read the same as another on the same subject.
        ordinal = ev.get("instrument_ordinal", "") if subject else ""
        place = ev.get("ordinal_place", "END")
        if subject is not None and ordinal and place == "MIDDLE":
            # the letter numbers the equipment unit, so it belongs beside its noun
            eq = dict(subject.get("equipment") or {})
            eq["ordinal"] = ordinal
            subject = dict(subject, equipment=eq)
        # The unit number is the one printed beside the instrument, not the one on
        # the title block.  A steam sheet coded #10 draws HRSG #11 and #12 side by
        # side and the client writes the HRSG the instrument is on: measured over
        # the 438 client lines that carry a mark, the nearest printed mark is right
        # on 173 lines the sheet code gets wrong and wrong on 31 it gets right -
        # net 142.  With no mark printed near the instrument the sheet code stands.
        unit_code, mark = _local_unit(cands, units_by_page.get(r.page_no) or set(),
                                      info.get("unit_code", ""),
                                      pat.unit_prefix_skip)
        ev["unit_mark_source"] = mark
        if unit_code != info.get("unit_code", ""):
            stats["local_unit"] += 1
        built = desc.assemble(unit_code, r.system, tag, isa, pat,
                              subject=subject,
                              suffix=ordinal if place != "MIDDLE" else "",
                              type_=r.type,
                              between=((subject.get("equipment") or {}).get("between", "")
                                       if subject else ""))
        if ev.get("description_tags"):
            # `description_signal: all` - the sentence names every folded signal.
            # Built by re-reading the alarm words of each one off the same table,
            # so the extra words come from the client's counts like the first
            # signal's do, not from a new rule.
            extra = []
            for sig in ev["description_tags"][1:]:
                for w in desc.alarm_words(str(sig).upper(), (True,), pat):
                    extra.append(w)
            if extra:
                built = dict(built, text=" ".join([built["text"]] + extra))
        if parts_ok:
            r.description = built["text"]
            ev["description_sources"] = built["sources"]
            ev["description_axis"] = axis
            if subject:
                ev["description_selected"] = {
                    "middle": built["middle"], "kind": subject["kind"],
                    "axis": axis, "distance": subject["distance"],
                    "direction": subject["direction"],
                    "connected": bool(subject.get("connected")),
                    "connected_by": subject.get("connected_by", ""),
                    "equipment": subject.get("equipment") or {},
                }
        r.description_grade, r.remark = _grade(
            parts_ok, built["middle"], middle_kind, False, why)
        code, note = _user_input_note(
            r.type, built["middle"],
            (subject.get("equipment") or {}).get("noun", "") if subject else "",
            " ".join(desc.system_words(r.system, pat)[0]))
        if note:
            ev["user_input_reason"] = note
            if code:
                ev.setdefault("review_codes", [])
                if code not in ev["review_codes"]:
                    ev["review_codes"].append(code)
            stats["user_input"] += 1
            r.remark = f"{r.remark} — {note}" if r.remark else note
        # Now that the grade is known, say what this row still needs - and take
        # off any earlier draft sentence, so `needs_review` and the grade cannot
        # disagree with each other.
        keep = [x for x in (r.needs_review or "").split("; ")
                if x and x not in DESCRIPTION_REVIEW.values()]
        want = DESCRIPTION_REVIEW.get(r.description_grade, "")
        if want:
            keep.append(want)
            ev.setdefault("review_codes", [])
            if "DESCRIPTION_INCOMPLETE" not in ev["review_codes"]:
                ev["review_codes"].append("DESCRIPTION_INCOMPLETE")
        else:
            ev["review_codes"] = [c for c in (ev.get("review_codes") or [])
                                  if c != "DESCRIPTION_INCOMPLETE"]
        r.needs_review = "; ".join(keep)
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
    if middle_kind == dcand.EQUIPMENT:
        # The drawing names the equipment and the instrument sits beside it: every
        # piece of the sentence has a source on the sheet.  That is all this grade
        # claims, and it is worth being exact about what it does not claim - of the
        # 455 of these rows the client's list also covers, 27 match it word for
        # word and 338 name the same equipment.  A narrower, surer grade was looked
        # for and is not there: agreement runs 63-80% in every band of distance,
        # runner-up margin, candidate count, direction and noun source, so no
        # threshold separates the right ones from the wrong ones.  Rather than
        # invent one, the grade keeps its rule and its label says what it means.
        return GRADE_CONFIRMED, REMARK[GRADE_CONFIRMED]
    # A route (`TO CLEAN DRAIN TANK`) names where the pipe goes, not what the
    # instrument is on, so it is offered rather than asserted.
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
        codes = []
        if skip_desc:
            description, desc_ev, desc_reason = "", {}, ""
        else:
            # The reason is not raised here: what the row still needs depends on
            # the grade the Description pass ends with, and that pass has not run
            # yet.  `_finish_descriptions` writes it once the answer is known.
            description, desc_ev, _draft_reason = _describe_row(
                meta, getattr(d, "anchor", "") or type_, isa, pat)
        if undefined:
            codes.append("MULTIPLIER_UNDEFINED")
            reasons.append(f"unit code '{unit}' is not in the legend's UNIT "
                           f"IDENTIFICATION NUMBERS table, so no multiplier")
        if "VENDOR_MARK_UNDEFINED" in (getattr(d, "rules_hit", []) or []):
            codes.append("VENDOR_MARK_UNDEFINED")
            reasons.append("a vendor mark is drawn on this symbol but this "
                           "drawing's NOTES do not define what it means, so "
                           "whether it is vendor supply is undecided")
        if scope_keywords:
            codes.append("SCOPE_OVERRIDE_UNRESOLVED")
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
                "review_codes": codes,
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
        reasons, codes = [], []
        if any(m in b.actuator_evidence for m in IP_TOKEN_EVIDENCE):
            codes.append("IP_TOKEN_AS_ACTUATOR")
            reasons.append(
                "an 'I/P' token was taken as this valve's actuator, but every "
                "such token in this document is part of an equipment name "
                "(e.g. 'IP TURBINE'), not a positioner - confirm before shipping")
        if unread:
            codes.append("ACTUATOR_LETTER_UNREAD")
            reasons.append("actuator enclosure found but its letter could not be "
                           "derived from this document")
        if not unread and b.kind not in ACTUATED_BODIES:
            codes.append("ACTUATOR_ON_UNEXPECTED_BODY")
            reasons.append(
                f"a {b.actuator} actuator was read onto a {b.kind} body, and no "
                f"deliverable covers that body family "
                f"({', '.join(sorted(ACTUATED_BODIES))})"
                + (f"; the tag bubble says {b.tag}" if b.tag else "")
                + " - confirm before shipping")
        if undefined:
            codes.append("MULTIPLIER_UNDEFINED")
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
                "review_codes": codes,
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
