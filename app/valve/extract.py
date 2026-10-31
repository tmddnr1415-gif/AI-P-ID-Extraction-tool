"""Valve Datasheet — deterministic extraction from the PDF text layer (PyMuPDF).

No OCR and no LLM here.  A datasheet page is a ruled table: the row numbers sit in a narrow column,
the ruling lines are in the drawing layer.  For every numbered row we take the vertical rules that
cross it, cut the row into cells, and read each cell's words.  Cells left of the value column are
labels, cells right of it are values; two labels pair with the left / right halves of the value
area.  Every value keeps its page and box so the screen can show where it was read.

A value that cannot be paired with a label is kept as a raw row (status `review`), never guessed.
Scanned pages (no text layer) come back with `scanned=True` and no fields: the screen says so.

Output of `read_pdf(path)`:
  {"pages": n, "sheets": [Sheet...], "docs": {doc_no: {"general_notes": {...}, "index": [...]}}, "other_pages": [...]}
  Sheet = {"page", "doc_no", "rev", "sheet", "of", "title", "date", "rev_history", "tag", "rows": [Row],
           "notes": [{"no", "text", "bbox"}], "group": caption}
  Row   = {"row", "group", "label", "key", "section", "value", "unit", "bbox", "status"}
"""
from __future__ import annotations

import re
from collections import Counter

import pymupdf

from app.valve import schema

_DOC_RE = re.compile(r"\b\d{2,3}-\d{2}-IN-DTS-\d{5}\b")
_LOOSE_DOC = re.compile(r"\d{2,3}-\d{2}-[A-Z]{2}-[A-Z]{2,4}-\d{1,6}")   # as printed, typos included
_ANY_DOC_RE = re.compile(r"\b[0-9A-Z]{2,5}-[0-9A-Z]{2,4}-[A-Z]{2}-[A-Z]{3}-\d{5}\b")
_NOTE_REF = re.compile(r"(gen(?:eral|\.)?\s*note|note)\s*[-–:#]?\s*(\d+)", re.I)


# ── geometry helpers ────────────────────────────────────────────────────────────

# Narrowest empty space between two vertical rules that still counts as a cell.  Measured, not chosen
# (P&ID principle: a threshold only inside an empty band of the distribution): on the 456-page sample every
# space is 5–7 pt (double rules) or ≥ 21 pt (cells), nothing in 8–20 pt.  spike/valve_eval.py re-measures the
# band on every document it is given and says so when a new form puts widths inside it.
DOUBLE_RULE_GAP = 9.0

def _verticals(page):
    """Vertical rules as (x, y0, y1).  Lines and thin rectangles; a rectangle gives both sides."""
    out = []
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] == "l":
                a, b = it[1], it[2]
                if abs(a.x - b.x) < 0.8 and abs(a.y - b.y) > 3:
                    out.append((a.x, min(a.y, b.y), max(a.y, b.y)))
            elif it[0] == "re":
                r = it[1]
                if r.height > 3:
                    if r.width < 1.5:
                        out.append(((r.x0 + r.x1) / 2, r.y0, r.y1))
                    else:
                        out.append((r.x0, r.y0, r.y1))
                        out.append((r.x1, r.y0, r.y1))
    return out


def _horizontals(page, x_a, x_b):
    """y of horizontal rules that span the x range [x_a, x_b]."""
    out = []
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] == "l":
                a, b = it[1], it[2]
                if abs(a.y - b.y) < 0.8 and min(a.x, b.x) <= x_a and max(a.x, b.x) >= x_b:
                    out.append(a.y)
            elif it[0] == "re":
                r = it[1]
                if r.x0 <= x_a and r.x1 >= x_b:
                    out += [r.y0, r.y1] if r.height > 1.5 else [(r.y0 + r.y1) / 2]
    return out


def _xs_at(vert, y, x_min, x_max):
    xs = sorted(x for x, y0, y1 in vert if y0 - 0.5 <= y <= y1 + 0.5 and x_min - 2 <= x <= x_max + 2)
    merged = []
    for x in xs:                      # double rules (313/316, 436/439/441) are one boundary
        if merged and x - merged[-1] < 5:
            continue
        merged.append(x)
    return merged


def _lines(words):
    """Words → lines.  A word joins a line when its vertical centre lies inside that line's own height — no fixed
    bucket (a 3-pt bucket split 'SWAGELOK (General Note - 7)' whose words sit 0.9 pt apart; P&ID failure type ④)."""
    lines = []
    for w in sorted(words, key=lambda w: (w[1] + w[3]) / 2):
        c = (w[1] + w[3]) / 2
        if lines and lines[-1][0] <= c <= lines[-1][1]:
            ln = lines[-1]
            ln[2].append(w)
            ln[0], ln[1] = min(ln[0], w[1]), max(ln[1], w[3])
        else:
            lines.append([w[1], w[3], [w]])
    return [sorted(ln[2], key=lambda w: w[0]) for ln in lines]


def _text(words):
    return " ".join(w[4] for ln in _lines(words) for w in ln).strip()


def _bbox(words):
    if not words:
        return None
    return [round(min(w[0] for w in words), 1), round(min(w[1] for w in words), 1),
            round(max(w[2] for w in words), 1), round(max(w[3] for w in words), 1)]


def _row_numbers(words, page_w):
    """Words that are the row index column: integers, aligned in one narrow x band, mostly consecutive."""
    cands = [w for w in words if w[4].isdigit() and 1 <= int(w[4]) <= 99 and w[2] < page_w * 0.4]
    if not cands:
        return []
    band = Counter(round(w[2] / 4) for w in cands).most_common(1)[0][0]   # right-aligned numbers share x1
    col = [w for w in cands if abs(round(w[2] / 4) - band) <= 1]
    col.sort(key=lambda w: w[1])
    nums = [int(w[4]) for w in col]
    if len(col) < 8 or sum(1 for a, b in zip(nums, nums[1:]) if b == a + 1) < len(col) * 0.7:
        return []
    return col


def _number_columns(words):
    """Columns of consecutive row numbers (Form 102 has two: 1-52 left, 53-100 right)."""
    cands = [w for w in words if w[4].isdigit() and 1 <= int(w[4]) <= 120]
    groups, cur = [], None
    for w in sorted(cands, key=lambda w: (w[0] + w[2]) / 2):
        cx = (w[0] + w[2]) / 2
        if cur and cx - cur[-1] < 4:
            cur[-1] = cx
            groups[-1].append(w)
        else:
            cur = [cx]
            groups.append([w])
    out = []
    for col in groups:
        col = sorted(col, key=lambda w: w[1])
        nums = [int(w[4]) for w in col]
        if len(col) >= 20 and sum(1 for a, b in zip(nums, nums[1:]) if b == a + 1) >= len(col) * 0.8:
            out.append(col)
    return out


