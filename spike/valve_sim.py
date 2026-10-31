"""Mass simulation — an engineer's expectation vs the review engines, thousands of synthetic ball valve datasheets.

    python3 spike/valve_sim.py [--n 3000] [--seed 1] [--fuzz 500] [--show 8]

Every case is generated from a few knobs (materials · temperatures · piping class · tag · notes …); the same knobs
give the ENGINEER ORACLE: the findings a ball valve engineer would raise.  The engines (matreview · expert · tagrules ·
issues · requirements · pms · process · location) run on the generated datasheet, and the two sets are compared rule
by rule: false negatives (engineer saw it, the tool did not), false positives (the tool raised what the engineer would
not), crashes (any exception).  Only the rules the oracle models are scored; other findings are listed as 'unmodelled'.
A fuzz pass feeds garbage (None · empty · unicode · huge numbers · wrong units) and demands no exception.
"""
from __future__ import annotations

import re
import argparse
import collections
import random
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.valve import expert, issues, location, material, matreview, pms as pmsmod, process, requirements, tagrules  # noqa: E402

# ----------------------------------------------------------------------------- vocabulary (CO2 PJT style)
BODY_SS = ["316/316L SS A351-CF8M/CF3M", "316/316L SS A351-CF8M", "ASTM A351 CF8M", "316L SS A351-CF3M"]
BODY_CS = ["CS A216-WCB", "Carbon Steel ASTM A216 Grade WCB"]
BODY_LT = ["ASTM A350-LF2 / A352-LCC", "ITCS A352-LCC", "ASTM A350 LF6 Class 2/ ASTM A352 LCC"]
BALL = ["316 SS / HF", "316 SS/HF", "SS 316/HF", "316 SS/FHF", "316 SS", "ASTM A182 F316L"]
STEM_PH = ["ASTM A182 F316L/ ASTM A564 Type 630", "17-4PH (A564 Type 630) H1150D"]
SEATS = {"RTFE": 230, "R-PTFE": 230, "RTFE ST": 230, "PTFE": 200, "PEEK": 260, "Metal seated (TCC)": None, "Nylon": 93}
PIPE_SS = ["316/316L SS A312-TP316/316L", "A312-TP316/316L", "316/316L SS A358-316/316L CL.1"]
PIPE_CS = ["CS A106-B", "CS A672-C60 Class 22"]
PIPE_LT = ["ITCS A333-6", "ITCS A333-6 SMLS BE"]
CLASSES = {  # code: (rating, facing, material, services, pt max T, nace)
    "1C0K8": (150, "RAISED FACE", "STAINLESS STEEL", ["Carbon Dioxide", "Hydrogen Sulphide", "Hydrocarbon", "Sour Water"], 399, True),
    "3C0K8": (300, "RAISED FACE", "STAINLESS STEEL", ["Carbon Dioxide", "Hydrogen Sulphide", "Hydrocarbon", "Sour Water"], 209, True),
    "6C0K8": (600, "RAISED FACE", "STAINLESS STEEL", ["Carbon Dioxide", "Hydrocarbon"], 260, True),
    "XC0K8": (1500, "RING JOINT", "STAINLESS STEEL", ["Carbon Dioxide", "Feed Gas", "Hydrogen Sulphide", "Hydrocarbon", "Sour Water"], 247, True),
    "1A1A": (150, "RAISED FACE", "CARBON STEEL", ["Instrument Air", "Nitrogen", "Plant Air"], 204, False),
    "3R1B3": (300, "RAISED FACE", "CARBON STEEL - LOW TEMP.", ["Low temperature General Process", "Propane"], 204, False),
    "1C3AS2": (150, "RAISED FACE", "CARBON STEEL", ["Carbon Dioxide", "Hydrocarbon", "Sour Water"], 260, True),
}
FLUIDS = ["CO2", "HYDROCARBON", "SOUR WATER", "AMINE", "RELIEF GAS", "PROPANE REFRIGERANT", "NITROGEN", "FUEL GAS"]
FUNCS = ["ESDV", "BDV", "XV", "MOV", "SDV"]
SIZES = ['2"', '3"', '4"', '6"', '8"', '10"', '12"', '18"', '22"', '24"', "2 in", "4 in", "26 in"]
BOLT_NOTES = {
    "B8M2": "Stud Bolt material: Continuous thread, 316 SS A193-B8M CL.2, W/ 2 HVY HEX NUTS, A194-8MA, B1.1, NACE MR0175/ISO 15156",
    "B8M2_plain": "Stud Bolt material: 316 SS A193-B8M CL.2, W/ 2 HVY HEX NUTS, A194-8MA, B1.1",
    "B7": "Stud Bolt material: Continuous thread, CR-MO A193-B7, W/ 2 HVY HEX NUTS, A194-2H, B1.1, ZINC FLAKE COATED",
    "B7M": "Bolt Material: ASTM A193 Grade B7M / A320 Gr. L7M (Max. Hardness 22HRC), Nuts Material: ASTM A194 Grade 7M",
}
GN_POOL = {
    "fugitive": "XV in CO2, hazardous and toxic service to be provided with Class A type tested fugitive emission packing in accordance with ISO 15848-1.",
    "pfp": "Passive fire protection (PFP) shall be provided for valves (as stated in the respective datasheet) along with their actuators.",
    "rgd": "Elastomers and soft sealing materials shall be selected for compatibility with CO2 service and to prevent rapid gas decompression.",
    "antistatic": "Valves shall be provided with anti-static device and blow-out proof stem design.",
    "pst": "Partial stroke test facility shall be provided for all ESDV.",
    "paint": "Any coating or corrosion protection system shall be as per painting specification.",
}


