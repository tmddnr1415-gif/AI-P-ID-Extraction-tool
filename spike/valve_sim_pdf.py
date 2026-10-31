#!/usr/bin/env python3
"""Extraction robustness — synthetic On/Off-form datasheet PDFs with controlled layout variations (valve22).

    python3 spike/valve_sim_pdf.py [--n 200] [--seed 1] [--out /tmp/valve_sim_pdf] [--keep]

The generator draws the ruled table the CO2 PJT On/Off form (Form No 80) has — row-number column, caption column,
label cells, value column with a double rule, Max/Nor/Min unit cells on process rows, NOTES box on sheet 2, a document
page with GENERAL NOTES — from values it chooses, then perturbs the layout the way other vendors / projects do:
font size, column positions, label synonyms, missing row numbers, wrapped values, blank rows, units in their own
cell vs appended, note numbering styles, A3, 90° rotation, slight skew, hairline vs thick rules, sheet 2, scanned.
The placed values are the oracle; app.valve.extract.read_pdf is measured against them per variation.
"""
from __future__ import annotations

import argparse
import collections
import io
import random
import sys
import tempfile
import traceback
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.valve import extract, schema  # noqa: E402

# (row, caption, [(label, key)], values) — a 2-label row has two values; process rows carry a unit
ROWS = [
    (1, "GENERAL", [("Tag No.", "tag"), ("Item No.", "item_no")]),
    (2, "GENERAL", [("Manufacturer", "manufacturer"), ("Model", "model")]),
    (3, "GENERAL", [("Service", "service")]),
    (4, "GENERAL", [("PID No.", "pid_no")]),
    (5, "GENERAL", [("Line No.", "line_no")]),
    (6, "GENERAL", [("Area classification", "area_class")]),
    (7, "GENERAL", [("Tightness requirement", "tightness")]),
    (9, "PIPE DATA", [("Piping class", "piping_class")]),
    (10, "PIPE DATA", [("Line Size and Sch. Inlet", "line_size_inlet"), ("Outlet", "line_size_outlet")]),
    (11, "PIPE DATA", [("Pipe insulation", "pipe_insulation"), ("Pipe material", "pipe_material")]),
    (12, "PROCESS DATA", [("Fluid", "fluid"), ("Sour service", "sour_service")]),
    (13, "PROCESS DATA", [("Fluid State", "fluid_state"), ("Corrosive", "corrosive")]),
    (14, "PROCESS DATA", [("Operating Pressure", "op_pressure"), ("Design Pressure", "design_pressure")]),
    (15, "PROCESS DATA", [("Operating Temp.", "op_temp"), ("Design Temperature", "design_temp")]),
    (16, "PROCESS DATA", [("Max. Diff. Pressure Valve closed", "max_dp_closed")]),
    (17, "PROCESS DATA", [("Valve fail safe position", "fail_position")]),
    (21, "VALVE BODY", [("Body Size", "body_size"), ("Body Type", "body_type")]),
    (22, "VALVE BODY", [("Connections", "connections"), ("Rating", "rating")]),
    (23, "VALVE BODY", [("Leakage Class", "leakage_class"), ("Fireproofing", "fireproofing")]),
    (24, "VALVE BODY", [("Body material", "body_material")]),
    (25, "VALVE BODY", [("Ball / Disc Material", "ball_material")]),
    (26, "VALVE BODY", [("Seat Material", "seat_material"), ("Seal Material", "seal_material")]),
    (27, "VALVE BODY", [("Stem Material", "stem_material")]),
    (28, "VALVE BODY", [("Bolting / Gasket", "bolting_gasket")]),
    (29, "VALVE BODY", [("Packing Type", "packing_type")]),
    (30, "VALVE BODY", [("Packing material", "packing_material")]),
    (31, "VALVE BODY", [("Painting", "painting")]),
    (32, "VALVE BODY", [("NACE Requirement", "nace")]),
    (33, "VALVE BODY", [("SIL Requirement", "sil"), ("Fire Safe Requirement", "fire_safe")]),
    (34, "ACTUATOR", [("Manufacturer", "act_manufacturer"), ("Model No.", "act_model")]),
    (35, "ACTUATOR", [("Type", "type")]),
    (36, "ACTUATOR", [("Material", "material")]),
    (37, "ACTUATOR", [("Operating Medium", "act_medium")]),
    (40, "ACTUATOR", [("Safety Factor", "act_safety_factor")]),
    (41, "ACTUATOR", [("Action on Air Failure", "air_failure")]),
]
PROCESS_UNIT = {"op_pressure": "bar-g", "design_pressure": "bar-g", "op_temp": "°C", "design_temp": "°C", "max_dp_closed": "psi"}
# a vendor's wording for the same thing (not in schema.LABELS): the reader must keep the row as 'review', not misread it
SYNONYMS = {"Service": "Service description", "Body material": "Body / bonnet material", "Rating": "Pressure class",
            "Seat Material": "Seat", "Connections": "End connections", "Fluid State": "Phase"}