# ── one page ────────────────────────────────────────────────────────────────────

def _header(page, words, top_y):
    """Title block above the table: DOCUMENT NO. · SHEET x OF y · REV. · DATE · title · revision lines."""
    full = page.get_text()
    head = [w for w in words if w[3] <= top_y + 1]
    doc = _DOC_RE.search(full) or _ANY_DOC_RE.search(full)
    out = {"doc_no": doc.group(0) if doc else "", "rev": "", "sheet": None, "of": None, "date": "", "title": "",
           "rev_history": []}
    lab = next((w for w in head if w[4].upper().startswith("DOCUMENT")), None)
    if lab:                                                 # the number printed in the DOCUMENT NO. cell itself
        below = sorted((w for w in head if w[1] >= lab[3] - 1 and w[0] < lab[2] + (lab[2] - lab[0]) and
                        w[2] > lab[0] - (lab[2] - lab[0]) and _LOOSE_DOC.fullmatch(w[4])), key=lambda w: w[1])
        if below:
            out["doc_no_printed"] = below[0][4]
            if _DOC_RE.fullmatch(below[0][4]) or _ANY_DOC_RE.fullmatch(below[0][4]):
                out["doc_no"] = below[0][4]

    def right_of(label, maxdx=200):
        lab = [w for w in head if w[4].upper().rstrip(".") == label]
        if not lab:
            return ""
        l = lab[0]
        cy = (l[1] + l[3]) / 2
        same = [w for w in head if abs((w[1] + w[3]) / 2 - cy) < 3 and l[2] < w[0] < l[2] + maxdx]
        return _text(same)

    out["rev"] = right_of("REV", 120).split(" ")[0] if right_of("REV", 120) else ""
    for lab in [w for w in head if w[4].upper().rstrip(".:") == "DATE"]:   # the DATE label followed by a date
        cy = (lab[1] + lab[3]) / 2
        nxt = [w for w in head if abs((w[1] + w[3]) / 2 - cy) < 3 and lab[2] < w[0] < lab[2] + 120
               and re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2,4}", w[4])]
        if nxt:
            out["date"] = nxt[0][4]
            break
    m = re.search(r"SHEET\s+(\d+)\s+OF\s+(\d+)", " ".join(w[4] for w in sorted(head, key=lambda w: (round(w[1]), w[0]))))
    if not m:
        sh, of = right_of("SHEET", 120), right_of("OF", 60)
        if sh.split() and sh.split()[0].isdigit():
            out["sheet"] = int(sh.split()[0])
        if of.split() and of.split()[0].isdigit():
            out["of"] = int(of.split()[0])
    else:
        out["sheet"], out["of"] = int(m.group(1)), int(m.group(2))
    hmax = max((w[3] - w[1] for w in head), default=0)       # the form title is the largest type in the block
    out["title"] = _text([w for w in head if (w[3] - w[1]) > hmax - 1.5]) if hmax > 11 else ""
    for w in head:                                          # revision lines: '<rev> <by> <d/m/yyyy> <description>'
        if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", w[4]):
            cy = (w[1] + w[3]) / 2
            line = sorted([v for v in head if abs((v[1] + v[3]) / 2 - cy) < 2.5], key=lambda v: v[0])
            txt = " ".join(v[4] for v in line)
            if re.match(r"^[0-9A-Z]{1,2}\s+\S+\s+\d", txt) and "Print" not in txt:
                out["rev_history"].append(txt)
    out["rev_history"] = sorted(set(out["rev_history"]))
    return out


_HIDDEN_CACHE: dict = {}


def _hidden_boxes(page):
    """Text the eye cannot see: a span painted over later by an opaque fill (a white box left on an Excel drop-down —
    'N/A or other' under the Fluid State cell; a '4' under the '2' of 'SHEET 1 OF 2').  Judged from the page's own
    drawing order (seqno), no fixed value.  Returns [(hidden spans, visible spans)] as (x0,y0,x1,y1,text) — [] if none."""
    key = (id(page.parent), page.number, page.rect.width)
    if key in _HIDDEN_CACHE:
        return _HIDDEN_CACHE[key]
    spans = []
    for sp in page.get_texttrace():
        x0, y0, x1, y1 = sp["bbox"]
        m = (y1 - y0) * 0.25                                 # the glyphs' own height, not a page constant
        spans.append((x0, y0, x1, y1, x0 + m, y0 + m, x1 - m, y1 - m, sp["seqno"], "".join(chr(c[0]) for c in sp["chars"])))
    hmin = min((s[7] - s[5] for s in spans if s[7] > s[5]), default=0)
    fills = [(r.x0, r.y0, r.x1, r.y1, d["seqno"]) for d in page.get_drawings()
             if d.get("fill") is not None and (d.get("fill_opacity") or 1) >= 1
             for r in (d["rect"],) if r.height >= hmin and r.width > 0]   # a ruling line cannot cover a glyph
    hidden, shown = [], []
    for x0, y0, x1, y1, c0, c1, c2, c3, seq, t in spans:
        cover = c2 > c0 and c3 > c1 and any(sq > seq and fx0 <= c0 and fy0 <= c1 and fx1 >= c2 and fy1 >= c3
                                             for fx0, fy0, fx1, fy1, sq in fills)
        (hidden if cover else shown).append((x0, y0, x1, y1, t))
    out = [(hidden, shown)] if hidden else []
    if len(_HIDDEN_CACHE) > 64:
        _HIDDEN_CACHE.clear()
    _HIDDEN_CACHE[key] = out
    return out


def _visible(items, hidden, box=lambda w: w[:4], text=lambda w: w[4]):
    """Drop a word / span only when every span that could have printed it is hidden (place + text): a visible '2'
    printed over a hidden '4' — or over a hidden '2' — stays, once."""
    if not hidden:
        return items
    hid, shown = hidden[0]
    inside = lambda r, cx, cy: r[0] <= cx <= r[2] and r[1] <= cy <= r[3]   # noqa: E731
    keep = []
    for it in items:
        x0, y0, x1, y1 = box(it)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        t = text(it).strip()
        if t and any(inside(h, cx, cy) and t in h[4] for h in hid):
            if not any(inside(r, cx, cy) and t in r[4] for r in shown):
                continue                                     # only hidden spans print it
            if any(text(k).strip() == t and inside(box(k), cx, cy) for k in keep):
                continue                                     # a hidden 'NA' under a visible 'NA' prints once
        keep.append(it)
    return keep


