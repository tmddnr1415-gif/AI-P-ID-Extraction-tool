"""Valve Datasheet Review — evaluation: where does it fail, and how fast is it.

    python3 spike/valve_eval.py --ds Datasheet.pdf --tbe TBE.xlsx --pms PMS.pdf [--out /tmp/valve_eval] [--save-baseline | --check]

A  extraction  datasheets per form, field status, rows the reader could not pair, labels it does not know,
               values that look like mis-reads (a label word, a bare row number, a 'Label :' inside the value)
B  TBE agreement  for every TBE column the Valve List fills: does the extracted value equal the TBE's own
               Requirement row?  exact · same (notation) · soft (VTA / note reference) · different  + examples
C  PMS         result per item and the top reasons
D  issues      per type / severity
E  speed       seconds for extraction (per page), PMS read, issue computation, mark-up PDF, Issue List xlsx

The report (out/report.md) holds client values — keep it out of the repository.  --save-baseline writes only
counts to spike/valve_eval_baseline.json so a later change can be compared number for number.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import openpyxl  # noqa: E402

from app.valve import exports, extract, issues, material, pms, schema, tbe  # noqa: E402

LABEL_WORDS = {schema.norm_label(k) for k in schema.LABELS} | {"model no.", "tag no.", "type", "material"}


def suspicious(v: str, key: str = "") -> str:
    t = (v or "").strip()
    if not t:
        return ""
    n = schema.norm_label(t)
    if n in LABEL_WORDS and n not in ("na", "vta", "type", "material", "open", "closed", "close", "yes", "no", "spring"):
        return "value is a label"
    if re.fullmatch(r"\d{1,3}", t) and int(t) <= 100 and key not in ("line_schedule", "qty", "act_rated_power") and "size" not in key:
        return "bare number (row index?)"
    if re.search(r"\b[A-Z][A-Za-z .]{2,30}\s:\s*$", t):
        return "ends with 'Label :'"
    if re.search(r"\s\|\s", t):
        return "several cells joined"
    return ""


_PT = {}


def _norm_ws(t):
    return re.sub(r"\s+", " ", str(t)).strip().upper()


def page_text(path, pages):
    import pymupdf
    key = tuple(pages)
    if key not in _PT:
        with pymupdf.open(path) as doc:
            _PT[key] = _norm_ws(" ".join(doc[p - 1].get_text() for p in pages))
    return _PT[key]


def run(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rep, base = [], {}
    T = {}

    widths = collections.Counter()                      # every space between vertical rules the reader sees
    _xs = extract._xs_at

    def spy(vert, y, x0, x1):
        xs = _xs(vert, y, x0, x1)
        widths.update(round(q - p) for p, q in zip(xs, xs[1:]))
        return xs
    extract._xs_at = spy
    try:
        t0 = time.time()
        res = extract.read_pdf(a.ds)
    finally:
        extract._xs_at = _xs
    dss = extract.group_datasheets(res)
    T["extract_s"] = round(time.time() - t0, 2)
    T["extract_ms_per_page"] = round(1000 * T["extract_s"] / max(1, res["pages"]), 1)
    forms = collections.Counter(("102" if any((r.get("row") or 0) > 61 for r in d["fields"].values()) else "on/off")
                                for d in dss)
    st = collections.Counter(r["status"] for d in dss for r in d["fields"].values())
    rep += ["# Valve Datasheet Review — evaluation", "", "## A. Extraction",
            f"- pages {res['pages']} · datasheets {len(dss)} · forms {dict(forms)} · scanned pages "
            f"{sum(1 for o in res['other_pages'] if o.get('kind') == 'scanned')}",
            f"- pages per datasheet {dict(collections.Counter(len(d['pages']) for d in dss))} · without notes "
            f"{sum(1 for d in dss if not d['notes'])} · without doc no. {sum(1 for d in dss if not d['doc_no'])} · "
            f"without rev {sum(1 for d in dss if not d['rev'])}",
            f"- field status {dict(st)}"]
    base["A"] = {"datasheets": len(dss), "forms": dict(forms), "status": dict(st),
                 "no_notes": sum(1 for d in dss if not d["notes"])}
    raw = collections.Counter()
    unknown = collections.Counter()
    sus = collections.defaultdict(list)
    for d in dss:
        for k, r in d["fields"].items():
            if k.startswith("raw."):
                raw[(r["row"], r["label"][:50])] += 1
            if k.startswith("x."):
                unknown[r["label"][:40]] += 1
            why = suspicious(r.get("value"), k)
            if why:
                sus[why].append((d["tag"], k, r["value"][:50], r.get("page")))
    # threshold audit — is DOUBLE_RULE_GAP inside an empty band of this document's widths?
    g = extract.DOUBLE_RULE_GAP
    lo = max((w for w in widths if w < g), default=0)
    hi = min((w for w in widths if w >= g), default=999)
    clear = lo > 0 and hi / lo >= 2                     # an empty band: the next width is at least twice the last gap
    rep += ["", "### thresholds measured on this document",
            f"- DOUBLE_RULE_GAP {g} pt: double-rule gaps up to {lo} pt · narrowest cell {hi} pt · "
            + ("empty band — OK" if clear else "**no clear empty band around it — check this form**")]
    base["thresholds"] = {"double_rule_gap": {"value": g, "gaps_up_to": lo, "cells_from": hi, "empty_band": clear}}
    # fingerprint — every read cell (tag · rev · key · value · status · page); the cells stay in --out only
    import hashlib
    cells = sorted(f"{d['tag_key']}|{d['rev']}|{k}|{r.get('value') or ''}|{r['status']}|{r.get('page')}"
                   for d in dss for k, r in d["fields"].items())
    base["fingerprint"] = hashlib.sha256("\n".join(cells).encode()).hexdigest()[:12]
    base["cells"] = len(cells)
    (out / "cells.txt").write_text("\n".join(cells) + "\n", encoding="utf-8")
    rep += ["", "### rows not paired (raw)"] + [f"- row {k[0]} `{k[1]}` × {v}" for k, v in raw.most_common(20)]
    rep += ["", "### labels not in the dictionary (x.*)"] + [f"- `{k}` × {v}" for k, v in unknown.most_common(40)]
    rep += ["", "### suspicious values"]
    for why, L in sus.items():
        rep.append(f"- **{why}** × {len(L)}: " + "; ".join(f"{t} {k}='{v}' p.{p}" for t, k, v, p in L[:8]))
    base["A"].update({"raw": sum(raw.values()), "unknown_labels": sum(unknown.values()),
                      "suspicious": {k: len(v) for k, v in sus.items()}})

    # B — TBE agreement
    if a.tbe:
        wb = openpyxl.load_workbook(a.tbe)
        bykey = {d["tag_key"]: d for d in dss}
        agg = collections.defaultdict(collections.Counter)
        ex = collections.defaultdict(list)
        for ws in wb.worksheets:
            an = tbe.analyse_sheet(ws)
            if not an:
                continue
            for blk in an["blocks"]:
                d = bykey.get(schema.norm_tag(blk["tag"]))
                if not d:
                    agg["(tag)"]["missing"] += 1
                    continue
                for c, path in an["paths"].items():
                    b = tbe._builder(path)
                    if not b or b == "TAG" or c == an["supplier_col"]:
                        continue
                    want = ws.cell(blk["row"], c).value
                    got, keys = b(d["fields"])
                    if want in (None, ""):
                        continue
                    want = str(want)
                    if tbe._cmp(want) == tbe._cmp(got):
                        kind = "exact"
                    elif got and (material.same(want, got) or material.equivalent(want, got)):
                        kind = "same"
                    elif tbe._is_placeholder(want):
                        kind = "tbe_vta"
                    elif not got or tbe._is_placeholder(got) or re.search(r"note\s*[-–]?\s*\d", got, re.I):
                        kind = "soft"
                    else:
                        kind = "different"
                    if kind == "different":                 # misread, or does the datasheet really say something else?
                        pt = page_text(a.ds, d["pages"])
                        w = _norm_ws(want)
                        informative = len(w) >= 12 or re.search(r"\d", w)
                        kind = "misread" if informative and re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", pt) else "different"
                    agg[path][kind] += 1
                    if kind in ("different", "misread") and len(ex[path]) < (8 if kind == "misread" else 4):
                        ex[path].append((("MISREAD " if kind == "misread" else "") + d["tag_key"], want[:45], got[:45]))
        rep += ["", "## B. Agreement with TBE Requirement rows", "",
                "| column | n | exact | same | soft | tbe VTA | misread | different | agree% |", "|---|---|---|---|---|---|---|---|---|"]
        tot = collections.Counter()
        for path, c in sorted(agg.items(), key=lambda kv: -(kv[1]["misread"] * 100 + kv[1]["different"])):
            n = sum(c.values())
            tot.update(c)
            rep.append(f"| {path[:45]} | {n} | {c['exact']} | {c['same']} | {c['soft']} | {c['tbe_vta']} | {c['misread']} | {c['different']} | "
                       f"{100 * (c['exact'] + c['same']) / max(1, n):.0f} |")
        n = sum(tot.values())
        rep.append(f"| **all** | {n} | {tot['exact']} | {tot['same']} | {tot['soft']} | {tot['tbe_vta']} | {tot['misread']} | {tot['different']} | "
                   f"{100 * (tot['exact'] + tot['same']) / max(1, n):.1f} |")
        comp = tot["exact"] + tot["same"] + tot["different"] + tot["misread"]
        rep += ["", f"**Comparable cells (both sides give a value): {comp} · agree {tot['exact'] + tot['same']} "
                f"({100 * (tot['exact'] + tot['same']) / max(1, comp):.1f}%) · misread {tot['misread']} · "
                f"datasheet really differs from TBE {tot['different']}** — 'misread' = the TBE text is on the datasheet page "
                "but another text was read; 'different' = the TBE text is not on the datasheet at all."]
        base["B_comparable"] = {"n": comp, "agree": tot["exact"] + tot["same"], "misread": tot["misread"]}
        rep += ["", "### different — examples (TBE → datasheet)"]
        for path, L in ex.items():
            rep.append(f"- **{path[:50]}**: " + "; ".join(f"{t}: '{w}' → '{g}'" for t, w, g in L))
        base["B"] = dict(tot)

    # C — PMS
    P = None
    if a.pms:
        t0 = time.time()
        P = pms.read_pms(a.pms)
        T["pms_read_s"] = round(time.time() - t0, 2)
        pc = collections.Counter()
        why = collections.defaultdict(collections.Counter)
        for d in dss:
            area = pms.area_of_title(res["docs"].get(d["doc_no"], {}).get("title", ""))
            for r in pms.check(d["fields"], P, area, d["notes"]):
                pc[(r["item"], r["result"])] += 1
                if r["result"] != material.COMPLIANT:
                    why[r["item"]][re.sub(r"'[^']*'", "'…'", r["reason"])[:90]] += 1
        rep += ["", "## C. PMS", ""] + [f"- {k[0]} · {k[1]}: {v}" for k, v in sorted(pc.items())]
        rep += ["", "### reasons (not compliant)"]
        for item, c in why.items():
            rep.append(f"- **{item}**: " + "; ".join(f"{k} × {v}" for k, v in c.most_common(4)))
        base["C"] = {f"{k[0]}|{k[1]}": v for k, v in pc.items()}

    # D — issues
    t0 = time.time()
    allis = []
    for d in dss:
        doc = res["docs"].get(d["doc_no"], {})
        ds = {"fields": [dict(v, key=k, edited_value=None) for k, v in d["fields"].items()], "notes": d["notes"],
              "pages": d["pages"], "doc_no": d["doc_no"], "sheets": d.get("sheets", []), "comments": []}
        for i in issues.compute(ds, doc.get("general_notes", {}), P, pms.area_of_title(doc.get("title", ""))):
            allis.append(dict(i, ds_id=0, tag=d["tag_key"], doc_no=d["doc_no"], rev=d["rev"], document_id=0,
                              filename="Datasheet.pdf", valve_type=d["valve_type"], pages=d["pages"]))
    T["issues_ms_per_ds"] = round(1000 * (time.time() - t0) / max(1, len(dss)), 1)
    ic = collections.Counter((i["type"], i["severity"]) for i in allis)
    rep += ["", "## D. Issues", ""] + [f"- {k[0]} ({k[1]}): {v}" for k, v in sorted(ic.items())]
    base["D"] = {f"{k[0]}|{k[1]}": v for k, v in ic.items()}

    # E — speed of deliverables
    sel = [i for i in allis if i["type"] != "Extraction Review"]
    t0 = time.time()
    exports.issues_xlsx(sel, "http://pc:8000", "EVAL")
    T["issue_xlsx_s"] = round(time.time() - t0, 2)
    by = collections.OrderedDict()
    for i in sel:
        by.setdefault(i["tag"], []).append(i)
    entries = [{"path": a.ds, "pages": L[0]["pages"], "tag": t, "doc_no": L[0]["doc_no"], "rev": L[0]["rev"],
                "filename": "Datasheet.pdf", "issues": L} for t, L in list(by.items())[:40]]
    t0 = time.time()
    pdf = exports.markup_pdf(entries, "EVAL")
    T["markup_s_per_ds"] = round((time.time() - t0) / max(1, len(entries)), 3)
    T["markup_kb_per_ds"] = round(len(pdf) / 1024 / max(1, len(entries)), 1)
    rep += ["", "## E. Speed", ""] + [f"- {k}: {v}" for k, v in T.items()]
    base["E"] = T
    (out / "report.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep))
    if a.check:
        return check(base, out)
    if a.save_baseline:
        (ROOT / "spike" / "valve_eval_baseline.json").write_text(json.dumps(base, indent=1, ensure_ascii=False) + "\n")
        (out / "cells_baseline.txt").write_text((out / "cells.txt").read_text(encoding="utf-8"), encoding="utf-8")
    return base


def check(base, out):
    """Gate (P&ID §3): the fingerprint and the quality counts must not move without a cell-level reason."""
    old = json.loads((ROOT / "spike" / "valve_eval_baseline.json").read_text())
    moved = []
    if old.get("fingerprint") and old["fingerprint"] != base["fingerprint"]:
        moved.append(f"fingerprint {old['fingerprint']} → {base['fingerprint']} (cells {old.get('cells')} → {base['cells']})")
    for sec in ("A", "B_comparable", "C", "D"):
        for k in sorted(set(old.get(sec, {})) | set(base.get(sec, {}))):
            if old.get(sec, {}).get(k) != base.get(sec, {}).get(k):
                moved.append(f"{sec}.{k}: {old.get(sec, {}).get(k)} → {base.get(sec, {}).get(k)}")
    if not base["thresholds"]["double_rule_gap"]["empty_band"]:
        moved.append("DOUBLE_RULE_GAP is not inside an empty band on this document")
    snap = out / "cells_baseline.txt"
    if moved and snap.exists():                      # which cells moved (client values — stays in --out)
        a_, b_ = set(snap.read_text(encoding="utf-8").splitlines()), set((out / "cells.txt").read_text(encoding="utf-8").splitlines())
        (out / "cells_diff.txt").write_text("\n".join(["- " + x for x in sorted(a_ - b_)] + ["+ " + x for x in sorted(b_ - a_)]) + "\n",
                                            encoding="utf-8")
        moved.append(f"cell diff: {out / 'cells_diff.txt'} (-{len(a_ - b_)} +{len(b_ - a_)})")
    print("\nCHECK: " + ("baseline unchanged" if not moved else "MOVED\n  " + "\n  ".join(moved)))
    if moved:
        sys.exit(1)
    return base


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ds", required=True)
    ap.add_argument("--tbe")
    ap.add_argument("--pms")
    ap.add_argument("--out", default="/tmp/valve_eval")
    ap.add_argument("--save-baseline", action="store_true")
    ap.add_argument("--check", action="store_true", help="fail when the fingerprint or a quality count moved")
    run(ap.parse_args())