VALUES = {
    "tag": ["98ESDV 980001", "98BDV -101", "315MOV 980004", "19XV 122", "08SDV 412A"], "item_no": ["VTA", "ITEM-01"],
    "manufacturer": ["VTA", "Vendor A"], "model": ["VTA"], "service": ["HC FROM 98-Y101 ESDV", "RELIEF GAS TO HP COLD VENT", "CO2 TO INJECTION"],
    "pid_no": ["999-98-PR-PID-00012", "98-98-PR-PID-00007"], "line_no": ['98DHC-1018-2"-1C3AS2-N', 'P98981016-6"(XC0K8)-N'],
    "area_class": ["ZONE 2 IIB T3", "HOLD"], "tightness": ["Tight Shut-Off"], "piping_class": ["1C3AS2", "XC0K8", "3C0K8", "1A1A"],
    "line_size_inlet": ["2 in sch. 160", "6 in sch. 80S"], "line_size_outlet": ["2", "6"], "pipe_insulation": ["N (Non-Insulated)", "5 (Cold Insulation)"],
    "pipe_material": ["CS A106-B", "316/316L SS A312-TP316/316L"], "fluid": ["", "CO2", "HYDROCARBON"], "sour_service": ["", "Yes"],
    "fluid_state": ["", "Liquid", "Vapor"], "corrosive": ["", "Yes"], "op_pressure": ["", "43.8", "7"], "design_pressure": ["", "98", "154"],
    "op_temp": ["", "36", "57"], "design_temp": ["", "85", "260"], "max_dp_closed": ["", "98"], "fail_position": ["Close", "Open", "Last"],
    "body_size": ['2"', '4"', '10"', "22 in"], "body_type": ["Ball (Full Bore) - Trunnion", "Ball (Full Bore) - Floating", "Note - 2"],
    "connections": ["Flanged RF (ASME B16.5)", "Flanged RTJ (ASME B16.5)"], "rating": ["150#", "300#", "1500#"],
    "leakage_class": ["API 598 / ISO 5208 Rate A", "ISO 5208 Rate B (Note-7)"], "fireproofing": ["Not Required", "Required (General Note - 26, 27)"],
    "body_material": ["316/316L SS A351-CF8M/CF3M", "CS A216-WCB", "Note-11"], "ball_material": ["316 SS / HF", "ASTM A182 F316L"],
    "seat_material": ["RTFE", "PEEK", "R-PTFE"], "seal_material": ["Graphite (VTA)"], "stem_material": ["316 SS/HF", "ASTM A182 F316L/ ASTM A564 Type 630"],
    "bolting_gasket": ["Note-1", "Note - 1"], "packing_type": ["VTA (General Note - 31)"], "packing_material": ["Graphite (VTA)"],
    "painting": ["General Note - 23"], "nace": ["Yes", "Yes (MR0175/ISO 15156)", "NA"], "sil": ["SIL 2 (Minimum)", "-"],
    "fire_safe": ["HOLD (in accordance with API 607/ API 6FA)", "Yes"], "act_manufacturer": ["VTA"], "act_model": ["VTA"],
    "type": ["General Note - 5", "Spring return"], "material": ["Note-3"], "act_medium": ["Instrument Air"],
    "act_safety_factor": ["1.5 times the valve torque at full rated diff press of valve", "1.5 Times"], "air_failure": ["Fail Close", "Fail Open"],
}
NOTES = ["Stud Bolt material: CR-MO A193-B7M, W/ 2 HVY HEX NUTS, A194-2HM, B1.1, DIA (IMP) X LEN (MET).",
         "Body type shall be Ball (Full Bore) - Floating.",
         "Body, Bonnet Stem and Trim parts shall be EN10204 of certification type 3.2, whereas bolting and other wetted parts shall be EN10204 of certification type 2.1.",
         "Anti-static device and blow-out proof stem shall be provided as per API 6D.",
         "Valve Seat Material : PEEK with ASTM A182 F316L as seat backing",
         "VTA - vendor to advise, TBC - To be Confirmed, NA - Not Applicable."]