def rint(rng, a, b):
    return rng.randint(a, b)


def nps(size: str) -> float:
    import re
    m = re.search(r"\d+(?:\.\d+)?", size)
    return float(m.group(0)) if m else 0.0


# ----------------------------------------------------------------------------- one case
def gen_case(rng: random.Random, i: int) -> dict:
    """-> {'spec', 'ds', 'cls', 'pdoc', 'peers', 'tagprof', 'expect': {rule: level|True}}"""
    cls_code = rng.choice(list(CLASSES))
    rating, facing, cmat, services, tmax, nace_cls = CLASSES[cls_code]
    area = rng.choice(["North", "South", "Brownfield", "W15"])
    site = {"North": "North", "South": "South", "W15": "W15", "Brownfield": rng.choice(["North", "South"])}[area]
    unit = "98" if area != "Brownfield" else rng.choice(["09", "19", "84"])
    func = rng.choice(FUNCS)
    loop = rng.choice([f"98{rint(rng, 0, 4)}{rint(rng, 0, 9):02d}{rint(rng, 1, 9)}", f"{rint(rng, 100, 999)}"])
    pre = "99" if (rng.random() < 0.05) else unit
    prefix_dev = pre != unit
    tag_raw = f"{pre}{func} {loop}" if area != "South" else f"{pre}{func} -{loop}"
    tag_key = f"{pre}{func}{loop}"
    fluid = rng.choice(FLUIDS)
    co2 = fluid == "CO2"
    sour = fluid in ("SOUR WATER", "AMINE") or rng.random() < 0.3
    dt = rng.choice([85, 90, 100, 155, 195, 196, 202, 211, 213, 230, 260])
    dp = rng.choice([3.5, 10, 13, 31, 57, 98, 154])
    size = rng.choice(SIZES)
    body_kind = rng.choice(["ss", "ss", "ss", "cs", "lt"])
    body = rng.choice({"ss": BODY_SS, "cs": BODY_CS, "lt": BODY_LT}[body_kind])
    pipe_kind = rng.choice(["ss", "cs", "lt"])
    pipe = rng.choice({"ss": PIPE_SS, "cs": PIPE_CS, "lt": PIPE_LT}[pipe_kind])
    seat = rng.choice(list(SEATS))
    ball = rng.choice(BALL)
    stem = rng.choice(BALL + STEM_PH)
    vtype = rng.choice(["Trunnion", "Floating"])
    bore = rng.choice(["Full Bore", "Reduced Bore"])
    conn_face = rng.choice(["RF", "RTJ"])
    conn_std = "B16.47B" if rng.random() < 0.15 else "B16.5"
    connections = f"Flanged {conn_face} (ASME {conn_std})"
    fail = rng.choice(["Close", "Open", "Last"])
    sil = rng.choice(["SIL 2 (Minimum)", "SIL 1", "-", ""])
    leak = rng.choice(["API 598 / ISO 5208 Rate A", "ISO 5208 Rate B (Note-7)", "Tight Shut-Off"])
    tight = "Tight Shut-Off"
    ins = rng.choice(["N (Non-Insulated)", "E (Electrical Heat Tracing)", "5 (Cold Insulation)", "NA"])
    pig = rng.choice(["", "", "Yes"])
    nace_val = rng.choice(["Yes", "Yes (MR0175/ISO 15156)", "No", "NA", ""])
    fire = rng.choice(["Yes (API 607)", "Not Required", "HOLD (in accordance with API 607/ API 6FA)", ""])
    pfp = rng.choice(["Not Required", "Required (General Note - 26, 27)", "NA"])
    bolt = rng.choice(list(BOLT_NOTES))
    hold_field = rng.random() < 0.15
    blank_proc = rng.random() < 0.3
    gn_keys = {k for k in GN_POOL if rng.random() < 0.6}
    line_cls = cls_code if rng.random() < 0.9 else "1C3AS1"
    line_size = nps(size) if rng.random() < 0.9 else nps(size) + 1
    line_no = f"PW2409631-{line_size:g}\"({line_cls})-N"
    dual_note = cmat == "STAINLESS STEEL" and rng.random() < 0.7
    seat_note = rng.random() < 0.7
    ext_stem = rng.random() < 0.5
    dup_tag = rng.random() < 0.05
    peer_body = rng.choice(BODY_SS)
    peer_outlier = rng.random() < 0.15
    seatcfg = rng.random() < 0.3                                            # note states SPE/DPE + cavity relief
    phase = rng.choice(["Vapor", "Vapor", "Liquid", "Mixed"])               # Process Data fluid phase
    erosive = rng.choice(["No", "No", "No", "Yes"])
    act_sf = rng.choice(["1.5 times the valve torque", "1.25 Times", "1.1 times the valve torque", "2.0 x"])
    seal = rng.choice(["Graphite (VTA)", "Graphite (VTA)", "FKM O-ring (RGD tested)", "Viton"])
    op_gt = rng.random() < 0.05                                             # operating pressure above design
    af_contra = rng.random() < 0.05                                         # air-failure action contradicts fail position

    nace_req = nace_cls or nace_val.startswith("Y") or sour
    # ---- fields
    rows = []

    def F(key, value, row, display, section="", unit=""):
        rows.append({"key": key, "value": value, "edited_value": None, "row": row, "display": display, "page": 1,
                     "bbox": [10, row * 10, 100, row * 10 + 8], "section": section, "unit": unit, "status": "ok"})
    F("tag", tag_raw, 1, "Tag No.")
    F("service", f"{fluid} FROM X TO Y", 3, "Service")
    F("pid_no", f"98-98-PR-PID-{rint(rng, 1, 60):05d}", 4, "P&ID No.")
    F("line_no", line_no, 5, "Line No.")
    F("area_class", "HOLD" if hold_field else "ZONE 2 IIB T3", 6, "Area classification")
    F("tightness", tight, 7, "Tightness requirement")
    F("piping_class", cls_code, 9, "Piping class")
    F("line_size_inlet", f"{line_size:g} in sch. 40S", 10, "Line Size")
    F("pipe_insulation", ins, 11, "Pipe insulation")
    F("pipe_material", pipe, 11, "Pipe material")
    F("fluid", "" if blank_proc else fluid, 12, "Fluid", "process")
    F("sour_service", "Yes" if sour and not blank_proc else "", 12, "Sour service", "process")
    F("fluid_state", "" if blank_proc else rng.choice(["Liquid", "Gas/Vapor", "Vapor"]), 13, "Fluid State", "process")
    F("op_pressure", "" if blank_proc else str(dp + 5 if op_gt else dp - 1), 14, "Operating Pressure", "process", "barg")
    F("design_pressure", "" if blank_proc else str(dp), 14, "Design Pressure", "process", "barg")
    F("op_temp", "" if blank_proc else str(dt - 20), 15, "Operating Temp.", "process", "°C")
    F("design_temp", "" if blank_proc else str(dt), 15, "Design Temperature", "process", "°C")
    F("fail_position", fail, 17, "Valve fail safe position")
    F("air_failure", {"Close": "Fail Open" if af_contra else "Fail Close", "Open": "Fail Close" if af_contra else "Fail Open", "Last": "NA"}[fail], 17, "Action on Air Failure")
    F("erosive", "" if blank_proc else erosive, 13, "Erosive", "process")
    F("body_size", size, 21, "Body Size")
    F("body_type", f"Ball ({bore}) - {vtype}", 21, "Body Type")
    F("connections", connections, 22, "Connections")
    F("rating", f"{rating}#", 22, "Rating")
    F("leakage_class", leak, 23, "Leakage Class")
    F("fireproofing", pfp, 23, "Fireproofing (PFP)")
    F("body_material", body, 24, "Body material")
    F("ball_material", ball, 25, "Ball / Disc (Trim) Material")
    F("seat_material", seat, 26, "Seat Material")
    F("seal_material", seal, 26, "Seal Material")
    F("stem_material", stem, 27, "Stem Material")
    F("bolting_gasket", "Note-1", 28, "Bolting / Gasket")
    F("packing_material", "Graphite (VTA)", 30, "Packing material")
    F("nace", nace_val, 32, "NACE Requirement")
    F("fire_safe", fire, 33, "Fire Safe Requirement")
    F("sil", sil, 33, "SIL Requirement")
    F("act_spring", "Required / SS 316 (VTA)" if fail != "Last" or rng.random() < 0.3 else "Not Required", 40, "Spring")
    F("piggable", pig, 12, "Piggable")
    F("act_safety_factor", act_sf, 41, "Actuator safety factor")
    notes = [{"no": 1, "text": BOLT_NOTES[bolt], "page": 2, "bbox": None},
             {"no": 3, "text": "Body, Bonnet Stem and Trim parts shall be EN10204 of certification type 3.2.", "page": 2, "bbox": None}]
    if ext_stem and "Cold" in ins:
        notes.append({"no": 5, "text": "Extended stem / bonnet shall be provided for cold insulated valves.", "page": 2, "bbox": None})
    if seatcfg:
        notes.append({"no": 6, "text": "Seat configuration: DPE with cavity relief as per API 6D.", "page": 2, "bbox": None})
    gn = {str(n): GN_POOL[k] for n, k in enumerate(sorted(gn_keys), start=20)}
    ds = {"id": i, "tag": tag_raw, "tag_key": tag_key, "doc_no": f"{unit}-51-IN-DTS-00002", "rev": "0", "valve_type": func,
          "fields": rows, "notes": notes, "pages": [1, 2], "sheets": [[1, 1, 2], [2, 2, 2]], "comments": [], "general_notes": gn,
          "process_ref": None, "location": {"area": area, "site": site, "unit": unit, "system": "", "basis": ""}}
    # ---- PMS class
    item_body = {"STAINLESS STEEL": "316/316L SS A351-CF8M/CF3M", "CARBON STEEL": "CS A216-WCB", "CARBON STEEL - LOW TEMP.": "ITCS A352-LCC"}[cmat]
    pms_fire = rng.random() < 0.7
    item_desc = (f"BALL VALVE, {item_body}, CL{rating}, "
                 f"{'RTJ' if facing == 'RING JOINT' else 'RF'}, B16.10, {rng.choice(['TRUNNION', 'FLOATING'])}, FULL PORT, 316 SS BALL/STEM, RTFE ST, "
                 f"{'FIRE TESTED TO API 607' if pms_fire else 'API 6D'}{', NACE MR0175/ISO 15156' if nace_cls else ''}")
    item_fits = nps(size) <= 24
    item_type = "TRUNNION" if "TRUNNION" in item_desc else "FLOATING"
    pt = [(38.0, rating / 7.5), (93.0, rating / 8.5), (149.0, rating / 9.5), (204.0, rating / 10.5)] + ([(260.0, rating / 12)] if tmax >= 260 else [])
    if tmax == 209:
        pt.append((209.0, rating / 10.6))
    if tmax == 247:
        pt = [(85.0, 154.0), (247.0, 154.0)]
    if tmax == 399:
        pt += [(316.0, 9.6), (399.0, 6.5)]
    cls = {"code": cls_code, "area": "QN", "facing": facing, "rating": rating, "material": cmat, "ca": "0.0 MM" if cmat == "STAINLESS STEEL" else "3 MM",
           "trim": "TRIM 12 (316 SS/HF)", "header_page": 5, "pt": pt, "pt_basis": "ASME B16.5", "services": services,
           "class_notes": {**({"002": "ALL MATERIALS SHALL COMPLY WITH NACE MR 0175 / ISO-15156"} if nace_cls else {}),
                           **({"018": "THE USE OF RPTFE SOFT SEATED MATERIALS IS RESTRICTED TO MAX. TEMPERATURE OF 230°C"} if seat_note else {}),
                           **({"034": "ALL SS 316/SS316L SHALL BE DUAL GRADE CERTIFIED"} if dual_note else {})},
           "item_notes": {}, "items": [{"code": "PVBSED15RF02TD08U703", "from": 0.5, "to": 24.0, "branch": None, "kind": "BALL VALVE",
                                        "desc": item_desc, "page": 6, "bbox": [0, 0, 1, 1]}], "pages": [5, 6]}
    if nace_cls:
        cls["nace"] = "MR0175/ISO 15156"
    pms = {"areas": {"QN": {cls_code: cls}}}
    # ---- process data
    pd_fluid = fluid if rng.random() < 0.9 else "RELF GAS FR X"
    pd_vals = {"fluid": {"v": pd_fluid, "unit": ""}, "design_temp": {"v": f"{dt:.2f}", "unit": "°C"}, "design_pressure": {"v": f"{dp:.2f}", "unit": "bar(g)"},
               "op_pressure": {"v": f"{dp - 1:.2f}", "unit": "bar(g)"}, "fail_position": {"v": {"Close": "FC", "Open": "FO", "Last": "FL"}[fail], "unit": ""},
               "fluid_state": {"v": phase, "unit": ""}, "remarks": {"v": "Toxic, Corrosive and sour service, FV" if sour else "", "unit": ""}}
    pd_row = {"sr": 1, "tag": tag_raw, "page": 12, "values": pd_vals}
    pdoc = {"doc_no": "98-98-PR-DTS-00023", "by_tag": {tag_key: pd_row}, "rows": [pd_row], "n_tags": 1}
    # ---- peers (same class, 8 others)
    peer_items = [{"tag": f"P{k}", "fields": {"piping_class": cls_code, "body_material": peer_body, "seat_material": "RTFE", "rating": f"{rating}#"}} for k in range(8)]
    if peer_outlier:
        body = rng.choice(BODY_CS)
        rows[[r["key"] for r in rows].index("body_material")]["value"] = body
        body_kind = "cs"
    peers = expert.build_peers(peer_items + [{"tag": tag_key, "fields": {"piping_class": cls_code, "body_material": body, "seat_material": seat, "rating": f"{rating}#"}}])
    # ---- tag profile
    tag_items = [{"tag_raw": f"{unit}{func} {'98' if area != 'South' else ''}0{k:03d}" if area != "South" else f"{unit}{func} -{k:03d}", "tag_key": f"{unit}{func}{'980' if area != 'South' else ''}{k:03d}",
                  "area": area, "site": site, "unit": unit, "system": "", "pid_no": "98-98-PR-PID-00002", "doc_no": ds["doc_no"], "fail": "Close"} for k in range(1, 9)]
    me = {"tag_raw": tag_raw, "tag_key": tag_key, "area": area, "site": site, "unit": unit, "system": "", "pid_no": "98-98-PR-PID-00002",
          "doc_no": ds["doc_no"], "fail": fail, "page": 1, "bbox": None}
    tag_items.append(me)
    if dup_tag:
        tag_items.append(dict(me, doc_no="999-98-IN-DTS-00002"))
    tagprof = tagrules.learn(tag_items)

    # ============================================================== the engineer's expectations
    E = {}
    soft = SEATS[seat] is not None
    seat_lim = SEATS[seat]
    seat_name_rptfe = seat.upper().startswith(("RTFE", "R-PTFE"))
    if soft:
        if seat_note and seat_name_rptfe and dt > 230:
            E["MR-01"] = "Action"
        elif dt > seat_lim:
            E["MR-02"] = "Action"
        elif dt >= seat_lim - 30:
            E["MR-02"] = "Confirm"
    if dt > tmax:
        E["MR-03"] = "Action"
    else:
        pr = matreview._interp(pt, dt)
        if pr is not None and dp > pr * 1.0001:
            E["MR-03"] = "Action"
    if body_kind == "cs" and (pipe_kind == "lt" or "LOW TEMP" in cmat):
        E["MR-04"] = "Action"
    if (body_kind == "ss") != (pipe_kind == "ss"):
        E["MR-05"] = "Confirm"
    if co2 and body_kind != "ss":
        E["MR-06"] = "Confirm" if cmat == "STAINLESS STEEL" else "Note"      # CA 0.0 MM reads as no allowance
    if nace_req and (body_kind == "ss" or "316" in ball or "316" in stem):
        E["MR-07"] = "Note"
    if "630" in stem or "17-4" in stem:
        E["MR-08"] = "Note" if ("H1150D" in stem or not nace_req) else "Confirm"
    if "HF" in ball.upper() or "HF" in stem.upper():
        E["MR-09"] = "Note"
    if dual_note:
        for v in (body, ball, stem):
            if ("316L" in v.upper() or "CF3M" in v.upper()) and not any(x in v.upper().replace("316L", "") for x in ("316", "CF8M")):
                E["MR-10"] = "Confirm"
    if bolt == "B8M2" and nace_req:
        E["MR-11"] = "Note"
    elif bolt == "B8M2_plain" and nace_req:
        E["MR-11"] = "Confirm"
    elif bolt == "B7" and nace_req:
        E["MR-11"] = "Confirm"
    elif bolt == "B7M":
        E["MR-11"] = "Note"
    elastomer_seal = any(x in seal.upper() for x in ("FKM", "VITON", "O-RING"))
    if co2 and elastomer_seal:
        E["MR-12"] = "Confirm"
    elif co2 and "rgd" in gn_keys:
        E["MR-12"] = "Note"
    if soft and fire.upper().startswith(("Y", "REQ")):
        E["MR-13"] = "Note"
    alias = {"CO2": "CARBON DIOXIDE", "NITROGEN": "NITROGEN", "RELIEF GAS": "VENT", "PROPANE REFRIGERANT": "PROPANE", "FUEL GAS": "FUEL GAS"}
    listed = " ".join(services).upper()
    words = [alias.get(pd_fluid, pd_fluid)] + pd_fluid.split()
    if not any(w in listed for w in words if len(w) > 2) and not (co2 and "CARBON DIOXIDE" in listed):
        E["MR-14"] = "Confirm"
    if nace_req and body_kind != "ss":
        E["MR-15"] = "Note"
    # valve design
    if conn_face != ("RTJ" if facing == "RING JOINT" else "RF"):
        E["VR-01"] = "Action"
    if conn_std == "B16.47B" and nps(size) <= 24:
        E["VR-02"] = "Action"
    elif conn_std == "B16.5" and nps(size) > 24:
        E["VR-02"] = "Action"
    lim = next((v for k, v in sorted(expert.FLOATING_MAX_NPS.items()) if rating <= k), None)
    if vtype == "Floating" and lim and nps(size) > lim:
        E["VR-03"] = "Confirm"
    if vtype.upper() != item_type and item_fits:
        E["VR-04"] = "Confirm"
    spring = rows[[r["key"] for r in rows].index("act_spring")]["value"]
    if fail in ("Close", "Open") and spring.startswith("Not"):
        E["VR-05"] = "Action"
    elif fail == "Last" and spring.startswith("Req"):
        E["VR-05"] = "Confirm"
    if sil.startswith("SIL"):
        if fail == "Last":
            E["VR-06"] = "Confirm"
        elif sil.startswith("SIL 2") and "pst" not in gn_keys:
            E["VR-06"] = "Note"
    if "Rate B" in leak and (soft or True):
        E["VR-07"] = "Confirm"
    flammable = pd_fluid in ("HYDROCARBON", "SOUR WATER", "AMINE", "RELIEF GAS", "PROPANE REFRIGERANT", "FUEL GAS", "RELF GAS FR X") or sour
    if fire == "" and (flammable or (pms_fire and item_fits)):
        E["VR-09"] = "Confirm"                                           # blank fire-safe where service or PMS item asks for it
    if "antistatic" not in gn_keys:
        E["VR-08"] = "Note"                                                  # neither anti-static nor blow-out stated anywhere
    if vtype == "Trunnion" and not seatcfg:
        E["VR-10"] = "Confirm" if (phase in ("Liquid", "Mixed") or (pd_fluid == "CO2" and dp >= 74)) else "Note"
    if erosive == "Yes" and not blank_proc and soft:
        E["VR-14"] = "Confirm"
    if act_sf.startswith("1.1"):
        E["VR-15"] = "Confirm"
    if "Cold" in ins and not ext_stem:
        E["VR-11"] = "Confirm"
    if pig == "Yes" and bore == "Reduced Bore":
        E["VR-12"] = "Action"
    if line_size != nps(size):
        E["VR-13"] = "Action" if nps(size) > line_size else ("Confirm" if bore == "Full Bore" else None)
        if E["VR-13"] is None:
            del E["VR-13"]
    peer_seat_diff = not seat.upper().startswith(("RTFE", "R-PTFE"))
    peer_body_diff = peer_outlier or not (material.same(peer_body, body) or material.equivalent(peer_body, body)
                                          or expert._toks(peer_body) <= expert._toks(body)
                                          or material.compare(peer_body, body)[0] == material.COMPLIANT)   # 'A351 CF8M' = the peers' 316 CF8M/CF3M
    if peer_seat_diff or peer_body_diff:
        E["PC-01"] = "Confirm"
    # tags
    if dup_tag:
        E["TG-04"] = "Action"
    if func in ("ESDV", "SDV") and fail == "Open" or func == "BDV" and fail == "Close":
        E["TG-05"] = "Confirm"
    if prefix_dev:
        E["TG-02"] = "Confirm"                                               # learned: prefix = Unit (8 peers); this one says 99
    if area != "South":
        if len(loop) != 6 or not loop.startswith("980"):
            E["TG-03"] = "Confirm"                                           # peers: 980nnn
    elif len(loop) != 3:
        E["TG-03"] = "Confirm"                                               # South peers: -nnn
    # issues
    if hold_field or fire.startswith("HOLD"):
        E["Open Item"] = True
    if blank_proc or not sour or not nace_val.strip():                      # sour_service row blank · NACE (required) blank
        E["Data Missing"] = True
    if line_cls != cls_code:
        E["Data Error:piping_class"] = True
    if op_gt and not blank_proc:
        E["Data Error:op_pressure"] = True
    if af_contra and fail != "Last":
        E["Data Error:air_failure"] = True
    # requirements
    if nace_val.strip() or "NACE" in BOLT_NOTES[bolt]:                      # the row (any value, via its label) or the bolting note
        E["req:nace"] = True
    E["req:cert"] = True
    if "fugitive" in gn_keys:
        E["req:fugitive"] = True
    if "pfp" in gn_keys or pfp.strip():
        E["req:pfp"] = True
    if sil.strip():                                                          # '-' = stated as not applicable (negative entry)
        E["req:sil"] = True
    # pms check
    E["pms:Pressure Class"] = material.COMPLIANT
    if nace_cls:                                                             # class requires NACE: row Yes / N(o|A) / blank
        nn = "NACE MR0175" in BOLT_NOTES[bolt]
        E["pms:NACE"] = (material.COMPLIANT if nace_val.startswith("Y") else material.REVIEW if re.match(r"\s*(NA|N/A)\b", nace_val)
                         else material.NON if nace_val.startswith("N")
                         else material.COMPLIANT if nn else material.REVIEW)
    for key, v in (("Trim (Ball) Material", ball), ("Stem Material", stem)):
        u = v.upper()
        if item_fits:                                                        # the ball item says '316 SS BALL/STEM'
            E[f"pms:{key}"] = (material.NON if u.startswith("17-4PH") else material.REVIEW if "F316L" in u and "316 SS" not in u
                               else material.COMPLIANT)
        else:                                                                # no item for 26 in: class header 'TRIM 12 (316 SS/HF)' is the fallback
            E[f"pms:{key}"] = material.compare("316 SS/HF", v)[0]
    if item_fits:
        if pms_fire and fire.strip():
            E["pms:Fire Safe"] = (material.NON if fire.upper().startswith(("NO", "NOT")) else material.REVIEW if fire.startswith("HOLD")
                                  else material.COMPLIANT)
        want = {"STAINLESS STEEL": "ss", "CARBON STEEL": "cs", "CARBON STEEL - LOW TEMP.": "lt"}[cmat]
        E["pms:Body Material"] = material.COMPLIANT if body_kind == want else material.NON
        E["pms:Seat Material"] = material.COMPLIANT if seat_name_rptfe else (material.REVIEW if seat.upper().startswith("PTFE") else material.NON)
    # process
    E["proc:design_temp"] = process.MATCH if not blank_proc else process.DS_BLANK
    E["proc:fail_position"] = process.MATCH
    E["loc"] = (area, site, unit)
    spec = dict(cls=cls_code, dt=dt, dp=dp, body=body, pipe=pipe, seat=seat, ball=ball, stem=stem, fluid=fluid, size=size, conn=connections,
                vtype=vtype, fail=fail, sil=sil, leak=leak, ins=ins, pig=pig, nace=nace_val, fire=fire, bolt=bolt, hold=hold_field, seatcfg=seatcfg,
                phase=phase, erosive=erosive, sf=act_sf, seal=seal, prefix_dev=prefix_dev, op_gt=op_gt, af=af_contra,
                blank=blank_proc, gn=sorted(gn_keys), line=line_no, dup=dup_tag, outlier=peer_outlier, tag=tag_raw)
    return {"spec": spec, "ds": ds, "cls": cls, "pms": pms, "pdoc": pdoc, "pd_row": pd_row, "peers": peers, "tagprof": tagprof, "me": me, "expect": E}


