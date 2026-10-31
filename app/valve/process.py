"""Process Data verification (Phase 3) — read the 'Process Data for On-Off Valve' tables and compare the process
items of each datasheet with them.

Reading: a page is a ruled table (one or more tag rows).  Column bands come from the page's own vertical rules;
the header rows above the unit row name each band; a data row is a line whose first band holds the serial number.
Nothing is positioned by a constant — only this page's rules and words.

Comparing (spec §6.3 · prompt P5): only process items — fluid · phase · operating/design pressure · operating/design
temperature · differential pressure · flow · stroke time · fail-safe position · tightness · line/P&ID numbers.
Valve size · bore · rating · pipe class · materials are NOT compared (mechanical data).
A number is converted only when the dimension is sure and, for a gauge/absolute pressure, the basis is written on
both sides ('bar(g)' ↔ 'bar-g' ok · 'psi' ↔ 'bar(g)' → Review Required).  Anything unclear is Review Required,
never Pass/Fail.
"""
from __future__ import annotations

import re

import pymupdf

from app.valve import extract, schema

# header phrase (normalised) -> process key.  Keys shared with the datasheet where the same thing is meant.
COLUMNS = [
    ("tag number", "tag"), ("spi tag", "spi_tag"), ("location", "location"), ("quantity", "quantity"), ("pid no", "pid_no"),
    ("valve type", "valve_type"), ("line no", "line_no"), ("line size", "line_size"), ("valve size", "valve_size"),
    ("valve bore", "bore"), ("pipe class", "piping_class"), ("service fluid", "fluid"), ("process fluid phase", "fluid_state"),
    ("flow rate", "flow"), ("maximum pressure drop", "max_dp"), ("operating temperature", "op_temp"),
    ("design temperature", "design_temp"), ("operating pressure", "op_pressure"), ("design pressure", "design_pressure"),
    ("molecular weight", "mol_weight"), ("density at t&p", "density"), ("viscosity at t&p", "viscosity"),
    ("upstream/downstream max pressure difference for opening", "dp_open"),
    ("upstream/downstream max pressure difference for closing", "dp_close"),
    ("operating time (opening)", "stroke_open_s"), ("operating time (closing)", "stroke_close_s"),
    ("normal position", "normal_position"), ("safety position", "fail_position"), ("required tightness", "tightness"),
    ("actutaor/driver type", "act_type"), ("actuator/driver type", "act_type"), ("notes", "notes"), ("remarks", "remarks"),
]
NOT_COMPARED = {"valve_size", "bore", "piping_class", "valve_type", "line_size"}      # mechanical — never process-verified
DISPLAY = {"fluid": "Service Fluid", "fluid_state": "Fluid Phase", "op_pressure": "Operating Pressure", "design_pressure": "Design Pressure",
           "op_temp": "Operating Temperature", "design_temp": "Design Temperature", "max_dp": "Max. Pressure Drop",
           "dp_close": "Max. ΔP for Closing", "dp_open": "Max. ΔP for Opening", "flow": "Flow Rate", "mol_weight": "Molecular Weight",
           "density": "Density", "viscosity": "Viscosity", "stroke_open_s": "Operating Time (Opening)", "stroke_close_s": "Operating Time (Closing)",
           "fail_position": "Safety (Fail) Position", "tightness": "Required Tightness", "line_no": "Line No.", "pid_no": "P&ID No.",
           "normal_position": "Normal Position", "act_type": "Actuator / Driver Type"}
MATCH, MISMATCH, REVIEW, NOT_IN_PD, REFERENCED, DS_BLANK = ("Match", "Mismatch", "Review Required", "Not in Process Data",
                                                              "Referenced", "Datasheet Blank")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().replace("\n", " ")).strip()


# ── reading ──────────────────────────────────────────────────────────────────────

_UNIT_WORDS = {"m3/h", "bar", "°c", "ºc", "bar(g)", "bar(a)", "barg", "bara", "kg/kmol", "kg/m³", "kg/m3", "cp", "second", "sec", "s",
               "kg/h", "nm3/h", "psi", "psig", "psia", "kpa", "kpag", "mpa", "°f", "mm", "in", "%"}