GENERAL = ["This Data sheet shall be read in conjunction with Doc.No:98-98-IN-DEC-00001.",
           "Passive fire protection (PFP) shall be provided for valves as stated in the respective datasheet.",
           "XV in CO2, hazardous and toxic service to be provided with Class A type tested fugitive emission packing in accordance with ISO 15848-1.",
           "Elastomers and soft sealing materials shall be selected for compatibility with CO2 service and to prevent rapid gas decompression."]

VARIATIONS = ["baseline", "font_small", "font_large", "columns_shifted", "label_synonyms", "missing_row_numbers", "wrapped_values",
              "extra_blank_rows", "max_nor_min_block", "unit_appended", "note_style_dash", "note_style_upper", "a3", "rotated_90",
              "skew", "hairlines", "thick_rules", "sheet2_continuation", "scanned"]


def _spec(rng: random.Random, variation: str) -> dict:
    """What goes on the page (the oracle) and how it is drawn."""
    fields = {}
    for _, _, labs in ROWS:
        for lab, key in labs:
            fields[key] = rng.choice(VALUES[key])
    fields["tag"] = rng.choice(VALUES["tag"])
    s = {"variation": variation, "fields": fields, "tag": fields["tag"], "doc_no": rng.choice(["999-98-IN-DTS-00002", "98-51-IN-DTS-00002", "315-51-IN-DTS-00011"]),
         "rev": rng.choice(["0", "A", "B", "1"]), "font": 7.8, "shift": 0.0, "scale": 1.0, "rule_w": 0.6, "rule_gray": 0.0, "synonyms": False,
         "drop_numbers": set(), "wrap_keys": set(), "blank_rows": [], "mnm": False, "unit_in_cell": True, "note_style": "dot",
         "a3": False, "rotate": 0, "skew": 0.0, "sheet2": False, "scanned": False, "n_notes": rng.randint(2, 6), "n_general": rng.randint(2, 4)}
    if variation == "font_small":
        s["font"] = 5.8
    elif variation == "font_large":
        s["font"] = 9.8
    elif variation == "columns_shifted":
        s["scale"] = rng.uniform(0.88, 1.05)
        s["shift"] = rng.uniform(-15, min(25, 587 - 560 * s["scale"]))   # the table stays on the page
    elif variation == "label_synonyms":
        s["synonyms"] = True
    elif variation == "missing_row_numbers":
        s["drop_numbers"] = set(rng.sample([r for r, _, _ in ROWS], 3))
    elif variation == "wrapped_values":
        s["wrap_keys"] = {"service", "body_material", "act_safety_factor", "fire_safe"}
        fields["service"] = "RELIEF GAS FROM 98-Y9801 TO HP COLD VENT BDV"
        fields["body_material"] = "316/316L SS A351-CF8M/CF3M"
    elif variation == "extra_blank_rows":
        s["blank_rows"] = [18, 19, 20, 38, 39]
    elif variation == "max_nor_min_block":
        s["mnm"] = True
    elif variation == "unit_appended":
        s["unit_in_cell"] = False
    elif variation == "note_style_dash":
        s["note_style"] = "dash"
    elif variation == "note_style_upper":
        s["note_style"] = "upper"
    elif variation == "a3":
        s["a3"] = True
    elif variation == "rotated_90":
        s["rotate"] = 90
    elif variation == "skew":
        s["skew"] = 0.1                                      # degrees — a vector form is never really crooked
    elif variation == "hairlines":
        s["rule_w"], s["rule_gray"] = 0.25, 0.65
    elif variation == "thick_rules":
        s["rule_w"] = 1.6
    elif variation == "sheet2_continuation":
        s["sheet2"] = True
    elif variation == "scanned":
        s["scanned"] = True
    return s