# ----------------------------------------------------------------------------- run the engines
def run_engines(c: dict) -> dict:
    """-> {rule: level|value} as the tool says (plus 'unmodelled' list)."""
    ds, cls = c["ds"], c["cls"]
    got = {}
    reqs = requirements.find(ds, ds["general_notes"])
    prows = process.check(ds, c["pdoc"])
    mr = matreview.review(ds, ds["general_notes"], cls, prows, c["pd_row"], reqs)
    vr = expert.review(ds, ds["general_notes"], cls, prows, c["pd_row"], reqs, c["peers"])
    tg = tagrules.check(c["me"], c["tagprof"])
    rank = {"Action": 3, "Confirm": 2, "Note": 1}
    for m in mr + vr + tg:
        if rank[m["level"]] >= rank.get(got.get(m["rule"]), 0):
            got[m["rule"]] = m["level"]                              # a rule raised twice: its highest level
        assert m["short"] and len(m["short"]) <= 120, f"short too long: {m['rule']} {len(m['short'])}"
        assert m["basis"] and isinstance(m["evidence"], list)
    F = {f["key"]: f for f in ds["fields"]}
    iss = issues.compute(ds, ds["general_notes"], c["pms"], "QN", None, None, pms_rows=pmsmod.check(F, c["pms"], "QN", ds["notes"]),
                         process_rows=prows, material_rows=mr + vr + tg)
    for i in iss:
        if i["type"] == "Open Item":
            got["Open Item"] = True
        if i["type"] == "Data Missing":
            got["Data Missing"] = True
        if i["type"] == "Data Error":
            got[f"Data Error:{i['key']}"] = True
        assert len(i["description"]) <= 200, i["description"]
    for r in reqs:
        got[f"req:{r['key']}"] = True
    requirements.columns(reqs)
    requirements.summary(reqs)
    for r in pmsmod.check(F, c["pms"], "QN", ds["notes"]):
        got[f"pms:{r['item']}"] = r["result"]
    for r in prows:
        got[f"proc:{r['key']}"] = r["result"]
    L = location.locate(ds["doc_no"], f"DATA SHEET FOR ON/OFF VALVE OF CO2 SEQUESTRATION IN QELNG {ds['location']['site'].upper()}"
                        + (f" (SYSTEM 999 - UNIT {ds['location']['unit']})" if ds["location"]["area"] == "Brownfield" else ""),
                        F["pid_no"]["value"], ds["tag_key"], "")
    if ds["location"]["area"] == "W15":
        L = location.locate(ds["doc_no"], "DATA SHEET FOR ON/OFF VALVE OF CO2 SEQUESTRATION IN W15 INJECTION AREA", F["pid_no"]["value"], ds["tag_key"], "")
    got["loc"] = (L["area"], L["site"], L["unit"])
    return got


