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
    # valve37 — the same On/Off form (Code 80) as printed for butterfly valves of another project
    ("line n°", "line_no", "general", "Line Number"),
    ("valve power failure position", "fail_position", "actuator", "Valve Fail Safe Position"),
    ("seat trim material", "seat_material", "mechanical", "Seat Material"),
    ("seat seal material", "seal_material", "mechanical", "Seal Material"),
    ("buffer tank", "buffer_vessel", "accessories", "Buffer Vessel (Volume Tank)"),
    ("tank mini pressure sizing", "vessel_min_pressure", "accessories", "Vessel Min Pressure Sizing"),
    ("effective capacity", "psv_capacity", "accessories", "PSV Effective Capacity"),
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
    ("yoke", "ACTUAT", "act_yoke_material", "actuator", "Actuator Yoke Material"),
    ("stem", "ACTUAT", "act_stem_material", "actuator", "Actuator Stem Material"),
    ("power supply", None, "power_supply", "actuator", "Power Supply"),
    ("rated power", None, "act_rated_power", "actuator", "Rated Power"),
    ("stroke speed (close to open)", None, "stroke_open", "actuator", "Stroke Time Open"),
    ("stroke speed (open to close)", None, "stroke_closed", "actuator", "Stroke Time Closed"),
    ("type", "GENERAL", "ex_type", "special", "Ex Protection Type"),
    ("flange face finish", None, "flange_finish", "mechanical", "Flange Face Finish"),
    ("flow direction", None, "flow_direction", "mechanical", "Flow Direction"),
    ("trim construction", None, "trim_construction", "mechanical", "Trim Construction"),
    ("ser no.", None, "serial_no", "general", "Serial No."),
]


def lookup_102(label: str, group: str, heading: str = ""):
    n = norm_label(label).rstrip(" :")
    g = (group or "").upper().replace(" ", "")
    for lab, gw, key, sec, disp in _L102:
        if n == lab and (gw is None or gw in g):
            return key, sec, disp
    return None


def effective(f: dict | None) -> str:
    """The value to check: the reviewer's correction, else the value inside the note the cell points at
    ('Note 14' -> '316/316L SS ASTM A351-CF8M/CF3M'), else what the cell says."""
    if not f:
        return ""
    if f.get("edited_value") is not None:
        return f["edited_value"]
    ref = f.get("ref") or {}
    if isinstance(ref, dict) and ref.get("value"):
        return ref["value"]
    return f.get("value") or ""



# ── valve37: valve kinds — Ball (the original module) · Globe · Butterfly · PSV ─────────────────────────────
# A project opened from the Globe / Butterfly / PSV menu is named '<project> · <Kind>' (valve.js ?kind=).  The kind
# of the PROJECT decides which review rules run (a Ball project runs exactly what it ran before); the kind of each
# DATASHEET (family) is read from the sheet itself and only used to say when a sheet was put in the wrong menu.
KINDS = {"ball": "Ball Valve", "globe": "Globe Valve", "butterfly": "Butterfly Valve", "psv": "PSV"}


def project_kind(name: str) -> str:
    """'CO2 PJT · Globe Valve' -> 'globe'.  Anything else (all projects made before valve37) -> 'ball'."""
    n = (name or "").strip().lower()
    for k, disp in KINDS.items():
        if k != "ball" and n.endswith("· " + disp.lower()):
            return k
    return "ball"


def family(form: str, fields: dict, title: str = "", tag: str = "") -> str:
    """What the datasheet itself says it is: 'ball' · 'globe' · 'butterfly' · 'psv' · '' (cannot tell).
    Read from the form and the sheet's own words (Valve Type / Body Type / Instrument Type / title) — not from the
    tag letters alone (a Form 101 control valve is 'FV' whether globe or butterfly)."""
    def val(k):
        f = fields.get(k) or {}
        return str(f.get("value") or "")
    t = " ".join([title or "", val("body_type"), val("instrument_type"), val("psv_type")]).lower()
    if form == "701" or re.search(r"relief valve|safety valve|safety relief", (title or "").lower()):
        return "psv"
    if "butterfly" in t or re.search(r"\b(triple|double)\s*offset\b", t):
        return "butterfly"
    if "globe" in t:
        return "globe"
    if "ball" in t:
        return "ball"
    vt = valve_type(tag)
    if vt in ("PSV", "PRV", "SRV", "PVRV", "PVSV") and form != "101":
        return "psv"
    return ""