def _draw(doc, s: dict):
    k = 1.414 if s["a3"] else 1.0
    W, H = 595 * k, 842 * k
    page = doc.new_page(width=W, height=H)
    fs = s["font"] * k
    sc = s["scale"] * k
    sh = s["shift"] * k
    X = lambda x: x * sc + sh                                # noqa: E731  (column geometry of the real form, perturbed)
    pitch = 11.25 * k * max(1.0, s["font"] / 7.8)
    morph = None
    if s["skew"]:
        morph = (pymupdf.Point(W / 2, H / 2), pymupdf.Matrix(1, 0, 0, 1, 0, 0).prerotate(s["skew"]))
    rule = dict(width=s["rule_w"] * k, color=(s["rule_gray"],) * 3)

    def text(x, y, t, size=None, bold=False):
        page.insert_text(pymupdf.Point(x, y), t, fontsize=size or fs, fontname="hebo" if bold else "helv", morph=morph)

    def line(x0, y0, x1, y1):
        page.draw_line(pymupdf.Point(x0, y0), pymupdf.Point(x1, y1), morph=morph, **rule)

    # title block
    text(X(45), 42 * k, "Form No : 80", size=fs)
    text(X(240), 31 * k, "JOB No.   LTC/C/TEC/6647/24", size=fs)
    text(X(330), 66 * k, "On / Off Valve", size=14 * k, bold=True)
    text(X(454), 72 * k, "DOCUMENT NO.")
    text(X(454), 86 * k, s["doc_no"])
    text(X(454), 108 * k, "SHEET")
    text(X(497), 108 * k, "2" if s.get("_sheet2") else "1")
    text(X(513), 108 * k, "OF")
    text(X(539), 108 * k, "2" if s["sheet2"] else "1")
    text(X(454), 129 * k, "REV.")
    text(X(497), 129 * k, s["rev"])
    text(X(454), 151 * k, "DATE")
    text(X(497), 151 * k, "19/9/2026")
    text(X(140), 90 * k, f"{s['rev']} PK 19/9/2026 Approved for Construction")
    text(X(140), 101 * k, "A PK 14/7/2026 Issued for Inter-Discipline Check")
    # table
    rows = [r for r in ROWS if not s.get("_sheet2")] if not s.get("_sheet2") else []
    y_top = 158 * k
    n_rows = max(r for r, _, _ in ROWS) + (len(s["blank_rows"]) if s["blank_rows"] else 0)
    if s["mnm"]:
        n_rows += 1
    xs = {"cap0": X(43), "cap1": X(122), "num1": X(136), "lab_mid": X(221), "val0a": X(313), "val0b": X(316), "mid_a": X(437), "mid_b": X(441),
          "right": X(560), "unit_l": X(380), "unit_r": X(505)}
    y_bot = y_top + pitch * (n_rows + 1)
    for key in ("cap0", "cap1", "num1", "val0a", "val0b", "mid_a", "mid_b", "right"):
        line(xs[key], y_top, xs[key], y_bot)
    line(xs["cap0"], y_top, xs["right"], y_top)
    line(xs["cap0"], y_bot, xs["right"], y_bot)
    placed = {}                                             # key -> (value, unit) as printed on THIS page
    y = y_top
    caption_at = {}
    row_items = []
    all_rows = sorted(set(r for r, _, _ in ROWS) | set(s["blank_rows"]))
    bands = []
    cur_cap = None
    for r in all_rows:
        y += pitch
        spec = next((x for x in ROWS if x[0] == r), None)
        line(xs["num1"], y, xs["right"], y)                  # row rule (right of the caption column)
        if spec and spec[1] != cur_cap:
            if cur_cap is not None:
                bands.append(y - pitch)
            cur_cap = spec[1]
            caption_at[cur_cap] = y
        if r not in s["drop_numbers"]:
            t = str(r)
            w = pymupdf.get_text_length(t, fontname="helv", fontsize=fs)
            text(xs["num1"] - 2 * k - w, y - pitch * 0.25, t)
        if not spec:
            continue
        labs = spec[2]
        if len(labs) == 2:
            line(xs["lab_mid"], y - pitch, xs["lab_mid"], y)
        for i, (lab, key) in enumerate(labs):
            val = s["fields"][key]
            unit = PROCESS_UNIT.get(key, "")
            lab_x = xs["num1"] + 3.5 * k if i == 0 else xs["lab_mid"] + 4 * k
            ltxt = SYNONYMS.get(lab, lab) if s["synonyms"] else lab
            cell_w = (xs["lab_mid"] if (i == 0 and len(labs) == 2) else xs["val0a"]) - lab_x - 2 * k
            lfs = fs
            while lfs > 4 and pymupdf.get_text_length(ltxt, fontname="helv", fontsize=lfs) > cell_w:
                lfs -= 0.5                                   # a vendor shrinks a long label to its cell
            text(lab_x, y - pitch * 0.25, ltxt, size=lfs)
            v0 = xs["val0b"] if (i == 0 or len(labs) == 1) else xs["mid_b"]
            v1 = xs["mid_a"] if (i == 0 and len(labs) == 2) else xs["right"]
            if len(labs) == 1:
                v0, v1 = xs["val0b"], xs["right"]
            vx = v0 + 3 * k
            if unit and s["unit_in_cell"]:
                ux = xs["unit_l"] if v0 == xs["val0b"] else xs["unit_r"]
                line(ux, y - pitch, ux, y)
                if val:
                    text(vx, y - pitch * 0.25, val)
                text(ux + 3 * k, y - pitch * 0.25, unit)
                placed[key] = (val, unit)
            elif unit:
                if val:
                    text(vx, y - pitch * 0.25, f"{val} {unit}")
                placed[key] = (f"{val} {unit}" if val else "", "")
            elif val and (key in s["wrap_keys"] and len(val) > 22 or
                          pymupdf.get_text_length(val, fontname="helv", fontsize=fs) > (v1 - vx - 2 * k)):
                cut = val.rfind(" ", 0, len(val) // 2 + 6)
                if cut <= 0:
                    cut = val.rfind(" ")
                a, b = val[:cut], val[cut + 1:]
                text(vx, y - pitch * 0.55, a, size=fs * 0.8)
                text(vx, y - pitch * 0.12, b, size=fs * 0.8)
                placed[key] = (val, "")
            else:
                if val:
                    text(vx, y - pitch * 0.25, val)
                placed[key] = (val, "")
            hit = schema.lookup(lab, spec[1])
            row_items.append((r, hit[0] if hit else key, ltxt))
            if hit and hit[0] != key:
                placed[hit[0]] = placed.pop(key)
    bands.append(y)
    # caption column: captions centred in their band, rules between bands
    prev = y_top
    for cap, yc in caption_at.items():
        text(xs["cap0"] + 18 * k, yc + pitch * 0.5, cap, size=fs)
    for b in bands:
        line(xs["cap0"], b, xs["num1"], b)
    if s["mnm"]:                                            # a Max / Nor / Min block under the process rows
        y += pitch
        line(xs["num1"], y, xs["right"], y)
        for i, t in enumerate(("Max", "Nor", "Min", "Unit")):
            text(xs["val0b"] + (10 + 60 * i) * k, y - pitch * 0.25, t)
    # NOTES box
    ny = y_bot + 12 * k
    notes = NOTES[:s["n_notes"]] if not (s["sheet2"] and not s.get("_sheet2")) else []
    box_bottom = H - 30 * k
    yy = ny + 12 * k
    if notes:                                               # only the notes that fit the box are printed (and counted)
        wpl = (xs["right"] - xs["cap0"] - 12 * k) / pymupdf.get_text_length("abcdefghij", fontname="helv", fontsize=fs) * 10 / 6.5
        kept, y_try = [], yy
        for n in notes:
            need = int(len(n.split()) / max(1, wpl)) + 1
            if y_try + need * pitch * 0.9 > box_bottom - 4 * k:
                break
            kept.append(n)
            y_try += need * pitch * 0.9
        notes = kept
        text(xs["cap0"] + 4 * k, ny, "NOTES :", bold=True)
        page.draw_rect(pymupdf.Rect(xs["cap0"], ny - 10 * k, xs["right"], box_bottom), **rule)
    for i, n in enumerate(notes, 1):
        head = {"dot": f"{i}. ", "dash": f"Note-{i} ", "upper": f"NOTE-{i:02d} "}[s["note_style"]]
        words = (head + n).split()
        lines_, cur = [], ""
        for w in words:
            if pymupdf.get_text_length(cur + " " + w, fontname="helv", fontsize=fs) > (xs["right"] - xs["cap0"] - 12 * k):
                lines_.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        lines_.append(cur)
        for ln in lines_:
            if yy > box_bottom - 3 * k:
                break                                       # never print outside the box
            text(xs["cap0"] + 6 * k, yy, ln)
            yy += pitch * 0.9
    page.insert_text(pymupdf.Point(xs["right"] - 60 * k, H - 20 * k), "Page 1 of 9", fontsize=fs)
    if s["rotate"]:
        page.set_rotation(s["rotate"])
    return page, placed, len(notes), row_items


def make_pdf(s: dict) -> tuple[bytes, dict]:
    doc = pymupdf.open()
    page, placed, n_notes, row_items = _draw(doc, s)
    oracle = {"fields": placed, "notes": n_notes, "rows": row_items, "pages": 1}
    if s["sheet2"]:
        s2 = dict(s, _sheet2=True, blank_rows=[], mnm=False)
        _, _, n2, _ = _draw(doc, s2)
        oracle["pages"], oracle["notes"] = 2, n2
    # document page with GENERAL NOTES (what the real documents have)
    gp = doc.new_page(width=595, height=842)
    gp.insert_text((40, 60), "Doc. No.:", fontsize=8)
    gp.insert_text((40, 72), s["doc_no"], fontsize=8)
    gp.insert_text((40, 90), "Doc. Title:", fontsize=8)
    gp.insert_text((40, 102), "DATA SHEET FOR ON/OFF VALVE OF CO2 SEQUESTRATION IN QELNG NORTH", fontsize=8)
    gp.insert_text((40, 130), "GENERAL NOTES", fontsize=9)
    yy = 146
    for i, g in enumerate(GENERAL[:s["n_general"]], 1):
        gp.insert_text((40, yy), f"{i}. {g}", fontsize=7.5)
        yy += 14
    oracle["general"] = s["n_general"]
    if s["scanned"]:                                        # the datasheet page as a picture only
        page = doc[0]                                       # the handle from _draw is stale after new_page
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
        out = pymupdf.open()
        np_ = out.new_page(width=page.rect.width, height=page.rect.height)
        np_.insert_image(np_.rect, stream=pix.tobytes("png"))
        out.insert_pdf(doc, from_page=doc.page_count - 1, to_page=doc.page_count - 1)
        data = out.tobytes()
        out.close()
        doc.close()
        return data, oracle
    data = doc.tobytes()
    doc.close()
    return data, oracle


def score(s: dict, oracle: dict, res: dict) -> dict:
    out = {"exc": 0, "fields": 0, "hit": 0, "mapped": 0, "map_ok": 0, "false_review": 0, "tag": 0, "doc": 0, "rev": 0, "sheet": 0,
           "notes": 0, "general": 0, "scanned_ok": 0, "pages": 0}
    if s["scanned"]:
        out["scanned_ok"] = int(any(o.get("kind") == "scanned" for o in res["other_pages"]) and not res["sheets"])
        return out
    dss = extract.group_datasheets(res)
    if not dss:
        return out
    d = dss[0]
    F = d["fields"]
    out["pages"] = int(len(d["pages"]) == oracle["pages"])
    out["tag"] = int(schema.norm_tag(d["tag"]) == schema.norm_tag(s["tag"]))
    out["doc"] = int(d["doc_no"] == s["doc_no"])
    out["rev"] = int(d["rev"] == s["rev"])
    out["sheet"] = int(d["sheets"] and d["sheets"][0][1] == 1 and d["sheets"][0][2] == (2 if s["sheet2"] else 1))
    out["notes"] = int(len(d["notes"]) == oracle["notes"])
    gn = res["docs"].get(s["doc_no"], {}).get("general_notes", {})
    out["general"] = int(len(gn) == oracle["general"])
    known = [(r, key, lab) for r, key, lab in oracle["rows"] if schema.lookup(lab, "") and schema.lookup(lab, "")[0] == key]
    syn = [(r, key, lab) for r, key, lab in oracle["rows"] if not schema.lookup(lab, "")]
    for r, key, lab in known:
        out["fields"] += 1
        want, unit = oracle["fields"][key]
        f = F.get(key)
        if f is not None and (f.get("value") or "").strip() == want.strip() and (f.get("unit") or "") == unit:
            out["hit"] += 1
    # label mapping: every printed known label should land on its own key (not raw / another key)
    by_row = collections.defaultdict(list)
    for rr in d["rows"]:
        by_row[rr["row"]].append(rr)
    for r, key, lab in known:
        out["mapped"] += 1
        if any(rr["key"] == key for rr in by_row.get(r, [])):
            out["map_ok"] += 1
    for r, key, lab in syn:                                   # vendor wording: must be review (never misread as another key)
        rows = by_row.get(r, [])
        if any(rr["status"] != "review" and rr["key"] != key and not rr["key"].startswith("raw") for rr in rows if rr["label"] == lab):
            out["false_review"] += 1                          # misread
    return out


def run(n: int, seed: int, out_dir: Path | None, variations=None):
    rng = random.Random(seed)
    agg = collections.defaultdict(lambda: collections.Counter())
    examples = collections.defaultdict(list)
    variations = variations or VARIATIONS
    for i in range(n):
        var = variations[i % len(variations)]
        s = _spec(rng, var)
        data, oracle = make_pdf(s)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(data)
            path = fh.name
        if out_dir:
            (out_dir / f"{var}_{i}.pdf").write_bytes(data)
        try:
            res = extract.read_pdf(path)
            sc = score(s, oracle, res)
        except Exception:                                     # noqa: BLE001
            sc = {"exc": 1}
            examples[var].append(traceback.format_exc()[-300:])
        Path(path).unlink(missing_ok=True)
        a = agg[var]
        a["n"] += 1
        for k, v in sc.items():
            a[k] += v
        if sc.get("fields") and sc["hit"] < sc["fields"] and len(examples[var]) < 2:
            dss = extract.group_datasheets(res)
            F = dss[0]["fields"] if dss else {}
            miss = [(k, oracle["fields"][k][0], (F.get(k) or {}).get("value")) for k in oracle["fields"]
                    if k in [kk for _, kk, _ in oracle["rows"]] and (F.get(k) or {}).get("value", "").strip() != oracle["fields"][k][0].strip()][:3]
            examples[var].append(str(miss))
    return agg, examples


def report(agg, examples) -> str:
    L = [f"{'variation':22} {'n':>3} {'recall':>7} {'map':>6} {'tag':>4} {'doc':>4} {'rev':>4} {'sht':>4} {'notes':>5} {'gen':>4} {'misread':>7} {'exc':>3}"]
    tot = collections.Counter()
    for var, a in agg.items():
        for k, v in a.items():
            tot[k] += v
        rec = a["hit"] / a["fields"] if a["fields"] else (a["scanned_ok"] / a["n"] if a["n"] else 0)
        mp = a["map_ok"] / a["mapped"] if a["mapped"] else 1
        L.append(f"{var:22} {a['n']:3d} {rec:7.3f} {mp:6.3f} {a['tag']:4d} {a['doc']:4d} {a['rev']:4d} {a['sheet']:4d} {a['notes']:5d} {a['general']:4d} {a['false_review']:7d} {a['exc']:3d}"
                 + ("  (scanned flagged)" if var == "scanned" else ""))
    L.append(f"{'TOTAL':22} {tot['n']:3d} {tot['hit'] / max(1, tot['fields']):7.3f} {tot['map_ok'] / max(1, tot['mapped']):6.3f}  exc {tot['exc']}")
    for var, ex in examples.items():
        for e in ex[:1]:
            L.append(f"  e.g. {var}: {e[:200]}")
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=190)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    od = Path(a.out) if a.out else None
    if od:
        od.mkdir(parents=True, exist_ok=True)
    agg, ex = run(a.n, a.seed, od, [v for v in a.only.split(",") if v] or None)
    print(report(agg, ex))
