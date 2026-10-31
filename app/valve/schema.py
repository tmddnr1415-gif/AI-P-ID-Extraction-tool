"""Valve Datasheet — field dictionary.

The on/off valve datasheet (form "ON / OFF VALVE", 61 numbered rows over two sheets) is read by
**row label**, not by row number: the same number carries different labels between documents
(row 8 'Typical Detail' / 'Typical' / 'SIL Rating', row 33 'SIL Requirement' / 'Fire Safe Requirement').

LABELS maps a normalised label to (key, section, display name).  A label that is not here is still
kept — as `raw.<row>.<n>` with status `review` — so nothing printed on the sheet is dropped.

Sections follow the specification (A General · B Process · C Mechanical · D Special · E Accessories).
`process` marks the fields Process Data Verification may compare (spec §6.3: size, rating and
materials are never process data).
"""
from __future__ import annotations

import re

SECTIONS = [
    ("general", "General Information"),
    ("process", "Process Data"),
    ("mechanical", "Valve Mechanical Data"),
    ("actuator", "Actuator"),
    ("special", "Special Requirements"),
    ("accessories", "Accessories"),
]

# normalised label -> (key, section, display name)
_L = [
    # A. General
    ("tag no.", "tag", "general", "Tag Number"),
    ("item no.", "item_no", "general", "Item No."),
    ("manufacturer", "manufacturer", "general", "Manufacturer"),
    ("model", "model", "general", "Model"),
    ("service", "service", "general", "Service Description"),
    ("pid no.", "pid_no", "general", "P&ID Number"),
    ("line no.", "line_no", "general", "Line Number"),
    ("area classification", "area_class", "special", "Area Classification"),
    ("tightness requirement", "tightness", "mechanical", "Tightness Requirement"),
    ("typical detail", "typical", "general", "Typical Detail"),
    ("typical", "typical", "general", "Typical Detail"),
    ("sil rating", "sil", "special", "SIL Requirement"),
    # Pipe data
    ("piping class", "piping_class", "mechanical", "Piping Class"),
    ("line size and sch. inlet", "line_size_inlet", "mechanical", "Line Size / Sch. (Inlet)"),
    ("outlet", "line_size_outlet", "mechanical", "Line Size (Outlet)"),
    ("pipe insulation", "pipe_insulation", "mechanical", "Pipe Insulation"),
    ("pipe material", "pipe_material", "mechanical", "Pipe Material"),
    # B. Process
    ("fluid", "fluid", "process", "Fluid"),
    ("sour service", "sour_service", "special", "Sour Service"),
    ("fluid state", "fluid_state", "process", "Fluid State"),
    ("corrosive", "corrosive", "special", "Corrosive"),
    ("erosive", "erosive", "special", "Erosive"),
    ("toxic", "toxic", "special", "Toxic"),
    ("operating pressure", "op_pressure", "process", "Operating Pressure"),
    ("design pressure", "design_pressure", "process", "Design Pressure"),
    ("operating temp.", "op_temp", "process", "Operating Temperature"),
    ("design temperature", "design_temp", "process", "Design Temperature"),
    ("max. diff. pressure valve closed", "max_dp_closed", "process", "Max. Diff. Pressure (Valve Closed)"),
    ("valve fail safe position", "fail_position", "actuator", "Valve Fail Safe Position"),
    ("stroke time (s)", "stroke_time_s", "actuator", "Stroke Time (s)"),
    ("open", "stroke_open", "actuator", "Stroke Time Open"),
    ("closed", "stroke_closed", "actuator", "Stroke Time Closed"),
    # C. Valve body
    ("body size", "body_size", "mechanical", "Valve Size"),
    ("body type", "body_type", "mechanical", "Body Type"),
    ("connections", "connections", "mechanical", "End Connection"),
    ("rating", "rating", "mechanical", "Pressure Rating"),
    ("leakage class", "leakage_class", "mechanical", "Leakage Class"),
    ("fireproofing", "fireproofing", "special", "Fireproofing (PFP)"),
    ("body material", "body_material", "mechanical", "Body Material"),
    ("ball / disc material", "ball_material", "mechanical", "Ball / Disc (Trim) Material"),
    ("seat material", "seat_material", "mechanical", "Seat Material"),
    ("seal material", "seal_material", "mechanical", "Seal Material"),
    ("stem material", "stem_material", "mechanical", "Stem Material"),
    ("bolting / gasket", "bolting_gasket", "mechanical", "Bolting / Gasket"),
    ("packing type", "packing_type", "mechanical", "Packing Type"),
    ("packing material", "packing_material", "mechanical", "Packing Material"),
    ("painting", "painting", "special", "Painting"),
    ("nace requirement", "nace", "special", "NACE Requirement"),
    ("sil requirement", "sil", "special", "SIL Requirement"),
    ("fire safe requirement", "fire_safe", "special", "Fire Safe Requirement"),
    ("piggable valve body", "piggable", "mechanical", "Piggable Valve Body"),
    # Actuator (rows 34-44 — 'Manufacturer' / 'Model No.' repeat, see SECTION_PREFIX)
    ("model no.", "model", "general", "Model No."),
    ("type", "type", "actuator", "Type"),
    ("actuator size", "act_size", "actuator", "Actuator Size"),
    ("material", "material", "actuator", "Material"),
    ("operating medium", "act_medium", "actuator", "Operating Medium"),
    ("operating min pressure", "act_min_pressure", "actuator", "Operating Min Pressure"),
    ("stroke time", "act_stroke_time", "actuator", "Stroke Time"),
    ("torque", "act_torque", "actuator", "Torque"),
    ("min", "act_torque_min", "actuator", "Torque Min"),
    ("torque min", "act_torque_min", "actuator", "Torque Min"),
    ("max", "act_torque_max", "actuator", "Torque Max"),
    ("safety factor", "act_safety_factor", "actuator", "Safety Factor"),
    ("action on power failure", "power_failure", "actuator", "Action on Power Failure"),
    ("action on air failure", "air_failure", "actuator", "Action on Air Failure"),
    ("air consumption", "act_air_consumption", "actuator", "Air Consumption"),
    ("air supply connection", "act_air_connection", "actuator", "Air Supply Connection"),
    ("handwheel", "handwheel", "accessories", "Handwheel"),
    ("spring", "act_spring", "actuator", "Spring"),
    # Solenoid valve
    ("solenoid valve", "sov", "accessories", "Solenoid Valve"),
    ("solenoïd valve", "sov", "accessories", "Solenoid Valve"),
    ("tag no", "tag_no", "accessories", "Tag No."),
    ("body material ", "body_material", "accessories", "Body Material"),
    ("power supply", "power_supply", "accessories", "Power Supply"),
    ("coil rating", "coil_rating", "accessories", "Coil Rating"),
    ("electrical connection", "elec_connection", "accessories", "Electrical Connection"),
    ("ingress protection", "ingress", "accessories", "Ingress Protection"),
    ("electrical protection", "elec_protection", "accessories", "Electrical Protection"),
    ("cable gland", "cable_gland", "accessories", "Cable Gland"),
    ("manual reset", "manual_reset", "accessories", "Manual Reset"),
    ("functional sketch", "functional_sketch", "accessories", "Functional Sketch"),
    # Sheet 2 accessories (rows 52-61)
    ("limit switch", "limit_switch", "accessories", "Limit Switch"),
    ("limlit switch type", "limit_switch_type", "accessories", "Limit Switch Type"),
    ("filter regulator", "afr", "accessories", "Air Filter Regulator"),
    ("pressure safety valve", "psv", "accessories", "Pressure Safety Valve"),
    ("psv effective capacity", "psv_capacity", "accessories", "PSV Effective Capacity"),
    ("buffer vessel", "buffer_vessel", "accessories", "Buffer Vessel (Volume Tank)"),
    ("vessel min pressure sizing", "vessel_min_pressure", "accessories", "Vessel Min Pressure Sizing"),
    ("tubing", "tubing", "accessories", "Tubing"),
    ("fitting", "fitting", "accessories", "Fitting"),
    ("opened", "ls_opened", "accessories", "Limit Switch Opened"),
]