# ── Form 101 (Control Valve: Globe / Butterfly CV) ─────────────────────────────────────────────────────────
# Same page layout as Form 102 (two numbered columns, 'Label : value', bold values) but many labels repeat in several
# blocks (Manufacturer · Model · Size · Tag No · Notes · Handwheel · Rating · Material).  The block is the vertical caption
# band the row sits in (TAG · VALVE GEN. · GENERAL DESIGN DATA · POSITNR. · BODY/BONNET · VALVE TRIM · ACTUATOR · PAINT ·
# VALVE ACC. · PNEUMATIC ACC. · ELECTRICAL ACC.), and inside a block the last bare caption row (heading: 'Instrument Air
# Supply' · 'Enclosure' · 'Air Set' · 'Volume Tank' · 'Solenoid Valve' · 'Colour') or the 'Type of Position Indication' row.
# (label, block word or None, heading word or None, key, section, display) — first match wins.
_L101 = [
    ("tag no.", "TAG", None, "tag", "general", "Tag Number"),
    ("instrument type", None, None, "instrument_type", "general", "Instrument Type"),
    ("pid no.", None, None, "pid_no", "general", "P&ID Number"),
    ("valve type", None, None, "body_type", "mechanical", "Valve Type"),
    ("service", "TAG", None, "service", "general", "Service Description"),
    ("valve service", None, None, "valve_function", "general", "Valve Service"),
    ("package", None, None, "package", "general", "Package"),
    ("quantity tags", None, None, "qty", "general", "Quantity"),
    ("manufacturer name", None, None, "manufacturer", "general", "Manufacturer"),
    ("model no", None, None, "model", "general", "Model Number"),
    ("ser no.", None, None, "serial_no", "general", "Serial No."),
    ("air failure action", None, None, "fail_position", "actuator", "Air Failure Action"),
    ("max. shut off pressure", None, None, "max_dp_closed", "process", "Max. Shut Off Pressure"),
    ("leakage class", None, None, "leakage_class", "mechanical", "Leakage Class"),
    ("material corrosion requirement", None, None, "corrosion_req", "mechanical", "Material Corrosion Requirement"),
    ("line no.", None, None, "line_no", "general", "Line Number"),
    ("line size", None, None, "line_size_inlet", "mechanical", "Line Size"),
    ("schedule", None, None, "line_schedule", "mechanical", "Schedule"),
    ("serviceclass", None, None, "piping_class", "mechanical", "Piping Class"),
    ("service class", None, None, "piping_class", "mechanical", "Piping Class"),
    ("insulation thickness", None, None, "pipe_insulation", "mechanical", "Insulation Thickness"),
    ("design pressure", None, None, "design_pressure", "process", "Design Pressure"),
    ("design temperature", None, None, "design_temp", "process", "Design Temperature"),
    ("notes for line", None, None, "line_notes", "general", "Notes for Line"),
    ("mechanical design pressure", "ACTUAT", None, "act_design_pressure", "actuator", "Actuator Mechanical Design Pressure"),
    ("mechanical design pressure", None, "AIR", "ia_design_pressure", "accessories", "Instrument Air Mech. Design Pressure"),
    ("operating pressure(max/min)", None, None, "ia_op_pressure", "accessories", "Instrument Air Operating Pressure (Max/Min)"),
    ("operating pressure (max/min)", None, None, "ia_op_pressure", "accessories", "Instrument Air Operating Pressure (Max/Min)"),
    ("dew point temperature", None, None, "ia_dew_point", "accessories", "Instrument Air Dew Point"),
    ("class", None, None, "area_class", "special", "Hazardous Area Class"),
    ("type", "GENERAL", None, "ex_type", "special", "Ex Protection Type"),
    ("certificate", None, None, "ex_certificate", "special", "Ex Certificate"),
    ("weather protection", None, None, "ingress", "special", "Weather Protection"),
    ("positioner type", None, None, "positioner", "positioner", "Positioner Type"),
    ("manufacturer", "POS", None, "pos_manufacturer", "positioner", "Positioner Manufacturer"),
    ("model", "POS", None, "pos_model", "positioner", "Positioner Model"),
    ("input signal type", None, None, "pos_signal", "positioner", "Positioner Input Signal"),
    ("gauges", "POS", None, "pos_gauges", "positioner", "Positioner Gauges"),
    ("bypass", None, None, "pos_bypass", "positioner", "Positioner Bypass"),
    ("body size", None, None, "body_size", "mechanical", "Valve Size"),
    ("rating", "BODY", None, "rating", "mechanical", "Pressure Rating"),
    ("conn type", None, None, "connections", "mechanical", "End Connection"),
    ("end conn type", None, None, "connections", "mechanical", "End Connection"),
    ("conn. type", None, None, "connections", "mechanical", "End Connection"),
    ("flange face finish", None, None, "flange_finish", "mechanical", "Flange Face Finish"),
    ("face to face dimension", None, None, "face_to_face", "mechanical", "Face to Face Dimension"),
    ("body/bonnet material", None, None, "body_material", "mechanical", "Body / Bonnet Material"),
    ("type of bonnet", None, None, "bonnet_type", "mechanical", "Bonnet Type"),
    ("flow direction", None, None, "flow_direction", "mechanical", "Flow Direction"),
    ("corrosion allowance", None, None, "corrosion_allowance", "mechanical", "Corrosion Allowance"),
    ("gasket material", None, None, "gasket_material", "mechanical", "Gasket Material"),
    ("packing mat.", None, None, "packing_material", "mechanical", "Packing Material"),
    ("packing material", None, None, "packing_material", "mechanical", "Packing Material"),
    ("trim type", None, None, "trim_type", "trim", "Trim Type"),
    ("size", "TRIM", None, "trim_size", "trim", "Trim Size"),
    ("trim construction", None, None, "trim_construction", "trim", "Trim Construction"),
    ("rated cv", None, None, "rated_cv", "trim", "Rated Cv"),
    ("rated travel", None, None, "rated_travel", "trim", "Rated Travel"),
    ("characteristic", None, None, "flow_char", "trim", "Flow Characteristic"),
    ("plug / ball / disc", None, None, "ball_material", "trim", "Plug / Ball / Disc Material"),
    ("seat", "TRIM", None, "seat_material", "trim", "Seat Material"),
    ("cage / guide", None, None, "cage_material", "trim", "Cage / Guide Material"),
    ("stem", "TRIM", None, "stem_material", "trim", "Stem Material"),
    ("manuf.", "ACTUAT", None, "act_manufacturer", "actuator", "Actuator Manufacturer"),
    ("model", "ACTUAT", None, "act_model", "actuator", "Actuator Model"),
    ("type of actuator", None, None, "act_type", "actuator", "Actuator Type"),
    ("size", "ACTUAT", None, "act_size", "actuator", "Actuator Size"),
    ("case", None, None, "act_material", "actuator", "Actuator Case Material"),
    ("yoke", "ACTUAT", None, "act_yoke_material", "actuator", "Actuator Yoke Material"),
    ("stem", "ACTUAT", None, "act_stem_material", "actuator", "Actuator Stem Material"),
    ("actuator force design pressure", None, None, "act_force_pressure", "actuator", "Actuator Force Design Pressure"),
    ("required air supply pressure", None, None, "act_air_supply", "actuator", "Required Air Supply Pressure"),
    ("stroke speed", None, None, "stroke_time_s", "actuator", "Stroke Speed"),
    ("travel indicator", None, None, "travel_indicator", "actuator", "Travel Indicator"),
    ("orientation", None, None, "act_orientation", "actuator", "Actuator Orientation"),
    ("painting system", None, None, "painting", "special", "Painting System"),
    ("body", "PAINT", None, "paint_body", "special", "Paint Colour — Body"),
    ("yoke", "PAINT", None, "paint_yoke", "special", "Paint Colour — Yoke"),
    ("actuator", "PAINT", None, "paint_actuator", "special", "Paint Colour — Actuator"),
    ("handwheel", "PAINT", None, "paint_handwheel", "special", "Paint Colour — Handwheel"),
    ("lubricator / isolation valve", None, None, "lubricator", "accessories", "Lubricator / Isolation Valve"),
    ("lubricant material", None, None, "lubricant", "accessories", "Lubricant Material"),
    ("handwheel", None, None, "handwheel", "accessories", "Handwheel"),
    ("mechanical valve stopper", None, None, "valve_stopper", "accessories", "Mechanical Valve Stopper"),
    ("air tube material", None, None, "tubing", "accessories", "Air Tube Material"),
    ("size", "PNEU", None, "tubing_size", "accessories", "Air Tube Size"),
    ("fitting type", None, None, "fitting", "accessories", "Fitting Type"),
    ("mat", None, None, "fitting_material", "accessories", "Fitting Material"),
    ("min.size and connection", None, None, "act_air_connection", "accessories", "Air Supply Min. Size and Connection"),
    ("air failure lock-up valve", None, None, "lockup_valve", "accessories", "Air Failure Lock-Up Valve"),
    ("set", None, None, "lockup_set", "accessories", "Lock-Up Valve Set"),
    ("manufacturer", None, "AIRSET", "afr_manufacturer", "accessories", "Air Set Manufacturer"),
    ("model", None, "AIRSET", "afr_model", "accessories", "Air Set Model"),
    ("filter / gauges", None, None, "afr", "accessories", "Air Filter Regulator / Gauges"),
    ("tag no.", None, "VOLUME", "vt_tag", "accessories", "Volume Tank Tag No."),
    ("volume tank code", None, None, "vt_code", "accessories", "Volume Tank Code"),
    ("basis of volume", None, None, "vt_basis", "accessories", "Volume Tank Basis of Volume"),
    ("material", None, "VOLUME", "vt_material", "accessories", "Volume Tank Material"),
    ("check valve", None, None, "vt_check_valve", "accessories", "Volume Tank Check Valve"),
    ("electrical connection", None, None, "elec_connection", "accessories", "Electrical Connection"),
    ("external terminal box", None, None, "terminal_box", "accessories", "External Terminal Box"),
    ("type of position indication", None, None, "pos_ind_type", "accessories", "Type of Position Indication"),
    ("tag no", None, "POSIND", "pos_tx_tag", "accessories", "Position Indication Tag No."),
    ("quantity", None, "POSIND", "pos_tx_qty", "accessories", "Position Indication Quantity"),
    ("type", None, "POSIND", "pos_tx_signal", "accessories", "Position Indication Signal"),
    ("manuf.", None, "POSIND", "pos_tx_manufacturer", "accessories", "Position Indication Manufacturer"),
    ("model", None, "POSIND", "pos_tx_model", "accessories", "Position Indication Model"),
    ("contact type", None, "POSIND", "pos_tx_contact", "accessories", "Position Indication Contact Type"),
    ("rating", None, "POSIND", "pos_tx_ingress", "accessories", "Position Indication Rating"),
    ("actuation points", None, "POSIND", "pos_tx_points", "accessories", "Position Indication Actuation Points"),
    ("tag no", None, "SOLENOID", "sov_tag", "accessories", "Solenoid Valve Tag No."),
    ("manuf.", None, "SOLENOID", "sov_manufacturer", "accessories", "Solenoid Valve Manufacturer"),
    ("model", None, "SOLENOID", "sov_model", "accessories", "Solenoid Valve Model"),
    ("power supply", None, "SOLENOID", "sov_power_supply", "accessories", "Solenoid Valve Power Supply"),
    ("energ act", None, None, "sov_energize", "accessories", "Solenoid Valve Energize Action"),
    ("body mat", None, None, "sov_body_material", "accessories", "Solenoid Valve Body Material"),
    ("man reset", None, None, "manual_reset", "accessories", "Solenoid Valve Manual Reset"),
    ("coil insulation class", None, None, "sov_coil_class", "accessories", "Solenoid Coil Insulation Class"),
    ("notes", None, None, "notes_row", "general", "Notes (row)"),
]


