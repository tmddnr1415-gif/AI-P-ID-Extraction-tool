"""valve37 — more datasheet forms for the Globe · Butterfly · PSV menus (deterministic, no OCR / LLM).

  Form 101  Control Valve (Globe CV · Butterfly CV) — sheet 1 is laid out like Form 102 (two numbered columns, 'Label : value',
            bold values) and is read by extract.read_page_102; this module re-files its rows by block caption + heading,
            because the same label means different things in different blocks (Positioner 'Manufacturer', Solenoid 'Tag No',
            Position-transmitter 'Rating', Paint 'Handwheel' …).  Sheet 2 is the Max/Nor/Min process + sizing table
            (extract.read_process_table); its sizing lines go to their own section.  Sheet 3 is the notes page (form 000).
  Form 701  Pressure Relief Valve — one numbered column 1-50, bold values on short underlines (1-3 per row), small sub-labels
            ('Type' · 'Action' · 'Size' · 'Rating' …) before a slot.  read_page_701 reads it slot by slot.
  Code 80   On/Off valve (the Ball form) printed with its title block at the BOTTOM of the page and a notes-only sheet 2.

Every number used here is measured on the page itself (rules, underlines, number column, text height) — no coordinates are fixed.
Nothing here runs for the forms the Ball module already reads (Form 80 with the title block on top, Form 102, process tables).
"""
from __future__ import annotations

import re

from app.valve import schema

_FORM_NO = re.compile(r"Form\s*No\s*[:.]?\s*(\d{3})\b", re.I)
_UNITS = {"bar-g", "barg", "bar(g)", "bar", "bara", "bar(a)", "bar-a", "psi", "psig", "psia", "kpa", "kpag", "mpa", "mpag", "ºc", "°c",
          "degc", "ºf", "°f", "kg/m3", "kg/m³", "cp", "%", "kg/h", "kg/hr", "t/h", "nm3/h", "m3/h", "mm2", "mm²", "in2", "in²", "n", "kn",
          "in", "mm", "g/mol", "kg/kmol"}


def _ex():
    from app.valve import extract                         # extract imports this module lazily — no import cycle
    return extract


def form_no(words, page) -> str | None:
    """'Form No : 101' / 'Form No: 701' printed above the title block (top fifth of the page)."""
    top = [w for w in words if w[3] < page.rect.height * 0.2]
    m = _FORM_NO.search(" ".join(w[4] for w in sorted(top, key=lambda w: (round(w[1]), w[0]))))
    return m.group(1) if m else None


def _spans(page):
    ex = _ex()
    out = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            for sp in ln["spans"]:
                t = sp["text"].strip()
                if t:
                    x0, y0, x1, y1 = sp["bbox"]
                    out.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "text": t, "size": sp["size"],
                                "bold": bool(sp["flags"] & 16) or "Bold" in sp["font"]})
    return ex._visible(out, ex._hidden_boxes(page), box=lambda s: (s["x0"], s["y0"], s["x1"], s["y1"]), text=lambda s: s["text"])


def _status(key_hit: bool, value: str) -> str:
    if not key_hit:
        return "review" if value else "blank"
    if not value:
        return "blank"
    return "placeholder" if schema.norm_label(value) in schema.PLACEHOLDERS else "ok"


def _header_doc_only(page, words, top_y, hdr, tag="", pid=""):
    """Forms 101 / 701: the document number is the one printed in the DOCUMENT/DRAWING NO. cell of the title block.
    extract._header falls back to any number-like text on the page (the P&ID number) — wrong here: a PSV prints its
    tag in that cell, a draft prints 'XX-XX-XX-XXX-XXXXX'.  Keep the header number only when it is printed in the block."""
    ex = _ex()
    head = " ".join(w[4] for w in words if w[3] <= top_y + 1)
    m = ex._DOC_RE.search(head) or ex._ANY_DOC_RE.search(head)
    if m and (not pid or schema.norm_tag(m.group(0)) != schema.norm_tag(pid)):
        hdr["doc_no"] = m.group(0)
    else:
        hdr["doc_no"] = ""
    return hdr


