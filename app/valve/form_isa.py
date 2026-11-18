"""valve41 — the ISA-20 style 'INSTRUMENT SPECIFICATION' sheet (Control Valve · Self-actuated Pressure Regulator).

Company PC 2026-11-18: the South control-valve / regulator datasheets were not read (one datasheet without a tag for a
40-page document).  They are printed on another form than the ones the readers knew:

  · numbered rows in two columns (1-55 left, 56-83 right), NO colon between label and value, one font for both
  · every label and every value sits in its own ruled cell: | no | label (| label2) | value (| value2 …) |
  · rows 1-30 use the whole width, rows 31-55 / 56-83 share it; a caption column left of each number column names the
    block (GENERAL · PIPE LINE · PROCESS CONDITIONS · BODY AND TRIM · ACTUATOR · POSITIONER · SOLENOID VALVE · …)
  · the process rows have four value cells under a caption row 'Units | @ Max. Flow | @ Norm. Flow | @ Min. Flow'
  · the title block is at the BOTTOM ('INSTRUMENT SPECIFICATION', Sheet x of y, Code, Doc. No., Rev., revision lines)

Read by the rules of the page itself — no coordinate is fixed: the label / value boundary of a block is the vertical rule
that crosses the most rows of that block; cells are the spaces between the rules that cross the row.  Labels are filed by
(label, block caption) — the same label means different things in different blocks (MFR · Model · Type).
"""
from __future__ import annotations

import re
from collections import Counter

from app.valve import schema

FORM = "ISA20"

