"""Issues — what is wrong or missing in a datasheet, each tied to its page and box (for mark-up and the issue list).

Rule-based only.  Every issue says what was checked against what:

  Data Missing        required field present on the form but empty                     orange  Major (process fields: Minor)
  Open Item           required field says HOLD / TBC / TBA                             orange  Minor
  Data Error          the sheet contradicts itself:                                   red     Major
                        · Line No. class '(1C0K8)' ≠ Piping class
                        · Line No. size ≠ Line Size
                        · operating > design (pressure / temperature, same unit)
                        · fail-safe position ≠ action on air failure
                        · 'General Note - N' / 'Note-N' that the document does not have
  PMS Non-Compliance  pms.check -> Non-Compliant                                       red     Major
  PMS Review          pms.check -> Review Required / Not Defined in PMS                red     Minor
  Revision Change     changed against the previous revision of the same tag            yellow  Info
  Reviewer Correction value corrected by a reviewer (read value → corrected value)       blue    Major
  Reviewer Comment    review comment / PDF note                                        blue    Major
  Extraction Review   label/value pairing the tool could not settle (internal)        purple  Internal

The `color` decides the PDF mark-up: red / orange / yellow / blue / purple (docs/valve/DESIGN.md §9).
"""
from __future__ import annotations

import re

from app.valve import material, pms as pmsmod, schema

REQUIRED = ["tag", "service", "pid_no", "line_no", "piping_class", "body_size", "rating", "body_type", "connections",
            "body_material", "ball_material", "stem_material", "seat_material", "act_type", "fail_position", "tightness",
            "leakage_class", "nace"]
PROCESS_REQUIRED = ["fluid", "op_pressure", "design_pressure", "op_temp", "design_temp"]
COLOR = {"Data Missing": "missing", "Open Item": "missing", "Data Error": "error", "PMS Non-Compliance": "error",
         "PMS Review": "error", "Revision Change": "revision", "Reviewer Correction": "comment",
         "Reviewer Comment": "comment", "Extraction Review": "extract"}
CONTRACTOR_TYPES = ["Data Missing", "Open Item", "Data Error", "PMS Non-Compliance", "PMS Review", "Revision Change",
                    "Reviewer Correction", "Reviewer Comment"]
_OPEN = re.compile(r"^\s*(HOLD|TBC|TBA|TO BE CONFIRMED)\b", re.I)
_GN = re.compile(r"gen(?:eral|\.)?\s*note\s*[-–:#]?\s*(\d+)", re.I)   # 'General Note-8' · 'Gen Note-30'

_N = re.compile(r"\bnote\s*[-–:#]?\s*(\d+)", re.I)                    # applied after _GN matches are removed


def _num(v):
    m = re.search(r"-?\d+(?:\.\d+)?", (v or "").replace(",", ""))
    return float(m.group(0)) if m else None


def _v(f):
    return schema.effective(f)