# ── Form 101 sheet 1 ─────────────────────────────────────────────────────────────────────────────────────────

def _bands(page, x_a, x_b):
    hz = sorted({round(y, 1) for y in _ex()._horizontals(page, x_a, x_b)})
    return [(a, b) for a, b in zip(hz, hz[1:]) if b - a > 4]


def fix_101(page, sh, words, cols):
    """Re-file the rows read_page_102 found on a Form 101 sheet 1: block caption by the ruled band the row sits in,
    keys by (label, block, heading); split 'Max / Min' values; notes boxes under the table; document number."""
    spans = _spans(page)
    row_pos = {}                                            # row number -> (column index, y)
    for ci, col in enumerate(cols):
        for w in col:
            row_pos.setdefault(int(w[4]), (ci, (w[1] + w[3]) / 2))
    blocks = []
    for ci, col in enumerate(cols):
        x_num1 = max(w[2] for w in col)
        letters = [s for s in spans if x_num1 + 1 <= s["x0"] <= x_num1 + 22 and len(s["text"]) <= 2 and s["text"][:1].isalpha()]
        bands = _bands(page, x_num1 + 4, x_num1 + 16)
        cap = []
        for a, b in bands:
            t = "".join(s["text"] for s in sorted(letters, key=lambda s: s["y0"]) if a <= (s["y0"] + s["y1"]) / 2 <= b)
            cap.append((a, b, t))
        blocks.append(cap)

    def block_of(n):
        ci, y = row_pos.get(n, (None, None))
        if ci is None:
            return ""
        return next((t for a, b, t in blocks[ci] if a <= y <= b), "")

    ctx, last_block = "", None
    for r in sorted(sh["rows"], key=lambda r: (r["row"], (r.get("label_bbox") or [0])[0])):
        blk = block_of(r["row"]) or r.get("group", "")
        if blk != last_block:
            ctx, last_block = "", blk
        if schema.norm_label(r["label"]) == "type of position indication":
            ctx = "POSIND"
        r["group"] = blk
        hit = schema.lookup_101(r["label"], blk, r.get("heading", ""), ctx if schema.norm_label(r["label"]) != "type of position indication" else "")
        if hit:
            key, sec, disp = hit
            if key == "notes_row":
                b = schema._blk(blk).lower()[:10] or "row"
                key, disp = f"notes_{b}", f"Notes ({blk.title() or 'row'})"
            r["key"], r["section"], r["display"] = key, sec, disp
            r["status"] = _status(True, r["value"])
        _tidy_value(r)
    extra = []
    for r in list(sh["rows"]):                             # 'Max / Min' and 'size / size' cells -> one field each
        extra += _split_pair(r)
    sh["rows"] += extra
    pid = next((r["value"] for r in sh["rows"] if r["key"] == "pid_no"), "")
    first_top = min(w[1] for c in cols for w in c)
    _header_doc_only(page, words, first_top - 2, sh, pid=pid)
    last_y = max(w[3] for c in cols for w in c)
    sh["notes"] = (sh.get("notes") or []) + _notes_boxes(page, words, last_y)
    sh["form"] = "101"
    return sh


_QUOTE = re.compile(r"(['‘’`])\s*(\w{1,3})\s*(['‘’`])")


def _tidy_value(r):
    if r["key"] == "ex_type" and r["value"]:                 # "Ex / ' / d / ' / / Ex ‘n’" -> "Ex 'd' / Ex ‘n’"
        v = re.sub(r"\s*/\s*", " ", r["value"])
        v = _QUOTE.sub(r"\1\2\3", v)
        v = re.sub(r"\s+", " ", v).strip()
        v = re.sub(r"(?<!or)(?<!and)\s+(?=Ex\b)", " / ", v)   # a list of types, not 'Ex n or Ex ec'
        r["value"] = re.sub(r"(?:\s*/\s*){2,}", " / ", v).strip(" /")


