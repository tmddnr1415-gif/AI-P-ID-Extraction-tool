"""Instrument Index · IO List (PDF) — read one record per tag, and compare the datasheets with them (Datasheet → List).

Both lists print a 4-line header block per column ('Tag No. / Loop No. / Instrument Type / Service' …) and, under it,
one record per tag with the values on the same stacked lines.  The column bands come from the header captions found on
each page (card: app/valve/forms/lists.json); a value's line inside its record is its distance from the record's first
line divided by the header's own line pitch, measured on the page.  Records are split by the horizontal rules under the
header when the page has them, otherwise at each line whose Tag cell holds a tag.

Comparison (user decision 2026-11-12): the datasheet is the reference.
  LIST-00  tag has a datasheet but is not in the list                  (누락)
  LIST-01  a value differs (service · P&ID · line · fluid · range · datasheet no. · manufacturer · model)  (값 다름)
  LIST-02  tag is in the list but no datasheet was uploaded            (List 에만)
"""
from __future__ import annotations

import json
import re
from statistics import median

import pymupdf

from app.valve import instrument, linelist
from app.valve.instreview import nums

SPEC = json.loads((instrument.FORMS / "lists.json").read_text(encoding="utf-8"))
# field per header line of each column (None = caption only)
SLOTS = {
    "instrument_index": [["rev"], ["tag", "loop", "inst_type", "service"], ["pid_no", "line_no", "equipment", "location"],
                         ["fluid", "phase", "area"], ["sys_in", "sig_in", "sys_in_loc", "bldg_in"],
                         ["sys_out", "sig_out", "sys_out_loc", "bldg_out"], "range",
                         ["loc_dwg", "hookup", "pneu_hookup", "install_dwg"], ["scope", "datasheet_no", "req_no"],
                         ["manufacturer", "model"], ["remark1", "remark2"]],
    "io_list": [["rev"], ["tag", "loop", "inst_type", "service"], ["pid_no", "line_no", "equipment", "location"],
                ["io_typical", "redundant", "is"], ["sys_in", "sig_in", "sys_in_loc", "bldg_in"],
                ["sys_out", "sig_out", "sys_out_loc", "bldg_out"], ["loop_powered", "ext", "powered", "power_supply"], "range",
                ["logic_no"], ["jb_dwg", "interconn_dwg", "loop_dwg"], ["remark1", "remark2"]],
}
_TAG = re.compile(r"^\d{0,3}[A-Z]{1,6}[\s\-]?\d{2,6}[A-Z]?$")
COMPARE = [("service", "Service"), ("pid_no", "P&ID No."), ("line_no", "Line No."), ("fluid", "Fluid"),
           ("range", "Range"), ("datasheet_no", "Datasheet No."), ("manufacturer", "Manufacturer"), ("model", "Model No.")]


def which(text: str) -> str:
    t = re.sub(r"\s+", " ", text or "").upper()
    if "IO LIST" in t and "IO TYPICAL" in t:
        return "io_list"
    if "INSTRUMENT INDEX" in t:
        return "instrument_index"
    return ""


def _lines(words, tol=2.0):
    out = []
    for w in sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0])):
        y = (w[1] + w[3]) / 2
        if out and abs(out[-1][0] - y) <= tol:
            out[-1][1].append(w)
        else:
            out.append([y, [w]])
    return [(y, sorted(ws, key=lambda w: w[0])) for y, ws in out]


def read_page(page, kind: str) -> dict:
    spec = SPEC[kind]
    words = page.get_text("words")
    tagcap = [w for w in words if w[4].upper() == "TAG" and w[1] < page.rect.height * 0.5]
    if not tagcap:
        return {"records": [], "why": "머리글 'Tag No.' 를 찾지 못함"}
    tc = min(tagcap, key=lambda w: w[1])
    cols = spec["columns"]
    dx = tc[0] - (cols[1]["x0"] + 2.0) if abs(tc[0] - (cols[1]["x0"] + 2.0)) < 40 else 0.0
    hdr = [w for w in words if tc[1] - 3 <= w[1] <= tc[1] + 40]
    hl = _lines(hdr)
    pitch = median([b[0] - a[0] for a, b in zip(hl, hl[1:])]) if len(hl) > 1 else 7.3
    hdr_bottom = max(w[3] for w in hdr)
    rules = sorted({round(it[1].y, 1) for dr in page.get_drawings() for it in dr["items"]
                    if it[0] == "l" and abs(it[1].y - it[2].y) < 0.5 and abs(it[1].x - it[2].x) > page.rect.width * 0.5
                    and it[1].y > hdr_bottom + 1})
    foot = min([w[1] for w in words if w[4].upper() in ("NOTES:", "NOTE:") and w[1] > hdr_bottom] or [page.rect.height])
    body = [w for w in words if hdr_bottom + 1 < w[1] < foot]
    bounds = [(c["x0"] + dx, c["x1"] + dx) for c in cols]
    col_of = lambda w: next((i for i, (a, b) in enumerate(bounds) if a - 1 <= (w[0] + w[2]) / 2 < b + 1), None)   # noqa: E731
    # records
    bands = []
    if len(rules) >= 2:
        edges = rules
        bands = [(a, b) for a, b in zip(edges, edges[1:]) if any(a < (w[1] + w[3]) / 2 < b for w in body)]
        last = edges[-1]
        if any((w[1] + w[3]) / 2 > last for w in body):
            bands.append((last, foot))
    else:
        starts = []
        for y, ws in _lines(body):
            tagtxt = " ".join(w[4] for w in ws if col_of(w) == 1)
            if tagtxt and _TAG.match(tagtxt.upper().replace(" ", "")) and (not starts or y - starts[-1] > pitch * 1.5):
                starts.append(y - pitch / 2)
        bands = [(a, b) for a, b in zip(starts, starts[1:] + [foot])]
    recs = []
    for a, b in bands:
        ws = [w for w in body if a < (w[1] + w[3]) / 2 < b]
        if not ws:
            continue
        top = min((w[1] + w[3]) / 2 for w in ws)
        rec = {"page": page.number + 1, "bbox": [round(min(w[0] for w in ws), 1), round(a, 1), round(max(w[2] for w in ws), 1), round(b, 1)]}
        for ci, slot in enumerate(SLOTS[kind]):
            cw = [w for w in ws if col_of(w) == ci]
            if not cw:
                continue
            lines = _lines(cw)
            if slot == "range":
                vals = [" ".join(w[4] for w in l) for _, l in lines]
                vals = [v for v in vals if v.strip() not in ("/", "-")]
                for k, v in zip(("range_min", "range_max", "range_unit"), vals):
                    rec[k] = v
                continue
            for y, l in lines:
                k = min(len(slot) - 1, max(0, round((y - top) / pitch)))
                txt = " ".join(w[4] for w in l)
                rec[slot[k]] = (rec.get(slot[k], "") + " " + txt).strip() if rec.get(slot[k]) else txt
        if rec.get("tag"):
            rec["tag_key"] = instrument.tag_key(rec["tag"])
            rec["range"] = " ~ ".join(x for x in (rec.get("range_min", ""), rec.get("range_max", "")) if x) + (f" {rec['range_unit']}" if rec.get("range_unit") else "")
            recs.append(rec)
    return {"records": recs, "pitch": round(pitch, 2), "dx": round(dx, 1), "rules": len(rules)}