MODELLED_PREFIX = ("MR-", "VR-", "PC-", "TG-", "Open Item", "Data Missing", "Data Error:", "req:", "pms:", "proc:", "loc")
MODELLED_EXACT = {"MR-01", "MR-02", "MR-03", "MR-04", "MR-05", "MR-06", "MR-07", "MR-08", "MR-09", "MR-10", "MR-11", "MR-12", "MR-13", "MR-14", "MR-15",
                  "VR-01", "VR-02", "VR-03", "VR-04", "VR-05", "VR-06", "VR-07", "VR-08", "VR-09", "VR-10", "VR-11", "VR-12", "VR-13", "VR-14", "VR-15",
                  "PC-01", "TG-02", "TG-03", "TG-04", "TG-05",
                  "Open Item", "Data Missing", "Data Error:piping_class", "Data Error:line_size_inlet", "Data Error:op_pressure", "Data Error:air_failure",
                  "req:nace", "req:cert", "req:fugitive", "req:pfp", "req:sil",
                  "pms:Pressure Class", "pms:Body Material", "pms:Seat Material", "pms:NACE", "pms:Trim (Ball) Material", "pms:Stem Material",
                  "pms:Fire Safe", "proc:design_temp", "proc:fail_position", "loc"}


def compare(exp: dict, got: dict) -> tuple[list, list, list]:
    """(false negatives, false positives, level mismatches) over the modelled rules."""
    fn, fp, lv = [], [], []
    for k in MODELLED_EXACT:
        e, g = exp.get(k), got.get(k)
        if e is not None and g is None:
            fn.append(k)
        elif e is None and g is not None:
            fp.append(k)
        elif e is not None and g is not None and e is not True and e != g:
            lv.append(f"{k}:{e}≠{g}")
    return fn, fp, lv