def _blk(group: str) -> str:
    return re.sub(r"[^A-Z]", "", (group or "").upper())


def lookup_101(label: str, group: str, heading: str = "", ctx: str = ""):
    """(key, section, display) for a Form 101 row.  group = block caption, heading = last bare caption, ctx = 'POSIND'
    after the 'Type of Position Indication' row of the ELECTRICAL ACC. block."""
    n = norm_label(label).rstrip(" :.") if norm_label(label).endswith(":") else norm_label(label)
    b = _blk(group)
    h = _blk(heading) + ("POSIND" if ctx == "POSIND" else "")
    if "AIRSET" in h.replace(" ", ""):
        h += "AIRSET"
    for lab, gw, hw, key, sec, disp in _L101:
        if n != lab and n.rstrip(".") != lab.rstrip("."):
            continue
        if gw and gw not in b and not (gw == "POS" and ("POSITNR" in b or "POSTNR" in b or "POSITIONER" in b)):
            continue
        if hw and hw not in h:
            continue
        return key, sec, disp
    return None


# Form 101 sheet 2 (Process / Sizing calculation data, rows × Unit · Max · Nor · Min): sizing results go to their own
# section so a blank sizing line is not a 'missing process data' finding; rows printed across all three cases are one value.
SIZING_101 = {"process case": ("case", "Process Case"), "case description": ("case_desc", "Case Description"),
              "superheat temperature": ("superheat", "Superheat Temperature"), "flash ratio": ("flash_ratio", "Flash Ratio"),
              "fl(liquid pressure recovery factor)": ("fl", "FL (Liquid Pressure Recovery Factor)"),
              "xt(pressure drop ratio factor)": ("xt", "Xt (Pressure Drop Ratio Factor)"),
              "start-up flow (min / nor / max)": ("startup_flow", "Start-up Flow"), "calculated cv": ("calc_cv", "Calculated Cv"),
              "required cv": ("req_cv", "Required Cv"), "travel of valve": ("travel", "Travel of Valve"),
              "predict spl": ("spl_pred", "Predicted SPL"), "allowable spl": ("spl_allow", "Allowable SPL")}