def compute(ds: dict, general_notes: dict | None = None, pms: dict | None = None, area: str = "",
            prev_cmp: list | None = None, states: dict | None = None, pms_rows: list | None = None) -> list[dict]:
    """ds: datasheet with fields (list of dicts with key/value/edited_value/page/bbox/row/status/display), notes,
    comments, pages, sheets.  Returns issue dicts (sorted by page, then position)."""
    F = {f["key"]: f for f in ds["fields"]}
    sheets = {p: (s, o) for p, s, o in (ds.get("sheets") or [])}
    out = []
    gn = {int(k) for k in (general_notes or {})}
    notes = {n["no"] for n in ds.get("notes", [])}

    def add(itype, key, desc, expected="", page=None, bbox=None, f=None, severity=None, extra=None):
        f = f or F.get(key) or {}
        page = page or f.get("page") or (ds["pages"][0] if ds.get("pages") else None)
        sh = sheets.get(page, (None, None))
        sev = severity or ("Info" if itype == "Revision Change" else "Internal" if itype == "Extraction Review"
                           else "Minor" if itype in ("Open Item", "PMS Review") else "Major")
        ikey = f"{itype}:{key}"
        st = (states or {}).get(ikey, {})
        out.append({"ikey": ikey, "type": itype, "color": COLOR[itype], "severity": sev, "key": key,
                    "field": f.get("display") or key, "row": f.get("row"), "value": _v(f), "unit": f.get("unit") or "",
                    "description": desc, "expected": expected, "page": page, "bbox": bbox or f.get("bbox"),
                    "sheet": sh[0] or ((ds["pages"].index(page) + 1) if page in ds.get("pages", []) else None),
                    "of": sh[1] or len(ds.get("pages", [])), "status": st.get("status", "Open"), "note": st.get("note", ""),
                    **(extra or {})})

    pref = ds.get("process_ref")
    if pref is None:                                         # stored datasheets from before valve03: look again
        from app.valve.extract import process_reference
        pref = process_reference(ds.get("notes"), general_notes)
    for k in REQUIRED + PROCESS_REQUIRED:
        f = F.get(k)
        if not f:
            continue                                         # not on this form: cannot be missing from it
        v = _v(f)
        proc = k in PROCESS_REQUIRED
        if proc and pref and not v.strip():
            continue                                         # blank on purpose: 'For Process data refer to …' (Phase 3 checks it)
        if not v.strip():
            add("Data Missing", k, f"{f.get('display') or k}: no value given" +
                (" (check whether the Process Data Sheet is referenced)" if proc else ""), severity="Minor" if proc else "Major")
        elif _OPEN.match(v):
            add("Open Item", k, f"{f.get('display') or k} is still '{v}'")

    line, pc = _v(F.get("line_no")), _v(F.get("piping_class"))
    m = re.search(r"\(([0-9A-Z][0-9A-Z\-]{2,9})\)", line)
    base = lambda c: schema.norm_tag(c.split("-")[0])   # noqa: E731  '1C3AS1-QG1' = class 1C3AS1 + line qualifier
    if m and pc and base(m.group(1)) != base(pc):
        add("Data Error", "piping_class", f"Class in Line No. '{m.group(1)}' differs from Piping class '{pc}'",
            expected=m.group(1))
    ms = re.search(r"-(\d+(?:\.\d+)?)\"", line)
    ls = _num(_v(F.get("line_size_inlet")))
    if ms and ls is not None and float(ms.group(1)) != ls:
        add("Data Error", "line_size_inlet", f"Size in Line No. {ms.group(1)}\" differs from Line Size {_v(F.get('line_size_inlet'))}",
            expected=f'{ms.group(1)}"')
    for op, de, what in (("op_pressure", "design_pressure", "pressure"), ("op_temp", "design_temp", "temperature")):
        a, b = F.get(op), F.get(de)
        if a and b and _num(_v(a)) is not None and _num(_v(b)) is not None and (a.get("unit") or "") == (b.get("unit") or ""):
            if _num(_v(a)) > _num(_v(b)):
                add("Data Error", op, f"Operating {what} {_v(a)} exceeds design {what} {_v(b)}", expected=f"≤ {_v(b)}")
    fp, af = _v(F.get("fail_position")).upper(), _v(F.get("air_failure")).upper()
    pick = lambda t: "CLOSE" if "CLOSE" in t else "OPEN" if "OPEN" in t else "LAST" if "LAST" in t else ""   # noqa: E731
    if pick(fp) and pick(af) and pick(fp) != pick(af):
        add("Data Error", "air_failure", f"Fail safe position '{_v(F.get('fail_position'))}' contradicts Action on Air Failure "
            f"'{_v(F.get('air_failure'))}'", expected=_v(F.get("fail_position")))
    for f in ds["fields"]:
        v = _v(f)
        for no in (int(x) for x in _GN.findall(v)):
            if gn and no not in gn:
                add("Data Error", f["key"], f"Referenced General Note {no} does not exist in {ds.get('doc_no')}", f=f)
        for no in (int(x) for x in _N.findall(re.sub(_GN, " ", v))):
            if notes and no not in notes:
                add("Data Error", f["key"], f"Referenced Note {no} does not exist on this datasheet", f=f)
        ref = f.get("ref") or {}
        if isinstance(ref, dict) and ref.get("mismatch"):
            mm = ref["mismatch"]
            add("Data Error", f["key"], f"{f.get('display') or f['key']} refers to Note {ref.get('no')}, which is about "
                f"'{ref.get('text', '')[:60]}'; Note {mm['no']} covers this item ('{mm['text'][:80]}')",
                expected=f"Note {mm['no']}" + (f": {mm['value']}" if mm.get("value") else ""), f=f)
        if f.get("status") == "review" and f.get("edited_value") is None and v:
            add("Extraction Review", f["key"], f"Label/value pairing of '{f.get('label') or f['key']}' could not be settled by the tool — check", f=f)
        if f.get("edited_value") is not None:
            add("Reviewer Correction", f["key"], f"Correction: '{f.get('value') or '(blank)'}' → '{f['edited_value']}'"
                f" ({f.get('edited_by') or '-'})", expected=f["edited_value"], f=f)

    if pms or pms_rows is not None:
        for r in (pms_rows if pms_rows is not None else pmsmod.check(F, pms, area, ds.get("notes"))):
            if r["result"] == material.COMPLIANT:
                continue
            it = "PMS Non-Compliance" if r["result"] == material.NON else "PMS Review"
            add(it, r["key"], f"{r['item']}: {r['reason']} (Class {r['class']})", expected=r["req"],
                extra={"pms_page": r.get("pms_page"), "pms_bbox": r.get("pms_bbox"), "result": r["result"]})

    for r in prev_cmp or []:
        if r["change"] in ("Modified", "Added", "Deleted"):
            add("Revision Change", r["key"], f"{r['change']}: '{r['previous'] or '(blank)'}' → '{r['new'] or '(blank)'}'",
                expected="", page=r.get("new_page"), bbox=r.get("new_bbox"),
                f={"display": r.get("display"), "row": r.get("row"), "value": r.get("new"), "unit": r.get("unit")})

    for c in ds.get("comments", []):
        add("Reviewer Comment", f"comment.{c['id']}", c["text"], page=c.get("page"), bbox=c.get("bbox"),
            f={"display": "Review Comment", "value": "", "row": None}, extra={"by": c.get("by"), "comment_id": c["id"]})
    seen, uniq = set(), []
    for i in out:                                         # the same check can fire twice (two note refs in one cell)
        k = (i["ikey"], i["description"])
        if k not in seen:
            seen.add(k)
            uniq.append(i)
    uniq.sort(key=lambda i: (i["page"] or 0, (i["bbox"] or [0, 0])[1], (i["bbox"] or [0])[0]))
    # numbers = what the paper shows: contractor issues 1…n first, internal extraction checks after them
    ordered = [i for i in uniq if i["type"] != "Extraction Review"] + [i for i in uniq if i["type"] == "Extraction Review"]
    for n, i in enumerate(ordered, 1):
        i["no"] = n
    return uniq