# (label, block word or None, key, section, display) — first match wins.  Block words are matched in the caption with
# spaces removed ('BODYANDTRIM', 'SOLENOIDVALVE').
_L = [
    ("tag no.", "GENERAL", "tag", "general", "Tag Number"),
    ("service", "GENERAL", "service", "general", "Service Description"),
    ("line no.", None, "line_no", "general", "Line Number"),
    ("p&id", None, "pid_no", "general", "P&ID Number"),
    ("area classification", None, "area_class", "special", "Hazardous Area Class"),
    ("ambient temperature min.", None, "ambient_temp_min", "basis", "Ambient Temperature (Min)"),
    ("ambient temperature max.", None, "ambient_temp_max", "basis", "Ambient Temperature (Max)"),
    ("allowable sound pressure level dba", None, "spl_allow", "sizing", "Allowable SPL"),
    ("allowable sound pressure level", None, "spl_allow", "sizing", "Allowable SPL"),
    ("tightness requirements", None, "leakage_class", "mechanical", "Leakage Class"),
    ("available air supply pressure min.", None, "ia_pressure_min", "accessories", "Instrument Air Supply Pressure (Min)"),
    ("available air supply pressure max.", None, "ia_pressure_max", "accessories", "Instrument Air Supply Pressure (Max)"),
    ("power failure position", None, "power_fail_position", "actuator", "Power Failure Position"),
    ("weather protection / certificate", None, "ingress", "special", "Weather Protection / Certificate"),
    ("line size and schedule inlet", None, "line_size_inlet", "mechanical", "Line Size (Inlet)"),
    ("line size and schedule outlet", None, "line_size_outlet", "mechanical", "Line Size (Outlet)"),
    ("pipe material", None, "pipe_material", "mechanical", "Pipe Material"),
    ("pipe insulation", None, "pipe_insulation", "mechanical", "Pipe Insulation"),
    ("process fluid", None, "fluid", "process", "Fluid"),
    ("upstream condition", None, "fluid_state", "process", "Fluid State"),
    ("differential pressure", None, "diff_pressure", "process", "Differential Pressure"),
    ("mfr", "BODY", "manufacturer", "general", "Manufacturer"),
    ("model", "BODY", "model", "general", "Model Number"),
    ("body type", None, "body_type", "mechanical", "Valve Type"),
    ("body size", None, "body_size", "mechanical", "Valve Size"),
    ("trim size", None, "trim_size", "trim", "Trim Size"),
    ("rated cv", None, "rated_cv", "trim", "Rated Cv"),
    ("characteris.", None, "flow_char", "trim", "Flow Characteristic"),
    ("characteristic", None, "flow_char", "trim", "Flow Characteristic"),
    ("end connec. & rating", None, "connections", "mechanical", "End Connection & Rating"),
    ("body material", None, "body_material", "mechanical", "Body Material"),
    ("bonnet type", None, "bonnet_type", "mechanical", "Bonnet Type"),
    ("material", "BODY", "bonnet_material", "mechanical", "Bonnet Material"),
    ("flow direction", None, "flow_direction", "mechanical", "Flow Direction"),
    ("flow action to", None, "flow_action", "mechanical", "Flow Action To"),
    ("lubricator", None, "lubricator", "accessories", "Lubricator"),
    ("isolat. valve", None, "lubricator_isolation", "accessories", "Lubricator Isolation Valve"),
    ("guiding", None, "guiding", "trim", "Guiding"),
    ("no. of ports", None, "ports", "trim", "No. of Ports"),
    ("trim type", None, "trim_type", "trim", "Trim Type"),
    ("rated travel", None, "rated_travel", "trim", "Rated Travel"),
    ("plug/ ball/ disk material", None, "ball_material", "trim", "Plug / Ball / Disc Material"),
    ("plug/ball/disk material", None, "ball_material", "trim", "Plug / Ball / Disc Material"),
    ("seat material", None, "seat_material", "trim", "Seat Material"),
    ("cage", None, "cage_material", "trim", "Cage / Guide Material"),
    ("stem material", None, "stem_material", "trim", "Stem Material"),
    ("gasket material", None, "gasket_material", "mechanical", "Gasket Material"),
    ("packing material", None, "packing_material", "mechanical", "Packing Material"),
    ("mfr", "ACTUATOR", "act_manufacturer", "actuator", "Actuator Manufacturer"),
    ("model", "ACTUATOR", "act_model", "actuator", "Actuator Model"),
    ("type", "ACTUATOR", "act_type", "actuator", "Actuator Type"),
    ("size", "ACTUATOR", "act_size", "actuator", "Actuator Size"),
    ("area", "ACTUATOR", "act_area", "actuator", "Actuator Effective Area"),
    ("air failure valve", None, "fail_position", "actuator", "Air Failure Action"),
    ("handwheel location", None, "handwheel", "accessories", "Handwheel"),
    ("bench range", None, "bench_range", "actuator", "Bench Range"),
    ("case/yoke material", None, "act_material", "actuator", "Actuator Case / Yoke Material"),
    ("mfr", "POSITIONER", "pos_manufacturer", "positioner", "Positioner Manufacturer"),
    ("model", "POSITIONER", "pos_model", "positioner", "Positioner Model"),
    ("signal: inlet", None, "pos_signal", "positioner", "Positioner Input Signal"),
    ("outlet", "POSITIONER", "pos_output", "positioner", "Positioner Output Signal"),
    ("increase signal valve", None, "pos_action", "positioner", "Increase Signal — Valve"),
    ("cam characteristic", None, "pos_cam", "positioner", "Cam Characteristic"),
    ("bypass", None, "pos_bypass", "positioner", "Positioner Bypass"),
    ("gauges", "POSITIONER", "pos_gauges", "positioner", "Positioner Gauges"),
    ("pos.tx. tag no.", None, "pos_tx_tag", "accessories", "Position Transmitter Tag No."),
    ("positioner tag", None, "pos_tag", "positioner", "Positioner Tag"),
    ("mfr", "SOLENOID", "sov_manufacturer", "accessories", "Solenoid Valve Manufacturer"),
    ("model", "SOLENOID", "sov_model", "accessories", "Solenoid Valve Model"),
    ("type", "SOLENOID", "sov_type", "accessories", "Solenoid Valve Type"),
    ("when de-enegr.valve", None, "sov_energize", "accessories", "Solenoid Valve — When De-energised"),
    ("when de-energ.valve", None, "sov_energize", "accessories", "Solenoid Valve — When De-energised"),
    ("mfr", "SWITCHES", "sw_manufacturer", "accessories", "Limit Switch Manufacturer"),
    ("model", "SWITCHES", "sw_model", "accessories", "Limit Switch Model"),
    ("type", "SWITCHES", "sw_type", "accessories", "Limit Switch Type"),
    ("quantity", "SWITCHES", "sw_qty", "accessories", "Limit Switch Quantity"),
    ("contacts / rating", None, "sw_contact", "accessories", "Limit Switch Contacts / Rating"),
    ("switching position", None, "sw_position", "accessories", "Switching Position"),
    ("mfr", "AIRSET", "afr_manufacturer", "accessories", "Air Set Manufacturer"),
    ("model", "AIRSET", "afr_model", "accessories", "Air Set Model"),
    ("set pressure", None, "afr_set", "accessories", "Air Set — Set Pressure"),
    ("filter", None, "afr", "accessories", "Air Filter Regulator"),
    ("gauge", "AIRSET", "afr_gauge", "accessories", "Air Set Gauge"),
    ("tubing/fit material", None, "tubing", "accessories", "Tubing / Fitting Material"),
    ("air tube material", None, "tubing", "accessories", "Air Tube Material"),
    ("hydro. pressure", None, "hydro_test", "special", "Hydrostatic Test"),
    ("leakage", "TESTS", "leak_test", "special", "Seat Leakage Test"),
    ("manufacturer", "PURCHASE", "po_manufacturer", "purchase", "Purchase — Manufacturer"),
    ("model", "PURCHASE", "po_model", "purchase", "Purchase — Model"),
    ("purchase order num.", None, "po_no", "purchase", "Purchase Order No."),
    ("price", None, "po_price", "purchase", "Price"),
    ("item number", None, "po_item", "purchase", "Item Number"),
    ("serial number", None, "serial_no", "purchase", "Serial No."),
]
# the Max / Norm / Min rows (same keys as the Form 101 process sheet, so the Process Data comparison is the same)
_PROC = {"flow rate": ("flow", "process", "Flow Rate"), "inlet pressure": ("inlet_pressure", "process", "Inlet (Upstream) Pressure"),
         "pressure drop": ("pressure_drop", "process", "Pressure Drop"), "inlet temperature": ("op_temp", "process", "Operating Temperature"),
         "inlet density / specific gravity / molecular mass": ("density", "process", "Density / SG / Molecular Mass"),
         # phase-dependent properties: kept and compared, but not 'missing process data' when blank (as on Form 101 sheet 2)
         "inlet compressibility factor": ("z_factor", "sizing", "Compressibility Factor"),
         "inlet viscosity": ("viscosity", "sizing", "Viscosity"), "inlet specific heats ratio": ("cp_cv", "sizing", "Specific Heat Ratio"),
         "inlet vapour pressure": ("vapor_pressure", "sizing", "Vapor Pressure"),
         "start-up flow (min / nor / max)": ("startup_flow", "sizing", "Start-up Flow"),
         "flow coefficient cv": ("calc_cv", "sizing", "Calculated Cv"), "travel": ("travel", "sizing", "Travel of Valve"),
         "sound pressure level": ("spl_pred", "sizing", "Predicted SPL")}