# fluid properties on sheet 2 that only one phase needs (gas: MW · k · Z; liquid: vapour · critical pressure; viscosity) —
# kept, shown, compared with Process Data, but not a 'missing process data' finding when blank
PROPS_101 = {"mol_weight", "cp_cv", "z_factor", "vapor_pressure", "critical_pressure", "viscosity"}
SPAN_101 = {"max. shut off pressure": ("sz_shutoff", "Max. Shut Off Pressure (sheet 2)"),
            "design pressure": ("sz_design_pressure", "Design Pressure (sheet 2)"),
            "design temperature": ("sz_design_temp", "Design Temperature (sheet 2)")}


# ── Form 701 (Pressure Relief Valve) ───────────────────────────────────────────────────────────────────────
# One numbered column (1-50); bold values on short underlines (1-3 slots per row); small sub-labels before a slot
# ('Type' · 'Action' · 'Sensing' · 'Vent' · 'Tightness' · 'Size' · 'Rating' · 'Inlet' · 'Outlet').  A label written
# 'A / B / C' gives one key per slot.  (normalised label) -> (keys for the slots, section, display names)
_L701 = {
    "tag no.": (["tag"], "general", ["Tag Number"]),
    "service": (["service"], "general", ["Service Description"]),
    "p&id no./line no./equipment no.": (["pid_no", "line_no", "equipment_no"], "general", ["P&ID Number", "Line Number", "Equipment No."]),
    "service class": (["piping_class"], "mechanical", ["Piping Class"]),
    "quantity tags": (["qty"], "general", ["Quantity"]),
    "code & standard": (["code_standard"], "basis", ["Code & Standard"]),
    "governing case": (["governing_case"], "basis", ["Governing Case"]),
    "api 526 compliance": (["api526"], "basis", ["API 526 Compliance"]),
    "type": (["psv_type"], "mechanical", ["Valve Type"]),
    "nozzle": (["nozzle_type"], "mechanical", ["Nozzle"]),
    "bonnet type": (["bonnet_type"], "mechanical", ["Bonnet Type"]),
    "pilot": (["pilot"], "mechanical", ["Pilot"]),
    "seat": (["seat"], "mechanical", ["Seat"]),
    "inlet": (["inlet"], "mechanical", ["Inlet"]),
    "outlet": (["outlet"], "mechanical", ["Outlet"]),
    "body / bonnet / seat (nozzle)": (["body_material", "bonnet_material", "nozzle_material"], "material",
                                      ["Body Material", "Bonnet Material", "Seat (Nozzle) Material"]),
    "piston / resilient seal / guide": (["disc_material", "resilient_seal", "guide_material"], "material",
                                        ["Piston / Disc Material", "Resilient Seal", "Guide Material"]),
    "adjusting rings / spring / bellows": (["rings_material", "spring_material", "bellows_material"], "material",
                                           ["Adjusting Rings Material", "Spring Material", "Bellows Material"]),
    "body / internal / seat": (["pilot_body_material", "pilot_internal_material", "pilot_seat_material"], "material",
                               ["Pilot Body Material", "Pilot Internal Material", "Pilot Seat Material"]),
    "diaphragm / tubing and fitting / spring": (["pilot_diaphragm", "pilot_tubing", "pilot_spring"], "material",
                                                ["Pilot Diaphragm", "Pilot Tubing and Fitting", "Pilot Spring"]),
    "filter body / filter element": (["filter_body", "filter_element"], "material", ["Filter Body", "Filter Element"]),
    "fluid / phase": (["fluid", "fluid_state"], "process", ["Fluid", "Phase"]),
    "max. relieving flow rate": (["relieving_flow"], "process", ["Max. Relieving Flow Rate"]),
    "operating pressure": (["op_pressure"], "process", ["Operating Pressure"]),
    "set pressure": (["set_pressure"], "process", ["Set Pressure"]),
    "cold differential set": (["cdtp"], "process", ["Cold Differential Test Pressure"]),
    "operating temperature": (["op_temp"], "process", ["Operating Temperature"]),
    "relief temperature": (["relief_temp"], "process", ["Relief Temperature"]),
    "allowable over pressure": (["overpressure"], "process", ["Allowable Over Pressure"]),
    "blowdown": (["blowdown"], "process", ["Blowdown"]),
    "superimposed back pressure": (["sbp"], "process", ["Superimposed Back Pressure"]),
    "constant / variable": (["sbp_constant", "sbp_variable"], "process", ["Back Pressure — Constant", "Back Pressure — Variable"]),
    "max. back pressure": (["max_bp"], "process", ["Max. Back Pressure"]),
    "molecular weight": (["mol_weight"], "process", ["Molecular Weight"]),
    "density @ rt": (["density"], "process", ["Density @ RT"]),
    "viscosity @ rt": (["viscosity"], "process", ["Viscosity @ RT"]),
    "compressibility factor": (["z_factor"], "process", ["Compressibility Factor"]),
    "specific heat ratio": (["cp_cv"], "process", ["Specific Heat Ratio"]),
    "design pressure": (["design_pressure"], "process", ["Design Pressure"]),
    "design temperature": (["design_temp"], "process", ["Design Temperature"]),
    "calculated area": (["calc_area"], "sizing", ["Calculated Area"]),
    "selected area": (["selected_area"], "sizing", ["Selected Area"]),
    "orifice designation": (["orifice"], "sizing", ["Orifice Designation"]),
    "reaction force": (["reaction_force"], "sizing", ["Reaction Force"]),
    "cap / lifting lever / test gag": (["cap_type", "lifting_lever", "test_gag"], "accessories", ["Cap", "Lifting Lever", "Test Gag"]),
    "bug screen / external filter": (["bug_screen", "ext_filter"], "accessories", ["Bug Screen", "External Filter"]),
    "back flow preventer / field test conn.": (["backflow_preventer", "field_test_conn"], "accessories",
                                               ["Back Flow Preventer", "Field Test Connection"]),
    "manufacturer": (["manufacturer"], "general", ["Manufacturer"]),
    "model no.": (["model"], "general", ["Model Number"]),
}
# sub-label words printed small before a value slot -> key suffix (Pilot Type · Seat Tightness · Inlet Size …)
SUB_701 = {"type": "type", "action": "action", "sensing": "sensing", "vent": "vent", "tightness": "tightness",
           "size": "size", "rating": "rating", "inlet": "inlet", "outlet": "outlet"}