def read_page(page, page_no: int):
    words = _visible(page.get_text("words"), _hidden_boxes(page))
    if not words:
        return {"page": page_no, "scanned": True}
    cols = _number_columns(words)
    if len(cols) >= 2 or (len(cols) == 1 and _colon_rows(words, cols[0])):
        return read_page_102(page, page_no, words, cols)
    nums = _row_numbers(words, page.rect.width)
    if not nums:
        return read_notes_page(page, page_no, words)
    if {"Max", "Nor", "Min", "Unit"} <= {w[4] for w in words}:
        return read_process_table(page, page_no, words, nums)
    vert = _verticals(page)
    x_num1 = max(w[2] for w in nums)
    x_right = max((x for x, *_ in vert), default=page.rect.width)
    ys = [((w[1] + w[3]) / 2) for w in nums]
    gaps = [b - a for a, b in zip(ys, ys[1:])]
    pitch = sorted(gaps)[len(gaps) // 2] if gaps else 12

    # value column = the boundary right of the label cells that most rows share (≈ x 313/316 on this form)
    starts = Counter()
    for y in ys:
        for x in _xs_at(vert, y, x_num1, x_right):
            if x > x_num1 + 40:
                starts[round(x / 6)] += 1
    common = sorted(k * 6 for k, c in starts.items() if c >= len(ys) * 0.6)
    x_val = next((x for x in common if x > x_num1 + 100), common[0] if common else page.rect.width * 0.5)
    mids = [x for x in common if x_val + 40 < x < x_right - 40]
    x_mid = mids[0] if mids else (x_val + x_right) / 2

    # group captions (GENERAL, PIPE DATA, ...) sit left of the row numbers, one per band between the
    # horizontal rules of that column.  A row belongs to the band it is in.
    x_cap0 = min((x for x, *_ in vert), default=0)
    captions = [w for w in words if x_cap0 - 2 <= w[0] and w[2] < x_num1 - 12 and re.fullmatch(r"[A-Z/&.]+", w[4])]
    hz = sorted({round(y, 1) for y in _horizontals(page, x_cap0 + 5, x_num1 - 15)})
    bands = [(a, b) for a, b in zip(hz, hz[1:]) if b - a > 4]

    def caption(y):
        for a, b in bands:
            if a <= y <= b:
                return _text([w for w in captions if a <= (w[1] + w[3]) / 2 <= b])
        return ""

    hdr = _header(page, words, min(w[1] for w in nums) - 2)
    rows, used = [], set(id(w) for w in nums)
    for i, nw in enumerate(nums):
        y = ys[i]
        y0 = (ys[i - 1] + y) / 2 if i else y - pitch / 2
        y1 = (ys[i + 1] + y) / 2 if i + 1 < len(ys) else y + pitch / 2
        bounds = [x for x in _xs_at(vert, y, x_num1, x_right) if x > x_num1 + 1]
        if not bounds or bounds[0] > x_num1 + 12:
            bounds = [x_num1 + 2] + bounds
        rw = [w for w in words if id(w) not in used and y0 <= (w[1] + w[3]) / 2 < y1 and w[0] >= x_num1]
        cells = []
        for a, b in zip(bounds, bounds[1:]):
            cw = [w for w in rw if a - 1 <= (w[0] + w[2]) / 2 < b]
            if b - a < DOUBLE_RULE_GAP and not cw:         # the gap between a double rule is not a cell
                continue
            cells.append({"x0": a, "x1": b, "words": cw, "text": _text(cw)})
        labels = [c for c in cells if c["x1"] <= x_val + 4 and c["text"]]
        vals = [c for c in cells if c["x0"] >= x_val - 4]
        left = [c for c in vals if (c["x0"] + c["x1"]) / 2 < x_mid]
        right = [c for c in vals if (c["x0"] + c["x1"]) / 2 >= x_mid]
        group = caption(y)
        n = int(nw[4])
        if len(labels) == 1:
            pairs = [(labels[0], vals)]
        elif len(labels) == 2:
            pairs = [(labels[0], left), (labels[1], right)]
        elif len(labels) == 3 and labels[1]["text"].lower() in ("min", "open") or (
                len(labels) == 3 and labels[2]["text"].lower() in ("max", "closed")):
            pairs = [(labels[0], []), (labels[1], left), (labels[2], right)]
        elif len(labels) > 2 and len(vals) == len(labels):          # one value cell under each label
            pairs = [(l, [v]) for l, v in zip(labels, vals)]
        elif len(labels) > 2 and len([v for v in vals if v["text"]]) == len(labels):
            pairs = [(l, [v]) for l, v in zip(labels, [v for v in vals if v["text"]])]
        else:
            pairs = []
        if not pairs and not labels and not any(c["text"] for c in vals):
            continue                                        # spare row (19, 20): nothing printed, nothing to read
        if not pairs:                                       # label/value counts do not line up: keep as raw
            txt = " | ".join(c["text"] for c in vals if c["text"])
            rows.append({"row": n, "group": group, "label": " / ".join(c["text"] for c in labels),
                         "key": f"raw.{n}", "section": "general", "display": f"Row {n} (raw)",
                         "value": txt, "unit": "", "bbox": _bbox([w for c in vals for w in c["words"]]),
                         "status": "review" if txt else "blank"})
            continue
        for k, (lab, vcells) in enumerate(pairs):
            hit = schema.lookup(lab["text"], group)
            vw = [w for c in vcells for w in c["words"]]
            texts = [c["text"] for c in vcells if c["text"]]
            is_unit = [schema.norm_label(t) in schema.UNIT_TOKENS for t in texts]
            if sum(1 for u in is_unit if not u) <= 1:      # '10 | bar-g' -> value 10, unit bar-g
                unit = next((t for t, u in zip(texts, is_unit) if u), "")
                parts = [t for t, u in zip(texts, is_unit) if not u]
            else:                                           # '2 | in | sch. | 40S' reads as written
                unit, parts = "", texts
            value = " ".join(parts).strip()
            if not value and unit and len(vcells) == 1:
                value, unit = "", unit
            key, sec, disp = hit if hit else (f"raw.{n}.{k}", "general", lab["text"])
            status = "ok" if value else "blank"
            if not hit:
                status = "review"
            elif value and schema.norm_label(value) in schema.PLACEHOLDERS:
                status = "placeholder"
            rows.append({"row": n, "group": group, "label": lab["text"], "key": key, "section": sec, "display": disp,
                         "value": value, "unit": unit, "bbox": _bbox(vw) or [vcells[0]["x0"], y0, vcells[-1]["x1"], y1] if vcells else None,
                         "label_bbox": _bbox(lab["words"]), "status": status})

    tag = next((r["value"] for r in rows if r["key"] == "tag" and r["value"]), "")
    if not any(r["key"] == "tag" for r in rows) and (not hdr["title"] or hdr["sheet"] is None):
        return None                                         # a numbered list that is not a datasheet (index page)
    # NOTES block (sheet 2): numbered paragraphs below the 'NOTES' caption
    notes = []
    nlab = [w for w in words if w[4].upper().startswith("NOTES")]
    if nlab:
        top = nlab[0][3]
        frame = [y for y in _horizontals(page, nlab[0][0], nlab[0][2]) if y > top]   # the notes box's own rules
        bottom = max(frame) if frame else page.rect.height  # the page footer ('Page 53 of 569') is outside the box
        body = [w for w in words if top - 1 < w[1] and w[3] <= bottom + 1 and w[0] > nlab[0][0] - 25 and id(w) not in used
                and not (min(ys) - 2 <= (w[1] + w[3]) / 2 <= max(ys) + pitch)]
        notes = _numbered(body)
    return {"page": page_no, **hdr, "tag": tag, "rows": rows, "notes": notes,
            "row_range": [int(nums[0][4]), int(nums[-1][4])]}


_UNIT_LIKE = re.compile(r"^(?:[A-Za-zº°%/µ]{1,4}|/)$")


def _stacks(spans, x_a, x_b):
    """Vertical letter captions ('T A G', 'V A L V E  G E N.') between x_a and x_b -> [(y0, y1, text)]."""
    let = sorted([s for s in spans if x_a <= s["x0"] <= x_b and len(s["text"]) <= 2 and s["text"][:1].isalpha()],
                 key=lambda s: s["y0"])
    out, cur = [], None
    for s in let:
        if cur and s["y0"] - cur[1] < 4.5:
            cur[1] = s["y1"]
            cur[2] += s["text"]
        else:
            cur = [s["y0"], s["y1"], s["text"]]
            out.append(cur)
    merged = []
    for st in out:                                           # 'VALVE' + 'GEN.' one blank line apart = one caption
        if merged and st[0] - merged[-1][1] < 9:
            merged[-1] = [merged[-1][0], st[1], merged[-1][2] + " " + st[2]]
        else:
            merged.append(list(st))
    return [tuple(m) for m in merged]


def _tag_beside(words):
    """'Tag No. : 315MOV 980004' / 'Tag Number : …' read by position (the text order differs per sheet)."""
    for w in words:
        if w[4] != "Tag":
            continue
        cy = (w[1] + w[3]) / 2
        line = sorted([v for v in words if abs((v[1] + v[3]) / 2 - cy) < 3 and v[0] >= w[0]], key=lambda v: v[0])
        if len(line) < 2 or not line[1][4].startswith(("No", "Number")):
            continue
        rest = [v for v in line[2:] if v[4] not in (":", ".:")]
        if line[1][4].endswith(":") or (len(line) > 2 and line[2][4] in (":", ".:")):
            out, last = [], line[1][2]
            for v in rest:
                if v[0] - last > 60:
                    break
                out.append(v[4])
                last = v[2]
            if out and re.match(r"^\d", out[0]):
                return " ".join(out)
    return ""


def _colon_rows(words, col) -> bool:
    """Form 102 writes 'Label : value' on each numbered row; the On/Off form puts labels and values in ruled cells.
    True when most numbered rows carry a ':' (a single-column Form 102 sheet, e.g. MOV sheet 2)."""
    lines = _lines([w for w in words if w[0] > max(n[2] for n in col)])
    hits = 0
    for n in col:
        cy = (n[1] + n[3]) / 2
        ln = next((ln for ln in lines if min(w[1] for w in ln) <= cy <= max(w[3] for w in ln)), [])
        hits += any(w[4].endswith(":") or w[4] == ":" for w in ln)
    return hits >= len(col) / 2


def read_page_102(page, page_no, words, cols):
    """Form 102 (e.g. Motor Operated Valve): numbered rows in two columns, 'Label : value' with bold values."""
    spans = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            for sp in ln["spans"]:
                t = sp["text"].strip()
                if t:
                    x0, y0, x1, y1 = sp["bbox"]
                    spans.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "text": t,
                                  "bold": bool(sp["flags"] & 16) or "Bold" in sp["font"]})
    spans = _visible(spans, _hidden_boxes(page), box=lambda s: (s["x0"], s["y0"], s["x1"], s["y1"]),
                     text=lambda s: s["text"])
    first_top = min(w[1] for c in cols for w in c)
    hdr = _header(page, words, first_top - 2)
    rows, notes = [], []
    x_page = page.rect.width
    for ci, col in enumerate(cols):
        x_num1 = max(w[2] for w in col)
        x_next = (min(w[0] for w in cols[ci + 1]) - 2) if ci + 1 < len(cols) else x_page
        next_ys = [(w[1] + w[3]) / 2 for w in cols[ci + 1]] if ci + 1 < len(cols) else []
        stacks = _stacks(spans, x_num1 + 1, x_num1 + 22)
        x_lab = x_num1 + 22 if stacks else x_num1 + 2
        ys = [(w[1] + w[3]) / 2 for w in col]
        pitch = sorted(b - a for a, b in zip(ys, ys[1:]))[len(ys) // 2]
        heading = ""
        for i, nw in enumerate(col):
            y = ys[i]
            y0, y1 = y - pitch / 2, y + pitch / 2
            # a row the next column does not number ('Instrument Type : …' beside rows 1-4) belongs to this row
            x_end = x_next if any(y0 <= ny < y1 for ny in next_ys) or not next_ys else x_page
            group = next((t for a, b, t in stacks if a - pitch * 0.6 <= y <= b + pitch * 0.6), "")
            if not group and stacks:
                group = min(stacks, key=lambda st: min(abs(y - st[0]), abs(y - st[1])))[2]
            row_sp = sorted([s for s in spans if y0 <= (s["y0"] + s["y1"]) / 2 < y1 and x_lab - 4 <= s["x0"] < x_end
                             and not (s["x0"] < x_num1 + 22 and len(s["text"]) <= 2 and s["text"][:1].isalpha())],
                            key=lambda s: s["x0"])
            pairs, lab, val, pre = [], None, [], []
            for sp in row_sp:
                t = sp["text"]
                if sp["bold"]:
                    if lab is None:
                        lab = {"text": " ".join(x["text"] for x in pre), "sp": pre}
                        pre = []
                    val.append(sp)
                    continue
                if ":" in t:
                    if lab is not None:
                        pairs.append((lab, val))
                    head, _, tail = t.partition(":")
                    lab = {"text": " ".join([x["text"] for x in pre] + [head]).strip(), "sp": pre + [sp]}
                    pre, val = [], []
                    if tail.strip():                     # 'Material: SS' printed in one span
                        val.append(dict(sp, text=tail.strip()))
                elif lab is not None and val and (_UNIT_LIKE.match(t) or schema.norm_label(t) in schema.UNIT_TOKENS):
                    val.append(dict(sp, unit=True))
                else:
                    pre.append(sp)
            if lab is not None:
                pairs.append((lab, val))
            if not pairs and pre:                         # a bare caption row ('Line', 'Enclosure', 'Material')
                heading = " ".join(x["text"] for x in pre).rstrip(":")
                if heading.lower().startswith("notes"):
                    heading = ""
                continue
            for k, (lab, vsp) in enumerate(pairs):
                text = lab["text"].strip()
                unit = " ".join(x["text"] for x in vsp if x.get("unit") and x["text"] != "/")
                value = " ".join(x["text"] for x in vsp if not x.get("unit")).strip()
                if " / " in " ".join(x["text"] for x in vsp):
                    value = " / ".join(x["text"] for x in vsp if not x.get("unit") and x["text"] != "/")
                if value and schema.norm_label(value) in schema.UNIT_TOKENS:
                    value, unit = "", value
                hit = schema.lookup_102(text, group, heading)
                key, sec, disp = hit if hit else ("x." + re.sub(r"[^a-z0-9]+", "_", schema.norm_label(text)).strip("_"),
                                                   "general", text)
                status = "ok" if value else "blank"
                if value and schema.norm_label(value) in schema.PLACEHOLDERS:
                    status = "placeholder"
                bb = _bbox([(x["x0"], x["y0"], x["x1"], x["y1"]) for x in vsp]) or \
                    _bbox([(x["x0"], x["y0"], x["x1"], x["y1"]) for x in lab["sp"]])
                rows.append({"row": int(nw[4]), "group": group, "label": text, "key": key, "section": sec,
                             "display": disp, "value": value, "unit": unit, "bbox": bb,
                             "label_bbox": _bbox([(x["x0"], x["y0"], x["x1"], x["y1"]) for x in lab["sp"]]),
                             "status": status, "heading": heading})
    tag = next((r["value"] for r in rows if r["key"] == "tag" and r["value"]), "")
    if not tag:                                           # later sheets repeat 'Tag No. : …' above the body
        tag = _tag_beside(words)
    return {"page": page_no, **hdr, "tag": tag, "rows": rows, "notes": notes, "form": "102",
            "row_range": [int(cols[0][0][4]), int(cols[-1][-1][4])]}


_PROC_KEYS = {"phase": ("fluid_state", "Fluid State"), "fluid name": ("fluid", "Fluid"),
              "flow rate": ("flow", "Flow Rate"), "upstream pressure": ("inlet_pressure", "Inlet (Upstream) Pressure"),
              "downstream pressure": ("outlet_pressure", "Outlet (Downstream) Pressure"),
              "temperature": ("op_temp", "Operating Temperature"), "density @ condition": ("density", "Density"),
              "molecular weight": ("mol_weight", "Molecular Weight"), "viscosity": ("viscosity", "Viscosity"),
              "vapour pressure": ("vapor_pressure", "Vapor Pressure"), "critical pressure": ("critical_pressure", "Critical Pressure"),
              "specific heat ratio": ("cp_cv", "Specific Heat Ratio"), "compressibility factor": ("z_factor", "Compressibility Factor")}


def read_process_table(page, page_no, words, nums):
    """Process-condition sheet: rows × (Unit · Max · Nor · Min).  Each case is its own field (flow.max …)."""
    hdr_w = {}
    for u in (w for w in words if w[4] == "Unit"):         # the header line is the one that has all four words
        cy = (u[1] + u[3]) / 2
        line = {w[4]: w for w in words if abs((w[1] + w[3]) / 2 - cy) < 3 and w[4] in ("Unit", "Max", "Nor", "Min")}
        if len(line) == 4:
            hdr_w = line
            break
    if len(hdr_w) < 4:
        return None
    order = sorted(hdr_w, key=lambda k: hdr_w[k][0])
    cx = [(hdr_w[k][0] + hdr_w[k][2]) / 2 for k in order]
    edges = [cx[0] - (cx[1] - cx[0]) / 2] + [(a + b) / 2 for a, b in zip(cx, cx[1:])] + [page.rect.width]
    colx = {k: (edges[i], edges[i + 1]) for i, k in enumerate(order)}
    x_num1 = max(w[2] for w in nums)
    lab_x1 = colx["Unit"][0]
    hdr = _header(page, words, min(w[1] for w in nums) - 2)
    ys = [(w[1] + w[3]) / 2 for w in nums]
    pitch = sorted(b - a for a, b in zip(ys, ys[1:]))[len(ys) // 2]
    rows = []
    for i, nw in enumerate(nums):
        y = ys[i]
        rw = [w for w in words if abs((w[1] + w[3]) / 2 - y) < pitch / 2 and w[0] > x_num1 + 2
              and not (w[0] < x_num1 + 22 and len(w[4]) <= 2)]
        lab = _text([w for w in rw if w[2] <= lab_x1 + 1])
        if any(w[4].endswith(":") or w[4] == ":" for w in rw):   # 'Tag No.: … Instrument Type : …' repeated from sheet 1
            for lab2, vws in _colon_pairs(rw):
                hit = schema.lookup_102(lab2, "", "")
                key, sec, disp = hit if hit else ("x." + re.sub(r"[^a-z0-9]+", "_", schema.norm_label(lab2)).strip("_"),
                                                   "general", lab2)
                v = _text(vws)
                rows.append({"row": int(nw[4]), "group": "", "label": lab2, "key": key, "section": sec, "display": disp,
                             "value": v, "unit": "", "bbox": _bbox(vws) or _bbox(rw), "label_bbox": None,
                             "status": "ok" if v else "blank"})
            continue
        if not lab or lab.startswith("Process Condition"):
            continue
        n = schema.norm_label(lab)
        key, disp = _PROC_KEYS.get(n, ("x." + re.sub(r"[^a-z0-9]+", "_", n).strip("_"), lab))
        unit = _text([w for w in rw if colx["Unit"][0] <= (w[0] + w[2]) / 2 < colx["Unit"][1]])
        for case in ("Max", "Nor", "Min"):
            a, b = colx[case]
            vw = [w for w in rw if a <= (w[0] + w[2]) / 2 < b]
            if vw and all(w[4] == "/" or _UNIT_LIKE.match(w[4]) or schema.norm_label(w[4]) in schema.UNIT_TOKENS
                          for w in vw):
                vw = []                                      # only the printed unit / '/' of an empty '__ / __ bar-g' cell
            v = _text(vw)
            rows.append({"row": int(nw[4]), "group": "PROCESS", "label": f"{lab} ({case})", "key": f"{key}.{case.lower()}",
                         "section": "process", "display": f"{disp} ({case})", "value": v, "unit": unit,
                         "bbox": _bbox(vw) or [a, y - pitch / 2, b, y + pitch / 2], "label_bbox": None,
                         "status": "ok" if v else "blank"})
    return {"page": page_no, **hdr, "tag": _tag_beside(words), "rows": rows, "notes": [], "form": "process-table"}


def _colon_pairs(words):
    """'Tag No.: 98MOV 980001   Instrument Type : Motor Operated …' → [(label, value words)].  Words are cut into
    runs where the gap is wider than the text's own height (a column gap, not a word space); a run ending in ':' is
    a label, the runs after it up to the next label are its value."""
    ws = sorted(words, key=lambda w: w[0])
    if not ws:
        return []
    h = sorted(w[3] - w[1] for w in ws)[len(ws) // 2]
    runs, cur = [], [ws[0]]
    for a, b in zip(ws, ws[1:]):
        if b[0] - a[2] > h:
            runs.append(cur)
            cur = []
        cur.append(b)
    runs.append(cur)
    out, lab = [], None
    for r in runs:
        r = sorted(r, key=lambda w: w[0])
        k = next((i for i, w in enumerate(r) if w[4].endswith(":")), None)
        if k is None:
            if lab is not None:
                lab[1] += r
            continue
        lab = [_text(r[:k + 1]).rstrip(":").strip(), list(r[k + 1:])]   # 'Instrument Type : Motor …' in one run
        out.append(lab)
    return [(a, b) for a, b in out if a]


def read_notes_page(page, page_no, words):
    """A continuation sheet that is only numbered notes under 'Tag Number : …' (Form 102 sheet 3)."""
    full = page.get_text()
    tag = _tag_beside(words)
    if not tag:
        return None
    tag_w = [w for w in words if w[4].startswith("Tag")]
    top = tag_w[0][3] + 2 if tag_w else 0
    hb = [w for w in words if w[4] in ("INSTRUMENT", "Revision")]
    bottom = min((w[1] for w in hb), default=page.rect.height) - 2
    body = [w for w in words if top < w[1] < bottom]
    notes = _numbered(body)
    if len(notes) < 2:
        return None
    hdr = _header(page, words, page.rect.height)          # this form's title block is at the bottom
    dn = _DOC_RE.search(full)
    sh = re.search(r"Sheet\s+(\d+)\s+of\s+(\d+)", full)
    sheet, of = (int(sh.group(1)), int(sh.group(2))) if sh else (None, None)
    if sh is None:                                         # 'Sheet | 3 | of | 3' in separate title-block cells
        def num_right(lab):
            cy = (lab[1] + lab[3]) / 2
            n = sorted((w for w in words if w[0] > lab[2] and w[1] <= cy <= w[3] and w[4].isdigit()), key=lambda w: w[0])
            return int(n[0][4]) if n else None
        for lab in (w for w in words if w[4] == "Sheet"):
            sheet = num_right(lab)
            ofw = next((w for w in words if w[4].lower() == "of" and w[1] <= (lab[1] + lab[3]) / 2 <= w[3]
                        and w[0] > lab[2]), None)
            of = num_right(ofw) if ofw else None
            if sheet and of:
                break
    hdr.update({"doc_no": dn.group(0) if dn else hdr["doc_no"], "sheet": sheet, "of": of})
    return {"page": page_no, **hdr, "tag": tag, "rows": [], "notes": notes, "form": "102",
            "continuation": True}


def _numbered(words):
    """Group words into lines, then lines into '1. …' '2. …' paragraphs (the paragraph keeps its box)."""
    out, cur, section = [], None, ""
    for ws in _lines(words):                             # lines by the words' own height, not a 2.5-pt bucket
        txt = " ".join(w[4] for w in ws)
        if txt.upper().startswith("NOTES"):
            txt = txt[5:].lstrip(" :")
            ws = ws[1:] if ws and ws[0][4].upper().startswith("NOTES") else ws
            if not txt:
                continue
        if re.fullmatch(r"[A-Z][A-Z /&-]{1,24}:", txt.strip()):   # 'HOLD:' — a new list starts, not part of the note
            section, cur = txt.strip().rstrip(":"), None
            continue
        nxt = cur["no"] + 1 if cur else None
        if nxt and re.search(rf"\s{nxt}\.(?=[A-Z])", txt):  # '… : Yes 14.Anti-Blow Out Stem : Yes' on one line
            head, _, tail = txt.partition(f" {nxt}.")
            if cur is not None:
                cur["text"] += " " + head
                cur["words"] += ws
            elif head.strip():
                pass
            txt = f"{nxt}.{tail}"
        m = re.match(r"^(\d{1,2})[.)](?:\s+|(?=[A-Z]))(.*)", txt)   # '14.Anti-Blow …' (no space) is note 14
        if m:
            cur = {"no": int(m.group(1)), "text": m.group(2), "words": list(ws), "section": section}
            out.append(cur)
        elif cur is not None:
            cur["text"] += " " + txt
            cur["words"] += ws
    return [dict({"no": n["no"], "text": n["text"].strip(), "bbox": _bbox(n["words"])},
                 **({"section": n["section"]} if n["section"] else {})) for n in out]


# ── document-level pages (cover · index · general notes) ────────────────────────

def _general_notes(text: str):
    """'GENERAL NOTES' section of a datasheet document: {no: text}.  Stops at the next numbered heading."""
    m = re.search(r"GENERAL NOTES\s*\n", text)
    if not m:
        return {}
    body = text[m.end():]
    body = re.split(r"\n\s*\d\.\s*\n\s*ATTACHMENT|\n\s*ATTACHMENT-|\n\s*\d\.\s+ATTACHMENT", body)[0]
    lines = [ln.strip() for ln in body.split("\n")]
    out, cur, skip = {}, None, 0
    heads = ("COMPANY:", "Contract No.:", "PROJECT:", "Doc. No.:", "CONTRACTOR:", "Doc. Title:")
    for i, ln in enumerate(lines):
        if skip:                                             # repeated page header between notes
            skip -= 1
            continue
        if ln in heads:
            skip = 1
            if ln == "Doc. Title:" and i + 2 < len(lines) and lines[i + 2] and lines[i + 2] == lines[i + 2].upper():
                skip = 2
            continue
        if not ln or re.match(r"^Page \d+ of \d+", ln) or re.match(r"^Rev\.\s*\S*$", ln):
            continue
        mm = re.match(r"^(\d{1,2})\.\s+(.*)", ln)
        if mm and (cur is None or int(mm.group(1)) == cur + 1):
            cur = int(mm.group(1))
            out[cur] = mm.group(2)
        elif cur is not None:
            out[cur] += " " + ln
    return out


class PdfError(ValueError):
    """A PDF this reader cannot use — the message says why, in words the user can act on."""


def open_pdf(path: str):
    try:
        doc = pymupdf.open(path)
    except Exception as e:                                   # noqa: BLE001
        raise PdfError(f"PDF 를 열 수 없습니다 (손상된 파일) — {type(e).__name__}")
    if doc.needs_pass and not doc.authenticate(""):          # owner-only protection opens with an empty password
        doc.close()
        raise PdfError("암호가 걸린 PDF 입니다 — 암호를 풀어 저장한 뒤 다시 올려 주세요")
    return doc


_STD = 842.0                                                 # the reader's thresholds are in A4 points


def _normalised(page):
    """(page to read, k): a page much larger or smaller than A4 (A3, A2, plotted forms) is shown on an A4-sized
    page first, so every distance the reader uses means the same thing; boxes are scaled back by 1/k."""
    r = page.rect
    k = _STD / max(r.width, r.height)
    if abs(k - 1) < 0.08:
        return page, 1.0
    tmp = pymupdf.open()
    np_ = tmp.new_page(width=r.width * k, height=r.height * k)
    np_.show_pdf_page(np_.rect, page.parent, page.number)
    return np_, k


def _place(box, k, mat):
    """Reader box -> box on the page as it is shown (scale back, then the page's own rotation)."""
    if not box:
        return box
    r = pymupdf.Rect(*box) * (1 / k)
    if mat is not None:
        r = r * mat
        r.normalize()
    return [round(v, 1) for v in (r.x0, r.y0, r.x1, r.y1)]


def read_pdf(path: str, progress=None):
    doc = open_pdf(path)
    sheets, other, docs = [], [], {}
    cont_doc = None
    damaged = bool(getattr(doc, "is_repaired", False))
    for i, page in enumerate(doc):
        if progress:
            progress(i + 1, doc.page_count)
        rot = page.rotation
        if rot:                                              # read unrotated; boxes are turned back afterwards
            page.set_rotation(0)
        rp, k = _normalised(page)
        sh = read_page(rp, i + 1)
        mat = None
        if rot:
            page.set_rotation(rot)
            mat = page.rotation_matrix
        if sh and not sh.get("scanned") and (k != 1.0 or mat is not None):
            for r in sh.get("rows", []):
                r["bbox"], r["label_bbox"] = _place(r.get("bbox"), k, mat), _place(r.get("label_bbox"), k, mat)
            for n in sh.get("notes", []):
                n["bbox"] = _place(n.get("bbox"), k, mat)
        if sh and not sh.get("scanned"):
            sheets.append(sh)
            continue
        if sh and sh.get("scanned") and damaged:
            other.append({"page": i + 1, "kind": "damaged"})
            continue
        if sh and sh.get("scanned"):
            other.append({"page": i + 1, "kind": "scanned"})
            continue
        text = page.get_text()
        m = re.search(r"Doc\. No\.:\s*\n?\s*(\S+)", text)
        dn = m.group(1) if m else cont_doc
        other.append({"page": i + 1, "kind": "document", "doc_no": dn or ""})
        if dn:
            d = docs.setdefault(dn, {"pages": [], "text": "", "title": ""})
            d["pages"].append(i + 1)
            d["text"] += "\n" + text
            t = re.search(r"Doc\. Title:\s*\n(.+)", text)
            if t and not d["title"]:
                parts = [t.group(1).strip()]               # a long title wraps onto the next line(s) in the same capitals
                for ln in text[t.end():].split("\n")[1:4]:
                    ln = ln.strip()
                    if not ln or ln != ln.upper() or ln.endswith(":") or re.match(r"^(\d+\.|Rev\.|Page )", ln):
                        break
                    parts.append(ln)
                d["title"] = " ".join(parts)
            cont_doc = dn
    for dn, d in docs.items():
        d["general_notes"] = _general_notes(d["text"])
        rv = re.search(r"\nRev\.\s*([0-9A-Z]{1,2})\b", d["text"])
        d["rev"] = rv.group(1) if rv else ""
        del d["text"]
    doc.close()
    return {"pages": len(sheets) + len(other), "sheets": sheets, "other_pages": other, "docs": docs, "damaged": damaged}


def group_datasheets(result: dict):
    """Sheets -> one datasheet per (doc_no, tag, rev): sheet 1 has the tag, later sheets continue it."""
    out, cur = [], None
    for sh in result["sheets"]:
        starts = bool(sh["tag"]) and (cur is None or cur["doc_no"] != sh["doc_no"]
                                      or schema.norm_tag(sh["tag"]) != cur["tag_key"]
                                      or (sh.get("sheet") == 1 and sh["rows"] and cur["pages"] and not sh.get("continuation")
                                          and any(r["key"] == "tag" for r in sh["rows"])
                                          and any(r["key"] == "tag" for r in cur["rows"])))
        if starts or cur is None:
            cur = {"tag": sh["tag"], "tag_key": schema.norm_tag(sh["tag"]), "doc_no": sh["doc_no"], "rev": sh["rev"],
                   "date": sh["date"], "title": sh["title"], "rev_history": list(sh["rev_history"]),
                   "pages": [], "fields": {}, "rows": [], "notes": [], "sheets": []}
            out.append(cur)
        cur["pages"].append(sh["page"])
        pr = sh.get("doc_no_printed")
        if pr and pr != cur["doc_no"] and sh.get("sheet") and not sh.get("continuation"):   # another number than sheet 1
            cur.setdefault("sheet_doc_mismatch", []).append({"page": sh["page"], "sheet": sh.get("sheet"), "printed": pr})
        cur["sheets"].append([sh["page"], sh.get("sheet"), sh.get("of")])     # PDF page -> 'Sheet x of y' on the form
        for r in sh["rows"]:
            r = dict(r, page=sh["page"])
            cur["rows"].append(r)
            k = r["key"]
            if k in cur["fields"] and cur["fields"][k]["value"] and not r["value"]:
                continue                                    # keep the first non-empty reading of a repeated key
            if k in cur["fields"] and cur["fields"][k]["value"] and r["value"]:
                k = f"{k}.{r['row']}"
            cur["fields"][k] = r
        for n in sh["notes"]:
            cur["notes"].append(dict(n, page=sh["page"]))
    for ds in out:
        ds["valve_type"] = schema.valve_type(ds["tag"])
        gn = result["docs"].get(ds["doc_no"], {}).get("general_notes", {})
        ds["process_ref"] = process_reference(ds["notes"], gn)
        for r in ds["fields"].values():                     # 'General Note - 8' / 'Note-1' -> the note it points at
            m = _NOTE_REF.search(r["value"] or "")
            if m:
                no = int(m.group(2))
                if m.group(1).lower().startswith("gen"):
                    if no in gn:
                        r["ref"] = {"kind": "general", "no": no, "text": gn[no]}
                else:
                    hit = next((n for n in ds["notes"] if n["no"] == no), None)
                    if hit:
                        r["ref"] = {"kind": "note", "no": no, "text": hit["text"], "page": hit["page"], "bbox": hit["bbox"]}
                if r.get("ref") and pure_reference(r["value"]) and r["ref"]["kind"] == "note":
                    wrong = wrong_note(r.get("label") or "", r["ref"], ds["notes"])
                    if wrong:
                        r["ref"]["mismatch"] = wrong            # the note is about something else: do not use its value
                        continue
                if r.get("ref") and pure_reference(r["value"]):
                    v = note_value(r["ref"]["text"], r.get("label") or "")
                    if v:
                        r["ref"]["value"] = v                   # 'Note 14' -> '316/316L SS ASTM A351-CF8M/CF3M''
    return out


_STOP = {"material", "of", "the", "and", "for", "type", "valve", "no", "shall", "be"}


def _subject(text: str) -> set[str]:
    """Words of a note's own heading ('Bolting /Nut: …' -> bolting, nut) or of a field label."""
    head = text.split(":")[0] if ":" in text[:70] else ""
    return {w for w in re.findall(r"[a-z]{3,}", head.lower()) if w not in _STOP}


def wrong_note(label: str, ref: dict, notes: list) -> dict | None:
    """A cell 'Body/Bonnet Material : Note-8' whose note 8 is headed 'Bolting /Nut: …' points at the wrong note.
    Only when the note has a heading, the heading shares no word with the label, and another note's heading does."""
    lw = {w for w in re.findall(r"[a-z]{3,}", (label or "").lower()) if w not in _STOP}
    nw = _subject(ref.get("text", ""))
    if not lw or not nw or lw & nw:
        return None
    best = max(((len(lw & _subject(n["text"])), n) for n in notes if n["no"] != ref.get("no")), key=lambda t: t[0],
               default=(0, None))
    if best[0] == 0:
        return None
    n = best[1]
    return {"no": n["no"], "text": n["text"][:200], "page": n.get("page"), "bbox": n.get("bbox"),
            "value": note_value(n["text"], label)}


_PURE_REF = re.compile(r"^\W*(gen(?:eral|\.)?\s*)?note\s*[-–:#]?\s*\d+\W*$", re.I)


def pure_reference(value: str) -> bool:
    """The cell says only 'Note 14' / 'General Note - 3' — the value is in that note."""
    return bool(_PURE_REF.match(value or ""))


def note_value(text: str, label: str = "") -> str:
    """'Body material shall be 316/316L SS …' -> '316/316L SS …' · 'Actuator Type: Motorized …' -> 'Motorized …'.
    Only short, single-statement notes; a long paragraph is left as a reference (no guessing)."""
    t = " ".join((text or "").split())
    if not t or len(t) > 160:
        return ""
    m = re.match(r"^([^:]{2,60}?)\s*:\s*(.+?)\.?$", t)
    if m:
        return m.group(2).strip()
    m = re.search(r"\bshall be\s+(.+?)\.?$", t, re.I)
    if m and len(m.group(1)) <= 120 and not re.search(r"\b(as per|in accordance|subject to|provided)\b", m.group(1), re.I):
        return m.group(1).strip()
    return ""


_PROC_REF = re.compile(r"process\s+data[^.]{0,40}?(?:refer|see|as per|according to|in accordance)|"
                       r"refer[^.]{0,40}?process\s+data|process\s+data[^.]{0,80}?-PR-DTS-", re.I)
_DOCNO = re.compile(r"\b[0-9A-Z]{2,5}-[0-9A-Z]{2,4}-[A-Z]{2}-[A-Z]{3}-\d{5}\b")


def process_reference(notes, general_notes) -> dict | None:
    """'For Process data please refer to Doc.No.: 03-02-PR-DTS-00002' -> {doc, where}.  The process fields of such a
    datasheet are blank on purpose; Phase 3 compares them with that document."""
    for n in notes or []:
        if _PROC_REF.search(n["text"]):
            d = _DOCNO.search(n["text"])
            return {"doc": d.group(0) if d else "", "where": f"Note {n['no']}", "text": n["text"][:200]}
    for no, t in (general_notes or {}).items():
        if _PROC_REF.search(t):
            d = _DOCNO.search(t)
            return {"doc": d.group(0) if d else "", "where": f"General Note {no}", "text": t[:200]}
    return None