_CASES = (("max", "Max"), ("nor", "Nor"), ("min", "Min"))
_RATING = re.compile(r"(?:CL(?:ASS)?\.?\s*\d{3,4}|\d{3,4}\s*(?:#|LB\b))", re.I)
_SIZE_SCH = re.compile(r"^(\S+)\s*(in|inch|mm|\")\s+(\S.*)$", re.I)
_UNITS = {"in", "mm", "%", "dba", "psi", "bar-g", "barg", "bar", "°c", "ºc", "cp", "kg/m³", "kg/m3", "pa-a"}
_UNIT_ONLY = {"in", "mm", "%", "dba", "psi", "bar-g", "barg", "bar", "°c", "ºc", "cp", "kg/m³", "kg/m3", "pa-a", "-", "aus gal/min"}


def _ex():
    from app.valve import extract                         # extract imports this module lazily — no import cycle
    return extract


def _n(label: str) -> str:
    return schema.norm_label(label).rstrip(" :")


def _blk(caption: str) -> str:
    return re.sub(r"[^A-Z]", "", (caption or "").upper())


def lookup(label: str, block: str):
    n, b = _n(label), _blk(block)
    for lab, bw, key, sec, disp in _L:
        if n == lab and (bw is None or bw in b):
            return key, sec, disp
    return None


def is_isa(page, words, cols) -> bool:
    """Two number columns, 'INSTRUMENT SPECIFICATION' printed under the table, and labels without a colon."""
    if len(cols) < 2:
        return False
    low_y = max(w[3] for c in cols for w in c)
    low = " ".join(w[4].upper() for w in sorted((w for w in words if w[1] > low_y), key=lambda w: (round(w[1]), w[0])))
    return "INSTRUMENT SPECIFICATION" in low


def _status(value: str) -> str:
    if not value:
        return "blank"
    return "placeholder" if schema.norm_label(value) in schema.PLACEHOLDERS else "ok"


def _txt(ws) -> str:
    return " ".join(w[4] for w in sorted(ws, key=lambda w: (round(w[1] / 3), w[0]))).strip()


