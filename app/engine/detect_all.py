#!/usr/bin/env python3
"""Phase 0 spike 2b — measure the page-6 ruleset over the whole drawing set.

This revision fixes the *measurement* rather than the detector.  The previous
run scored 81.9% / 73.5%, but that number mixed three different things
together, so it could not be used as a baseline:

* Five Excel drawing numbers have no page in the PDF at all — undetectable by
  construction, yet they were counted as recall misses.
* Fourteen pages have no Excel rows — counted as precision misses.
* Three drawing numbers are shared by two different drawings, so the 1:N join
  summed detections from one drawing against another drawing's rows.

Now the join is **page-level**.  Rows of a shared drawing number are attributed
to a specific page by matching the Excel `SYSTEM` column against the page's
drawing title, and the comparison is split into three disjoint sets:

    MATCHED     page and Excel rows both exist   <- rule quality measured here
    EXCEL_ONLY  Excel rows with no page          <- reported, never scored
    PDF_ONLY    page with no Excel rows          <- reported, never scored

The anchor dictionary is also corrected against the full 563-row Excel rather
than page 6 alone (see RULESET_V1 / RULESET_V2 in detect_symbols.py), and both
versions are scored side by side so the effect is visible.

No new detection rules are added here.

Usage
-----
    python spike/detect_all.py --pdf data/pid_total.pdf \
           --compare data/CZE_Field_Instrument.xlsx \
           --titleblocks out/titleblocks.csv \
           --json out/detect_all.json --failures out/failure_report.md
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from detect_symbols import (  # noqa: E402
    KNOWN_GLYPH_SIZES,
    RULESET_V1,
    RULESET_V2,
    RULESET_V3,
    bubble_sizes,
    detect,
    find_bubbles,
    find_marks,
    find_package_boxes,
    read_mark_dictionary,
)
import projectconfig  # noqa: E402
from pidcache import load_pages  # noqa: E402

CFG = projectconfig.load()

# A vendor mark written as literal text, e.g. "(*)" or "(**)".  Page 6 draws its
# marks as vector glyphs; other sheets type them instead, and the page-6 rule
# only knows how to see the drawn form.
MARK_TEXT_RE = re.compile(r"^\({1,2}\*{1,3}\)?$")

# Korean reviewer markup sits on these sheets as a separate annotation layer
# (삭제 = delete, 추가 = add, 위치이동 = relocate, 복원 = restore).  It matters twice
# over: its text is picked up by the anchor scanner, and it records revisions the
# Excel has not absorbed.  Diagnostic only — nothing acts on it.
HANGUL_RE = re.compile("[" + "".join(CFG.get("review_markup.script_ranges")) + "]")


def review_annotations(pc, lay_x=1960.0):
    out, cur, last = [], [], None
    ann = sorted([(r, t) for r, t in pc.words if HANGUL_RE.search(t)],
                 key=lambda z: (round(z[0].y0 / 8), z[0].x0))
    for r, t in ann:
        key = round(r.y0 / 8)
        if key != last:
            if cur:
                out.append(cur)
            cur, last = [], key
        cur.append((r, t))
    if cur:
        out.append(cur)
    res = []
    for grp in out:
        r0 = grp[0][0]
        # pull in the latin words on the same line, so "PIT 삭제" survives intact
        line = [(r, t) for r, t in pc.words
                if abs((r.y0 + r.y1) / 2 - (r0.y0 + r0.y1) / 2) < 6
                and abs(r.x0 - r0.x0) < 260]
        line.sort(key=lambda z: z[0].x0)
        res.append({"where": "TITLEBLOCK" if r0.x0 > lay_x else "DRAWING",
                    "pos": [round(r0.x0, 1), round(r0.y0, 1)],
                    "text": " ".join(t for _, t in line)})
    return res

def annotation_anchors(pc, unverified, x_reach=260.0, y_tol=8.0):
    """Split geometry-rejected anchors into review markup vs genuine misses.

    A reviewer note like "PIT 삭제" puts the letters PIT on the sheet with no
    bubble around them, so the anchor scanner picks it up and geometry
    verification throws it out.  Counting those as AMBIGUOUS_GEOMETRY overstates
    the geometry problem and hides a data-quality one, so they get their own
    bucket: an anchor is markup when Korean text shares its line.
    """
    han = [r for r, t in pc.words if HANGUL_RE.search(t)]
    ann, rest = [], []
    for u in unverified:
        cx, cy = u["center"]
        if any(abs((r.y0 + r.y1) / 2 - cy) <= y_tol and abs(r.x0 - cx) <= x_reach
               for r in han):
            ann.append(u)
        else:
            rest.append(u)
    return ann, rest


VENDOR_RULES = ("VENDOR_MARK_GLYPH", "VENDOR_MARK_TEXT", "VENDOR_MARK_BOX")
SCOPE_RULES = VENDOR_RULES + ("SCT_SUPPLIER_SCOPE",)


class ActiveScope(frozenset):
    """The exclusion rules that are switched ON.

    A distinct type, because there is a set of the same shape meaning the exact
    opposite - `detect_symbols.DEFAULT_DISABLED`, the rules switched OFF - and
    passing one where the other belongs type-checks, runs, and quietly changes
    the answer.  That is not hypothetical: app/pipeline.py did it, and the
    result was every vendor-supply symbol appearing as a deliverable row (906
    instead of 748) with nothing failing.

    `included_under` now requires this type, so the mistake raises instead of
    scoring.
    """

    def __repr__(self) -> str:
        return f"ActiveScope({sorted(self)})"

# The contribution of each vendor-mark notation, measured by switching them on
# one at a time.  SCT stays off by default (see DEFAULT_DISABLED).
COMBOS = {
    "none":            ActiveScope(),
    "glyph":           ActiveScope({"VENDOR_MARK_GLYPH"}),
    "glyph+text":      ActiveScope({"VENDOR_MARK_GLYPH", "VENDOR_MARK_TEXT"}),
    "glyph+text+box":  ActiveScope(VENDOR_RULES),
    "all+sct":         ActiveScope(SCOPE_RULES),
}

# The variant every published Phase 0 number was measured on.  Named so callers
# ask for it by name rather than assembling a set and hoping.
BASELINE_SCOPE_NAME = "glyph+text+box"


def active_scope(name: str) -> ActiveScope:
    """Look an exclusion set up by name; unknown names fail loudly."""
    try:
        return COMBOS[name]
    except KeyError:
        raise KeyError(f"unknown scope '{name}'; known: {sorted(COMBOS)}") from None

FAILURE_TYPES = [
    "NO_ANCHOR",
    "ANNOTATION_TEXT",
    "AMBIGUOUS_GEOMETRY",
    "SCOPE_CONFLICT",
    "VENDOR_MARK_UNDEFINED",
    "TYPE_MAPPING_MISS",
    "OVER_DETECT",
]

# Words that carry no discriminating power when matching an Excel SYSTEM value
# against a drawing title.
STOPWORDS = frozenset(str(w).upper() for w in CFG.get("matching.stopwords"))


def excel_type_under(det, rules):
    """The Excel TYPE this detection would carry under a given ruleset."""
    if det.anchor in rules.valves or det.anchor in rules.not_field:
        return None
    return rules.field_type_map.get(det.anchor)


def included_under(det, rules, active_scope: "ActiveScope") -> bool:
    if not isinstance(active_scope, ActiveScope):
        raise TypeError(
            "included_under() wants the rules that are ACTIVE, as an "
            "ActiveScope (use detect_all.active_scope('glyph+text+box') or a "
            "COMBOS value).  A plain frozenset was passed, which is how a "
            "*disabled* set such as detect_symbols.DEFAULT_DISABLED gets in "
            "here and silently inverts the meaning.  Got: "
            f"{sorted(active_scope)!r}")
    if excel_type_under(det, rules) is None:
        return False
    return not any(r in active_scope and r in det.rules_hit for r in SCOPE_RULES)


_SC_FROM, _SC_TO = (int(v) for v in CFG.get("formats.system_code_chars"))


def system_of(drawing_no: str) -> str:
    parts = drawing_no.split("-")
    return (parts[1][_SC_FROM:_SC_TO]
            if len(parts) > 1 and len(parts[1]) >= _SC_TO else "???")


def tokens(text: str) -> set:
    return {w for w in re.split(r"[^A-Z0-9&]+", (text or "").upper())
            if w and w not in STOPWORDS}


def title_match_score(system_value: str, title: str) -> float:
    """How well an Excel SYSTEM value matches a page's drawing title.

    Prefix matching, because the Excel abbreviates where the drawing does not
    ('Aux. Steam System' vs 'AUXILIARY STEAM SYSTEM').
    """
    sys_t, title_t = tokens(system_value), tokens(title)
    if not sys_t:
        return 0.0
    hits = 0
    for s in sys_t:
        for t in title_t:
            if s == t or (len(s) >= 3 and len(t) >= 3 and (s.startswith(t) or t.startswith(s))):
                hits += 1
                break
    return hits / len(sys_t)


def mark_notation(pc, mark_dict, glyph_size, marks, boxes):
    forms = collections.Counter(m.form for m in marks)
    return {"definitions": len(mark_dict),
            "legend_form": "GLYPH" if glyph_size else ("TEXT" if mark_dict else "NONE"),
            "glyph_size": list(glyph_size) if glyph_size else None,
            "glyph_marks_in_drawing": forms.get("GLYPH", 0),
            "text_marks_in_drawing": forms.get("TEXT", 0),
            "package_boxes": len(boxes)}


def load_excel(path: Path):
    import openpyxl

    col = CFG.get("excel.columns")
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[CFG.get("excel.sheet")]
    by_drawing: dict[str, list] = collections.defaultdict(list)
    total = spare = 0
    for i in range(int(CFG.get("excel.first_data_row")), ws.max_row + 1):
        no = ws.cell(i, col["no"]).value
        if not isinstance(no, (int, float)):
            continue
        total += 1
        pid = ws.cell(i, col["pid_no"]).value
        pid = str(pid).strip() if pid else ""
        if not pid:
            spare += 1
            continue
        by_drawing[pid].append({
            "row": i, "no": no,
            "type": (str(ws.cell(i, col["type"]).value).strip()
                     if ws.cell(i, col["type"]).value else ""),
            "qty": ws.cell(i, col["qty"]).value,
            "system": ws.cell(i, col["system"]).value,
            "description": ws.cell(i, col["description"]).value,
        })
    return by_drawing, total, spare


def attribute_rows(excel, pages_by_drawing, per_page):
    """Assign every Excel row to one page.

    Unique drawing numbers are trivial.  For the three numbers shared by two
    pages, each row goes to the page whose drawing title best matches the row's
    SYSTEM value; that is the only field in the Excel that distinguishes them.
    """
    owned: dict[int, list] = collections.defaultdict(list)
    decisions = []
    for dn, rows in excel.items():
        cand = pages_by_drawing.get(dn, [])
        if not cand:
            continue                      # EXCEL_ONLY, handled by the caller
        if len(cand) == 1:
            owned[cand[0]].extend(rows)
            continue
        scores = {p: 0.0 for p in cand}
        for r in rows:
            best_p, best_s = None, 0.0
            for p in cand:
                sc = title_match_score(str(r["system"]), per_page[p]["title"])
                if sc > best_s:
                    best_p, best_s = p, sc
            target = best_p if best_p is not None else cand[0]
            owned[target].append(r)
            scores[target] += 1
        decisions.append({
            "drawing_no": dn,
            "pages": cand,
            "titles": {p: per_page[p]["title"] for p in cand},
            "excel_systems": sorted({str(r["system"]) for r in rows}),
            "rows_assigned": {p: int(scores[p]) for p in cand},
        })
    return owned, decisions


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 0 spike 2b — all pages, page-level join")
    ap.add_argument("--pdf", default="data/pid_total.pdf")
    ap.add_argument("--compare", default="data/CZE_Field_Instrument.xlsx")
    ap.add_argument("--titleblocks", default="out/titleblocks.csv")
    ap.add_argument("--json", default="out/detect_all.json")
    ap.add_argument("--failures", default="out/failure_report.md")
    ap.add_argument("--revision-gap", default="out/revision_gap.md")
    args = ap.parse_args()

    tb = {int(r["page_no"]): r for r in
          csv.DictReader(open(args.titleblocks, encoding="utf-8-sig"))}
    excel, excel_total, excel_spare = load_excel(Path(args.compare))

    doc, pages = load_pages(args.pdf)
    targets = [pc for pc in pages
               if tb[pc.page_no]["page_kind"] == "PID"
               and tb[pc.page_no]["analysis_scope"] == "True"]
    print(f"pages in scope: {len(targets)}   "
          f"excel rows: {excel_total} ({excel_spare} SPARE without P&ID No.)")

    # ---- detect once, with the superset anchor dictionary (V2) --------
    per_page = {}
    size_dist = collections.Counter()
    for i, pc in enumerate(targets, 1):
        dets, scopes, mark_dict, unverified, unmapped, boxes = detect(pc, rules=RULESET_V3)
        _, glyph_size = read_mark_dictionary(pc)
        marks = find_marks(pc, glyph_size=glyph_size, allow_sizes=KNOWN_GLYPH_SIZES)
        sizes = bubble_sizes(find_bubbles(pc))
        size_dist.update(sizes)
        per_page[pc.page_no] = {
            "drawing_no": tb[pc.page_no]["drawing_no"],
            "title": tb[pc.page_no]["drawing_title"],
            "detections": dets, "scopes": scopes, "mark_dict": mark_dict,
            "unverified": unverified, "unmapped": unmapped, "sizes": sizes,
            "notation": mark_notation(pc, mark_dict, glyph_size, marks, boxes),
            "annotations": review_annotations(pc),
            "annotation_anchors": annotation_anchors(pc, unverified)[0],
            "true_unverified": annotation_anchors(pc, unverified)[1],
            "undefined_marks": sum(1 for d in dets
                                   if "VENDOR_MARK_UNDEFINED" in d.rules_hit),
        }
        print(f"  [{i:>2}/{len(targets)}] p{pc.page_no:<3} "
              f"{tb[pc.page_no]['drawing_no']}  anchors={len(dets):<4} "
              f"unverified={len(unverified):<3} defs={len(mark_dict)} "
              f"marks={len(marks)} boxes={len(boxes)}", flush=True)

    pages_by_drawing = collections.defaultdict(list)
    for pno, info in per_page.items():
        pages_by_drawing[info["drawing_no"]].append(pno)

    owned, decisions = attribute_rows(excel, pages_by_drawing, per_page)

    # ---- three disjoint sets ------------------------------------------
    matched = [p for p in per_page if owned.get(p)]
    pdf_only = [p for p in per_page if not owned.get(p)]
    excel_only = [dn for dn in excel if dn not in pages_by_drawing]

    def score(rules, active_scope, page_set):
        tp = det_tot = exp_tot = 0
        for pno in page_set:
            det = collections.Counter(
                excel_type_under(d, rules) for d in per_page[pno]["detections"]
                if included_under(d, rules, active_scope))
            exp = collections.Counter(r["type"] for r in owned.get(pno, []))
            for t in set(det) | set(exp):
                tp += min(det.get(t, 0), exp.get(t, 0))
            det_tot += sum(det.values())
            exp_tot += sum(exp.values())
        return {"tp": tp, "detected": det_tot, "expected": exp_tot,
                "recall": tp / exp_tot if exp_tot else 0.0,
                "precision": tp / det_tot if det_tot else 0.0}

    v1_scope = COMBOS["all+sct"]
    variants = {
        "v1_drawing_join": None,      # filled below, old-style number
        "v1_page_join": score(RULESET_V1, v1_scope, matched),
        "v2_glyph_only": score(RULESET_V2, COMBOS["glyph"], matched),
        "v3_none": score(RULESET_V3, COMBOS["none"], matched),
        "v3_glyph": score(RULESET_V3, COMBOS["glyph"], matched),
        "v3_glyph_text": score(RULESET_V3, COMBOS["glyph+text"], matched),
        "v3_glyph_text_box": score(RULESET_V3, COMBOS["glyph+text+box"], matched),
        "v3_all_sct": score(RULESET_V3, COMBOS["all+sct"], matched),
    }

    # The old headline, reproduced: drawing-level join over every page.
    old_tp = old_det = old_exp = 0
    by_dn_det = collections.defaultdict(collections.Counter)
    for pno, info in per_page.items():
        for d in info["detections"]:
            if included_under(d, RULESET_V1, v1_scope):
                by_dn_det[info["drawing_no"]][excel_type_under(d, RULESET_V1)] += 1
    for dn in set(by_dn_det) | set(excel):
        det, exp = by_dn_det.get(dn, collections.Counter()), collections.Counter(
            r["type"] for r in excel.get(dn, []))
        for t in set(det) | set(exp):
            old_tp += min(det.get(t, 0), exp.get(t, 0))
        old_det += sum(det.values())
        old_exp += sum(exp.values())
    variants["v1_drawing_join"] = {
        "tp": old_tp, "detected": old_det, "expected": old_exp,
        "recall": old_tp / old_exp if old_exp else 0.0,
        "precision": old_tp / old_det if old_det else 0.0}

    # ---- per-page detail, MATCHED only --------------------------------
    ACTIVE_SCOPE = COMBOS["glyph+text+box"]
    page_rows = []
    for pno in sorted(matched):
        info = per_page[pno]
        det = collections.Counter(
            excel_type_under(d, RULESET_V3) for d in info["detections"]
            if included_under(d, RULESET_V3, ACTIVE_SCOPE))
        exp = collections.Counter(r["type"] for r in owned[pno])
        tp = sum(min(det.get(t, 0), exp.get(t, 0)) for t in set(det) | set(exp))
        page_rows.append({
            "page_no": pno, "drawing_no": info["drawing_no"],
            "system": system_of(info["drawing_no"]), "title": info["title"],
            "detected": sum(det.values()), "expected": sum(exp.values()), "tp": tp,
            "det_counts": dict(det), "exp_counts": dict(exp),
        })

    failures = classify(page_rows, per_page, owned, ACTIVE_SCOPE)
    failures_v1 = classify(
        [_recount(p, per_page, owned, RULESET_V1, v1_scope) for p in page_rows],
        per_page, owned, v1_scope, rules=RULESET_V1)

    xmatch = cross_match(excel_only, pdf_only, excel, per_page)

    report(variants, page_rows, failures, failures_v1, size_dist, per_page,
           matched, pdf_only, excel_only, excel, decisions, xmatch)

    write_report(Path(args.failures), variants, page_rows, failures, failures_v1,
                 size_dist, per_page, matched, pdf_only, excel_only, excel,
                 decisions, excel_total, excel_spare, xmatch)

    write_revision_gap(Path(args.revision_gap), per_page, page_rows)

    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "sets": {"matched_pages": sorted(matched),
                 "pdf_only_pages": sorted(pdf_only),
                 "excel_only_drawings": sorted(excel_only)},
        "attribution_decisions": decisions,
        "excel_only_cross_match": xmatch,
        "variants": variants,
        "bubble_size_distribution": {f"{k[0]}x{k[1]}": v for k, v in size_dist.most_common()},
        "pages": page_rows,
        "failures": {k: [f for f in failures if f["type"] == k] for k in FAILURE_TYPES},
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out}, {args.failures} and {args.revision_gap}")
    return 0


def _recount(prow, per_page, owned, rules, scope):
    pno = prow["page_no"]
    det = collections.Counter(
        excel_type_under(d, rules) for d in per_page[pno]["detections"]
        if included_under(d, rules, scope))
    exp = collections.Counter(r["type"] for r in owned[pno])
    tp = sum(min(det.get(t, 0), exp.get(t, 0)) for t in set(det) | set(exp))
    return {**prow, "detected": sum(det.values()), "expected": sum(exp.values()),
            "tp": tp, "det_counts": dict(det), "exp_counts": dict(exp)}


def write_revision_gap(path, per_page, page_rows):
    """Drawings whose review markup records a revision the Excel has not taken up.

    Produced for the client to reconcile.  Nothing in the detector compensates
    for any of it — a rule that "corrects" for stale Excel rows would be fitting
    the answer key rather than reading the drawing.
    """
    rows = {r["page_no"]: r for r in page_rows}
    body_pages = [p for p in sorted(per_page)
                  if any(a["where"] == "DRAWING" for a in per_page[p]["annotations"])]

    L = []
    L.append("# 도면 개정 ↔ Excel 불일치 목록")
    L.append("")
    L.append("PDF 에 검토자 국문 주석 레이어가 있고, 그 내용이 Excel 에 반영되지 않았습니다.")
    L.append("**규칙으로 보정하지 않았습니다** — 발주처 확인용 목록입니다.")
    L.append("")
    L.append(f"도면 본문에 주석이 있는 도면 **{len(body_pages)}건**.")
    L.append("")
    L.append("| 페이지 | 도면번호 | 도면명 | 주석 | 검출 | Excel | 상태 |")
    L.append("|---|---|---|---|---|---|---|")
    for pno in body_pages:
        info = per_page[pno]
        r = rows.get(pno)
        det = sum(r["det_counts"].values()) if r else 0
        exp = sum(r["exp_counts"].values()) if r else 0
        state = "MATCHED" if r else "PDF_ONLY"
        texts = "<br>".join(a["text"][:56] for a in info["annotations"]
                            if a["where"] == "DRAWING")
        L.append(f"| p{pno} | `{info['drawing_no']}` | {info['title'][:32]} | {texts} "
                 f"| {det} | {exp} | {state} |")

    L.append("")
    L.append("## 수치로 확인된 건")
    L.append("")
    L.append("- **p49 `D00P-00GHB10-M05-0001`** — 주석 `PDIT 3EA, PIT 2EA 삭제`. "
             "Excel 은 `PDIT` 6 / `PIT` 4 인데 개정 도면과 검출은 모두 **3 / 2** 입니다. "
             "`RO FIT 1EA 삭제` 주석은 `FIT` 1행 결손과 대응합니다. "
             "주석을 반영하면 이 도면 재현율은 11/11 이 됩니다.")
    L.append("- **p44 `D00P-00SCB10-M05-0001`** — 주석 `PIT 삭제`. Excel 의 유일한 1행은 "
             "`Instument air ring header PRESSURE` (SYSTEM `Compressed Air System`) 로 "
             "이 도면 소관이 아닙니다. 검출 0 이 맞습니다.")
    L.append("- **p16 `D00P-10LCA10-M05-0001`** — `RO 추가` 주석 2건. 도면에는 반영됐는데 "
             "Excel 반영 여부 확인이 필요합니다.")
    L.append("")
    L.append("## 타이틀블록 `미접수` 표기")
    L.append("")
    tb = sorted(p for p in per_page
                if any(a["where"] == "TITLEBLOCK" for a in per_page[p]["annotations"]))
    L.append(f"`Rev.C P&ID 미접수` 가 타이틀블록에 붙은 페이지: {tb}")
    L.append("")
    L.append("최신 Rev 도면을 아직 수령하지 못했다는 표시입니다. Excel 이 최신 Rev 기준으로 "
             "작성됐다면, 이 페이지들의 결손은 검출기 문제가 아니라 도면 버전 차이입니다.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def classify(page_rows, per_page, owned, scope, rules=RULESET_V3):
    out = []
    for row in page_rows:
        pno = row["page_no"]
        info = per_page[pno]
        det, exp = row["det_counts"], row["exp_counts"]
        for t in sorted(set(det) | set(exp)):
            got, want = det.get(t, 0), exp.get(t, 0)
            if got == want:
                continue
            if got > want:
                extras = [d for d in info["detections"]
                          if excel_type_under(d, rules) == t
                          and included_under(d, rules, scope)]
                out.append(_mk(row, "OVER_DETECT", t, got - want, extras[:3],
                               f"detected {got} vs excel {want}"))
                continue

            deficit = want - got
            held = [d for d in info["detections"]
                    if excel_type_under(d, rules) == t
                    and "VENDOR_MARK_UNDEFINED" in d.rules_hit]
            scoped = [d for d in info["detections"]
                      if excel_type_under(d, rules) == t
                      and not included_under(d, rules, scope)
                      and any(r in d.rules_hit for r in SCOPE_RULES)]
            mistyped = [d for d in info["detections"] if d.anchor == t
                        and d.anchor in rules.not_field]
            unmapped = info["unmapped"]
            ambiguous = info["true_unverified"]
            markup = [a for a in info["annotation_anchors"] if a["anchor"] == t]

            if mistyped:
                out.append(_mk(row, "TYPE_MAPPING_MISS", t, deficit, mistyped[:3],
                               f"'{t}' is drawn but the ruleset calls it NOT_FIELD_INSTRUMENT"))
            elif held:
                out.append(_mk(row, "VENDOR_MARK_UNDEFINED", t, deficit, held[:3],
                               "mark present but undefined in this page's NOTES; exclusion held"))
            elif scoped:
                out.append(_mk(row, "SCOPE_CONFLICT", t, deficit, scoped[:3],
                               "excluded by a scope rule but the Excel keeps the row"))
            elif unmapped:
                toks = sorted({u["token"] for u in unmapped})[:6]
                out.append(_mk(row, "TYPE_MAPPING_MISS", t, deficit, unmapped[:3],
                               "bubble holds a tag outside the anchor dictionary: "
                               + ", ".join(toks)))
            elif markup:
                out.append(_mk(row, "ANNOTATION_TEXT", t, deficit, markup[:3],
                               "the only match is reviewer markup text, not a symbol — "
                               "the drawing was revised and the Excel still lists the row"))
            elif ambiguous:
                out.append(_mk(row, "AMBIGUOUS_GEOMETRY", t, deficit, ambiguous[:3],
                               "anchors found but no single enclosing bubble"))
            else:
                out.append(_mk(row, "NO_ANCHOR", t, deficit, [],
                               f"no '{t}' anchor found in any bubble on this page"))
    return out


def _mk(row, kind, type_, count, samples, cause):
    smp = []
    for obj in samples:
        if hasattr(obj, "center"):
            smp.append({"anchor": obj.anchor,
                        "center": [round(obj.center[0], 1), round(obj.center[1], 1)],
                        "rules_hit": list(obj.rules_hit)})
        else:
            smp.append({"anchor": obj.get("anchor") or obj.get("token"),
                        "center": obj.get("center")})
    return {"type": kind, "page_no": row["page_no"], "drawing_no": row["drawing_no"],
            "system": row["system"], "title": row["title"], "excel_type": type_,
            "count": count, "cause": cause, "samples": smp}


def cross_match(excel_only, pdf_only, excel, per_page):
    """Pair EXCEL_ONLY drawings with PDF_ONLY pages by system name.

    Diagnostic only — nothing is joined on the strength of it.  A high score
    means the drawing does exist in the PDF but under a different number, which
    is a data problem to fix upstream rather than a detector problem.
    """
    out = []
    for dn in sorted(excel_only):
        systems = sorted({str(r["system"]) for r in excel[dn]})
        best, best_score = None, 0.0
        for pno in pdf_only:
            sc = max(title_match_score(sv, per_page[pno]["title"]) for sv in systems)
            if sc > best_score:
                best, best_score = pno, sc
        out.append({
            "drawing_no": dn, "rows": len(excel[dn]), "systems": systems,
            "candidate_page": best, "score": round(best_score, 2),
            "candidate_drawing_no": per_page[best]["drawing_no"] if best else None,
            "candidate_title": per_page[best]["title"] if best else None,
        })
    return out


def system_table(page_rows):
    agg = collections.defaultdict(lambda: {"tp": 0, "det": 0, "exp": 0,
                                           "pages": 0, "title": ""})
    for r in page_rows:
        a = agg[r["system"]]
        a["tp"] += r["tp"]; a["det"] += r["detected"]; a["exp"] += r["expected"]
        a["pages"] += 1
        a["title"] = a["title"] or r["title"]
    rows = [{"system": k, "pages": a["pages"], "detected": a["det"],
             "expected": a["exp"], "tp": a["tp"],
             "recall": a["tp"] / a["exp"] if a["exp"] else 0.0,
             "precision": a["tp"] / a["det"] if a["det"] else 0.0,
             "title": a["title"]} for k, a in agg.items()]
    rows.sort(key=lambda r: (r["recall"], -r["expected"]))
    return rows


def _fail_counts(failures):
    cases = collections.Counter(f["type"] for f in failures)
    rows = collections.Counter()
    for f in failures:
        rows[f["type"]] += f["count"]
    return cases, rows


def report(variants, page_rows, failures, failures_v1, size_dist, per_page,
           matched, pdf_only, excel_only, excel, decisions, xmatch):
    print("\n" + "=" * 78)
    print("JOIN — attribution of shared drawing numbers")
    print("=" * 78)
    for d in decisions:
        print(f"  {d['drawing_no']}  pages {d['pages']}")
        print(f"     Excel SYSTEM: {', '.join(d['excel_systems'])}")
        for p, t in d["titles"].items():
            print(f"     p{p}: {t}   -> {d['rows_assigned'][p]} rows")
    print(f"\n  MATCHED    {len(matched):>3} pages")
    print(f"  PDF_ONLY   {len(pdf_only):>3} pages   {sorted(pdf_only)}")
    print(f"  EXCEL_ONLY {len(excel_only):>3} drawings "
          f"({sum(len(excel[d]) for d in excel_only)} rows)")

    print("\n  EXCEL_ONLY -> best matching PDF_ONLY page (diagnostic, not joined):")
    for x in xmatch:
        tgt = (f"p{x['candidate_page']} {x['candidate_drawing_no']}"
               if x["candidate_page"] else "(none)")
        print(f"    {x['drawing_no']} ({x['rows']} rows, {x['systems'][0]})")
        print(f"       -> {tgt}  score={x['score']}  {x['candidate_title'] or ''}")

    print("\n" + "=" * 78)
    print("SCORE — before and after the measurement fix (MATCHED set only)")
    print("=" * 78)
    labels = {
        "v1_drawing_join": "v1 rules, drawing join (2b headline)",
        "v1_page_join":    "v1 rules, page join",
        "v2_glyph_only":   "v2 rules, glyph marks only (2c baseline)",
        "v3_none":         "v3 rules, no vendor rule",
        "v3_glyph":        "v3 rules, glyph marks",
        "v3_glyph_text":   "v3 rules, glyph + text marks",
        "v3_glyph_text_box": "v3 rules, glyph + text + package box  <- new baseline",
        "v3_all_sct":      "v3 rules, all + SCT on",
    }
    print(f"{'variant':<44} {'det':>5} {'excel':>6} {'TP':>5} {'recall':>8} {'prec':>8}")
    for k in ("v1_drawing_join", "v1_page_join", "v2_glyph_only", "v3_none", "v3_glyph", "v3_glyph_text", "v3_glyph_text_box", "v3_all_sct"):
        v = variants[k]
        print(f"{labels[k]:<44} {v['detected']:>5} {v['expected']:>6} {v['tp']:>5} "
              f"{v['recall']:>7.1%} {v['precision']:>8.1%}")

    undef = {p: i["undefined_marks"] for p, i in per_page.items() if i["undefined_marks"]}
    print(f"\n  VENDOR_MARK_UNDEFINED detections (mark present, page's NOTES silent): "
          f"{sum(undef.values())} on pages {sorted(undef)}")

    mk_tot = sum(len(i["annotation_anchors"]) for i in per_page.values())
    mk_pages = {p: len(i["annotation_anchors"]) for p, i in per_page.items()
                if i["annotation_anchors"]}
    print(f"\n  anchors that are reviewer markup, not symbols: {mk_tot} "
          f"on pages {sorted(mk_pages)}")

    ann_pages = {p: i["annotations"] for p, i in per_page.items()
                 if any(a["where"] == "DRAWING" for a in i["annotations"])}
    print(f"\n  Korean review markup on {len(ann_pages)} drawing bodies:")
    for pno in sorted(ann_pages):
        for a in ann_pages[pno]:
            if a["where"] == "DRAWING":
                print(f"    p{pno:<3} {a['pos']}  {a['text'][:70]}")

    print("\n" + "=" * 78)
    print("PER-SYSTEM ACCURACY (MATCHED, recall ascending)")
    print("=" * 78)
    print(f"{'sys':<5} {'pg':>3} {'det':>5} {'excel':>6} {'TP':>5} {'recall':>8} {'prec':>8}  title")
    for r in system_table(page_rows):
        print(f"{r['system']:<5} {r['pages']:>3} {r['detected']:>5} {r['expected']:>6} "
              f"{r['tp']:>5} {r['recall']:>7.1%} {r['precision']:>7.1%}  {r['title'][:42]}")

    print("\n" + "=" * 78)
    print("FAILURE TYPES — v1 rules vs v3 rules (both on the MATCHED set)")
    print("=" * 78)
    c1, r1 = _fail_counts(failures_v1)
    c2, r2 = _fail_counts(failures)
    print(f"{'type':<24} {'v1 cases':>9} {'v1 rows':>8} {'v3 cases':>9} {'v3 rows':>8}")
    for t in FAILURE_TYPES:
        print(f"  {t:<22} {c1.get(t,0):>9} {r1.get(t,0):>8} {c2.get(t,0):>9} {r2.get(t,0):>8}")


def write_report(path, variants, page_rows, failures, failures_v1, size_dist,
                 per_page, matched, pdf_only, excel_only, excel, decisions,
                 excel_total, excel_spare, xmatch):
    c1, r1 = _fail_counts(failures_v1)
    c2, r2 = _fail_counts(failures)
    v = variants["v3_glyph_text_box"]
    L = []
    L.append("# 실패 리포트 — Phase 0 spike 2b (측정 재정의)\n")
    L.append("검출 규칙은 추가하지 않았습니다. 이번 변경은 **조인 기준 확정**과 "
             "**전체 Excel 로 확인된 앵커 매핑 수정** 두 가지뿐입니다.\n")

    L.append("\n## A. 조인 기준 — 페이지 단위\n")
    L.append("### 도면번호 공유 3건의 귀속 판정\n")
    L.append("Excel `SYSTEM` 열을 페이지의 `drawing_title` 과 토큰 대조(접두 일치 허용)해 "
             "행 단위로 귀속시켰습니다.\n")
    for d in decisions:
        L.append(f"**`{d['drawing_no']}`** — pages {d['pages']}  ")
        L.append(f"Excel SYSTEM: {', '.join(d['excel_systems']) or '(행 없음)'}  ")
        for p, t in d["titles"].items():
            L.append(f"- p{p}: {t} → **{d['rows_assigned'][p]}행**")
        L.append("")
    gma = [dn for dn, ps in
           [(x["drawing_no"], x["pages"]) for x in decisions]]
    if "D00P-00GMA10-M05-0001" not in gma:
        L.append("**`D00P-00GMA10-M05-0001`** (p52 / p55) — Excel 전체에 `GMA` 를 "
                 "포함한 `P&ID No.` 가 **한 건도 없습니다**. 귀속시킬 행 자체가 없으므로 "
                 "두 페이지 모두 `PDF_ONLY` 입니다.\n")

    L.append("\n### 3개 집합\n")
    L.append("| 집합 | 규모 | 처리 |")
    L.append("|---|---|---|")
    L.append(f"| `MATCHED` | {len(matched)}페이지 / Excel {v['expected']}행 | **규칙 성능은 여기서만 측정** |")
    L.append(f"| `EXCEL_ONLY` | {len(excel_only)}도면 / {sum(len(excel[d]) for d in excel_only)}행 | 검출 불가, 점수에서 제외 |")
    L.append(f"| `PDF_ONLY` | {len(pdf_only)}페이지 | 정답 없음, 점수에서 제외 |")

    L.append("\n#### EXCEL_ONLY — Excel 에만 있는 도면\n")
    L.append("| 도면번호 | 행 수 | Excel SYSTEM |")
    L.append("|---|---|---|")
    for dn in sorted(excel_only):
        systems = sorted({str(r["system"]) for r in excel[dn]})
        L.append(f"| `{dn}` | {len(excel[dn])} | {', '.join(systems)} |")

    L.append("\n**원인 판정** — 위 5건은 모두 PDF 안에 해당 도면이 "
             "**다른 번호로 존재**합니다. 도면 누락이 아니라 채번 불일치입니다.\n")
    L.append("| Excel 도면번호 | 행 | Excel SYSTEM | PDF 상의 실제 페이지 | 그 페이지의 타이틀블록 번호 | 일치도 |")
    L.append("|---|---|---|---|---|---|")
    for x in xmatch:
        tgt = f"p{x['candidate_page']} — {x['candidate_title']}" if x["candidate_page"] else "(없음)"
        L.append(f"| `{x['drawing_no']}` | {x['rows']} | {x['systems'][0]} | {tgt} "
                 f"| `{x['candidate_drawing_no'] or '-'}` | {x['score']} |")

    L.append("\n#### PDF_ONLY — Excel 에 행이 없는 페이지\n")
    L.append("| 페이지 | 도면번호 | 도면명 | 검출 |")
    L.append("|---|---|---|---|")
    for pno in sorted(pdf_only):
        info = per_page[pno]
        n = sum(1 for d in info["detections"]
                if included_under(d, RULESET_V3, active_scope(BASELINE_SCOPE_NAME)))
        L.append(f"| p{pno} | `{info['drawing_no']}` | {info['title']} | {n} |")

    L.append("\n## B. 앵커 사전 수정\n")
    L.append("| 코드 | 조치 | 근거 |")
    L.append("|---|---|---|")
    L.append("| `FE` | 비대상 → **Field 대상** | Excel `FE` 18행. "
             "`D00P-10MAN10-M05-0001` 행 61/71/82 (`... SPRAY WATER FLOW ELEMENT`), "
             "해당 p10 도면의 FE 버블 3개와 일치 |")
    L.append("| `LSH`/`LSHH`/`LSL` | **→ `LS` 매핑** | Excel `LS` 22행, 설명이 "
             "`... LEVEL HIGH HIGH` / `... LEVEL HIGH`. "
             "`D00P-10LBC40-M05-0001` 행 20~23, 해당 p7 도면에 LSHH 4 + LSH 4 |")
    L.append("| `ZS` | **추가하지 않음** | Excel `TYPE` 열에 `ZS` **0행**. "
             "이전 리포트에서 `ZS` 옆의 숫자는 같은 페이지의 *다른* TYPE 결손이었고 "
             "ZS 자체의 행 수가 아니었습니다 |")
    L.append("| `LG` | **추가하지 않음** | Excel `TYPE` 열에 `LG` **0행**. 위와 동일 |")

    L.append("\n### 한 페이지 표본으로 굳어진 규칙 재점검 (전체 Excel 대조)\n")
    L.append("| 규칙 | 근거 | 판정 |")
    L.append("|---|---|---|")
    L.append("| `FE` = 비대상 | Excel FE **18행** | ❌ 오류 — 이번에 철회 |")
    L.append("| `FT` = 비대상 | Excel `FIT` **31행**. `D00P-10MAN10-M05-0001` 이 "
             "`FIT` 5행을 요구하고 p10 도면에 `FT` 버블이 정확히 5개 |"
             " ⚠️ **오류로 보임 — 이번 지시 목록 밖이라 미적용** |")
    L.append("| `TW` = 비대상 | Excel `TYPE` 에 `TW` 0행 | ✅ 유지 |")
    L.append("| `TT`→`TIT`, `PT`→`PIT` | Excel 에 `TT`/`PT` TYPE 0행, `TIT` 99 / `PIT` 108행 | ✅ 유지 |")
    L.append("| `MOV` = 밸브 | Excel Field 리스트에 밸브 TYPE 없음 | ✅ 유지 |")

    L.append("\n## C. SCT 규칙 — 기본 비활성\n")
    a, b = variants["v3_glyph_text_box"], variants["v3_all_sct"]
    L.append(f"- 끈 상태: 검출 {a['detected']} / TP {a['tp']} / 재현율 {a['recall']:.1%} / 정밀도 {a['precision']:.1%}")
    L.append(f"- 켠 상태: 검출 {b['detected']} / TP {b['tp']} / 재현율 {b['recall']:.1%} / 정밀도 {b['precision']:.1%}")
    L.append("- 코드는 유지하고 `--enable-rule SCT_SUPPLIER_SCOPE` 로 켤 수 있습니다. "
             "비활성 사유는 `detect_symbols.py` 의 `DEFAULT_DISABLED` 주석에 근거와 함께 기록했습니다.")

    L.append("\n## 1. 측정 재정의 전후 비교\n")
    L.append("| 변형 | 검출 | Excel | 일치 | 재현율 | 정밀도 |")
    L.append("|---|---|---|---|---|---|")
    labels = {"v1_drawing_join": "v1 규칙 + 도면 조인 (2b 발표값)",
              "v1_page_join": "v1 규칙 + 페이지 조인",
              "v2_glyph_only": "v2 규칙 + 글리프 마크만 (2c 기준선)",
              "v3_none": "v3 규칙 + 벤더 규칙 없음",
              "v3_glyph": "v3 규칙 + 글리프",
              "v3_glyph_text": "v3 규칙 + 글리프 + 텍스트",
              "v3_glyph_text_box": "**v3 규칙 + 글리프 + 텍스트 + 패키지박스 (새 기준선)**",
              "v3_all_sct": "v3 규칙 + 전부 + SCT on"}
    for k in ("v1_drawing_join", "v1_page_join", "v2_glyph_only", "v3_none", "v3_glyph", "v3_glyph_text", "v3_glyph_text_box", "v3_all_sct"):
        x = variants[k]
        L.append(f"| {labels[k]} | {x['detected']} | {x['expected']} | {x['tp']} "
                 f"| {x['recall']:.1%} | {x['precision']:.1%} |")

    L.append("\n## 2. 계통별 정확도 (MATCHED, 재현율 오름차순)\n")
    L.append("| 계통 | 페이지 | 검출 | Excel | 일치 | 재현율 | 정밀도 | 대표 도면명 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in system_table(page_rows):
        L.append(f"| `{r['system']}` | {r['pages']} | {r['detected']} | {r['expected']} "
                 f"| {r['tp']} | {r['recall']:.1%} | {r['precision']:.1%} | {r['title'][:38]} |")

    L.append("\n## 4~5. 실패 유형 재집계 (v1 규칙 → v3 규칙, MATCHED 기준)\n")
    L.append("| 유형 | v1 케이스 | v1 행 | v3 케이스 | v3 행 | 변화 |")
    L.append("|---|---|---|---|---|---|")
    for t in FAILURE_TYPES:
        delta = r2.get(t, 0) - r1.get(t, 0)
        L.append(f"| `{t}` | {c1.get(t,0)} | {r1.get(t,0)} | {c2.get(t,0)} | {r2.get(t,0)} "
                 f"| {delta:+d} |")

    L.append("\n## 유형별 대표 사례 (v2 기준)\n")
    for t in FAILURE_TYPES:
        items = sorted([f for f in failures if f["type"] == t], key=lambda f: -f["count"])
        L.append(f"\n### `{t}` — {c2.get(t,0)} 케이스 / {r2.get(t,0)} 행\n")
        if not items:
            L.append("해당 없음.\n")
            continue
        for f in items[:3]:
            L.append(f"**p{f['page_no']} {f['drawing_no']}** (계통 `{f['system']}`, "
                     f"TYPE `{f['excel_type']}`, {f['count']}행)  ")
            L.append(f"{f['title']}  ")
            L.append(f"추정 원인: {f['cause']}  ")
            for s in f["samples"]:
                rules = "/".join(s["rules_hit"]) if s.get("rules_hit") else "-"
                L.append(f"- `{s['anchor']}` @ {s['center']}  규칙: {rules}")
            L.append("")

    L.append("\n## 버블 치수 분포 (페이지별 실측)\n")
    L.append("| 스타디움 | 개수 | 페이지 수 |")
    L.append("|---|---|---|")
    for (lo, sh), n in size_dist.most_common(6):
        users = sum(1 for i in per_page.values() if (lo, sh) in i["sizes"])
        L.append(f"| {lo} x {sh} | {n} | {users} |")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
