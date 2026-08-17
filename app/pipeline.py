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
import extract_titleblocks as tb   # noqa: E402
import detect_symbols as ds        # noqa: E402
import detect_all as da            # noqa: E402
import detect_valves as dv         # noqa: E402
import parse_notes as pn           # noqa: E402
import pipe_graph                  # noqa: E402

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
        rows.extend(_field_rows(pc, meta, dets, mult, annotations, scope_keywords))
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
            "reason": f"{rule} — 이 심볼은 제외되어 리스트에 나오지 않습니다",
            # The sentence this page's NOTES prints about the mark.  For an
            # excluded symbol this *is* the answer to "why is it not in my
            # list", so it travels with the mark rather than living in a row
            # that was never created.
            "notes_text": _notes_quotes(d),
        })
    return out


def _field_rows(pc, meta, dets, mult, annotations, scope_keywords=()) -> list:
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
            needs_review="; ".join(reasons),
            annotation=("reviewer markup on this drawing" if marked else ""),
            rect=rect,
            evidence={
                "anchor": getattr(d, "anchor", ""),
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


def _trace_rows(rows, per_page, style, clock) -> dict:
    """Attach a pipe trace to every row that has a rectangle.

    One graph per page, then one walk per row.  The result goes in the row's
    evidence as `trace` and is classified TRACED / MULTIPLE / FAILED so the
    accuracy of this stage can be counted rather than asserted.
    """
    area = CFG.rect("regions.drawing_area")
    stats = collections.Counter()
    graphs = {}
    by_page = collections.defaultdict(list)
    for r in rows:
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
    return {"per_status": dict(stats), "graphs": graphs}


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
        out.append(f"[SCT {sct.get('kind')}] {sct['label']}")
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
