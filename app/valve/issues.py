"""Issues — what is wrong or missing in a datasheet, each tied to its page and box (for mark-up and the issue list).

Rule-based only.  Every issue says what was checked against what:

  Data Missing        required field present on the form but empty · every blank PROCESS DATA item
                      (also when the sheet refers to a Process Data Sheet — the reference is named)   orange  Major
  Open Item           any field or note on HOLD / TBC / TBA ('HOLD (…)', 'Hold-1' → the HOLD list item)   orange  Major
  Data Error          the sheet contradicts itself:                                   red     Major
                        · Line No. class '(1C0K8)' ≠ Piping class
                        · Line No. size ≠ Line Size
                        · operating > design (pressure / temperature, same unit)
                        · fail-safe position ≠ action on air failure
                        · 'General Note - N' / 'Note-N' that the document does not have
                        · a later sheet prints another Document No. / repeats Tag · PID · Service · Line differently
  PMS Non-Compliance  pms.check -> Non-Compliant                                       red     Major
  PMS Review          pms.check -> Review Required / Not Defined in PMS                red     Minor
  Revision Change     changed against the previous revision of the same tag            yellow  Info
  Reviewer Correction value corrected by a reviewer (read value → corrected value)       blue    Major
  Reviewer Comment    review comment / PDF mark-up (category comment · question)        blue    Major / Minor
                      a mark-up in category error / missing becomes Data Error / Data Missing (red / orange)
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
# every item printed in the PROCESS DATA block is checked for a value (user request 2026-10-31: all blank process
# data must be marked, also when the sheet refers to a Process Data Sheet).  Section 'process' plus the process-row
# items the On/Off form files under other sections; mechanical items (schema.NOT_PROCESS) never count.
PROCESS_ROW_ITEMS = {"sour_service", "corrosive", "erosive", "toxic", "stroke_open", "stroke_closed", "stroke_time_s"}
COLOR = {"Data Missing": "missing", "Open Item": "missing", "Data Error": "error", "PMS Non-Compliance": "error", "Process Mismatch": "process",
         "PMS Review": "error", "Revision Change": "revision", "Reviewer Correction": "comment",
         "Reviewer Comment": "comment", "Extraction Review": "extract"}
CONTRACTOR_TYPES = ["Data Missing", "Open Item", "Data Error", "PMS Non-Compliance", "PMS Review", "Process Mismatch", "Revision Change",
                    "Reviewer Correction", "Reviewer Comment"]
# reviewer mark-up category -> (issue type, severity, description prefix) — the contractor reads one list
MARK_TYPE = {"comment": ("Reviewer Comment", "Major", ""), "question": ("Reviewer Comment", "Minor", "Question: "),
             "error": ("Data Error", "Major", "Reviewer: "), "missing": ("Data Missing", "Major", "Reviewer: ")}
_OPEN = re.compile(r"\b(HOLD|TBC|TBA)\b|\bto be confirmed\b", re.I)     # anywhere in the value: 'HOLD (… API 607)' · 'Note-9, Hold-1'
_LEGEND = re.compile(r"\b(HOLD|TBC|TBA)\s*[-=:–]\s*to be\b", re.I)          # 'TBC - To be Confirmed' only defines the word
_HOLD_REF = re.compile(r"\bhold\s*[-–#]?\s*(\d+)", re.I)                       # 'Hold-1' -> item 1 of the HOLD list
_GN = re.compile(r"gen(?:eral|\.)?\s*note\s*[-–:#]?\s*(\d+)", re.I)   # 'General Note-8' · 'Gen Note-30'

_N = re.compile(r"\bnote\s*[-–:#]?\s*(\d+)", re.I)                    # applied after _GN matches are removed


def _num(v):
    m = re.search(r"-?\d+(?:\.\d+)?", (v or "").replace(",", ""))
    return float(m.group(0)) if m else None


def _v(f):
    return schema.effective(f)


def compute(ds: dict, general_notes: dict | None = None, pms: dict | None = None, area: str = "",
            prev_cmp: list | None = None, states: dict | None = None, pms_rows: list | None = None,
            process_rows: list | None = None) -> list[dict]:
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
                           else "Minor" if itype == "PMS Review" else "Major")   # HOLD / TBC = Major: release it and give the value
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
    for k in REQUIRED:
        f = F.get(k)
        if not f:
            continue                                         # not on this form: cannot be missing from it
        v = _v(f)
        if not v.strip():
            add("Data Missing", k, f"{f.get('display') or k}: no value given")
    # process data — every blank item of the PROCESS DATA block (a Max/Nor/Min parameter counts once, when all cases are blank)
    pd_val = {}
    for r in process_rows or []:
        if r.get("pd") and r.get("ds_key"):
            pd_val[r["ds_key"].split(".")[0]] = f"{r['pd']} {r.get('pd_unit') or ''}".strip()
    groups = {}
    for f in ds["fields"]:
        k = f["key"]
        base = k.rsplit(".", 1)[0] if k.endswith((".max", ".nor", ".min")) else k
        if (f.get("section") == "process" or base in PROCESS_ROW_ITEMS) and base not in schema.NOT_PROCESS:
            groups.setdefault(base, []).append(f)
    has_open_closed = "stroke_open" in groups or "stroke_closed" in groups
    for base, fs in groups.items():
        if base == "stroke_time_s" and has_open_closed:
            continue                                         # the row caption; its Open / Closed cells are checked
        vals = [_v(f) for f in fs]
        if any(v.strip() for v in vals):
            continue
        f0 = next((f for f in fs if f["key"].endswith(".nor")), fs[0])
        disp = (f0.get("display") or base).replace(" (Nor)", "")
        why = f"{disp}: no value given" + (" (Max / Nor / Min all blank)" if len(fs) > 1 else "")
        if pref:
            why += f" — datasheet refers to Process Data Sheet {pref.get('doc') or ''} ({pref.get('where', '')}); state the value or confirm".replace("  ", " ")
        add("Data Missing", base, why, expected=pd_val.get(base, ""), f=dict(f0, display=disp), severity="Major")

    # HOLD / TBC / TBA anywhere — every field and every note (user request 2026-10-31: release the HOLD, give the value)
    hold_notes = {n["no"]: n for n in ds.get("notes", []) if (n.get("section") or "").upper() == "HOLD"}
    for f in ds["fields"]:
        v = _v(f)
        if not v.strip() or not _OPEN.search(v) or _LEGEND.search(v):
            continue
        refd = [hold_notes[int(m)] for m in _HOLD_REF.findall(v) if int(m) in hold_notes]
        add("Open Item", f["key"], f"{f.get('display') or f['key']} is '{v}' — on HOLD / TBC: release the HOLD and give the value"
            + "".join(f" (HOLD {h['no']}: {h['text'][:100]})" for h in refd), expected="Value to be given (HOLD release)", f=f)
    for n in ds.get("notes", []):
        held = (n.get("section") or "").upper() == "HOLD"
        if held or (_OPEN.search(n["text"]) and not _LEGEND.search(n["text"])):
            add("Open Item", f"note.{'hold.' if held else ''}{n['no']}", f"{'HOLD ' if held else 'Note '}{n['no']}: '{n['text'][:140]}' — "
                "still on HOLD / TBC: release and confirm", expected="Confirmed content (HOLD release)", page=n.get("page"), bbox=n.get("bbox"),
                f={"display": f"{'HOLD' if held else 'Note'} {n['no']}", "value": n["text"][:80], "row": None})

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
    for mm in ds.get("sheet_doc_mismatch") or []:            # the sheet's own title block prints another number
        add("Data Error", f"doc_no.p{mm['page']}", f"Sheet {mm.get('sheet') or '?'} prints Document No. '{mm['printed']}'"
            f" — sheet 1 has '{ds.get('doc_no')}'", expected=ds.get("doc_no") or "", page=mm["page"],
            f={"display": "Document No.", "value": mm["printed"], "row": None})
    for f in ds["fields"]:                                   # a later sheet repeats the header rows (Tag · PID · …)
        base, _, row = f["key"].rpartition(".")
        if base in ("tag", "pid_no", "service", "line_no") and row.isdigit() and base in F:
            a, b = _v(F[base]), _v(f)
            if a and b and schema.norm_tag(a) != schema.norm_tag(b):
                add("Data Error", f["key"], f"{F[base].get('display') or base} on p.{f.get('page')} is '{b}' — sheet 1 says '{a}'",
                    expected=a, f=f)
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

    for r in process_rows or []:                         # Phase 3: datasheet process item ≠ Process Data table
        if r["result"] == "Mismatch":
            add("Process Mismatch", r.get("ds_key") or r["key"], f"{r['item']}: {r['reason']} (Process Data p.{r.get('pd_page')})",
                expected=f"{r['pd']} {r.get('pd_unit') or ''}".strip(), page=r.get("ds_page"), bbox=r.get("ds_bbox"),
                f={"display": r["item"], "value": r.get("ds"), "unit": r.get("ds_unit"), "row": None},
                extra={"pd_page": r.get("pd_page"), "pd_bbox": r.get("pd_bbox"), "result": r["result"]})
    for r in prev_cmp or []:
        if r["change"] in ("Modified", "Added", "Deleted"):
            add("Revision Change", r["key"], f"{r['change']}: '{r['previous'] or '(blank)'}' → '{r['new'] or '(blank)'}'",
                expected="", page=r.get("new_page"), bbox=r.get("new_bbox"),
                f={"display": r.get("display"), "row": r.get("row"), "value": r.get("new"), "unit": r.get("unit")})

    for c in ds.get("comments", []):                         # reviewer mark-ups: the category says what kind of finding
        cat = c.get("category") or "comment"
        it, sev, pre = MARK_TYPE.get(cat, MARK_TYPE["comment"])
        text = c.get("text") or ""
        add(it, f"comment.{c['id']}", pre + (text or "(see mark-up on the PDF)"), page=c.get("page"), bbox=c.get("bbox"),
            f={"display": "Reviewer Mark-up" if c.get("bbox") else "Review Comment", "value": "", "row": None},
            severity=sev, extra={"by": c.get("by"), "comment_id": c["id"], "category": cat,
                                 "kind": c.get("kind") or ("rect" if c.get("bbox") else None), "points": c.get("points"),
                                 "text_raw": text})
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