_PAIRS = {"design_pressure": ("design_pressure_min", "Design Pressure (Min)"),
          "design_temp": ("design_temp_min", "Design Temperature (Min)"),
          "ia_op_pressure": ("ia_op_pressure_min", "Instrument Air Operating Pressure (Min)"),
          "body_size": ("body_size_2", "Valve Size (2nd value)")}


def _split_pair(r):
    """'98 / bar-g' -> 98 (unit bar-g) · '195 / -30 / ºC' -> 195 and Min -30 · '1.5 / (VTA) / in' -> 1.5 and 2nd value VTA."""
    if r["key"] not in _PAIRS or not r["value"] or "/" not in r["value"]:
        return []
    parts = []
    for p in r["value"].split("/"):
        p = p.strip()
        w = p.split()
        if len(w) > 1 and schema.norm_label(w[-1]) in _UNITS:  # '4.5  bar-g' -> value 4.5 · unit bar-g
            parts += [" ".join(w[:-1]), w[-1]]
        else:
            parts.append(p)
    units = [p for p in parts if schema.norm_label(p) in _UNITS]
    vals = [p for p in parts if p and p not in units]
    if units and not r.get("unit"):
        r["unit"] = units[0]
    if not vals:
        r["value"] = ""
        r["status"] = "blank"
        return []
    r["value"] = vals[0]
    r["status"] = _status(True, r["value"])
    if len(vals) < 2:
        return []
    k2, d2 = _PAIRS[r["key"]]
    v2 = vals[1].strip("()")
    return [dict(r, key=k2, display=d2, value=v2, status=_status(True, v2))]


def fix_101_sheet2(sh, prev):
    """Form 101 sheet 2: sizing lines -> section 'sizing'; lines printed across Max/Nor/Min -> one value; header number
    as on sheet 1 (a draft prints no document number)."""
    keep, spans = [], {}
    for r in sh["rows"]:
        m = re.match(r"^(.*) \((Max|Nor|Min)\)$", r.get("label") or "")
        if not m:
            keep.append(r)
            continue
        base, case = schema.norm_label(m.group(1)), m.group(2).lower()
        if base in schema.SIZING_101:
            k, disp = schema.SIZING_101[base]
            keep.append(dict(r, key=f"{k}.{case}", section="sizing", display=f"{disp} ({m.group(2)})",
                             status="ok" if r["value"] else "blank"))
        elif base in schema.SPAN_101:
            spans.setdefault(base, []).append(r)
        elif r["key"].rsplit(".", 1)[0] in schema.PROPS_101:
            keep.append(dict(r, section="sizing"))             # phase-dependent property: not 'missing' when blank
        else:
            keep.append(r)
    for base, rs in spans.items():
        k, disp = schema.SPAN_101[base]
        order = {"max": 0, "nor": 1, "min": 2}
        rs.sort(key=lambda r: order[r["key"].rsplit(".", 1)[-1]])
        txt = " ".join(r["value"] for r in rs if r["value"])
        parts = [p for p in re.split(r"\s+", txt) if p and p != "/"]
        units = [p for p in parts if schema.norm_label(p) in _UNITS]
        vals = [p for p in parts if p not in units]
        bbs = [r["bbox"] for r in rs if r["value"] and r.get("bbox")]
        bb = [min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs)] if bbs else rs[0].get("bbox")
        v = " / ".join(vals)
        keep.append(dict(rs[0], key=k, section="sizing", display=disp, label=rs[0]["label"].rsplit(" (", 1)[0],
                         value=v, unit=(units[0] if units else rs[0].get("unit", "")), bbox=bb, status="ok" if v else "blank"))
    sh["rows"] = keep
    if prev:
        sh["doc_no"] = prev.get("doc_no", sh.get("doc_no", ""))
    sh["form"] = "101"
    return sh