def read_pdf(path: str) -> dict:
    out = {"kind": "", "records": [], "pages": 0, "doc_no": "", "rev": ""}
    with pymupdf.open(path, filetype="pdf") as doc:
        out["pages"] = doc.page_count
        for page in doc:
            text = page.get_text()
            k = which(text)
            if not k:
                continue
            out["kind"] = out["kind"] or k
            if not out["rev"]:
                m = re.search(r"Revision\s+No\.\s*:?\s*([A-Z0-9]{1,3})\b", re.sub(r"\s+", " ", text))
                out["rev"] = m.group(1) if m else ""
            if not out["doc_no"]:
                m = re.search(r"\b\d{2,4}-\d{2}-[A-Z]{2}-[A-Z]{3}-\d{4,6}\b", text)
                out["doc_no"] = m.group(0) if m else ""
            out["records"] += read_page(page, k)["records"]
    by = {}
    for r in out["records"]:
        by.setdefault(r["tag_key"], r)
    out["by_tag"] = by
    out["n_tags"] = len(by)
    return out


def _same(field: str, ds: str, ls: str) -> bool:
    if field == "range":
        a, b = nums(ds), nums(ls)
        if not a or not b:
            return linelist.key(ds) == linelist.key(ls)
        ua = re.sub(r"[^a-z]", "", re.sub(r"[-\d.,~/\s]+", " ", ds.lower()))
        ub = re.sub(r"[^a-z]", "", re.sub(r"[-\d.,~/\s]+", " ", ls.lower()))
        return sorted(a)[:2] == sorted(b)[:2] and (not ua or not ub or ua == ub)
    if field in ("service", "fluid", "manufacturer"):
        wa, wb = set(re.findall(r"[A-Z0-9]{2,}", ds.upper())), set(re.findall(r"[A-Z0-9]{2,}", ls.upper()))
        return bool(wa and wb and (wa <= wb or wb <= wa))
    return linelist.key(ds) == linelist.key(ls)


def compare(ds_rows: list[dict], lst: dict | None, list_name: str) -> list[dict]:
    """ds_rows: [{tag, tag_key, kind, sheet_id, doc_no, values: {field: text}}] → one row per finding (and OK rows)."""
    if not lst:
        return []
    out, seen = [], set()
    for d in ds_rows:
        seen.add(d["tag_key"])
        r = lst["by_tag"].get(d["tag_key"])
        base = {"tag": d["tag"], "kind": d["kind"], "sheet_id": d.get("sheet_id"), "list": list_name}
        if not r:
            out.append(dict(base, rule="LIST-00", field="Tag", ds=d["tag"], lst="", result="누락",
                            reason=f"Datasheet 는 있으나 {list_name} 에 이 Tag 가 없음"))
            continue
        for f, lab in COMPARE:
            dv, lv = (d["values"].get(f) or "").strip(), (r.get(f) or "").strip()
            if not dv or not lv:
                continue
            same = _same(f, dv, lv)
            out.append(dict(base, rule="LIST-01", field=lab, ds=dv, lst=lv, result="OK" if same else "값 다름",
                            reason="같음" if same else f"Datasheet '{dv}' · {list_name} '{lv}'", page=r["page"]))
    for k, r in lst["by_tag"].items():
        if k not in seen:
            out.append({"tag": r["tag"], "kind": "", "sheet_id": None, "list": list_name, "rule": "LIST-02", "field": "Tag",
                        "ds": "", "lst": r["tag"], "result": "List 에만", "reason": f"{list_name} 에 있으나 Datasheet 가 없음", "page": r["page"]})
    return out
