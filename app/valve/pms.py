"""PMS (Piping Material Specification) — read the class sheets and check a valve datasheet against them.

Reads Appendix C class sheets of e.g. 98-98-PI-SPC-00001 (text layer, PyMuPDF):
  header  'Class: 1C0K8' · 'Class 150, 316/316L, SS, RF, 0mm C.A., NACE …' · 'Flange Class: CLASS 150' ·
          'Material: STAINLESS STEEL' · 'Valve Trim: TRIM 12 (316 SS/HF)' · 'NACE Requirement: …' · 'Corrosion Allowance'
  items   one block each: code · size from · '-' · size to · description ('BALL VALVE, 316/316L SS A351-CF8M/CF3M,
          CL150, RF, … TRUNNION, API 6D, … FULL PORT, 316 SS BALL/STEM, RTFE ST, FIRE TESTED TO API 607, NACE …')

check(ds_fields, pms) compares the datasheet's piping class, rating, body, trim, seat, NACE and fire-safe values
with the class header and the ball-valve item that fits the valve (size range · bore · trunnion/floating), using
material.compare (meaning, not spelling).  Every result carries the PMS page and the box of the item it used.
"""
from __future__ import annotations

import re

import pymupdf

from app.valve import material, schema

_CLASS = re.compile(r"Class:\s*([0-9A-Z]{2,8})\b")
_ITEM = re.compile(r"^(P[A-Z0-9]{8,})\n([\d.]+)\n-\n([\d.]+)\n(.+)$", re.S)
_HDR_KEYS = {"Flange Facing": "facing", "Corrosion Allowance": "ca", "Post Weld Heat Treat": "pwht",
             "NACE Requirement": "nace", "Flange Class": "flange_class", "Material": "material", "Valve Trim": "trim"}


_CODE = re.compile(r"^P[A-Z0-9]{8,}$")
_SIZE_LINE = re.compile(r"^[\d.\s\-xX/]+$")


def parse_item(block: str) -> dict | None:
    """One PMS item block: code, size line(s), description.  Sizes come in several layouts:
    '42 / - / 42' · '0.75 - / 1.5 / 0.5 / - / 1' (run range, then branch range) · '2' (one size)."""
    lines = [ln.strip() for ln in block.strip().split("\n") if ln.strip()]
    if not lines or not _CODE.match(lines[0]):
        return None
    k = 1
    while k < len(lines) and (_SIZE_LINE.match(lines[k]) or lines[k] == "-"):
        k += 1
    desc = " ".join(" ".join(lines[k:]).split())
    toks = re.findall(r"\d+(?:\.\d+)?|-", " ".join(lines[1:k]))
    if not desc or not toks or toks[0] == "-":
        return None
    nums, j = [], 0
    while j < len(toks):                                  # 'a - b' is a range, a lone 'a' is one size
        if toks[j] == "-":
            j += 1
            continue
        a = float(toks[j])
        if j + 2 < len(toks) and toks[j + 1] == "-" and toks[j + 2] != "-":
            nums.append((a, float(toks[j + 2])))
            j += 3
        else:
            nums.append((a, a))
            j += 1
    run = nums[0]
    return {"code": lines[0], "from": run[0], "to": run[1], "branch": list(nums[1]) if len(nums) > 1 else None,
            "kind": desc.split(",")[0].strip(), "desc": desc}


READER_VERSION = 2          # 2 = class header also gives P-T limits, services, class / item notes (valve10)
_NUM = re.compile(r"^-?\d+(?:\.\d+)?$")