def _bands(page) -> list[tuple[float, float]]:
    """Column bands from the vertical rules that span most of the table height."""
    vert = extract._verticals(page)
    if not vert:
        return []
    hmax = max(y1 - y0 for _, y0, y1 in vert)
    xs = sorted({round(x, 1) for x, y0, y1 in vert if y1 - y0 >= hmax * 0.3})
    out, last = [], None
    for x in xs:
        if last is not None and x - last > 6:
            out.append((last, x))
        last = x
    return out


def _cell(words, a, b):
    return [w for w in words if a - 1 <= (w[0] + w[2]) / 2 < b + 1]


def read_page(page, page_no: int) -> dict | None:
    words = page.get_text("words")
    if not words:
        return None
    bands = _bands(page)
    if len(bands) < 8:
        return None
    lines = extract._lines(words)
    unit_i = next((i for i, ln in enumerate(lines) if sum(1 for w in ln if w[4].lower() in _UNIT_WORDS) >= 4), None)
    sr_i = next((i for i, ln in enumerate(lines) if any(w[4] == "Sr" for w in ln) and any(w[4].startswith("Tag") for w in ln)), None)
    if unit_i is None or sr_i is None:
        return None
    title_i = next((i for i, ln in enumerate(lines) if "Process Data" in " ".join(w[4] for w in ln)), -1)
    head_lines = [ln for i, ln in enumerate(lines) if title_i < i <= max(unit_i, sr_i) and i != unit_i]   # every header line above the units
    cols = []
    for a, b in bands:
        label = _norm(" ".join(w[4] for ln in head_lines for w in sorted(_cell(ln, a, b), key=lambda w: w[0])))
        label = re.sub(r"\s*\.\s*", ". ", label).replace("no .", "no.").strip(" .")
        unit = " ".join(w[4] for w in sorted(_cell(lines[unit_i], a, b), key=lambda w: w[0]))
        key = next((k for phrase, k in COLUMNS if phrase in label.replace(".", "").replace("  ", " ")), None)
        cols.append({"x0": a, "x1": b, "label": label, "unit": unit, "key": key})
    if not any(c["key"] == "tag" for c in cols):
        return None
    tag_i = next(i for i, c in enumerate(cols) if c["key"] == "tag")
    rows, body = [], lines[unit_i + 1:]
    cur = None
    for ln in body:
        first = " ".join(w[4] for w in _cell(ln, cols[0]["x0"], cols[0]["x1"]))
        tag_words = _cell(ln, cols[tag_i]["x0"], cols[tag_i]["x1"])
        if first.strip().isdigit() and tag_words:                       # a new tag row
            cur = {"sr": int(first), "tag": "", "page": page_no, "values": {}, "y0": min(w[1] for w in ln), "y1": max(w[3] for w in ln)}
            rows.append(cur)
        if cur is None:
            continue
        if ln and min(w[1] for w in ln) > cur["y1"] + 40:              # far below: a footer, not a wrapped cell
            cur = None
            continue
        cur["y1"] = max(cur["y1"], max(w[3] for w in ln))
        for c in cols:
            cw = _cell(ln, c["x0"], c["x1"])
            if not cw:
                continue
            k = c["key"] or f"x.{re.sub(r'[^a-z0-9]+', '_', c['label'])[:30]}"
            v = cur["values"].setdefault(k, {"v": "", "unit": c["unit"], "bbox": None, "label": c["label"]})
            v["v"] = (v["v"] + " " + " ".join(w[4] for w in sorted(cw, key=lambda w: w[0]))).strip()
            bb = extract._bbox(cw)
            v["bbox"] = bb if not v["bbox"] else [min(v["bbox"][0], bb[0]), min(v["bbox"][1], bb[1]), max(v["bbox"][2], bb[2]), max(v["bbox"][3], bb[3])]
    for r in rows:
        r["tag"] = r["values"].get("tag", {}).get("v", "")
        r["tag_key"] = schema.norm_tag(r["tag"])
        r["bbox"] = r["values"].get("tag", {}).get("bbox")
        r.pop("y0", None), r.pop("y1", None)
    title = next((" ".join(w[4] for w in ln) for ln in lines[:3] if "Process Data" in " ".join(w[4] for w in ln)), "")
    return {"page": page_no, "title": title, "columns": [{"key": c["key"], "label": c["label"], "unit": c["unit"]} for c in cols],
            "rows": [r for r in rows if r["tag_key"]]}