def norm_label(s: str) -> str:
    s = (s or "").replace(" ", " ").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


LABELS = {norm_label(a): (k, sec, disp) for a, k, sec, disp in _L}

# A label that repeats in several sections gets the section's prefix, decided by the row's group
# caption in the left column of the sheet (GENERAL / PIPE DATA / ... / ACTUATOR / SOLENOID VALVE).
SECTION_PREFIX = {"ACTUATOR": "act_", "SOLENOID": "sov_"}
_REPEATING = {"manufacturer", "model", "type", "material", "body_material", "tag", "tag_no", "stroke_time_s"}

UNIT_TOKENS = {"bar-g", "barg", "bar(g)", "bar", "bara", "bar(a)", "psi", "psig", "kpa", "mpa", "ºc", "°c",
               "degc", "ºf", "°f", "in", "mm", "sch.", "s", "sec", "kg/h", "t/h", "m3/h", "nm3/h", "cp", "kg/m3"}

# Values that are on the sheet but are not engineering data — shown as written, flagged for the reviewer.
PLACEHOLDERS = {"vta": "Vendor to Advise", "tbc": "To be Confirmed", "tba": "To be Advised", "hold": "Hold",
                "na": "Not Applicable", "n/a": "Not Applicable", "-": "Not specified"}