def _row(n, block, label, key, sec, disp, vws, lws, cell, known=True, unit=""):
    ex = _ex()
    value = _txt(vws)
    st = _status(value)
    if not known:
        st = "review" if value else "blank"
    return {"row": n, "group": block, "label": label, "key": key, "section": sec, "display": disp, "value": value, "unit": unit,
            "bbox": ex._bbox(vws) or [round(v, 1) for v in cell], "label_bbox": ex._bbox(lws), "status": st, "heading": ""}


def read_page(page, page_no, words, cols):
    """One ISA-20 sheet 1 → the same sheet dict the other readers give ({page, doc_no, rev, sheet, of, tag, rows, notes, form})."""
    ex = _ex()
    vert = ex._verticals(page)
    cols = sorted(cols, key=lambda c: min(w[0] for w in c))[:2]
    left, right = cols[0], cols[1]
    x_frame1 = max(x for x, *_ in vert)
    ys_all = sorted((w[1] + w[3]) / 2 for c in cols for w in c)
    gaps = sorted(b - a for a, b in zip(ys_all, ys_all[1:]) if b - a > 2)
    pitch = gaps[len(gaps) // 2] if gaps else 11.0
    r_y0, r_y1 = min(w[1] for w in right) - pitch / 2, max(w[3] for w in right) + pitch / 2
    r_x0 = min(w[0] for w in right)

    def band(col, i):
        y = (col[i][1] + col[i][3]) / 2
        a = ((col[i - 1][1] + col[i - 1][3]) / 2 + y) / 2 if i else y - pitch / 2
        b = ((col[i + 1][1] + col[i + 1][3]) / 2 + y) / 2 if i + 1 < len(col) else y + pitch / 2
        return y, max(a, y - pitch * 0.6), min(b, y + pitch * 0.6)

    # the three blocks: left rows over the whole width · left rows beside the right column · the right column
    blocks = {"A": [], "B": [], "R": []}
    for i, w in enumerate(left):
        y, a, b = band(left, i)
        blocks["B" if r_y0 <= y <= r_y1 else "A"].append((w, y, a, b))
    for i, w in enumerate(right):
        y, a, b = band(right, i)
        blocks["R"].append((w, y, a, b))

    def limits(name, w, y):
        """(x after the number cell, right end of the row)."""
        x0 = max(v[2] for v in (right if name == "R" else left))
        xs = ex._xs_at(vert, y, x0, x_frame1)
        if name != "B":
            return x0, (xs[-1] if xs else x_frame1)
        lefts = [x for x in xs if x <= r_x0 + 1]            # … | caption column | right numbers: the row ends before the caption column
        return x0, (lefts[-2] if len(lefts) >= 2 else (lefts[-1] if lefts else r_x0))

    def divider(name):
        cover = Counter()
        for w, y, a, b in blocks[name]:
            x0, x1 = limits(name, w, y)
            for x in ex._xs_at(vert, y, x0, x1):
                if x0 + 12 < x < x1 - 12:
                    cover[round(x)] += 1
        if not cover:
            return None
        top = max(cover.values())
        return min(x for x, c in cover.items() if c >= top * 0.9)   # the rule (nearly) every row of the block has

    # block captions: the cell left of each number column (between the two rules left of the numbers), one caption per
    # ruled band of that cell
    def captions(col):
        x_num0 = min(w[0] for w in col)
        y_mid = (col[len(col) // 2][1] + col[len(col) // 2][3]) / 2
        lefts = [x for x in ex._xs_at(vert, y_mid, 0, x_num0) if x <= x_num0 + 1]
        if len(lefts) < 2:
            return []
        xa, xb = lefts[-2], lefts[-1]
        ya, yb = min(w[1] for w in col) - pitch, max(w[3] for w in col) + pitch
        cw = [w for w in words if xa - 1 <= w[0] and w[2] <= xb + 1 and ya <= w[1] <= yb and re.fullmatch(r"[A-Z/&.]+", w[4])]
        hz = sorted({round(y, 1) for y in ex._horizontals(page, xa + 4, xb - 4) if ya <= y <= yb})
        hz = [ya] + hz + [yb]
        out = []
        for a, b in zip(hz, hz[1:]):
            if b - a > 4:
                t = " ".join(w[4] for w in sorted((w for w in cw if a <= (w[1] + w[3]) / 2 <= b), key=lambda w: (round(w[1]), w[0])))
                out.append((a, b, t))
        return out

    caps = {"A": captions(left), "B": captions(left), "R": captions(right)}

    def block_of(name, y):
        return next((t for a, b, t in caps[name] if a <= y <= b), "")

    num_ids = {id(w) for c in cols for w in c}
    rows, hdr_cells = [], None
    for name in ("A", "B", "R"):
        xd = divider(name)
        for w, y, a, b in blocks[name]:
            n = int(w[4])
            x0, x1 = limits(name, w, y)
            if xd is None:
                continue
            rw = [v for v in words if id(v) not in num_ids and a <= (v[1] + v[3]) / 2 <= b and x0 - 1 <= (v[0] + v[2]) / 2 <= x1 + 1]
            xs = [x for x in ex._xs_at(vert, y, x0, x1) if x0 - 2 <= x <= x1 + 2]
            lab_b = [x0] + [x for x in xs if x0 + 3 < x < xd - 3] + [xd]
            val_b = [xd] + [x for x in xs if xd + 3 < x < x1 - 8] + [x1]
            lcells = [[v for v in rw if p <= (v[0] + v[2]) / 2 < q] for p, q in zip(lab_b, lab_b[1:])]
            vcells = [([v for v in rw if p <= (v[0] + v[2]) / 2 < q], (p, a, q, b)) for p, q in zip(val_b, val_b[1:])]
            lcells = [c for c in lcells if c]
            merged = []                                     # a cell that holds only the printed unit belongs to the value before it
            for c, box in vcells:
                if not c and box[2] - box[0] < 8:           # the gap of a double rule, not a cell
                    continue
                if merged and c and _txt(c).lower() in _UNITS:
                    pc, pb = merged[-1]
                    merged[-1] = (pc + c, (pb[0], pb[1], box[2], pb[3]))
                else:
                    merged.append((c, box))
            vcells = merged
            blk = block_of(name, y)
            labels = [_txt(c) for c in lcells]
            if not labels:
                vt = [_txt(c).lower() for c, _ in vcells]
                if len(vcells) >= 4 and vt[0].startswith("unit") and any("max" in t for t in vt):   # the caption row of the process table
                    hdr_cells = [(p, q) for _, (p, _a, q, _b) in vcells]
                continue
            head = _n(labels[0])
            # ── process rows: Units | Max | Norm | Min ────────────────────────────────────────────────
            if head in _PROC and hdr_cells and len(labels) == 1:
                key, sec, disp = _PROC[head]
                cells = [[v for v in rw if p - 1 <= (v[0] + v[2]) / 2 < q - 1] for p, q in hdr_cells]
                unit = _txt(cells[0]) if cells else ""
                unit = re.sub(r"\s*-$", "", unit).strip()
                for (ck, cn), cws, (p, q) in zip(_CASES, cells[1:4], hdr_cells[1:4]):
                    rows.append(_row(n, blk, f"{labels[0]} ({cn})", f"{key}.{ck}", sec, f"{disp} ({cn})", cws, lcells[0], (p, a, q, b), unit=unit))
                continue
            # ── label / value pairs ───────────────────────────────────────────────────────────────────
            parts = [f"{labels[0].rstrip(' :')} {lb}" for lb in labels[1:]]
            if len(labels) == 3 and all(lookup(pl, blk) for pl in parts) and len(vcells) >= 2:
                # 'Ambient Temperature: | Min. | Max.' · 'Line Size and Schedule | Inlet | Outlet' = a heading and two parts:
                # the value cells left / right of the rule nearest the middle of the value space belong to each part
                inner = [bx[0] for _, bx in vcells[1:]]
                mid = min(inner, key=lambda x: abs(x - (xd + x1) / 2))
                g1 = [(c, bx) for c, bx in vcells if bx[0] < mid - 0.5]
                g2 = [(c, bx) for c, bx in vcells if bx[0] >= mid - 0.5]
                pairs = []
                for pl, lc, g in zip(parts, lcells[1:], (g1, g2)):
                    ws_ = [v for c, _ in g for v in c]
                    pairs.append((pl, lc, (ws_, (g[0][1][0], a, g[-1][1][2], b))))
            elif len(labels) == len(vcells) + 1 and len(labels) > 1:    # a heading + its parts, one value cell each
                pairs = [(pl, lc, vc) for pl, lc, vc in zip(parts, lcells[1:], vcells)]
            elif len(labels) > 2 and len(vcells) == 2 * (len(labels) - 1):   # 'Line Size and Schedule | Inlet | Outlet' = size · schedule each
                pairs = []
                for i, (lb, lc) in enumerate(zip(labels[1:], lcells[1:])):
                    (c1, b1), (c2, b2) = vcells[2 * i], vcells[2 * i + 1]
                    pairs.append((f"{labels[0].rstrip(' :')} {lb}", lc, (c1 + c2, (b1[0], b1[1], b2[2], b1[3]))))
            elif len(labels) == len(vcells):
                pairs = list(zip(labels, lcells, vcells))
            elif len(labels) == 1:                                      # one label, several value cells: one value
                allw = [v for c, _ in vcells for v in c]
                pairs = [(labels[0], lcells[0], (allw, (xd, a, x1, b)))]
            else:                                                       # more labels than value cells: by position
                pairs = []
                for i, (lb, lc) in enumerate(zip(labels, lcells)):
                    vc = vcells[i] if i < len(vcells) else ([], (xd, a, x1, b))
                    pairs.append((lb, lc, vc))
            for lb, lc, (vws, cell) in pairs:
                hit = lookup(lb, blk)
                if hit:
                    key, sec, disp = hit
                else:
                    key, sec, disp = "x." + re.sub(r"[^a-z0-9]+", "_", _n(lb)).strip("_"), "general", lb
                r = _row(n, blk, lb, key, sec, disp, vws, lc, cell, known=bool(hit))
                _refine(r, rows, n, blk)
                rows.append(r)
    rows.sort(key=lambda r: (r["row"], (r.get("bbox") or [0])[0]))
    last_y = max(w[3] for c in cols for w in c)
    ft = _forms().footer(page, words, last_y)
    title_w = _txt([w for w in words if w[1] > last_y and re.fullmatch(r"[A-Za-z/&.\-]+", w[4])
                    and _between_title(w, words, last_y)])
    hdr = {"doc_no": ft.get("doc_no", ""), "rev": ft.get("rev", ""), "sheet": ft.get("sheet"), "of": ft.get("of"),
           "date": ft.get("date", ""), "title": title_w, "rev_history": ft.get("rev_history", [])}
    tag = next((r["value"] for r in rows if r["key"] == "tag" and r["value"]), "")
    return {"page": page_no, **hdr, "tag": tag, "rows": rows, "notes": [], "form": FORM,
            "row_range": [int(left[0][4]), int(right[-1][4])]}


def _forms():
    from app.valve import forms_ext
    return forms_ext


def _between_title(w, words, last_y) -> bool:
    """Words of the title cell: the line(s) from 'INSTRUMENT SPECIFICATION' down to the 'Sheet … of' line, in its column."""
    ins = next((v for v in words if v[4].upper() == "INSTRUMENT" and v[1] > last_y), None)
    sh = next((v for v in words if v[4].lower() == "sheet" and v[1] > last_y), None)
    if not ins:
        return False
    y1 = sh[1] - 1 if sh else ins[3] + 40
    spec = next((v for v in words if v[4].upper() == "SPECIFICATION" and abs(v[1] - ins[1]) < 3), ins)
    return ins[1] - 1 <= w[1] <= y1 and ins[0] - 40 <= (w[0] + w[2]) / 2 <= spec[2] + 40


def _refine(r, rows, n, blk):
    """Values the cell prints together: '4 in 80' = size + schedule · 'RF,1500#' = connection + rating · a cell that holds
    only the printed unit ('in' · 'psi') is blank."""
    v = r["value"]
    if r["key"] in ("line_size_inlet", "line_size_outlet"):
        m = _SIZE_SCH.match(v)
        if m:
            r["value"], r["unit"] = m.group(1), m.group(2)
            side = "inlet" if r["key"].endswith("inlet") else "outlet"
            rows.append(dict(r, key=f"line_schedule_{side}", display=f"Line Schedule ({side.title()})", label="Schedule",
                             value=m.group(3), unit="", status=_status(m.group(3))))
    elif r["key"] == "connections":
        m = _RATING.search(v)
        if m:
            rows.append(dict(r, key="rating", display="Pressure Rating", label="Rating", value=m.group(0), status="ok"))
    if r["value"].lower() in _UNIT_ONLY and r["key"] not in ("tag",):
        if r["value"] != "-":
            r["unit"] = r["value"]
        r["value"], r["status"] = "", "blank"
    else:
        m = re.match(r"^(.*\S)\s+(in|mm|°C|ºC|bar-g|barg|psi|dBA)$", r["value"])
        if m and re.search(r"\d", m.group(1)) and r["key"] not in ("service", "line_no", "pid_no", "tag"):
            r["value"], r["unit"] = m.group(1), m.group(2)