def read_process_data(path: str) -> dict:
    doc = extract.open_pdf(path)
    pages, rows, dn = [], [], ""
    m = extract._ANY_DOC_RE.search(doc[0].get_text()) if doc.page_count else None
    dn = m.group(0) if m else ""
    for i, page in enumerate(doc):
        r = read_page(page, i + 1)
        if r:
            pages.append({"page": r["page"], "title": r["title"], "rows": len(r["rows"])})
            rows.extend(r["rows"])
    by = {}
    for r in rows:
        by.setdefault(r["tag_key"], r)                                   # first row wins (a tag listed twice = same data)
    return {"doc_no": dn, "pages": pages, "rows": rows, "by_tag": by, "n_tags": len(by)}


# ── comparing ─────────────────────────────────────────────────────────────────────

_PRESS = {"bar": 1.0, "barg": 1.0, "bara": 1.0, "psi": 0.0689476, "psig": 0.0689476, "psia": 0.0689476, "kpa": 0.01, "kpag": 0.01,
          "kpaa": 0.01, "mpa": 10.0, "mpag": 10.0, "mpaa": 10.0, "kg/cm2": 0.980665, "kg/cm2g": 0.980665}


def unit_of(u: str) -> tuple[str, str | None, float | None]:
    """('press'|'temp'|'time'|'flow'|'other', basis g/a/None, factor to bar/°C/s)."""
    t = (u or "").lower().replace(" ", "").replace("º", "°").replace("-", "").replace("(", "").replace(")", "")
    if not t:
        return "other", None, None
    if t in ("°c", "degc", "c", "℃"):
        return "temp", None, 1.0
    if t in ("°f", "degf", "f"):
        return "temp", "F", None
    if t in ("s", "sec", "second", "seconds"):
        return "time", None, 1.0
    if t in ("min", "minute", "minutes"):
        return "time", None, 60.0
    if t in _PRESS:
        basis = "g" if t.endswith("g") and t != "kpag"[:0] else "a" if t.endswith("a") else None
        basis = "g" if t.endswith("g") else "a" if t.endswith("a") and t not in ("kpa", "mpa") else None
        return "press", basis, _PRESS[t]
    if t in ("m3/h", "nm3/h", "kg/h", "t/h", "m3/hr", "kg/hr"):
        return "flow", t, 1.0
    return "other", None, None


def _num(v: str):
    m = re.search(r"-?\d+(?:[.,]\d+)?", (v or "").replace(",", ""))
    return float(m.group(0)) if m else None


def _blank(v: str) -> bool:
    return not (v or "").strip() or (v or "").strip() in ("-", "—", "NA", "N/A") or schema.norm_label(v) in schema.PLACEHOLDERS


_FAIL = {"fc": "close", "fail close": "close", "close": "close", "closed": "close", "fo": "open", "fail open": "open", "open": "open",
         "fl": "last", "fail last": "last", "last": "last", "lock": "last"}
_TIGHT = {"tso": "tight shut-off", "tight shut-off": "tight shut-off", "tight shutoff": "tight shut-off", "tight shut off": "tight shut-off"}
_PHASE = {"vapor": "gas", "vapour": "gas", "gas": "gas", "liquid": "liquid", "liq": "liquid", "two phase": "two phase", "2-phase": "two phase"}

# datasheet key(s) that hold the same item as a process column
DS_KEYS = {"fluid": ["fluid", "fluid.nor"], "fluid_state": ["fluid_state", "fluid_state.nor"], "op_pressure": ["op_pressure", "inlet_pressure.nor", "inlet_pressure.max"],
           "design_pressure": ["design_pressure", "design_pressure.max", "design_pressure.nor"], "op_temp": ["op_temp", "op_temp.nor", "op_temp.max"],
           "design_temp": ["design_temp", "design_temp.max", "design_temp.nor"], "dp_close": ["max_dp_closed", "max_dp_closed.max"], "max_dp": ["max_dp_closed"],
           "flow": ["flow", "flow.nor", "flow.max"], "mol_weight": ["mol_weight", "mol_weight.nor"], "density": ["density", "density.nor"],
           "viscosity": ["viscosity", "viscosity.nor"], "stroke_close_s": ["stroke_time_s", "stroke_closed", "stroke_time"], "stroke_open_s": ["stroke_open"],
           "fail_position": ["fail_position", "failureaction", "air_failure"], "tightness": ["tightness"], "line_no": ["line_no"], "pid_no": ["pid_no"]}