def _notes_boxes(page, words, y_from):
    """'Common Notes :' / 'Individual Notes :' boxes under the numbered table (Forms 101 · 701)."""
    ex = _ex()
    below = [w for w in words if w[1] > y_from + 2]
    labs = {w[4].rstrip(":").lower(): w for w in below if w[4].rstrip(":").lower() in ("common", "individual")}
    if not labs:
        return []
    cut = labs["individual"][0] - 2 if "individual" in labs else page.rect.width
    top = min(w[3] for w in labs.values())
    foot = [w for w in below if re.fullmatch(r"form", w[4], re.I)]          # 'form 101_R9.02' footer stamp
    bottom = min((w[1] for w in foot), default=page.rect.height) - 1
    out = []
    for name, x_a, x_b in (("Common Notes", 0, cut), ("", cut, page.rect.width)):
        body = [w for w in below if top < (w[1] + w[3]) / 2 < bottom and x_a <= w[0] < x_b
                and w[4].rstrip(":").lower() not in ("common", "individual", "notes")]
        for n in ex._numbered(body):
            out.append(dict(n, section=name) if name else n)
    return out


# ── Form 701 (Pressure Relief Valve) ─────────────────────────────────────────────────────────────────────────

def _underlines(page, x_from):
    out = []
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] == "re":
                r = it[1]
                if r.height < 1.5 and r.width > 8 and r.x0 >= x_from - 2:
                    out.append((r.x0, r.x1, (r.y0 + r.y1) / 2))
            elif it[0] == "l":
                a, b = it[1], it[2]
                if abs(a.y - b.y) < 0.6 and abs(a.x - b.x) > 8 and min(a.x, b.x) >= x_from - 2:
                    out.append((min(a.x, b.x), max(a.x, b.x), (a.y + b.y) / 2))
    return out


