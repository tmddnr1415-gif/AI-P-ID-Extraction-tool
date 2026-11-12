"""Learn blank instrument-datasheet forms → one "form card" (JSON) per form.

    python3 spike/valve_form_learn.py /tmp/forms app/valve/forms/

Reads only the PDF text layer and vector rules (pymupdf words + drawings) — no OCR, no LLM.  Every position comes from
the page itself: the row-number column, the section column (vertical letters or horizontal captions), the label
cell and the value cells are found from that page's own words and rules.  Nothing printed is invented: a label that
the text layer does not give is written as "" and listed in the card's `ambiguous`.

The forms are client material: they are read from the given folder and are never copied.  Owner / project names in
the title blocks are not written into any output (only the form number, the printed form title, the footer tag).

Outputs (in the out folder): <form_id>.json per form · index.json · lists.json (Instrument Index / IO List column
headers, Process Line List structure).  A compact verification table is printed at the end.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import warnings
from collections import Counter

warnings.filterwarnings("ignore")
import pymupdf  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:                                                    # align std_key with the valve reader where it already has names
    from app.valve import schema as vschema             # noqa: E402
except Exception:                                       # pragma: no cover — the script also runs without the app
    vschema = None

CARD_VERSION = "form-card-v1"

# File-name code → (form_id, common name, kind).  The file name is the only id of 5063 (no form number printed).
FORMS = {
    "101": ("101", "Control Valve", "cv"),
    "80": ("80", "On-Off Valve (SDV / BDV)", "onoff"),
    "701": ("701", "Pressure Safety Valve", "psv"),
    "203": ("203", "Analyzer", "analyzer"),
    "310": ("310", "Restriction Orifice", "ro"),
    "313": ("313", "Flow Transmitter", "ft"),
    "505": ("505", "Magnetic Level Gauge", "mlg"),
    "506": ("506", "Level Transmitter", "lt"),
    "5063": ("5063", "Guided Wave Radar Level Transmitter", "gwr"),
    "601": ("601", "Pressure / Differential Pressure Transmitter", "pt"),
    "605": ("605", "Pressure Gauge", "pg"),
    "606": ("606", "Differential Pressure Gauge", "dpg"),
    "801": ("801", "Temperature Transmitter", "tt"),
    "803": ("803", "Temperature Gauge", "tg"),
}
# INSTRUMENT_REVIEW_PLAN.md §2 (as written there) — only used for the verification table.
PLAN = {"101": 100, "80": 61, "701": 50, "203": 40, "310": 41, "313": 48, "505": 50, "506": 48, "5063": 50,
        "601": 48, "605": 47, "606": 47, "801": 30, "803": 45}

# Words that may make up section captions; used only to put spaces into vertically stacked letters
# ('VALVEMATERIAL' → 'VALVE MATERIAL').  A caption that cannot be split exactly with these stays as printed.
SECTION_VOCAB = {"TAG", "PROC", "PROC.", "PRO", "PROCESS", "DATA", "GENERAL", "GEN", "GEN.", "ELEMENT", "TRANSMITTER",
                 "OPTIONS", "OPTION", "MFR", "ANALYZER", "ENVIRON", "UTILITIES", "OUTPUT", "INPUT", "CHAMBER",
                 "ACCESSORY", "ACCESSORIES", "MATERIAL", "INDICATOR", "SENSOR", "GAUGE", "THERMOMETER", "WELL",
                 "VALVE", "BODY", "BONNET", "TRIM", "ACTUATOR", "POSITIONER", "BASIS", "DESIGN", "CONN.", "CONN",
                 "SIZE", "SEL", "MAIN", "PILOT", "SIZING", "CALCULATION", "CONDITIONS", "CONDITION", "ACC.", "ACC",
                 "LEVEL", "SOLENOID", "PIPE", "NOTES", "MTR", "SPEC", "SPECIFICATION", "SERVICE", "PNEUMATIC", "ELECTRICAL",
                 "VAL", "PAINT", "POSTNR.", "ACCESS.", "ACCESORY", "METER", "GEN.", "/"}

# ── std_key dictionary: (regex on the normalised label, key).  First match wins. ─────────────────────────────
STD = [
    (r"tag no\.?( \(loop no\.?:? \))?", "tag"), (r"tag number", "tag"),
    (r"(quantity tags|tag quantity|qty tags)", "tag_qty"),
    (r"(p&id|pid) no\.?", "pid_no"),
    (r"line no\.?", "line_no"), (r"line number", "line_no"),
    (r"equipment no\.?|equip no\.?", "equipment_no"), (r"vessel no\.?", "vessel_no"), (r"loop no\.?:?", "loop_no"),
    (r"service", "service"), (r"service ?class", "piping_class"), (r"piping class", "piping_class"),
    (r"line size( and sch\.? inlet)?", "line_size"), (r"(line )?schedule|sch\.?", "line_schedule"),
    (r"fluid( name)?", "fluid"), (r"phase|fluid state", "fluid_state"),
    (r"upper fluid", "fluid_upper"), (r"lower fluid", "fluid_lower"),
    (r"operating pressure( \(max/nr/min\)| pressure\(max/min\))?", "op_pressure"),
    (r"operating temp(erature|\.)?", "op_temp"),
    (r"design pressure( \(max/min\))?", "design_pressure"), (r"design temp(erature)?( \(max/min\))?", "design_temp"),
    (r"pressure ?\((min/nor/max|max / min)\)", "op_pressure"), (r"temperature ?\((min/nor/max|max / min)\)", "op_temp"),
    (r"(operating )?density( @ condition| @ rt|:)?", "density"), (r"flow rate( ?\(min/nor/max\))?", "flow"),
    (r"max\.? relieving flow rate", "flow"), (r"molecular weight|mw", "mol_weight"),
    (r"(operating )?viscosity( @ rt)?", "viscosity"),
    (r"manufacturer( name)?", "manufacturer"), (r"model (no\.?|number)", "model"),
    (r"process connection", "process_connection"), (r"electrical connection", "elec_connection"),
    (r"(elec\. )?hazardous protection:?", "hazardous_area"), (r"weather protection( class)?", "weather_protection"),
    (r"enclosure type:?", "enclosure"), (r"(electrical )?power supply", "power_supply"),
    (r"calibration range", "calibration_range"), (r"instrument range", "instrument_range"),
    (r"set pressure", "set_pressure"), (r"accuracy", "accuracy"), (r"mounting", "mounting"),
]
COMPOSITE = {"line size / material": ("line_size", ["pipe_material"]),
             "line number / size / sch.": ("line_no", ["line_size", "line_schedule"]),
             "service / equip no": ("service", ["equipment_no"])}
_STD = [(re.compile(rf"^(?:{p})$"), k) for p, k in STD]
PROCESS_KEYS = {"fluid", "fluid_state", "fluid_upper", "fluid_lower", "op_pressure", "op_temp", "design_pressure",
                "design_temp", "density", "flow", "mol_weight", "viscosity", "set_pressure"}
NOT_PROCESS = set(getattr(vschema, "NOT_PROCESS", set())) | {"piping_class", "line_size", "line_schedule"}
GENERIC = {"manufacturer", "model", "type", "material", "size", "construction", "service", "mounting",
           "process_connection", "length", "other", "wetted_part"}
UNIT_RX = re.compile(r"%|dBA|mm|degC|°C|ºC|bar\(g\)|barg|kg/m3|cP")
SIZING = re.compile(r"(^|_)(cv|spl|travel|calculated|required_cv|fl|xt|flash_ratio|area|orifice|reaction)(_|$)")
SUGGESTED_REQUIRED = ["tag", "service", "pid_no", "line_no", "equipment_no", "vessel_no", "piping_class", "line_size",
                      "fluid", "fluid_state", "op_pressure", "design_pressure", "op_temp", "design_temp",
                      "manufacturer", "model"]


def norm(s: str) -> str:
    s = (s or "").replace(" ", " ").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s.rstrip(" :").strip()


def snake(s: str) -> str:
    s = norm(s).replace("&", " and ").replace("%", " pct ").replace("ï", "i")
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or ""


def std_of(label: str, section: str, form_id: str):
    """(std_key, also) — the existing valve dictionary for 80 / 101, then STD, then a snake key."""
    label = re.sub(r"\s*:?\s*yes,?\s*no\s*$", "", label or "", flags=re.I)
    n = norm(label)
    if n.startswith("("):
        n = n.strip("() :").strip()
    if n in COMPOSITE:
        return COMPOSITE[n][0], list(COMPOSITE[n][1])
    if not n:
        return "", []
    if re.fullmatch(r"(quantity tags|tag quantity|qty tags)", n):
        return "tag_qty", []                       # one key for every form (101's valve dictionary says 'qty')
    if vschema is not None:
        hit = None
        if form_id == "101":
            hit = vschema.lookup_102(label, section)
        elif form_id == "80":
            hit = vschema.lookup(label, section)
        if hit:
            return hit[0], []
    for rx, k in _STD:
        if rx.match(n):
            return k, []
    if "/" in n or " or " in n:                    # 'P&ID No./Line No./Equipment No.' — one key per printed part
        parts = [p.strip() for p in re.split(r"\s*/\s*|\s+or\s+", n) if p.strip()]
        keys = []
        for p in parts:
            k = next((k for rx, k in _STD if rx.match(p)), None)
            if k:
                keys.append(k)
        if keys and len(keys) == len(parts):
            return keys[0], keys[1:]
    return snake(label), []


# ── geometry helpers (same ideas as app/valve/extract.py: words → lines; rules from drawings) ────────────────

def cy(w):
    return (w[1] + w[3]) / 2


def cx(w):
    return (w[0] + w[2]) / 2


def lines_of(words):
    out = []
    for w in sorted(words, key=cy):
        c = cy(w)
        if out and out[-1][0] - 0.5 <= c <= out[-1][1] + 0.5:
            out[-1][2].append(w)
            out[-1][0], out[-1][1] = min(out[-1][0], w[1]), max(out[-1][1], w[3])
        else:
            out.append([w[1], w[3], [w]])
    return [sorted(ln[2], key=lambda w: w[0]) for ln in out]


def text_of(words):
    return " ".join(w[4] for ln in lines_of(words) for w in ln).strip()


def bbox_of(words):
    if not words:
        return None
    return [round(min(w[0] for w in words), 1), round(min(w[1] for w in words), 1),
            round(max(w[2] for w in words), 1), round(max(w[3] for w in words), 1)]


def rules(page):
    """(verticals [(x, y0, y1)], horizontals [(y, x0, x1)])."""
    vs, hs = [], []
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] == "l":
                a, b = it[1], it[2]
                if abs(a.x - b.x) < 0.8 and abs(a.y - b.y) > 3:
                    vs.append(((a.x + b.x) / 2, min(a.y, b.y), max(a.y, b.y)))
                elif abs(a.y - b.y) < 0.8 and abs(a.x - b.x) > 3:
                    hs.append(((a.y + b.y) / 2, min(a.x, b.x), max(a.x, b.x)))
            elif it[0] == "re":
                r = it[1]
                if r.width < 1.5 and r.height > 3:
                    vs.append(((r.x0 + r.x1) / 2, r.y0, r.y1))
                elif r.height < 1.5 and r.width > 3:
                    hs.append(((r.y0 + r.y1) / 2, r.x0, r.x1))
                elif r.width >= 1.5 and r.height >= 1.5:
                    vs += [(r.x0, r.y0, r.y1), (r.x1, r.y0, r.y1)]
                    hs += [(r.y0, r.x0, r.x1), (r.y1, r.x0, r.x1)]
    return vs, hs


def xs_at(vs, y, x_min, x_max):
    xs = sorted(x for x, y0, y1 in vs if y0 + 0.5 <= y <= y1 - 0.5 and x_min < x < x_max)
    out = []
    for x in xs:
        if out and x - out[-1] < 5:               # double rules are one boundary
            continue
        out.append(x)
    return out


def is_vletter(w):
    t = w[4]
    return (w[3] - w[1]) < 7.6 and len(t.rstrip(".")) <= 1 and (t.isupper() or t in "/.&")


def is_int(t):
    return t.isdigit() and 1 <= int(t) <= 150


def number_columns(words):
    """Columns of row numbers: integers sharing one x band, mostly consecutive."""
    cands = [w for w in words if is_int(w[4]) and (w[3] - w[1]) > 7.5]
    groups = []
    for w in sorted(cands, key=cx):
        if groups and cx(w) - groups[-1][-1] < 5:
            groups[-1][0].append(w)
            groups[-1][-1] = cx(w)
        else:
            groups.append([[w], cx(w)])
    out = []
    for g, _ in groups:
        g = sorted(g, key=cy)
        nums = [int(w[4]) for w in g]
        steps = sum(1 for a, b in zip(nums, nums[1:]) if b == a + 1)
        if len(g) >= 5 and steps >= (len(g) - 1) * 0.8:
            out.append(g)
    return sorted(out, key=lambda g: min(w[0] for w in g))


def segment(s: str) -> str:
    """'VALVEMATERIAL' → 'VALVE MATERIAL' when the vocabulary splits it exactly; else unchanged."""
    if " " in s or not s:
        return s
    best = {0: []}
    for i in range(len(s)):
        if i not in best:
            continue
        for j in range(i + 1, len(s) + 1):
            if s[i:j] in SECTION_VOCAB and j not in best:
                best[j] = best[i] + [s[i:j]]
    if len(s) in best:
        return " ".join(best[len(s)]).replace(" / ", "/").replace("/ ", "/").replace(" /", "/")
    return s


def caption_text(words):
    """Section caption from the words of one band: stacked letters read top-down per column, else plain lines."""
    if not words:
        return "", ""
    if sum(1 for w in words if is_vletter(w) or len(w[4]) <= 2) >= len(words) * 0.7:
        cols = []
        for w in sorted(words, key=cx):
            if cols and cx(w) - cols[-1][1] < 3.5:
                cols[-1][0].append(w)
            else:
                cols.append([[w], cx(w)])
        parts = ["".join(w[4] for w in sorted(c, key=cy)) for c, _ in cols]
        raw = parts[0]
        for p in parts[1:]:
            raw += p if p.startswith("/") else " / " + p
        return raw, " / ".join(segment(p) if not p.startswith("/") else p for p in parts).replace(" / /", "/")
    t = text_of(words)
    return t, t


# ── one page → rows ─────────────────────────────────────────────────────────────────────────────────────────

def read_rows(page, pno, form_id):
    words = page.get_text("words")
    cols = number_columns(words)
    if not cols:
        return [], {}
    vs, hs = rules(page)
    right_edge = max((x for x, y0, y1 in vs if y1 - y0 > 100), default=page.rect.width - 20)
    num_ids = {id(w) for g in cols for w in g}
    rows, info = [], {"columns": []}
    for ci, col in enumerate(cols):
        nx0, nx1 = min(w[0] for w in col), max(w[2] for w in col)
        col_right = (min(w[0] for w in cols[ci + 1]) - 2) if ci + 1 < len(cols) else right_edge
        next_top = (min(cy(w) for w in cols[ci + 1]) - 6) if ci + 1 < len(cols) else None
        ys = [cy(w) for w in col]
        gaps = sorted(b - a for a, b in zip(ys, ys[1:]))
        pitch = gaps[len(gaps) // 2] if gaps else 11
        bounds = [ys[0] - pitch / 2] + [(a + b) / 2 for a, b in zip(ys, ys[1:])] + [ys[-1] + pitch / 2]
        top, bot = bounds[0], bounds[-1]
        inside = [w for w in words if top <= cy(w) < bot and id(w) not in num_ids and w[0] >= nx0 - 1 - (999 if ci == 0 else 0)
                  and w[2] <= (right_edge if next_top else col_right) + 2]
        # label start = the most common x0 of the first non-letter word right of the numbers in each row
        firsts = []
        for i, nw in enumerate(col):
            rw = sorted((w for w in inside if bounds[i] <= cy(w) < bounds[i + 1] and w[0] > nx1 + 1 and not is_vletter(w)
                         and not (len(w[4]) <= 2 and w[0] < nx1 + 12 and (w[3] - w[1]) < 9.5 and w[4].isupper())),
                        key=lambda w: w[0])
            if rw:
                firsts.append(round(rw[0][0]))
        lab_x0 = min(x for x, c in Counter(firsts).items() if c >= max(2, Counter(firsts).most_common(1)[0][1] * 0.3)) \
            if firsts else nx1 + 20
        sec_words = [w for w in inside if w[2] <= lab_x0 - 1.5 and (
            (w[0] >= nx1 - 1 and (is_vletter(w) or (len(w[4].rstrip(".")) <= 1 and w[4].isupper())))
            or (ci == 0 and w[2] <= nx0 + 1))]
        sec_ids = {id(w) for w in sec_words}
        # section bands from the horizontal rules that cross the section column
        bands = []
        if sec_words:
            sx0, sx1 = min(w[0] for w in sec_words), max(w[2] for w in sec_words)
            hy = sorted({round(y, 1) for y, a, b in hs if a <= sx0 + 1 and b >= sx1 - 1 and top - 6 <= y <= bot + 6})
            hy = [y for i, y in enumerate(hy) if not i or y - hy[i - 1] > 3]
            edges = [min(top, hy[0]) if hy else top] + [y for y in hy if top + 3 < y < bot - 3] + [max(bot, hy[-1]) if hy else bot]
            for a, b in zip(edges, edges[1:]):
                bw = [w for w in sec_words if a <= cy(w) < b]
                raw, name = caption_text(bw)
                band = {"y0": round(a, 1), "y1": round(b, 1), "raw": raw, "name": name, "bbox": bbox_of(bw), "inner": []}
                # nested captions (701: 'VALVE MATERIAL' outside, 'MAIN' / 'PILOT' inside): an inner letter column
                # with its own rules splits the band; rows then read 'outer / inner'
                lcols = []
                for w in sorted((w for w in bw if is_vletter(w)), key=cx):
                    if lcols and cx(w) - lcols[-1][1] < 3.5:
                        lcols[-1][0].append(w)
                    else:
                        lcols.append([[w], cx(w)])
                if len(lcols) >= 2:
                    iw = lcols[-1][0]
                    ix0, ix1 = min(w[0] for w in iw), max(w[2] for w in iw)
                    ox1 = max(w[2] for w in lcols[0][0])
                    iy = sorted({round(y, 1) for y, xa, xb in hs if xa <= ix0 + 0.5 and xb >= ix1 - 0.5 and xa > ox1 - 1
                                 and a + 3 < y < b - 3})
                    if iy:
                        ie = [a] + iy + [b]
                        for ya, yb in zip(ie, ie[1:]):
                            sw = [w for w in iw if ya <= cy(w) < yb]
                            band["inner"].append({"y0": ya, "y1": yb, "text": "".join(w[4] for w in sorted(sw, key=cy))})
                        outer = "".join(w[4] for w in sorted(lcols[0][0], key=cy))
                        band["outer_raw"], band["outer"] = outer, segment(outer)
                bands.append(band)
        info["columns"].append({"num_x": [round(nx0, 1), round(nx1, 1)], "label_x0": lab_x0, "right": round(col_right, 1),
                                "sections": bands})

        def section_at(y):
            for b in bands:
                if b["y0"] <= y < b["y1"]:
                    for ib in b["inner"]:
                        if ib["y0"] <= y < ib["y1"]:
                            return {"raw": b["outer_raw"] + " / " + ib["text"], "name": b["outer"] + " / " + segment(ib["text"])}
                    return b
            return None

        for i, nw in enumerate(col):
            y0, y1, yc = bounds[i], bounds[i + 1], ys[i]
            # rows above the start of the next number column run to the table's right edge (101 rows 1-4)
            row_right = right_edge if next_top is not None and yc < next_top else col_right
            rw = [w for w in inside if y0 <= cy(w) < y1 and id(w) not in sec_ids and w[0] > nx1 + 1 and cx(w) < row_right]
            cuts = [x for x in xs_at(vs, yc, lab_x0 + 6, row_right - 3)]
            # the label cell ends at the first rule right of where the label words end … or before the first word
            # that sits right of a rule
            lab_end = cuts[0] if cuts else row_right
            lab_w = [w for w in rw if cx(w) < lab_end]
            val_w = [w for w in rw if cx(w) >= lab_end]
            cells = []
            edges = [lab_end] + cuts[1:] + [row_right]
            for a, b in zip(edges, edges[1:]):
                if b - a < 4:
                    continue
                cw = [w for w in val_w if a <= cx(w) < b]
                chunks = []
                for w in sorted(cw, key=lambda w: w[0]):
                    if chunks and w[0] - chunks[-1][-1][2] < 12 and abs(cy(w) - cy(chunks[-1][-1])) < 6:
                        chunks[-1].append(w)
                    else:
                        chunks.append([w])
                cells.append({"x0": round(a, 1), "x1": round(b, 1), "chunks": chunks})
            sub, sub_bb, marks = [], [], []
            for c in cells:
                for ch in c["chunks"]:
                    t = text_of(ch)
                    if re.fullmatch(r"[/\-:!,.]+", t):
                        marks.append(t)
                        continue
                    sub.append(t)
                    sub_bb.append(bbox_of(ch))
            sec = section_at(yc)
            # one label cell may print two labels ('Model No :   Ser No. :') — split where the words leave a wide gap
            chunks = []
            for ln in lines_of(lab_w):
                for w in ln:
                    if chunks and w[0] - chunks[-1][-1][2] > 18 and abs(cy(w) - cy(chunks[-1][-1])) < 4:
                        chunks.append([w])
                    elif chunks and abs(cy(w) - cy(chunks[-1][-1])) < 4:
                        chunks[-1].append(w)
                    elif chunks and len(chunks) == 1:
                        chunks[-1].append(w)
                    else:
                        chunks.append([w])
            main = chunks[0] if chunks else []
            extra = []
            for ch in chunks[1:]:
                t = text_of(ch)
                if re.fullmatch(r"[/\-:!,.]+", t):
                    marks.append(t)
                else:
                    extra.append({"text": t.rstrip(" :").strip(), "bbox": bbox_of(ch)})
            lab_w = main
            label = text_of(lab_w)
            val_x0, vcells = lab_end, [[c["x0"], c["x1"]] for c in cells] if len(cells) > 1 else []
            if not cuts and lab_w:
                # no rule between label and value ('Tag No. :  ____  Instrument Type : ____'): the value runs from
                # the end of each printed label to the start of the next one
                spans, x = [], max(w[2] for w in lab_w) + 2
                for ex in extra:
                    spans.append([round(x, 1), round(ex["bbox"][0] - 2, 1)])
                    x = ex["bbox"][2] + 2
                spans.append([round(x, 1), round(row_right, 1)])
                val_x0 = spans[0][0]
                vcells = spans if len(spans) > 1 else []
            rows.append({
                "no": int(nw[4]), "page": pno + 1, "column": ci + 1,
                "label": label, "label_bbox": bbox_of(lab_w),
                "label_x0": round(min((w[0] for w in lab_w), default=lab_x0), 1),
                "section_raw": sec["raw"] if sec else "", "section": sec["name"] if sec else "",
                "row_bbox": [round(nx0, 1), round(y0, 1), round(row_right, 1), round(y1, 1)],
                "value_bbox": [round(val_x0, 1), round(y0, 1), round(row_right, 1), round(y1, 1)],
                "value_cells": vcells,
                "subcols": sub, "subcol_bboxes": sub_bb, "marks": marks,
                "small_subcols": bool(sub) and all((b[3] - b[1]) < 8.2 for b in sub_bb),
                "inline_labels": extra,
            })
    return rows, info


def page_footer(page):
    t = page.get_text()
    m = re.findall(r"form\s+([0-9+]{2,8}_R[0-9.]+)", t)
    return m[-1] if m else ""


def page_title(page):
    """Printed form title (the large words of the title block) — owner/project words are never kept."""
    ws = page.get_text("words")
    big = [w for w in ws if (w[3] - w[1]) > 13 and w[1] < 140]
    if big:
        return text_of(big)
    # other title block (5063): 'DATA SHEETS FOR' and the line under it, in the middle of the block
    lns = lines_of([w for w in ws if w[1] < 100 and 200 < w[0] < 410 and (w[3] - w[1]) < 10.5])
    for i, ln in enumerate(lns):
        t = " ".join(w[4] for w in ln)
        if t.startswith("DATA SHEETS FOR") and i + 1 < len(lns):
            return t + " " + " ".join(w[4] for w in lns[i + 1])
    return ""


def notes_regions(page, pno):
    ws = page.get_text("words")
    _, hs = rules(page)
    out = []
    lns = lines_of(ws)
    for ln in lns:
        for i, w in enumerate(ln):
            hit = w[4] in ("Common", "Individual") and i + 1 < len(ln) and ln[i + 1][4].startswith("Notes")
            hit = hit or (w[4] == "NOTES" and i == 0 and len(ln) <= 2)
            if hit:
                below = sorted(y for y, a, b in hs if y > w[3] + 4 and b - a > page.rect.width * 0.4)
                foot = [x for x in ws if x[4] == "form" and x[1] > w[3]]
                y1 = below[0] if below else (min(x[1] for x in foot) - 4 if foot else page.rect.height - 40)
                out.append({"kind": w[4].lower() if w[4] != "NOTES" else "notes", "page": pno + 1, "bbox": [round(w[0], 1), round(w[1], 1),
                            round(page.rect.width - 22, 1), round(y1, 1)]})
    return out


# ── one form → card ─────────────────────────────────────────────────────────────────────────────────────────

def code_of(path):
    b = os.path.basename(path)
    m = re.search(r"-(\d{2,4})(?:_|-)", b)
    return m.group(1) if m else None


def learn(path):
    code = code_of(path)
    form_id, name, kind = FORMS[code]
    doc = pymupdf.open(path)
    pages, items, ambiguous, notes, page_roles = [], [], [], [], []
    footers, block, last_no, printed_no = [], 0, None, ""
    title = ""
    sizes = Counter()
    for pno, page in enumerate(doc):
        w, h = round(page.rect.width), round(page.rect.height)
        sizes["A4" if (w, h) in ((595, 842), (842, 595)) else "Letter" if (w, h) in ((612, 792), (792, 612)) else f"{w}x{h}"] += 1
        txt = page.get_text()
        m = re.search(r"Form\s+No\s*:\s*(\d+)", txt)
        if m and not printed_no:
            printed_no = m.group(1)
        if not title:
            title = page_title(page)
        ft = page_footer(page)
        if ft:
            footers.append({"page": pno + 1, "tag": ft})
        rows, info = read_rows(page, pno, form_id)
        notes += notes_regions(page, pno)
        if rows:
            first = min(r["no"] for r in rows)
            if last_no is None or first <= last_no:
                block += 1
            last_no = max(r["no"] for r in rows)
            for r in rows:
                r["block"] = block
            items += rows
            page_roles.append({"page": pno + 1, "role": "items", "rows": [first, last_no], "block": block})
        elif re.search(r"Individual\s+Notes|Common\s+Notes", txt):
            page_roles.append({"page": pno + 1, "role": "notes"})
        elif txt.strip():
            page_roles.append({"page": pno + 1, "role": "footer-only" if ft and len(txt.split()) <= 3 else "header-only"})
        else:
            page_roles.append({"page": pno + 1, "role": "blank"})

    items.sort(key=lambda r: (r["block"], r["no"]))
    # header rows (only column captions, no label) hand their captions to the following rows that share their cells
    CAPS = {"Max", "Nor", "Min", "Unit", "Normal", "Maximum", "Minimum"}
    for r in items:
        r["role"] = "item"
        units = [t for t in r["subcols"] if UNIT_RX.fullmatch(t)]
        if units:
            r["unit_printed"] = units
            keep = [i for i, t in enumerate(r["subcols"]) if t not in units]
            r["subcols"] = [r["subcols"][i] for i in keep]
            r["subcol_bboxes"] = [r["subcol_bboxes"][i] for i in keep]
    for i, r in enumerate(items):
        if len(r["subcols"]) >= 3 and set(r["subcols"]) <= CAPS:
            if not r["label"] or "condition" in norm(r["label"]):
                r["role"] = "header"
            # a header row: column captions only (with or without a caption label) — the rows below that print no
            # captions of their own are read with these columns
            for s in items[i + 1:]:
                if s["block"] != r["block"] or s["section"] != r["section"] or s["subcols"] or not s["label"]:
                    break
                s["subcols"] = list(r["subcols"])
                s["subcols_from"] = r["no"]
    # parents by indent (a row whose label starts further right belongs to the nearest row above that starts left of it)
    for i, r in enumerate(items):
        r["parent"] = None
        if not r["label"]:
            continue
        for p in reversed(items[:i]):
            if p["block"] != r["block"] or p["column"] != r["column"] or p["section"] != r["section"]:
                break
            if p["label"] and p["label_x0"] < r["label_x0"] - 3.5:
                r["parent"] = p["no"]
                break
    by_no = {(r["block"], r["no"]): r for r in items}
    seen = Counter()
    for r in items:
        par = by_no.get((r["block"], r["parent"])) if r["parent"] else None
        key, also = std_of(r["label"], r["section"], form_id)
        if par and key and (key in GENERIC or key.split("_")[0] in ("wetted", "other", "type", "material", "size")) \
                and norm(par["label"]) not in ("mfr", "manufacturer"):
            pk, _ = std_of(par["label"], par["section"], form_id)
            key = f"{pk}_{key}" if pk else key
        if not key and r["role"] == "header":
            key = "header_" + "_".join(snake(s) for s in r["subcols"])
        if key in ("op_pressure", "op_temp", "pressure", "temperature") or norm(r["label"]) in ("pressure", "temperature"):
            subs = " ".join(r["subcols"]).lower()
            base = "pressure" if "press" in (key + norm(r["label"])) else "temp"
            if "des" in subs and ("oper" in subs or "ope." in subs):
                key, also = ("op_pressure", ["design_pressure"]) if base == "pressure" else ("op_temp", ["design_temp"])
        sec_s = snake(r["section"] or "")
        if key in GENERIC and not par and form_id not in ("80", "101") and sec_s not in ("tag", "general", "gen", "mfr", ""):
            key = f"{sec_s}_{key}"
        key_b = key
        if key_b and seen[key_b] and sec_s and not key_b.startswith(sec_s):
            key_b = f"{sec_s}_{key_b}"
        seen[key_b] += 1
        if seen[key_b] > 1 and key_b:
            key_b = f"{key_b}_{seen[key_b]}"
        if key_b:
            seen[key_b] += 0
        r["std_key"] = key_b
        if also:
            r["std_keys_also"] = also
        if re.search(r"yes,?\s*no|\(y\s*/\s*n\)", r["label"], re.I):
            r["options"] = ["Yes", "No"]
        sec_u = (r["section_raw"] or "").upper().replace(" ", "")
        base_key = re.sub(r"_\d+$", "", key_b)
        r["process"] = bool((sec_u.startswith("PRO") or "PROCESS" in sec_u or base_key in PROCESS_KEYS)
                            and base_key not in NOT_PROCESS and r["role"] == "item" and r["label"]
                            and not SIZING.search(base_key))
        if not r["label"]:
            why = "header row (column captions only)" if r["role"] == "header" else \
                ("no label printed — value captions only: " + " / ".join(r["subcols"])) if r["subcols"] else "blank row (no label printed)"
            ambiguous.append({"block": r["block"], "no": r["no"], "page": r["page"], "issue": why})
        if not r["section"]:
            ambiguous.append({"block": r["block"], "no": r["no"], "page": r["page"], "issue": "no section caption in this band"})
        elif " " not in r["section"] and "/" not in r["section"] and len(r["section"]) > 8 and r["section"] not in SECTION_VOCAB:
            ambiguous.append({"block": r["block"], "no": r["no"], "page": r["page"],
                              "issue": f"section letters '{r['section_raw']}' could not be split into words"})

    # numbering check per block
    gaps, dups = {}, {}
    for b in sorted({r["block"] for r in items}):
        nos = [r["no"] for r in items if r["block"] == b]
        c = Counter(nos)
        dups[b] = sorted(n for n, k in c.items() if k > 1)
        gaps[b] = [n for n in range(1, max(nos) + 1) if n not in c]

    footer_tags = [f["tag"] for f in footers]
    own = [t for t in footer_tags if not t.startswith("000_")]
    rev = own[0] if own else ""
    card = {
        "card_version": CARD_VERSION,
        "source": "blank form PDF — text layer and rules only (spike/valve_form_learn.py); values are not in the blank form",
        "form_id": form_id,
        "title": name,
        "printed_title": title,
        "item_kind": kind,
        "form_no_printed": printed_no or None,
        "footer_tag": own[0] if own else (footer_tags[0] if footer_tags else ""),
        "footer_tags": footers,
        "revision_tag": ("form " + rev) if rev else "",
        "page_size": sizes.most_common(1)[0][0],
        "pages": len(doc),
        "page_roles": page_roles,
        "identify": [],
        "blocks": [],
        "items": [],
        "notes_region": notes,
        "required": {"status": "suggested — to be confirmed by the user", "keys": []},
        "tag_key_rule": "match tags by uppercase with spaces, hyphens and underscores removed (FT-1001A = FT 1001 A → FT1001A)",
        "numbering": {"gaps": {str(k): v for k, v in gaps.items()}, "duplicates": {str(k): v for k, v in dups.items()},
                      "allowed_gaps": {}},
        "ambiguous": ambiguous,
        "notes": [],
    }
    for b in sorted({r["block"] for r in items}):
        rs = [r for r in items if r["block"] == b]
        secs = []
        for r in rs:
            if r["section"] and r["section"] not in secs:
                secs.append(r["section"])
        card["blocks"].append({"block": b, "pages": sorted({r["page"] for r in rs}), "first": min(r["no"] for r in rs),
                               "last": max(r["no"] for r in rs), "n_items": len(rs), "sections": secs})
    for r in items:
        it = {"no": r["no"], "block": r["block"], "label": r["label"], "section": r["section"],
              "section_printed": r["section_raw"], "page": r["page"], "label_bbox": r["label_bbox"],
              "value_bbox": r["value_bbox"], "subcols": r["subcols"], "std_key": r["std_key"], "process": r["process"],
              "role": r["role"]}
        subl = [dict(x) for x in r["inline_labels"]]
        if not r["small_subcols"] and r["role"] != "header" and not r.get("subcols_from"):
            subl += [{"text": t, "bbox": bb} for t, bb in zip(r["subcols"], r["subcol_bboxes"]) if (bb[3] - bb[1]) >= 8.2]
        for x in subl:
            k, _ = std_of(x["text"], r["section"], form_id)
            x["std_key"] = k
        if subl:
            it["sublabels"] = subl
        for k in ("std_keys_also", "options", "subcols_from", "unit_printed"):
            if r.get(k):
                it[k] = r[k]
        if r["value_cells"]:
            it["value_cells"] = r["value_cells"]
        if r["parent"]:
            it["parent"] = r["parent"]
        card["items"].append(it)
    # identification — printed marks only (form number, footer tag, printed title); labels/sections added in post_fix
    ident = []
    if printed_no:
        ident.append({"kind": "text", "regex": rf"Form\s+No\s*:\s*{printed_no}\b"})
    if rev:
        ident.append({"kind": "text", "regex": r"form\s+" + re.escape(rev).replace(r"\ ", r"\s+")})
    if title:
        ident.append({"kind": "text", "regex": re.escape(title).replace(r"\ ", r"\s+")})
    ident.append({"kind": "file_name", "regex": rf"(?:^|[^0-9]){code}(?:[-_ .]|$)"})
    card["identify"] = ident
    present = {r["std_key"] for r in items} | {k for r in items for k in r.get("std_keys_also", [])}
    req = [k for k in SUGGESTED_REQUIRED if k in present]
    req += [r["std_key"] for r in items if r["process"] and r["std_key"] not in req]
    card["required"]["keys"] = req
    doc.close()
    return card


# ── lists ───────────────────────────────────────────────────────────────────────────────────────────────────

def list_pdf_headers(path):
    """Column headers of a list template: words of the header band grouped by the vertical rules; stacked lines kept."""
    doc = pymupdf.open(path)
    page = doc[0]
    ws = page.get_text("words")
    vs, hs = rules(page)
    small = [w for w in ws if (w[3] - w[1]) < 8.5 and w[1] > 140]
    if not small:
        return {}
    y0, y1 = min(w[1] for w in small) - 1, max(w[3] for w in small) + 1
    xs = sorted({round(x, 1) for x, a, b in vs if a <= y0 + 2 and b >= y1 - 2})
    xs = [x for i, x in enumerate(xs) if not i or x - xs[i - 1] > 3]
    cols = []
    for a, b in zip(xs, xs[1:]):
        cw = [w for w in small if a <= cx(w) < b]
        if not cw:
            continue
        stacked = [re.sub(r"\s*/$", "", " ".join(w[4] for w in ln)).strip() for ln in lines_of(cw)]
        stacked = [t for t in stacked if t]
        cols.append({"x0": a, "x1": b, "lines": stacked, "header": " / ".join(stacked)})
    unread = [w[4] for w in small if not any(c["x0"] <= cx(w) < c["x1"] for c in cols)]
    big = [w for w in ws if (w[3] - w[1]) > 13]
    out = {"file_hint": re.sub(r"^[0-9a-f]{8}-", "", os.path.basename(path)), "title": text_of(big),
           "page_size": f"{round(page.rect.width)}x{round(page.rect.height)} pt",
           "orientation": "landscape" if page.rect.width > page.rect.height else "portrait",
           "paper": "A4" if sorted((round(page.rect.width), round(page.rect.height))) == [595, 842] else "other",
           "pages": len(doc), "header_rows": len(lines_of(small)), "columns": cols,
           "not_read": unread,
           "title_block_fields": [t for t in ("Domain", "Plant", "Area", "Unit", "Document No.", "Revision No.",
                                              "Revision Date.", "By", "Page", "Print Date") if t.split()[0] in
                                  {w[4].rstrip(":.") for w in ws if w[1] < 140}],
           "note": "title-block values (site / domain names) are not recorded"}
    doc.close()
    return out


def line_list(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    res = {"file_hint": re.sub(r"^[0-9a-f]{8}-", "", os.path.basename(path)), "sheets": wb.sheetnames, "tables": []}
    for ws in wb.worksheets:
        hdr = None
        for r in range(1, min(ws.max_row, 30) + 1):
            vals = [str(c.value).strip().upper() if c.value is not None else "" for c in ws[r]]
            if "LINE NUMBER" in vals or "LINE NO." in vals:
                hdr = r
                break
        if not hdr:
            res["tables"].append({"sheet": ws.title, "role": "cover / no line table"})
            continue
        merged = {}
        for mr in ws.merged_cells.ranges:
            if mr.min_row <= hdr + 2 and mr.max_row >= hdr:
                for rr in range(mr.min_row, mr.max_row + 1):
                    for cc in range(mr.min_col, mr.max_col + 1):
                        merged[(rr, cc)] = ws.cell(mr.min_row, mr.min_col).value
        # unit / sub-header rows: the rows below the header that hold no line number pattern
        last = hdr
        for r in range(hdr + 1, hdr + 4):
            a = ws.cell(r, 1).value
            if a is not None and re.search(r"\d", str(a)) and len(str(a)) > 6:
                break
            last = r
        cols = []
        for c in range(1, ws.max_column + 1):
            parts = []
            for r in range(hdr, last + 1):
                v = merged.get((r, c), ws.cell(r, c).value)
                v = re.sub(r"\s+", " ", str(v)).strip() if v is not None else ""
                if v and v not in parts:
                    parts.append(v)
            if parts:
                cols.append({"col": openpyxl.utils.get_column_letter(c), "header": " / ".join(parts), "parts": parts})
        notes_row = next((r for r in range(last + 1, ws.max_row + 1)
                          if str(ws.cell(r, 1).value or "").strip().upper().startswith("NOTES")), None)
        end = notes_row or ws.max_row + 1
        data = [r for r in range(last + 1, end) if str(ws.cell(r, 1).value or "").strip()]
        ex = [str(ws.cell(r, 1).value).strip() for r in data[:3]]
        res["tables"].append({"sheet": ws.title, "header_rows": [hdr, last], "first_data_row": last + 1,
                              "n_data_rows": len(data), "notes_block_row": notes_row, "sheet_max_row": ws.max_row,
                              "columns": cols, "example_line_no": ex})
    return res


def process_data_note(path):
    doc = pymupdf.open(path)
    sizes = Counter(f"{round(p.rect.width)}x{round(p.rect.height)}" for p in doc)
    titles = Counter()
    for p in doc:
        for ln in lines_of([w for w in p.get_text("words") if w[1] < 70 and (w[3] - w[1]) < 8.5]):
            t = " ".join(w[4] for w in ln)
            if t.lower().startswith("process data for"):
                titles[t] += 1
    hdr_words = []
    for p in doc:
        t = p.get_text()
        if "Sr" in t and "Tag" in t and "Number" in t:
            ws = [w for w in p.get_text("words") if 70 < w[1] < 110]
            hdr_words = [" ".join(w[4] for w in ln) for ln in lines_of(ws)]
            break
    out = {"file_hint": re.sub(r"^[0-9a-f]{8}-", "", os.path.basename(path)), "pages": len(doc), "page_sizes": dict(sizes),
           "table_titles": dict(titles), "header_lines_sample": hdr_words[:5],
           "layout": "cover page (A4 portrait) + notes page, then A3-landscape tables: 3 header lines + 1 unit line, "
                     "one row per tag numbered by 'Sr no.'; read by app/valve/process.py"}
    doc.close()
    return out


# ── main ────────────────────────────────────────────────────────────────────────────────────────────────────

def main(src, out):
    os.makedirs(out, exist_ok=True)
    cards = []
    for path in sorted(glob.glob(os.path.join(src, "*.pdf"))):
        code = code_of(path)
        if code not in FORMS:
            continue
        cards.append(learn(path))
    cards.sort(key=lambda c: int(c["form_id"]))
    post_fix(cards)
    index = []
    for c in cards:
        with open(os.path.join(out, f"{c['form_id']}.json"), "w", encoding="utf-8") as f:
            f.write(dump_card(c))
        secs = []
        for b in c["blocks"]:
            secs += [s for s in b["sections"] if s not in secs]
        index.append({"form_id": c["form_id"], "title": c["title"], "kind": c["item_kind"], "footer_tag": c["footer_tag"],
                      "pages": c["pages"], "page_size": c["page_size"], "n_items": len(c["items"]),
                      "blocks": [[b["first"], b["last"]] for b in c["blocks"]], "sections": secs})
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as f:
        f.write("[\n" + ",\n".join(json.dumps(r, ensure_ascii=False) for r in index) + "\n]\n")
    lists = {"note": "headers only — no data rows (2-3 example Line No. strings at most)",
             "tag_key_rule": "uppercase, spaces / hyphens / underscores removed (FT-1001A = FT 1001 A)"}
    for key, pat in (("instrument_index", "*Instrument_Index*.pdf"), ("io_list", "*IO_List*.pdf")):
        p = glob.glob(os.path.join(src, pat))
        lists[key] = list_pdf_headers(p[0]) if p else None
    lists["process_line_list"] = {}
    for p in sorted(glob.glob(os.path.join(src, "*PR-LIS-00002*.xlsx"))):
        b = os.path.basename(p)
        side = "south" if "-999-" in b else "north"
        lists["process_line_list"][side] = line_list(p)
    p = glob.glob(os.path.join(src, "*Process_Data*.pdf"))
    lists["process_data_sample"] = process_data_note(p[0]) if p else None
    with open(os.path.join(out, "lists.json"), "w", encoding="utf-8") as f:
        json.dump(lists, f, ensure_ascii=False, indent=1)
        f.write("\n")
    # verification table
    print(f"{'form':>5} {'kind':9} {'pages':>5} {'plan N':>6} {'found':>14} {'gaps':12} {'dups':6} {'blank':>5} sections")
    for c in cards:
        found = " + ".join(f"{b['first']}-{b['last']}" for b in c["blocks"])
        gaps = "; ".join(f"b{k}:{v}" for k, v in c["numbering"]["gaps"].items() if v) or "-"
        dups = "; ".join(f"b{k}:{v}" for k, v in c["numbering"]["duplicates"].items() if v) or "-"
        secs = sorted({it["section"] for it in c["items"]}, key=lambda s: next(i for i, it in enumerate(c["items"]) if it["section"] == s))
        blank = sum(1 for it in c["items"] if not it["label"])
        print(f"{c['form_id']:>5} {c['item_kind']:9} {c['pages']:>5} {PLAN.get(c['form_id'], '?'):>6} {found:>14} {gaps:12} {dups:6} {blank:>5} "
              + " · ".join(s or '∅' for s in secs))


def dump_card(c):
    """Readable, diff-friendly JSON: top-level keys one per line, one item / one list entry per line."""
    out = []
    for k, v in c.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            body = ",\n".join("  " + json.dumps(x, ensure_ascii=False) for x in v)
            out.append(f" {json.dumps(k)}: [\n{body}\n ]")
        else:
            out.append(f" {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}")
    return "{\n" + ",\n".join(out) + "\n}\n"


def post_fix(cards):
    """Card-level facts that need all forms: shared footers, identification marks unique to one form."""
    by_footer = Counter(c["footer_tag"] for c in cards if c["footer_tag"])
    lab_forms, sec_forms = {}, {}
    for c in cards:
        for it in c["items"]:
            lab_forms.setdefault(norm(it["label"]), set()).add(c["form_id"])
            sec_forms.setdefault(it["section"], set()).add(c["form_id"])
    for c in cards:
        if not c["footer_tag"]:
            c["notes"].append("no 'form NNN_Rx' footer printed")
        elif by_footer[c["footer_tag"]] > 1:
            others = [o["form_id"] for o in cards if o["footer_tag"] == c["footer_tag"] and o is not c]
            c["notes"].append(f"footer tag {c['footer_tag']} is shared with form {', '.join(others)} — do not identify by footer alone")
        if not c["form_no_printed"]:
            c["notes"].append("no 'Form No :' printed — identified by file name and item composition")
        if c["form_id"] == "5063":
            c["notes"].append("printed title says RADAR LEVEL TRANSMITTER; kind 'gwr' comes from the file name and the "
                              "probe items (Probe Type / Probe Length / Material - Probe)")
        if c["form_id"] == "606":
            c["notes"].append("no title block printed (no Form No / title / DOCUMENT NO.); items are the 605 items with "
                              "section GAUGE printed as METER")
        if c["form_id"] == "101":
            c["notes"].append("two numbered tables: block 1 = sheet 1 rows 1-100 (two columns, 1-52 | 53-100), "
                              "block 2 = sheet 2 Process / Sizing rows 1-38 (footer 101+102_R6.04)")
        uniq = []
        for it in c["items"]:
            n = norm(it["label"])
            if n and len(n) > 6 and lab_forms[n] == {c["form_id"]} and it["label"] not in uniq:
                uniq.append(it["label"])
        c["identify"] = [x for x in c["identify"] if x["kind"] not in ("label", "section")]
        c["identify"] += [{"kind": "label", "text": u} for u in uniq[:3]]
        secs = [s for s in dict.fromkeys(it["section"] for it in c["items"]) if s and sec_forms[s] == {c["form_id"]}]
        c["identify"] += [{"kind": "section", "text": s} for s in secs[:2]]
        if not uniq and not secs:
            c["notes"].append("no label or section unique to this form — identification needs the form number or file name")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