def header_blocks(lines: list[str]) -> dict:
    """The class sheet's lists: P-T limits [(°C, barg)], design code / ASME group, services, class and item notes.
    'Temperature / Pressure Limits' … numbers in (temperature, pressure) pairs … 'Service:' … 'Default Schedule Table'
    · 'General Class Notes' 002 / text … 'Item Specific Notes' 005 / text … 'Printed:'."""
    out = {"pt": [], "services": [], "class_notes": {}, "item_notes": {}}

    def span(a, stops):
        i = next((k for k, ln in enumerate(lines) if ln.startswith(a)), None)
        if i is None:
            return []
        j = next((k for k in range(i + 1, len(lines)) if any(lines[k].startswith(s) for s in stops)), len(lines))
        return lines[i + 1:j]
    nums = [float(x) for x in span("Temperature / Pressure Limits", ("Service:", "Default Schedule", "General Class Notes"))
            if _NUM.match(x)]
    out["pt"] = [(nums[k], nums[k + 1]) for k in range(0, len(nums) - 1, 2)]
    g = next((ln for ln in lines if ln.startswith("ASME B16")), "")
    out["pt_basis"] = g
    out["services"] = [x for x in span("Service:", ("Default Schedule", "General Class Notes", "Item Specific")) if x]
    for key, a, stops in (("class_notes", "General Class Notes", ("Item Specific Notes", "Printed:")),
                          ("item_notes", "Item Specific Notes", ("Printed:", "SCH", "APPENDIX"))):
        no = None
        for ln in span(a, stops):
            if re.fullmatch(r"\d{2,3}", ln):
                no = ln
                out[key][no] = ""
            elif no and ln:
                out[key][no] = (out[key][no] + " " + ln).strip()
    return out


def area_of_page(text: str) -> str:
    """Appendix C = QN and W15 area, Appendix D = QS (98-98-PI-SPC-00001 §6)."""
    m = re.search(r"APPENDIX\s+([A-Z])\.\s*PIPE MATERIAL CLASSES FOR\s+([A-Z0-9 ]+)", text.upper())
    if not m:
        return "QN"
    return "QS" if re.search(r"\bQS\b|SOUTH", m.group(2)) else "QN"


def area_of_title(title: str) -> str:
    """Datasheet document title -> PMS area ('' when the title does not say)."""
    t = (title or "").upper()
    return "QS" if "SOUTH" in t else "QN" if ("NORTH" in t or "W15" in t) else ""


def read_pms(path: str, progress=None) -> dict:
    areas: dict[str, dict] = {}
    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc):
            if progress:
                progress(i + 1, doc.page_count)
            text = page.get_text()
            m = _CLASS.search(text)
            if not m or "PIPING MATERIAL SPECIFICATION" not in text.upper():
                continue
            code, area = m.group(1), area_of_page(text)
            classes = areas.setdefault(area, {})
            c = classes.setdefault(code, {"code": code, "area": area, "pages": [], "items": [], "header_page": None})
            c["pages"].append(i + 1)
            if "Flange Class:" in text and not c.get("header_page"):
                c["header_page"] = i + 1
                lines = [ln.strip() for ln in text.split("\n")]
                k = lines.index(code) if code in lines else -1
                if k >= 0 and k + 1 < len(lines):
                    c["title"] = lines[k + 1]
                for ln in lines:
                    key, _, val = ln.partition(":")
                    if key.strip() in _HDR_KEYS and val.strip():
                        c[_HDR_KEYS[key.strip()]] = val.strip()
                c.update(header_blocks(lines))
                bb = page.search_for("Valve Trim:")
                c["trim_bbox"] = [round(v, 1) for v in bb[0]] if bb else None
                bb = page.search_for("Flange Class:")
                c["class_bbox"] = [round(v, 1) for v in bb[0]] if bb else None
            for b in page.get_text("blocks"):
                it = parse_item(b[4])
                if it:
                    c["items"].append(dict(it, page=i + 1, bbox=[round(v, 1) for v in b[:4]]))
    for classes in areas.values():
        for c in classes.values():
            m = re.search(r"CLASS\s*(\d+)", c.get("flange_class", "") or c.get("title", ""), re.I)
            c["rating"] = int(m.group(1)) if m else None
            if re.fullmatch(r"\s*(NONE|NA|N/A|NOT REQUIRED|-)?\s*", c.get("nace", "") or ""):
                c.pop("nace", None)                          # 'NACE Requirement: NONE' = no requirement
    return {"areas": areas, "v": READER_VERSION}