def read_page_701(page, page_no, words, col):
    ex = _ex()
    spans = _spans(page)
    nums = sorted(col, key=lambda w: w[1])
    x_num1 = max(w[2] for w in nums)
    ys = [(w[1] + w[3]) / 2 for w in nums]
    pitch = sorted(b - a for a, b in zip(ys, ys[1:]))[len(ys) // 2]
    y_top, y_bot = min(w[1] for w in nums), max(w[3] for w in nums)
    # the label column ends at the first vertical rule that runs the whole numbered table, well right of the numbers
    vert = ex._verticals(page)
    cover = sorted({round(x, 1) for x, a, b in vert if a <= y_top + 2 and b >= y_bot - 2 and x > x_num1 + pitch * 4})
    x_val0 = cover[0] if cover else page.rect.width * 0.32
    x_right = cover[-1] if len(cover) > 1 else page.rect.width
    lines = [u for u in _underlines(page, x_val0) if u[1] <= x_right + 2 and y_top - 2 <= u[2] <= y_bot + pitch]   # the table only
    # the page's value-slot grid: underline starts that recur on several rows (merged when closer than a label word),
    # used for a multi-item row printed without underlines ('Adjusting Rings / Spring / Bellows')
    clusters = []
    for x in sorted(round(a, 1) for a, b, uy in lines):
        if clusters and x - clusters[-1][-1] < pitch * 3.5:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    grid = [c[0] for c in clusters if len(c) >= 3]
    hdr = ex._header(page, words, y_top - 2)
    rows, prev_label = [], ""
    for i, nw in enumerate(nums):
        n, y = int(nw[4]), ys[i]
        y0, y1 = y - pitch / 2, y + pitch / 2
        rs = [s for s in spans if y0 <= (s["y0"] + s["y1"]) / 2 < y1 and s["x0"] > x_num1 + 1]
        lab_sp = [s for s in rs if s["x0"] < x_val0 - 4 and not s["bold"] and not (len(s["text"]) <= 2 and s["text"][:1].isalpha())
                  and s["text"] != "/"]                     # caption letters and the '/' of 'S / S' are not the label
        right = sorted([s for s in rs if (s["x0"] >= x_val0 - 4 or s["bold"]) and s["text"] != "/"], key=lambda s: s["x0"])   # '/' between slots
        label = " ".join(s["text"] for s in sorted(lab_sp, key=lambda s: s["x0"])).strip()
        segs = sorted({(round(a, 1), round(b, 1)) for a, b, uy in lines if y - pitch * 0.15 <= uy <= y + pitch * 0.85})
        merged = []
        for a, b in segs:
            if merged and a <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
            else:
                merged.append((a, b))
        subs = [s for s in right if not s["bold"] and schema.norm_label(s["text"]).rstrip(":") in schema.SUB_701]
        label0 = " ".join(s["text"] for s in sorted(lab_sp, key=lambda s: s["x0"])).strip() or prev_label
        nkeys = len((schema.lookup_701(label0) or ([1],))[0])
        if not merged and len(subs) >= 2:                     # no underlines: each sub-label opens a slot
            xs = [s["x0"] for s in subs]
            merged = [(a, (xs[j + 1] - 1) if j + 1 < len(xs) else x_right) for j, a in enumerate(xs)]
        elif not merged and nkeys > 1 and len(grid) >= 2:     # no underlines, several items: the page's slot grid
            merged = [(a, (grid[j + 1] - 1) if j + 1 < len(grid) else x_right) for j, a in enumerate(grid)]
        slots = [{"x0": a, "x1": b, "vals": [], "sub": ""} for a, b in merged] or [{"x0": x_val0, "x1": x_right, "vals": [], "sub": ""}]
        for s in right:
            word = schema.norm_label(s["text"]).rstrip(":")
            cx = (s["x0"] + s["x1"]) / 2
            if not s["bold"] and word in schema.SUB_701:
                nxt = [sl for sl in slots if sl["x0"] >= s["x0"] - 3] or slots[-1:]
                nxt[0]["sub"] = schema.SUB_701[word]
                continue
            inside = [sl for sl in slots if sl["x0"] - 4 <= cx <= sl["x1"] + 4]
            tgt = inside[0] if inside else min(slots, key=lambda sl: min(abs(cx - sl["x0"]), abs(cx - sl["x1"])))
            tgt["vals"].append(s)
        if not label and not any(sl["vals"] for sl in slots) and not any(sl["sub"] for sl in slots):
            continue
        if not label and prev_label and any(sl["sub"] for sl in slots):
            label = prev_label                                 # 'Pilot' prints once for its Type/Action and Sensing/Vent rows
        prev_label = label or prev_label
        hit = schema.lookup_701(label)
        lab_bb = ex._bbox([(s["x0"], s["y0"], s["x1"], s["y1"]) for s in lab_sp])
        texts = [" ".join(v["text"] for v in sl["vals"]).strip() for sl in slots]
        # a slot holding only a unit (bar-g · ºC · kg/m³) belongs to the value slot before it
        units = [""] * len(slots)
        keep = []
        for k, sl in enumerate(slots):
            if texts[k] and schema.norm_label(texts[k]) in _UNITS:
                tgt = keep[-1] if keep else None
                if tgt is not None:
                    units[tgt] = texts[k]
                else:
                    units[k] = texts[k]
                    keep.append(k)
                    texts[k] = ""
                continue
            keep.append(k)
        if hit:
            keys, sec, disps = hit
        else:
            slug = re.sub(r"[^a-z0-9]+", "_", schema.norm_label(label)).strip("_") or f"row{n}"
            keys, sec, disps = [f"x.{slug}"], "general", [label or f"Row {n}"]
        multi = len(keys) > 1
        for j, k in enumerate(keep):
            sl = slots[k]
            if multi:
                if j >= len(keys):
                    if not texts[k]:
                        continue                               # an unused slot beyond the printed items
                    key, disp = f"raw.{n}.{j}", f"{label} ({j + 1})"
                else:
                    key, disp = keys[j], disps[j]
            elif sl["sub"]:
                key, disp = schema.SUBKEY_701.get((keys[0], sl["sub"]), (f"{keys[0]}_{sl['sub']}", f"{disps[0]} {sl['sub'].title()}"))
            elif j == 0:
                key, disp = keys[0], disps[0]
            else:
                if not texts[k]:
                    continue                                   # an empty extra slot of a one-item row (unit / 2nd case)
                key, disp = f"{keys[0]}_{j + 1}", f"{disps[0]} ({j + 1})"
            v = texts[k]
            vb = ex._bbox([(x["x0"], x["y0"], x["x1"], x["y1"]) for x in sl["vals"]]) if v else [round(sl["x0"], 1), round(y0, 1), round(sl["x1"], 1), round(y1, 1)]
            ok = bool(hit) and not key.startswith("raw.")
            rows.append({"row": n, "group": "", "label": label, "key": key, "section": sec, "display": disp, "value": v,
                         "unit": units[k], "bbox": vb, "label_bbox": lab_bb, "status": _status(ok, v)})
    tag = next((r["value"] for r in rows if r["key"] == "tag" and r["value"]), "")
    pid = next((r["value"] for r in rows if r["key"] == "pid_no"), "")
    _header_doc_only(page, words, y_top - 2, hdr, tag=tag, pid=pid)
    if tag and schema.norm_tag(hdr["doc_no"]) == schema.norm_tag(tag):
        hdr["doc_no"] = ""
    notes = _notes_boxes(page, words, y_bot)
    return {"page": page_no, **hdr, "tag": tag, "rows": rows, "notes": notes, "form": "701",
            "row_range": [int(nums[0][4]), int(nums[-1][4])]}


# ── title block at the bottom (Code 80 printed by another project) ───────────────────────────────────────────

def footer(page, words, y_from):
    """'… Sheet 1 of 2 · Code: 80 · Dwg. No.: xxxxx · Rev.:A' and revision lines in a block under the table."""
    ex = _ex()
    low = [w for w in words if w[1] >= y_from]
    out = {}
    if not low:
        return out
    def right_num(lab):
        cy = (lab[1] + lab[3]) / 2
        n = sorted((w for w in low if w[0] > lab[2] and w[1] <= cy <= w[3] and w[4].isdigit()), key=lambda w: w[0])
        return int(n[0][4]) if n else None
    for lab in (w for w in low if w[4].lower() == "sheet"):
        sh = right_num(lab)
        ofw = next((w for w in low if w[4].lower() == "of" and w[1] <= (lab[1] + lab[3]) / 2 <= w[3] and w[0] > lab[2]), None)
        of = right_num(ofw) if ofw else None
        if sh and of:
            out["sheet"], out["of"] = sh, of
            break
    for w in low:
        m = re.match(r"^Rev\.?:?([0-9A-Z]{1,2})$", w[4])
        if m:
            out["rev"] = m.group(1)
        if w[4].lower().startswith("rev") and w[4].endswith(":"):
            cy = (w[1] + w[3]) / 2
            nx = sorted((v for v in low if v[0] > w[2] and abs((v[1] + v[3]) / 2 - cy) < 3), key=lambda v: v[0])
            if nx and re.fullmatch(r"[0-9A-Z]{1,2}", nx[0][4]):
                out["rev"] = nx[0][4]
    txt = " ".join(w[4] for w in sorted(low, key=lambda w: (round(w[1]), w[0])))
    m = re.search(r"Code\s*:\s*(\d+)", txt)
    if m:
        out["code"] = m.group(1)
    m = ex._DOC_RE.search(txt) or ex._ANY_DOC_RE.search(txt)
    out["doc_no"] = m.group(0) if m else ""
    if "DATA SHEET" in txt.upper():
        t = re.search(r"DATA SHEET\s+([A-Z /&-]+?VALVE)", txt.upper())
        out["title"] = ("DATA SHEET " + t.group(1)).strip() if t else "DATA SHEET"
    hist = []
    for ln in ex._lines(low):
        s = " ".join(w[4] for w in ln)
        mm = re.match(r"^([0-9A-Z]{1,2})\s+(\S+)\s+(\d{1,2}/\d{1,2}/\d{4})\s+(.+)", s)
        if mm and "Print" not in s:
            desc = re.sub(r"\s+(Sheet\s+\d+\s+of\s+\d+|Code\s*:|Dwg\.).*$", "", mm.group(4)).strip()   # same text line as the block cells
            hist.append(" ".join([mm.group(1), mm.group(2), mm.group(3), desc]))
            if out.get("rev") == mm.group(1):
                out["date"] = mm.group(3)
    out["rev_history"] = sorted(set(hist))
    if not out.get("date") and hist:
        out["date"] = hist[-1].split()[2]
    return out


def apply_footer(page, words, hdr, y_from):
    ft = footer(page, words, y_from)
    for k in ("sheet", "of", "rev", "date", "title", "doc_no"):
        if ft.get(k) and not hdr.get(k):
            hdr[k] = ft[k]
    if ft.get("rev_history") and not hdr.get("rev_history"):
        hdr["rev_history"] = ft["rev_history"]
    return hdr


# ── a notes-only continuation sheet (Code 80 sheet 2 · Form 101/701 'form 000' notes sheet) ─────────────────

def read_continuation(page, page_no, words, prev):
    """Only when the previous datasheet page says more sheets follow and THIS page prints the next sheet number of the same
    count (and, when it prints a tag, the same tag).  Anything else is left to the caller (cover, index, general notes)."""
    ex = _ex()
    if not prev or not prev.get("of") or not prev.get("sheet") or prev["sheet"] >= prev["of"]:
        return None
    tag_w = [w for w in words if w[4] == "Tag" or w[4].startswith("Tag")]
    ind = next((w for w in words if w[4].lower().startswith("individual")), None)
    top_y = (tag_w[0][1] if tag_w else ind[1] if ind else page.rect.height * 0.15) - 1
    hdr = ex._header(page, words, top_y)
    if hdr.get("sheet") is None:
        apply_footer(page, words, hdr, page.rect.height * 0.7)
    if hdr.get("sheet") != prev["sheet"] + 1 or (hdr.get("of") and hdr["of"] != prev["of"]):
        return None
    tag = ""
    for w in tag_w:                                          # 'Tag No.   98FV  980011' (no colon on this form)
        cy = (w[1] + w[3]) / 2
        line = sorted((v for v in words if abs((v[1] + v[3]) / 2 - cy) < 3 and v[0] > w[2]), key=lambda v: v[0])
        line = [v for v in line if v[4] not in (":", "No.", "No", "No.:", "Number", "Number:")]
        if line:
            tag = " ".join(v[4] for v in line[:3])
            break
    if tag and schema.norm_tag(tag) != schema.norm_tag(prev.get("tag", "")) and not schema.norm_tag(prev.get("tag", "")).startswith(schema.norm_tag(tag)):
        return None
    labels = [w for w in words if w[4].rstrip(":").lower() in ("notes", "individual", "common")]
    if not labels:
        return None
    start = min(w[3] for w in labels)
    foot = [w for w in words if w[1] > page.rect.height * 0.6 and re.fullmatch(r"(Code:|Revision|form|Sheet)", w[4], re.I)]
    bottom = min((w[1] for w in foot), default=page.rect.height) - 1
    low_notes = [w for w in words if w[4].rstrip(":").lower() == "notes" and w[1] > start + 20 and w[1] < bottom   # a 2nd 'Notes:' caption
                 and not any(c[4].lower().startswith("common") and abs(c[1] - w[1]) < 3 for c in words)]                # (not 'Common Notes')
    bottom = min([bottom] + [w[1] - 1 for w in low_notes])
    com = next((w for w in words if w[4].rstrip(":").lower() == "common" and w[1] > start), None)
    out = []
    parts = [("", start, com[1] - 1 if com else bottom)] + ([("Common Notes", com[3], bottom)] if com else [])
    for name, a, b in parts:
        body = [w for w in words if a < (w[1] + w[3]) / 2 < b and w[4].rstrip(":").lower() not in ("individual", "common")
                and not (w[4].rstrip(":").lower() == "notes" and w[0] < page.rect.width * 0.3 and (w[1] + w[3]) / 2 < a + 12)]
        for nt in ex._numbered(body):
            out.append(dict(nt, section=name) if name else nt)
    if not out:
        return None
    hdr["doc_no"] = prev.get("doc_no", "")
    return {"page": page_no, **hdr, "tag": prev.get("tag", ""), "rows": [], "notes": out,
            "form": prev.get("form"), "continuation": True}