def _ds_field(F: dict, keys: list[str]):
    for k in keys:
        f = F.get(k)
        if f and (schema.effective(f) or "").strip():
            return f
    return next((F[k] for k in keys if k in F), None)


def compare_item(key: str, ds_v: str, ds_u: str, pd_v: str, pd_u: str) -> tuple[str, str]:
    """(result, reason) for one item — the rules in the module docstring."""
    if _blank(pd_v):
        return NOT_IN_PD, "Process Data gives no value"
    if _blank(ds_v):
        return DS_BLANK, "Datasheet gives no value"
    if key in ("fail_position",):
        a, b = _FAIL.get(_norm(ds_v).replace("fail ", "fail "), None), _FAIL.get(_norm(pd_v), None)
        a = a or next((v for k2, v in _FAIL.items() if k2 in _norm(ds_v)), None)
        if a and b:
            return (MATCH, f"Both mean fail {a}") if a == b else (MISMATCH, f"Datasheet fail {a}, Process Data {pd_v} (fail {b})")
        return REVIEW, "Position wording not recognised"
    if key == "tightness":
        a, b = next((v for k2, v in _TIGHT.items() if k2 in _norm(ds_v)), None), _TIGHT.get(_norm(pd_v))
        if a and b:
            return (MATCH, "Both tight shut-off") if a == b else (MISMATCH, f"'{ds_v}' vs '{pd_v}'")
        return REVIEW, "Tightness wording not recognised"
    if key == "fluid_state":
        a, b = next((v for k2, v in _PHASE.items() if k2 in _norm(ds_v)), None), next((v for k2, v in _PHASE.items() if k2 in _norm(pd_v)), None)
        if a and b:
            return (MATCH, f"Both {a}") if a == b else (MISMATCH, f"Datasheet {a}, Process Data {b}")
        return REVIEW, "Phase wording not recognised"
    if key in ("fluid", "line_no", "pid_no"):
        a, b = schema.norm_tag(ds_v), schema.norm_tag(pd_v)
        if a == b:
            return MATCH, "Same"
        if key == "fluid":
            wa, wb = set(re.findall(r"[a-z0-9]{2,}", _norm(ds_v))), set(re.findall(r"[a-z0-9]{2,}", _norm(pd_v)))
            if wa and wb and (wa <= wb or wb <= wa):
                return MATCH, "Same fluid (one side says more)"
            if wa & wb:
                return REVIEW, f"Partly the same words: '{ds_v}' vs '{pd_v}'"
            return MISMATCH, f"'{ds_v}' vs '{pd_v}'"
        if key == "pid_no":                                            # 'A B' = the valve sits on two P&IDs
            pds = {schema.norm_tag(x) for x in re.sub(r"-\s+", "-", pd_v).split()}
            if a in pds:
                return MATCH, "Datasheet P&ID is one of those in Process Data" if len(pds) > 1 else "Same"
            return MISMATCH, f"'{ds_v}' vs '{pd_v}'"
        strip_q = lambda x: re.sub(r"\(([0-9A-Z]+)-[0-9A-Z]+\)", r"(\1)", x)   # noqa: E731  '(1C3AS1-QG1)' -> '(1C3AS1)'
        if schema.norm_tag(strip_q(ds_v)) == schema.norm_tag(strip_q(pd_v)):
            return REVIEW, f"Same line number; only the class qualifier differs ('{ds_v}' vs '{pd_v}')"
        return MISMATCH, f"'{ds_v}' vs '{pd_v}'"
    # numbers
    a, b = _num(ds_v), _num(pd_v)
    if a is None or b is None:
        return REVIEW, f"Not a number on one side: '{ds_v}' vs '{pd_v}'"
    da, ba, fa = unit_of(ds_u or ds_v[len(str(_num(ds_v))):]), None, None
    da, ba, fa = unit_of(ds_u) if ds_u else unit_of(re.sub(r"[-\d.,\s]+", "", ds_v, count=1))
    db, bb, fb = unit_of(pd_u)
    if key in ("op_pressure", "design_pressure", "dp_close", "dp_open", "max_dp"):
        if da != "press" or db != "press":
            return REVIEW, f"Pressure unit unclear ('{ds_u or '?'}' vs '{pd_u or '?'}')"
        if key in ("op_pressure", "design_pressure"):
            if ba is None or bb is None:
                return REVIEW, f"Gauge/absolute basis not written on both sides ('{ds_u}' vs '{pd_u}') — compare by hand"
            if ba != bb:
                return REVIEW, f"Different basis: '{ds_u}' vs '{pd_u}' (no atmospheric correction made)"
        va, vb = a * fa, b * fb
    elif key in ("op_temp", "design_temp"):
        if da != "temp" or db != "temp":
            return REVIEW, f"Temperature unit unclear ('{ds_u}' vs '{pd_u}')"
        va = (a - 32) * 5 / 9 if ba == "F" else a
        vb = (b - 32) * 5 / 9 if bb == "F" else b
    elif key in ("stroke_close_s", "stroke_open_s"):
        if da != "time" or db != "time":
            return REVIEW, f"Time unit unclear ('{ds_u}' vs '{pd_u}')"
        va, vb = a * fa, b * fb
    elif key == "flow":
        if da != "flow" or db != "flow" or ba != bb:
            return REVIEW, f"Flow unit differs or unclear ('{ds_u}' vs '{pd_u}')"
        va, vb = a, b
    else:                                                              # MW · density · viscosity: same unit text only
        if _norm(ds_u) and _norm(pd_u) and _norm(ds_u).replace(" ", "") != _norm(pd_u).replace(" ", ""):
            return REVIEW, f"Unit differs ('{ds_u}' vs '{pd_u}')"
        va, vb = a, b
    tol = max(0.01 * abs(vb), 0.05)
    if abs(va - vb) <= tol:
        return MATCH, f"{a} {ds_u or ''} = {b} {pd_u or ''}".replace("  ", " ")
    return MISMATCH, f"Datasheet {a} {ds_u or ''} ≠ Process Data {b} {pd_u or ''}".replace("  ", " ")