def ball_item_fields(desc: str) -> dict:
    d = desc.upper()
    m = re.search(r"BALL VALVE,\s*(.+?),\s*CL\s*(\d+)", d)
    out = {"body": m.group(1).strip() if m else "", "rating": int(m.group(2)) if m else None}
    t = re.search(r"([0-9A-Z/ .\-]+?)\s+BALL/STEM", d)
    out["trim"] = t.group(1).split(",")[-1].strip() if t else ""
    s = re.search(r",\s*([A-Z0-9\-]+)\s+ST\b", d)
    out["seat"] = s.group(1) if s else ""
    f = re.search(r"FIRE (?:TESTED|SAFE)[^,]*", d)
    out["fire"] = f.group(0) if f else ""
    out["bore"] = "FULL" if "FULL PORT" in d or "FULL BORE" in d else "REDUCED" if "RED PORT" in d or "REDUCED" in d else ""
    out["type"] = "TRUNNION" if "TRUNNION" in d else "FLOATING" if "FLOATING" in d else ""
    out["nace"] = "NACE" in d
    return out


def _inch(v: str):
    m = re.search(r"(\d+(?:\.\d+)?)(?:\s*(?:\"|in\b|inch))?", v or "")
    if not m:
        return None
    frac = re.search(r"(\d+)/(\d+)", v or "")
    return float(m.group(1)) if not frac or frac.start() > m.start() else float(frac.group(1)) / float(frac.group(2))


def find_class(pms: dict, piping_class: str, line_no: str = "", area: str = ""):
    """Class of the datasheet's area (QN/QS); exact code, else the code in the line number '(1C0K8)', else the
    longest class code that prefixes it.  Area unknown: QN first, then QS — said in the reason."""
    cl = (piping_class or "").strip().upper()
    order = [area] if area else ["QN", "QS"]
    for a in order:
        c, how = _find_in(pms.get("areas", {}).get(a, {}), cl, piping_class, line_no)
        if c:
            return c, how + ("" if area else f" (area unknown; found in PMS {a})")
    if area:                                                 # not in its own area: say where it is instead
        for a in ("QN", "QS"):
            if a != area:
                c, how = _find_in(pms.get("areas", {}).get(a, {}), cl, piping_class, line_no)
                if c:
                    return c, f"Piping class '{piping_class}' not in PMS {area} area but found in {a} — please confirm"
    return None, f"Piping class '{piping_class or '(blank)'}' is not defined in PMS{' ' + area if area else ''}"


def _find_in(classes, cl, piping_class, line_no):
    if cl in classes:
        return classes[cl], ""
    m = re.search(r"\(([0-9A-Z]{3,8})\)", line_no or "")
    if m and m.group(1) in classes:
        return classes[m.group(1)], f"Piping class '{piping_class}' not in PMS; used ({m.group(1)}) from Line No. — please confirm"
    pre = [k for k in classes if cl.startswith(k)]
    if pre:
        k = max(pre, key=len)
        return classes[k], f"Piping class '{piping_class}' not in PMS; matched '{k}' — please confirm"
    return None, ""


