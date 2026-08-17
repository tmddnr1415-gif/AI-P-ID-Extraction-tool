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
import hashlib
import json
import sys
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

CFG = projectconfig.load()

# The exclusion set Phase 0 scored on.  `included_under` takes the rules that
# are *active* - not the ones that are disabled - and passing
# `detect_symbols.DEFAULT_DISABLED` here meant the three vendor-mark rules were
# never applied, so every vendor-supply symbol came through as a deliverable
# row.  This is the `v3_glyph_text_box` variant, the one out/failure_report.md
# calls the baseline at 97.0 / 87.0; SCT stays out of it for the reason
# detect_symbols.DEFAULT_DISABLED records.
ACTIVE_SCOPE = da.COMBOS["glyph+text+box"]

# Which grid tab a row belongs to.  These are the four deliverables the client
# splits its packages by, plus the review queue.
TAB_FIELD = "FIELD"
TAB_BFV = "BFV"
TAB_MOV = "MOV"
TAB_PNEUMATIC = "PNEUMATIC"
TAB_REVIEW = "REVIEW"

# How a page relates to the client's Excel.  Exactly the three sets
# detect_all.py already scores with, computed the same way and reported per
# row so a reviewer can decide what to ship - the tool does not decide for them.
#
#   MATCHED       the drawing has rows in the client's Excel; this is the only
#                 set the Phase 0 accuracy numbers were ever measured on
#   PDF_ONLY      the drawing is in the PDF and has no rows in the Excel at all
#   REVISION_GAP  the drawing carries reviewer markup recording a revision the
#                 Excel has not taken up (out/revision_gap.md)
#
# A page can be both MATCHED and REVISION_GAP; the gap flag wins in the column
# because it is the one that changes what a reviewer should do about the row.
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
    origin: str = ""               # MATCHED | PDF_ONLY | REVISION_GAP
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


# The client's instrument list, used only to tell which drawings it covers.
# Nothing about detection reads it; it decides `origin`, and `origin` decides
# nothing on its own either - it is a column and a filter.
REFERENCE_EXCEL = Path(__file__).resolve().parent.parent / "data" / "CZE_Field_Instrument.xlsx"


def _page_origins(pages, tb_rows, per_page, reference: Path = REFERENCE_EXCEL) -> dict:
    """page_no -> MATCHED | PDF_ONLY | REVISION_GAP, by detect_all's own rule.

    The MATCHED / PDF_ONLY split is `detect_all.attribute_rows`, unchanged: a
    drawing number appearing on several sheets is attributed by matching the
    Excel SYSTEM value against the drawing title, which is what stopped 52
    phantom over-detections being counted in Phase 0.  REVISION_GAP is
    `detect_all.review_annotations` finding markup in the drawing body.
    """
    origins = {p: ORIGIN_PDF_ONLY for p in per_page}
    if reference.exists():
        excel, _total, _spare = da.load_excel(reference)
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


def analyse(pdf_path: Path, progress=None) -> dict:
    """Full analysis of one PDF.  `progress(done, total, message)` is optional."""
    def say(done, total, msg):
        if progress:
            progress(done, total, msg)

    doc, pages = pidcache.load_pages(pdf_path)
    total = len(pages) + 6
    say(1, total, "reading title blocks")

    library = tb.build_glyph_library(pages)
    tb_rows = {r["page_no"]: r for r in (tb.extract_page(pd, library) for pd in pages)}

    say(2, total, "measuring rules off the legend sheets")
    dv.LAYOUT, legend_derived = dv.derive_layout(pages)

    page_kinds = {p: r["page_kind"] for p, r in tb_rows.items()}
    say(3, total, "deriving unit multipliers from legend page 5")
    mult = projectconfig.derive_unit_multipliers(pages, CFG, page_kinds)

    targets = [pc for pc in pages
               if tb_rows[pc.page_no]["page_kind"] == "PID" and pc.analysis_scope]

    rows: list[Row] = []
    layers: dict[int, dict] = {}
    per_page: dict[int, dict] = {}

    for i, pc in enumerate(targets, 1):
        say(3 + i, total, f"page {pc.page_no} of {len(pages)}")
        meta = tb_rows[pc.page_no]
        dets, scopes, mark_dict, unverified, unmapped, boxes = ds.detect(
            pc, rules=ds.RULESET_V3)
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
        }
        rows.extend(_field_rows(pc, meta, dets, mult, annotations, scope_keywords))
        layers.setdefault(pc.page_no, collections.defaultdict(list))

    say(total - 2, total, "valve bodies and actuators")
    valve_results, glyphs = dv.analyse_all(pages)
    for page_no, res in valve_results.items():
        meta = tb_rows.get(page_no)
        if not meta or meta["page_kind"] != "PID":
            continue
        rows.extend(_valve_rows(page_no, meta, res, mult))

    origins = _page_origins(pages, tb_rows, per_page)
    for r in rows:
        r.origin = origins.get(r.page_no, ORIGIN_PDF_ONLY)

    say(total - 1, total, "building overlays")
    for r in rows:
        if not r.rect:
            continue
        layers.setdefault(r.page_no, collections.defaultdict(list))
        layers[r.page_no][r.tab].append({
            "key": r.key, "rect": [round(v, 1) for v in r.rect],
            "label": r.type or r.valve_type, "needs_review": bool(r.needs_review),
        })

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
    return {
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
                "qty_basis": (f"1 symbol x {factor} (unit code {unit}, "
                              f"{mult.source})" if not undefined else
                              f"unit code {unit} undefined"),
            }))
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
        if unread:
            reasons.append("actuator enclosure found but its letter could not be "
                           "derived from this document")
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