# Spec §6.3 — these are never process data, whatever document they appear in.
NOT_PROCESS = {"body_size", "rating", "body_material", "ball_material", "seat_material", "seal_material",
               "stem_material", "bolting_gasket", "packing_material", "packing_type", "connections",
               "line_size_inlet", "line_size_outlet", "piping_class", "pipe_material"}


def lookup(label: str, group: str):
    """(key, section, display) for a printed label in a row group, or None."""
    hit = LABELS.get(norm_label(label))
    if not hit:
        return None
    key, sec, disp = hit
    if "ACCESSOR" in (group or "").upper() and key in ("stroke_open", "stroke_closed"):
        return ("ls_opened", "accessories", "Limit Switch Opened") if key == "stroke_open" else \
            ("ls_closed", "accessories", "Limit Switch Closed")
    for g, pre in SECTION_PREFIX.items():
        if g in (group or "").upper() and key in _REPEATING:
            return pre + key, ("actuator" if pre == "act_" else "accessories"), f"{g.title()} {disp}"
    return key, sec, disp


def norm_tag(tag: str) -> str:
    """Matching key: '00XV 921' · '00XV-921' · '00XV921' -> '00XV921'."""
    return re.sub(r"[^0-9A-Z]", "", (tag or "").upper())


def valve_type(tag: str) -> str:
    """Function letters of the tag: '98ESDV004' -> 'ESDV', '00XV921' -> 'XV', '315MOV980004' -> 'MOV'."""
    m = re.match(r"^\d*([A-Z]+)", norm_tag(tag))
    return m.group(1) if m else ""