def check(fields: dict, pms: dict, area: str = "", notes: list | None = None) -> list[dict]:
    """fields: key -> {value|edited_value, page, bbox}.  -> rows of {item, req, ds, result, reason, pms_page, pms_bbox, key}."""
    val = lambda k: schema.effective(fields.get(k))   # noqa: E731  (a 'Note 14' cell is checked by what note 14 says)
    c, how = find_class(pms, val("piping_class"), val("line_no"), area)
    rows = []

    def add(item, key, req, ds, res, reason, page=None, bbox=None):
        rows.append({"item": item, "key": key, "req": req, "ds": ds, "result": res, "reason": reason,
                     "pms_page": page, "pms_bbox": bbox, "class": c["code"] if c else val("piping_class")})
    if not c:
        add("Piping Material Class", "piping_class", "—", val("piping_class"), material.NOT_DEFINED, how)
        return rows
    if how and ("please confirm" in how or how.startswith("Piping class")):
        add("Piping Material Class", "piping_class", c["code"], val("piping_class"), material.REVIEW, how,
            c.get("header_page"), c.get("class_bbox"))
    size = _inch(val("body_size"))
    bt = val("body_type").upper() + " " + val("trim_type").upper()
    want_bore = "FULL" if "FULL" in bt else "REDUCED" if "REDUC" in bt else ""
    want_type = "TRUNNION" if "TRUNNION" in bt else "FLOATING" if "FLOATING" in bt else ""
    balls = [it for it in c["items"] if it["kind"].upper().startswith("BALL VALVE")]
    fit = [it for it in balls if size is None or it["from"] - 1e-6 <= size <= it["to"] + 1e-6]
    best = None
    for it in fit:
        f = ball_item_fields(it["desc"])
        score = (f["bore"] == want_bore if want_bore else 0) + (f["type"] == want_type if want_type else 0)
        if best is None or score > best[0]:
            best = (score, it, f)
    # pressure class: class header first (it is the class), then the item
    r_ds = re.search(r"(\d{3,4})", val("rating"))
    req_rating = c.get("rating") or (best[2]["rating"] if best else None)
    if req_rating:
        if not r_ds:
            add("Pressure Class", "rating", f"CLASS {req_rating}", val("rating"), material.REVIEW, "Datasheet rating not readable",
                c.get("header_page"), c.get("class_bbox"))
        else:
            ok = int(r_ds.group(1)) == req_rating
            add("Pressure Class", "rating", f"CLASS {req_rating}", val("rating"), material.COMPLIANT if ok else material.NON,
                "Matches" if ok else f"PMS class {c['code']} is CLASS {req_rating}", c.get("header_page"), c.get("class_bbox"))
    if c.get("nace"):
        nv = val("nace").upper()
        nn = next((n for n in notes or [] if re.search(r"NACE\s*MR\s*0?175", n["text"], re.I)), None)
        if not nv.strip() and nn:                          # MOV form: no NACE field, the note says it
            add("NACE", "nace", c["nace"], f"Note {nn['no']}: {nn['text'][:70]}", material.COMPLIANT,
                f"Datasheet note {nn['no']} requires NACE", c.get("header_page"), None)
            nv = None
    if c.get("nace") and nv is not None:
        res = material.COMPLIANT if nv.startswith("Y") else material.NON if nv.startswith("N") else material.REVIEW
        add("NACE", "nace", c["nace"], val("nace"), res, "PMS class requires NACE" if res != material.COMPLIANT else "Matches",
            c.get("header_page"), None)
    # trim (ball/stem): the ball valve item's own 'X BALL/STEM' governs; the class header's general trim
    # (e.g. 'TRIM 8 (13CR/HF)', written for gate/globe valves) is only the fallback when no item says it
    if best and best[2]["trim"]:
        trim, tsrc, tpg, tbb = best[2]["trim"], f" · PMS item {best[1]['code']}", best[1]["page"], best[1]["bbox"]
    elif c.get("trim"):
        trim = re.sub(r"^TRIM\s*\d+\s*", "", c["trim"]).strip(" ()")
        tsrc, tpg, tbb = " · PMS class header trim", c.get("header_page"), c.get("trim_bbox")
    else:
        trim = ""
    if trim:
        for item, key in (("Trim (Ball) Material", "ball_material"), ("Stem Material", "stem_material")):
            if key in fields:
                res, why = material.compare(trim, val(key))
                add(item, key, trim, val(key), res, why + tsrc, tpg, tbb)
    if not best:
        add("Ball Valve Item", "body_size", "—", val("body_size"), material.NOT_DEFINED,
            f"No ball valve item for size {val('body_size')} in class {c['code']}", c.get("header_page"), None)
        return rows
    _, it, f = best
    pg, bb = it["page"], it["bbox"]
    if f["body"] and "body_material" in fields:
        res, why = material.compare(f["body"], val("body_material"))
        add("Body Material", "body_material", f["body"], val("body_material"), res, why + f" · PMS item {it['code']}", pg, bb)
    if f["seat"] and "seat_material" in fields:
        res, why = material.compare(f["seat"], val("seat_material"))
        add("Seat Material", "seat_material", f["seat"], val("seat_material"), res, why, pg, bb)
    if f["fire"] and val("fire_safe"):
        fv = val("fire_safe").upper()
        res = material.NON if fv.startswith(("NO", "NOT")) else material.COMPLIANT if fv.startswith(("YES", "REQ")) or "607" in fv \
            else material.REVIEW
        add("Fire Safe", "fire_safe", f["fire"], val("fire_safe"), res, "PMS item requires fire test", pg, bb)
    if want_bore and f["bore"] and f["bore"] != want_bore:
        add("Bore", "body_type", f["bore"] + " PORT", val("body_type"), material.REVIEW, "No PMS item with this bore for this size", pg, bb)
    return rows