def check(ds: dict, pdoc: dict | None) -> list[dict]:
    """Rows for one datasheet: every process item the Process Data table has, compared with the datasheet."""
    if not pdoc:
        return []
    row = (pdoc.get("by_tag") or {}).get(ds.get("tag_key"))
    F = {f["key"]: f for f in ds["fields"]} if isinstance(ds["fields"], list) else ds["fields"]
    out = []
    if not row:
        return [{"key": "tag", "item": "Tag in Process Data", "ds": ds.get("tag", ""), "ds_unit": "", "pd": "", "pd_unit": "",
                 "result": NOT_IN_PD, "reason": f"Tag {ds.get('tag_key')} is not in the Process Data document", "pd_page": None, "pd_bbox": None,
                 "ds_page": None, "ds_bbox": None}]
    ref = ds.get("process_ref")
    for key, keys in DS_KEYS.items():
        pv = row["values"].get(key)
        if pv is None:
            continue
        f = _ds_field(F, keys)
        ds_v = schema.effective(f) if f else ""
        ds_u = (f or {}).get("unit") or ""
        res, why = compare_item(key, ds_v, ds_u, pv["v"], pv["unit"])
        if res == DS_BLANK and ref:
            res, why = REFERENCED, f"Datasheet refers to the Process Data Sheet ({ref.get('where', '')}) — value taken from there"
        out.append({"key": key, "ds_key": (f or {}).get("key"), "item": DISPLAY.get(key, key), "ds": ds_v, "ds_unit": ds_u, "pd": pv["v"], "pd_unit": pv["unit"],
                    "result": res, "reason": why, "pd_page": row["page"], "pd_bbox": pv.get("bbox"),
                    "ds_page": (f or {}).get("page"), "ds_bbox": (f or {}).get("bbox")})
    return out