# ── Form 102 (Motor Operated Valve etc.): 'Label : value' rows ─────────────────────────────────
# (normalised label, optional group word) -> (key, section, display).  Group words come from the
# vertical captions (TAG · VALVE GEN. · GENERAL DESIGN DATA · BODY/BONNET · VALVE TRIM · ACTUATOR …).
_L102 = [
    ("tag no.", None, "tag", "general", "Tag Number"),
    ("pid no.", None, "pid_no", "general", "P&ID Number"),
    ("service", None, "service", "general", "Service Description"),
    ("instrument type", None, "instrument_type", "general", "Instrument Type"),
    ("valve type", None, "body_type", "mechanical", "Valve Type"),
    ("valve service", None, "valve_function", "general", "Valve Function"),
    ("quantity tags", None, "qty", "general", "Quantity"),
    ("manufacturer name", None, "manufacturer", "general", "Manufacturer"),
    ("model no", None, "model", "general", "Model Number"),
    ("failure action", None, "fail_position", "actuator", "Failure Action"),
    ("max. shut off pressure", None, "max_dp_closed", "process", "Max. Shut Off Pressure"),
    ("leakage class", None, "leakage_class", "mechanical", "Leakage Class"),
    ("material corrosion requirement", None, "corrosion_req", "mechanical", "Material Corrosion Requirement"),
    ("line no.", None, "line_no", "general", "Line Number"),
    ("line size", None, "line_size_inlet", "mechanical", "Line Size"),
    ("schedule", None, "line_schedule", "mechanical", "Schedule"),
    ("serviceclass", None, "piping_class", "mechanical", "Piping Class"),
    ("insulation thickness", None, "pipe_insulation", "mechanical", "Insulation Thickness"),
    ("design pressure", None, "design_pressure", "process", "Design Pressure"),
    ("design temperature", None, "design_temp", "process", "Design Temperature"),
    ("class", None, "area_class", "special", "Hazardous Area Class"),
    ("certificate", None, "ex_certificate", "special", "Ex Certificate"),
    ("weather protection", None, "ingress", "special", "Weather Protection"),
    ("body size", None, "body_size", "mechanical", "Valve Size"),
    ("rating", None, "rating", "mechanical", "Pressure Rating"),
    ("conn. type", None, "connections", "mechanical", "End Connection"),
    ("face to face dimension", None, "face_to_face", "mechanical", "Face to Face Dimension"),
    ("body/bonnet material", None, "body_material", "mechanical", "Body / Bonnet Material"),
    ("type of bonnet", None, "bonnet_type", "mechanical", "Bonnet Type"),
    ("corrosion allowance", None, "corrosion_allowance", "mechanical", "Corrosion Allowance"),
    ("gasket material", None, "gasket_material", "mechanical", "Gasket Material"),
    ("packing material", None, "packing_material", "mechanical", "Packing Material"),
    ("trim type", None, "trim_type", "mechanical", "Trim Type"),
    ("characteristic", None, "flow_char", "mechanical", "Flow Characteristic"),
    ("plug / ball / disc", None, "ball_material", "mechanical", "Plug / Ball / Disc Material"),
    ("seat", None, "seat_material", "mechanical", "Seat Material"),
    ("stem", "TRIM", "stem_material", "mechanical", "Stem Material"),
    ("manufacturer", "ACTUAT", "act_manufacturer", "actuator", "Actuator Manufacturer"),
    ("model", "ACTUAT", "act_model", "actuator", "Actuator Model"),
    ("type of actuator", None, "act_type", "actuator", "Actuator Type"),
    ("size", "ACTUAT", "act_size", "actuator", "Actuator Size"),
    ("case", "ACTUAT", "act_material", "actuator", "Actuator Case Material"),
    ("fireproofing", None, "fireproofing", "special", "Fireproofing (PFP)"),
    ("painting system", None, "painting", "special", "Painting"),
    ("handwheel", None, "handwheel", "accessories", "Handwheel"),
    ("position transmitter", None, "pos_tx", "accessories", "Position Transmitter"),
    ("limit switch tag no", None, "limit_switch", "accessories", "Limit Switch"),
]


def lookup_102(label: str, group: str, heading: str = ""):
    n = norm_label(label).rstrip(" :")
    g = (group or "").upper().replace(" ", "")
    for lab, gw, key, sec, disp in _L102:
        if n == lab and (gw is None or gw in g):
            return key, sec, disp
    return None