# ----------------------------------------------------------------------------- fuzz
def fuzz(n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    junk = ["", " ", None, "N/A", "VTA", "Note-99", "HOLD", "∞", "１２３", "9" * 40, "-1e308", "'); DROP", "ø", "🙂", "Class", "CL", "TRIM",
            "316", "A", "inch", "°F", "psig", "0", "-29", "999999", "2 in / 50 mm", "DN50", "\n\t", "Note 1 & 2", "See note", "TBC - To be confirmed"]
    errors = []
    for i in range(n):
        try:
            c = gen_case(rng, 100000 + i)
            ds = c["ds"]
            for f in ds["fields"]:
                if rng.random() < 0.35:
                    f["value"] = rng.choice(junk)
                if rng.random() < 0.05:
                    f["unit"] = rng.choice(junk)
                if rng.random() < 0.05:
                    f["bbox"] = None
            if rng.random() < 0.2:
                ds["notes"] = [dict(n, text=rng.choice(junk) or "") for n in ds["notes"]]
            if rng.random() < 0.2:
                ds["general_notes"] = {k: (rng.choice(junk) or "") for k in ds["general_notes"]}
            if rng.random() < 0.1:
                c["cls"]["pt"] = []
            if rng.random() < 0.1:
                c["cls"]["items"] = []
            if rng.random() < 0.1:
                c["cls"]["class_notes"] = {}
            if rng.random() < 0.1:
                c["pdoc"]["by_tag"][ds["tag_key"]]["values"] = {k: {"v": rng.choice(junk) or "", "unit": rng.choice(junk) or ""} for k in c["pd_row"]["values"]}
            if rng.random() < 0.1:
                c["me"]["tag_raw"] = rng.choice(junk) or ""
            run_engines(c)
            matreview.review(ds, None, None, None, None, None)
            expert.review(ds, None, None, None, None, None, None)
            tagrules.check(c["me"], None)
            for v in junk:
                material.compare(v or "", rng.choice(junk) or "")
                process.compare_item(rng.choice(list(process.DS_KEYS)), v or "", rng.choice(junk) or "", rng.choice(junk) or "", rng.choice(junk) or "")
                location.locate(v or "", v or "", v or "", v or "", v or "")
                tagrules.parse(v or "")
        except Exception as e:  # noqa: BLE001
            errors.append(f"fuzz #{i}: {type(e).__name__}: {str(e)[:120]} | {traceback.format_exc().splitlines()[-3]}")
    return errors


# ----------------------------------------------------------------------------- main
def simulate(n: int, seed: int, show: int = 6, quiet: bool = False) -> dict:
    rng = random.Random(seed)
    stats = collections.defaultdict(lambda: {"tp": 0, "fn": 0, "fp": 0, "lv": 0})
    crashes, ex_fn, ex_fp, ex_lv = [], collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
    for i in range(n):
        c = gen_case(rng, i)
        try:
            got = run_engines(c)
        except Exception as e:  # noqa: BLE001
            crashes.append(f"case {i}: {type(e).__name__}: {str(e)[:140]} | {traceback.format_exc().splitlines()[-3].strip()} | {c['spec']}")
            continue
        fn, fp, lv = compare(c["expect"], got)
        for k in MODELLED_EXACT:
            if c["expect"].get(k) is not None and got.get(k) is not None:
                stats[k]["tp"] += 1
        for k in fn:
            stats[k]["fn"] += 1
            ex_fn[k].append((i, c["spec"]))
        for k in fp:
            stats[k]["fp"] += 1
            ex_fp[k].append((i, c["spec"], got.get(k)))
        for k in lv:
            r = k.split(":")[0]
            stats[r]["lv"] += 1
            ex_lv[r].append((i, k, c["spec"]))
    fam = collections.defaultdict(lambda: {"tp": 0, "fn": 0, "fp": 0, "lv": 0})
    for k, v in stats.items():
        f = k.split(":")[0] if ":" in k else k[:2] if k[:2] in ("MR", "VR", "PC", "TG") else k
        for x in v:
            fam[f][x] += v[x]
    tp = sum(v["tp"] for v in stats.values()); fnn = sum(v["fn"] for v in stats.values()); fpp = sum(v["fp"] for v in stats.values())
    rec = tp / max(1, tp + fnn); prec = tp / max(1, tp + fpp)
    out = {"n": n, "crashes": crashes, "recall": rec, "precision": prec, "stats": dict(stats), "families": dict(fam),
           "fn": sum(v["fn"] for v in stats.values()), "fp": fpp, "lv": sum(v["lv"] for v in stats.values())}
    if quiet:
        return out
    print(f"cases {n} · crashes {len(crashes)} · recall {rec:.3f} · precision {prec:.3f} · level mismatches {out['lv']}")
    for f, v in sorted(fam.items()):
        r = v["tp"] / max(1, v["tp"] + v["fn"]); p = v["tp"] / max(1, v["tp"] + v["fp"])
        print(f"  {f:14} tp {v['tp']:5} fn {v['fn']:4} fp {v['fp']:4} lv {v['lv']:3}  recall {r:.3f} precision {p:.3f}")
    for c in crashes[:show]:
        print("CRASH", c)
    for k, L in sorted(ex_fn.items(), key=lambda kv: -len(kv[1]))[:show]:
        print(f"FN {k} ×{len(L)}  e.g. case {L[0][0]} {L[0][1]}")
    for k, L in sorted(ex_fp.items(), key=lambda kv: -len(kv[1]))[:show]:
        print(f"FP {k} ×{len(L)}  e.g. case {L[0][0]} got={L[0][2]} {L[0][1]}")
    for k, L in sorted(ex_lv.items(), key=lambda kv: -len(kv[1]))[:show]:
        print(f"LEVEL {k} ×{len(L)}  e.g. case {L[0][0]} {L[0][1]} {L[0][2]}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--fuzz", type=int, default=500)
    ap.add_argument("--show", type=int, default=8)
    a = ap.parse_args()
    simulate(a.n, a.seed, a.show)
    if a.fuzz:
        errs = fuzz(a.fuzz, a.seed)
        print(f"fuzz {a.fuzz} · exceptions {len(errs)}")
        for e in errs[:a.show]:
            print("  ", e)