# what a sub-labelled slot of a row is called: (row key, sub word) -> (key, display)
SUBKEY_701 = {("pilot", "type"): ("pilot_type", "Pilot Type"), ("pilot", "action"): ("pilot_action", "Pilot Action"),
              ("pilot", "sensing"): ("pilot_sensing", "Pilot Sensing"), ("pilot", "vent"): ("pilot_vent", "Pilot Vent"),
              ("seat", "type"): ("seat_type", "Seat Type"), ("seat", "tightness"): ("seat_tightness", "Seat Tightness"),
              ("inlet", "size"): ("inlet_size", "Inlet Size"), ("inlet", "rating"): ("inlet_rating", "Inlet Rating"),
              ("inlet", "type"): ("inlet_facing", "Inlet Connection Type"), ("outlet", "size"): ("outlet_size", "Outlet Size"),
              ("outlet", "rating"): ("outlet_rating", "Outlet Rating"), ("outlet", "type"): ("outlet_facing", "Outlet Connection Type"),
              ("piping_class", "inlet"): ("piping_class", "Piping Class (Inlet)"),
              ("piping_class", "outlet"): ("piping_class_outlet", "Piping Class (Outlet)")}


def lookup_701(label: str):
    n = norm_label(label).rstrip(" :")
    return _L701.get(n)


# fields a reviewer expects on each kind of sheet (Data Missing when present on the form but empty) — Ball keeps issues.REQUIRED
REQUIRED_BY_KIND = {
    "globe": ["tag", "service", "pid_no", "line_no", "piping_class", "body_size", "rating", "body_type", "connections",
              "body_material", "ball_material", "seat_material", "stem_material", "act_type", "fail_position", "leakage_class",
              "flow_char", "positioner", "pos_signal"],
    "butterfly": ["tag", "service", "pid_no", "line_no", "piping_class", "body_size", "rating", "body_type", "connections",
                  "body_material", "ball_material", "seat_material", "stem_material", "act_type", "fail_position", "leakage_class"],
    "psv": ["tag", "service", "pid_no", "piping_class", "psv_type", "inlet_size", "inlet_rating", "outlet_size", "outlet_rating",
            "orifice", "body_material", "nozzle_material", "disc_material", "spring_material"],
    # (PSV process items — fluid · set pressure · relieving flow · design P/T … — are checked by the PROCESS DATA rule)
}
