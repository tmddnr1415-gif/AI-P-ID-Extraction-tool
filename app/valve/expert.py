"""Ball valve engineering review — the design / function comments a ball valve engineer writes on a datasheet,
and the 'learned' check against every other datasheet of the project.

  VR-xx  design rules (connection, flange standard, floating/trunnion, PMS item, fail action, SIL, leakage, anti-static,
         blow-out, fire-safe, seat configuration / cavity relief, insulation, piggability, size, erosive, actuator factor)
  PC-01  peer check: what the other datasheets of the same piping class say (learned from all uploaded datasheets).

Same output shape and levels as matreview (Action / Confirm / Note).  Every finding names the knowledge entry
(knowledge.KB) it rests on, so the reviewer can read why.  A rule speaks only when the values it needs are written.
"""
from __future__ import annotations

import collections
import re

from app.valve import knowledge, material, schema
from app.valve.matreview import ACTION, CONFIRM, NOTE, SEVERITY

# Typical upper size (NPS) of floating ball valves per class — industry practice, sources differ (knowledge
# 'des.floating_trunnion'); the upper end of the quoted ranges is used so only clear cases are raised.
FLOATING_MAX_NPS = {150: 8, 300: 6, 600: 4, 900: 2, 1500: 2, 2500: 1.5}
PEER_MIN, PEER_SHARE = 5, 0.8          # peer check: at least 5 other datasheets, 80 % of them agree
PEER_FIELDS = ["body_material", "ball_material", "stem_material", "seat_material", "seal_material", "packing_material",
               "connections", "leakage_class", "nace", "rating", "body_type"]

_FLAMMABLE = re.compile(r"HYDROCARBON|FUEL\s*GAS|\bGAS\b|PROPANE|BUTANE|METHANE|CONDENSATE|\bOIL\b|H2S|SOUR|AMINE|RELIEF|FLARE|VENT", re.I)
_TOXIC = re.compile(r"\btoxic\b|\bH2S\b|\bsour\b", re.I)
_SOFT = re.compile(r"PTFE|RTFE|TFE|PEEK|NYLON|DEVLON|SOFT", re.I)
_METAL = re.compile(r"metal[- ]?seat|\bTCC\b|tungsten|stellite|chrom\w*\s+carbide", re.I)
_SEATCFG = re.compile(r"\bSPE\b|\bDPE\b|\bDIB\b|\bDBB\b|double\s+(?:block|piston|isolation)|self[- ]reliev|cavity\s+(?:pressure\s+)?relie", re.I)
_PLACE = re.compile(r"^\s*(VTA|TBC|TBA|HOLD|NA|N/A|-|—|)\s*$|note\s*[-–]?\s*\d+|general\s+note", re.I)


def _num(v):
    m = re.search(r"\d+(?:\.\d+)?", str(v or ""))
    return float(m.group(0)) if m else None


def _inch(v):
    from app.valve.pms import _inch as inch
    return inch(v)


def review(ds: dict, general_notes: dict | None = None, pms_class: dict | None = None, process_rows: list | None = None,
           pd_row: dict | None = None, requirements: list | None = None, peers: dict | None = None) -> list[dict]:
    F = {f["key"]: f for f in ds["fields"]} if isinstance(ds["fields"], list) else ds["fields"]
    val = lambda k: (schema.effective(F[k]) if k in F else "") or ""       # noqa: E731
    notes = ds.get("notes") or []
    gn = {str(k): v for k, v in (general_notes or {}).items()}
    c = pms_class or {}
    reqs = {r["key"] for r in requirements or [] if not r.get("negative")}
    all_text = " ".join(n["text"] for n in notes) + " " + " ".join(str(t) for t in gn.values()) + " " + \
        " ".join(val(k) for k in F)
    pdv = {r["key"]: r for r in process_rows or [] if r.get("pd") not in (None, "")}
    fluid = (pdv.get("fluid") or {}).get("pd") or val("fluid") or val("fluid.nor") or ""
    phase = (pdv.get("fluid_state") or {}).get("pd") or val("fluid_state") or val("fluid_state.nor") or ""
    remarks = " ".join(str((pd_row or {}).get("values", {}).get(k, {}).get("v") or "") for k in ("remarks", "notes"))
    out = []

    def ev(k):
        f = F.get(k) or {}
        return {"doc": "Datasheet", "where": f"row {f.get('row')} {f.get('display') or k}" if f.get("row") else (f.get("display") or k),
                "page": f.get("page"), "bbox": f.get("bbox"), "text": val(k)} if k in F else None

    def ev_pms(where, text):
        return {"doc": "PMS", "where": f"class {c.get('code')} · {where}", "page": c.get("header_page"), "bbox": None, "text": str(text)[:220]}

    def add(rule, level, title, key, short, comment, kb, evidence, basis=None):
        k = knowledge.get(kb)
        out.append({"rule": rule, "level": level, "severity": SEVERITY[level], "title": title, "key": key, "short": short, "comment": comment,
                    "basis": basis or k["ref"], "kb": kb, "kb_title": k["title"], "kb_text": k["text"],
                    "evidence": [e for e in evidence if e]})

    def resolved(k):                                       # 'Note 8 & 9' → the value plus what notes 8 and 9 say
        v = val(k)
        nos = {int(x) for x in re.findall(r"\d+", " ".join(re.findall(r"note\s*[-–]?\s*[\d\s&,and]+", v, re.I)))}
        return v + " " + " ".join(n["text"] for n in notes if n.get("no") in nos and not re.match(r"^\s*general", v, re.I))

    size = _inch(val("body_size"))
    rating = int(_num(val("rating")) or 0) or (c.get("rating") or 0)
    btype = (resolved("body_type") + " " + val("trim_type") + " " + val("trim_construction")).upper()
    vtype = "TRUNNION" if "TRUNNION" in btype else "FLOATING" if "FLOATING" in btype else ""
    conn = val("connections").upper()
    seat = val("seat_material")
    soft = bool(_SOFT.search(seat)) and not _METAL.search(seat)

    # VR-01 flange facing vs PMS class -------------------------------------------------------------------------
    face_ds = "RTJ" if re.search(r"RTJ|RING\s*JOINT", conn) else "RF" if re.search(r"\bRF\b|RAISED", conn) else ""
    face_pms = "RTJ" if "RING" in (c.get("facing") or "").upper() else "RF" if "RAISED" in (c.get("facing") or "").upper() else ""
    if face_ds and face_pms and face_ds != face_pms:
        add("VR-01", ACTION, "Flange facing differs from PMS class", "connections",
            f"Flange facing {face_ds}; PMS {c.get('code')} requires {face_pms}. Revise.",
            f"Datasheet end connection '{val('connections')}' is {face_ds}, but PMS class {c.get('code')} flange facing is "
            f"{c.get('facing')}. The valve flanges must mate the line flanges — correct the facing (RTJ face-to-face is longer).",
            "std.b165", [ev("connections"), ev_pms("Flange Facing", c.get("facing"))])

    # VR-02 flange standard vs size -------------------------------------------------------------------------------
    if size and "B16.47" in conn and size <= 24:
        add("VR-02", ACTION, "B16.47 flange on a valve ≤ NPS 24", "connections",
            f"{val('body_size')} valve: flanges to ASME B16.5, not B16.47. Revise.",
            f"Size {val('body_size')} uses ASME B16.5 flanges; B16.47 (Series A/B) covers NPS 26 and above.", "std.b165", [ev("connections"), ev("body_size")])
    elif size and size > 24 and "B16.5" in conn and "B16.47" not in conn:
        add("VR-02", ACTION, "B16.5 flange on a valve above NPS 24", "connections",
            f"{val('body_size')} valve: flanges to ASME B16.47 Series A/B. State series.",
            f"Size {val('body_size')} is above NPS 24: flanges are ASME B16.47 Series A or B — state which series matches the line.",
            "std.b165", [ev("connections"), ev("body_size")])

    # VR-03 floating ball beyond typical size × class ----------------------------------------------------------
    lim = next((v for k, v in sorted(FLOATING_MAX_NPS.items()) if rating and rating <= k), None) if rating else None
    if vtype == "FLOATING" and size and lim and size > lim:
        add("VR-03", CONFIRM, "Floating ball beyond typical size for the class", "body_type",
            f"Floating ball {val('body_size')} Class {rating}: confirm torque / design or use trunnion.",
            f"Floating ball {val('body_size')} in Class {rating}: floating designs are normally used up to about NPS {lim:g} in "
            f"this class (seat load and torque grow with size × pressure). Confirm the manufacturer's floating design / torque "
            "at full ΔP, or specify trunnion-mounted.", "des.floating_trunnion", [ev("body_type"), ev("body_size"), ev("rating")],
            basis="Industry practice (API 6D leaves the choice to the manufacturer) — company spec governs")

    # VR-04 floating / trunnion vs the PMS ball valve item --------------------------------------------------------
    if c.get("items") and vtype:
        from app.valve import pms as pmsmod
        best, _, _ = pmsmod.select_item(c, val)
        if best and best[2]["type"] and best[2]["type"] != vtype:
            add("VR-04", CONFIRM, "Ball type differs from the PMS item", "body_type",
                f"{vtype.title()} specified; PMS item {best[1]['code']} is {best[2]['type'].lower()}. Align with PMS.",
                f"Datasheet is {vtype.lower()}, PMS item {best[1]['code']} for this size is {best[2]['type'].lower()} "
                f"({best[1]['desc'][:120]}…). Align the datasheet with the PMS item or record the deviation.",
                "des.floating_trunnion", [ev("body_type"), {"doc": "PMS", "where": f"item {best[1]['code']}", "page": best[1]["page"],
                                                            "bbox": best[1]["bbox"], "text": best[1]["desc"][:200]}])

    # VR-05 fail action vs spring ----------------------------------------------------------------------------------
    fp, spring = val("fail_position").upper(), val("act_spring").upper()
    if fp.startswith(("CLOSE", "OPEN", "FC", "FO")) and spring and re.match(r"\s*(NOT\s+REQUIRED|NO\b|NA\b|N/A|NONE)", spring):
        add("VR-05", ACTION, "Fail-safe position without spring", "act_spring",
            f"Fail {val('fail_position')} requires spring-return actuator. Revise.",
            f"Fail position '{val('fail_position')}' needs a spring-return (or accumulator) actuator, but the spring is "
            f"'{val('act_spring')}'.", "des.actuator", [ev("fail_position"), ev("act_spring")])
    elif fp.startswith(("LAST", "FL", "STAY")) and spring.startswith("REQ"):
        add("VR-05", CONFIRM, "Fail-last with spring", "act_spring",
            "Fail last with spring specified. Confirm fail action.",
            f"Fail position '{val('fail_position')}' (stay-put) is normally double-acting; a spring is specified "
            f"('{val('act_spring')}'). Confirm the intended fail action.", "des.actuator", [ev("fail_position"), ev("act_spring")])

    # VR-06 SIL: fail-safe and partial stroke ----------------------------------------------------------------------
    sil = re.search(r"SIL\s*([1-4])", val("sil"), re.I)
    if sil:
        if fp.startswith(("LAST", "FL")):
            add("VR-06", CONFIRM, "SIL valve with fail-last action", "fail_position",
                f"{val('sil')} with fail last. Confirm fail-safe position.",
                f"{val('sil')} safety valve with fail position '{val('fail_position')}': a safety function normally needs a "
                "defined fail-safe position (spring return). Confirm with the SRS.", "std.sil", [ev("sil"), ev("fail_position")])
        if int(sil.group(1)) >= 2 and "pst" not in reqs:
            add("VR-06", NOTE, "SIL 2 without partial stroke test", "sil",
                f"{val('sil')}: confirm PST requirement and SIL certificate.",
                f"{val('sil')}: no partial stroke test requirement found on the datasheet or its notes. Confirm the proof-test "
                "strategy (PST / full stroke) and the SIL certificate of the valve + actuator assembly.", "std.sil", [ev("sil")])

    # VR-07 leakage class vs seat / tightness --------------------------------------------------------------------
    leak, tight = val("leakage_class").upper(), val("tightness").upper()
    rate = re.search(r"RATE\s*([A-G])", leak)
    if soft and rate and rate.group(1) != "A":
        add("VR-07", CONFIRM, "Soft seat with leakage rate below A", "leakage_class",
            f"Soft seat with {val('leakage_class')}. Confirm Rate A.",
            f"Soft seat '{seat}' with '{val('leakage_class')}': soft-seated ball valves are tested to Rate A (zero visible "
            "leakage). Confirm why a lower rate is accepted.", "std.leak", [ev("leakage_class"), ev("seat_material")])
    if ("TIGHT" in tight or "TSO" in tight) and rate and rate.group(1) != "A":
        add("VR-07", CONFIRM, "Tight shut-off but leakage rate below A", "leakage_class",
            f"TSO specified but {val('leakage_class')}. Confirm Rate A.",
            f"Tightness '{val('tightness')}' but leakage class '{val('leakage_class')}'. Tight shut-off is read as Rate A.",
            "std.leak", [ev("tightness"), ev("leakage_class")])

    # VR-08 anti-static / blow-out-proof stem -------------------------------------------------------------------
    for key, kname, rule_title in (("antistatic", "anti-static device", "Anti-static not stated"),
                                   ("blowout", "blow-out-proof stem", "Blow-out-proof stem not stated")):
        if key not in reqs and seat:
            add("VR-08", NOTE, rule_title, "body_type",
                f"State {kname} (API 6D / ISO 17292).",
                f"No {kname} requirement found on the datasheet, its notes or general notes. API 6D and ISO 17292 require it; "
                "state it or confirm the referenced valve specification covers it.", "des.stem", [ev("body_type")])

    # VR-09 fire-safe for flammable / toxic service ------------------------------------------------------------------
    service = f"{fluid} {remarks} {val('service')}"
    fire_doc = "fire_safe" in reqs or re.search(r"FIRE\s*(?:TESTED|SAFE)", " ".join(it.get("desc", "") for it in c.get("items") or []), re.I)
    if (_FLAMMABLE.search(fluid) or _TOXIC.search(service)) and not fire_doc:
        add("VR-09", CONFIRM, "No fire-safe requirement for flammable / toxic service", "fire_safe",
            f"{fluid or 'Toxic / flammable'} service: fire-safe (API 607) not stated. Confirm.",
            f"Service '{fluid or val('service')}' ({remarks.strip() or 'toxic/flammable'}) but no fire-safe (API 607 / ISO 10497) "
            "requirement is stated. Confirm the fire-safe requirement.", "std.fire",
            [ev("fire_safe"), ev("service"), {"doc": "Process Data" if pdv.get("fluid") else "Datasheet", "where": "Service Fluid",
                                              "page": (pdv.get("fluid") or {}).get("pd_page"), "bbox": (pdv.get("fluid") or {}).get("pd_bbox"),
                                              "text": f"{fluid} {remarks}".strip()}])

    # VR-10 seat configuration / cavity relief (trunnion) -----------------------------------------------------------
    if vtype == "TRUNNION" and not _SEATCFG.search(all_text):
        liquid = re.search(r"LIQUID|MIXED|DENSE|SUPERCRIT", phase.upper()) or (re.search(r"CO2|CARBON DIOXIDE", fluid, re.I)
                                                                              and (_num((pdv.get('design_pressure') or {}).get('pd')) or 0) >= 74)
        why = (f"the fluid phase is {phase}" if re.search(r"LIQUID|MIXED|DENSE|SUPERCRIT", phase.upper()) else
               f"the fluid is CO2 at design pressure {(pdv.get('design_pressure') or {}).get('pd')} barg, above the CO2 critical "
               "pressure (73.8 bar) — dense phase possible")
        add("VR-10", CONFIRM if liquid else NOTE, "Seat configuration / cavity relief not stated", "body_type",
            "State seat design (SPE/DPE) and cavity relief" + (" (liquid / dense phase service)." if liquid else "."),
            "Trunnion ball valve without a stated seat configuration (SPE / DPE, DBB / DIB) or cavity relief."
            + (f" Here {why}: liquid / dense fluid trapped in the closed cavity expands with temperature — with DPE seats a "
               "cavity relief valve is required." if liquid else
               " Vendor to state the seat design and the cavity pressure relief path."),
            "des.seats", [ev("body_type"), ev("fluid_state") or ev("fluid_state.nor")])

    # VR-11 cold insulation → extended stem ---------------------------------------------------------------------
    ins = val("pipe_insulation").upper()
    if re.search(r"COLD|\b5\b", ins) and not re.search(r"extended\s+(?:stem|bonnet)", all_text, re.I):
        add("VR-11", CONFIRM, "Cold-insulated valve without extended stem", "pipe_insulation",
            "Cold insulation: specify extended stem / bonnet.",
            f"Pipe insulation '{val('pipe_insulation')}': specify an extended stem / bonnet and stem vapour barrier so the "
            "actuator stays outside the insulation and free of ice.", "des.insulation", [ev("pipe_insulation")])

    # VR-12 piggable → full bore -------------------------------------------------------------------------------------
    if val("piggable").upper().startswith("Y") and "FULL" not in btype:
        red = bool(re.search(r"REDUC|RED\.?\s*PORT", btype))
        add("VR-12", ACTION if red else CONFIRM, "Piggable line without full bore" if red else "Piggable line — bore not stated", "body_type",
            "Piggable line: " + ("reduced bore not acceptable, use full bore." if red else "state full bore."),
            f"Line is piggable but the valve is '{val('body_type')}'"
            + (" (reduced bore)." if red else " and no full bore is stated (field or the notes it refers to).")
            + " Piggable lines need full, round bore valves.", "des.bore", [ev("piggable"), ev("body_type")])

    # VR-13 valve size vs line size ------------------------------------------------------------------------------------
    ls = _inch(val("line_size_inlet") or val("line_size"))
    if size and ls and abs(size - ls) > 1e-6:
        if size > ls:
            add("VR-13", ACTION, "Valve larger than the line", "body_size",
                f"Valve {val('body_size')} larger than line {val('line_size_inlet')}. Revise.",
                f"Valve size {val('body_size')} is larger than the line size {val('line_size_inlet')}.", "des.bore",
                [ev("body_size"), ev("line_size_inlet")])
        elif "FULL" in btype:
            add("VR-13", CONFIRM, "Full-bore valve smaller than the line", "body_size",
                f"Full-bore valve {val('body_size')} in {val('line_size_inlet')} line. Confirm size.",
                f"Valve {val('body_size')} in a {val('line_size_inlet')} line: reducers are needed and the bore is no longer "
                "line size. Confirm the size (and piggability / pressure drop).", "des.bore", [ev("body_size"), ev("line_size_inlet")])

    # VR-14 erosive service with soft seat -------------------------------------------------------------------------
    if val("erosive").upper().startswith("Y") and soft:
        add("VR-14", CONFIRM, "Soft seat in erosive service", "seat_material",
            f"Erosive service with soft seat {seat}. Consider metal seat.",
            f"Erosive service with soft seat '{seat}': consider a metal-seated, hard-faced ball and seats.", "des.metal_seat",
            [ev("erosive"), ev("seat_material")])

    # VR-15 actuator safety factor -------------------------------------------------------------------------------------
    sf = _num(val("act_safety_factor"))
    if sf and sf < 1.25 and "act_safety_factor" in F:
        add("VR-15", CONFIRM, "Low actuator sizing factor", "act_safety_factor",
            f"Actuator safety factor {sf:g} below 1.25. Confirm.",
            f"Actuator safety factor {sf:g} is below the usual 1.25–1.5 on the maximum valve torque. Confirm with the "
            "actuator specification; the valve MAST must still exceed the actuator output.", "des.actuator", [ev("act_safety_factor")])

    # PC-01 peer check — learned from every datasheet of the project ---------------------------------------------------
    for m in peer_findings(F, val, peers):
        out.append(m)
    return out


# ------------------------------------------------------------------------------------------------ peer learning
_PEER_NOISE = {"AS", "PER", "ACC", "ACCORDANCE", "TO", "IN", "SHALL", "BE"}


def _toks(v: str) -> frozenset:
    return frozenset(t for t in material.tokens(v) if t not in _PEER_NOISE)


def _vkey(v: str) -> str:
    return " ".join(sorted(_toks(v)))


def build_peers(datasheets: list[dict]) -> dict:
    """datasheets: [{id, tag, fields: key -> value(str)}] (latest revision of each tag).  -> {(field, class): Counter, …}
    Groups by piping class: a class fixes the materials, rating and facing, so its datasheets should agree."""
    prof = {"n": len(datasheets), "groups": collections.defaultdict(collections.Counter), "example": {}, "tags": collections.defaultdict(list)}
    for d in datasheets:
        cls = (d["fields"].get("piping_class") or "").strip().upper()
        if not cls or _PLACE.match(cls):
            continue
        for k in PEER_FIELDS:
            v = (d["fields"].get(k) or "").strip()
            if not v or _PLACE.match(v):
                continue
            g = (k, cls)
            vk = _vkey(v)
            prof["groups"][g][vk] += 1
            prof["example"].setdefault((g, vk), v)
            prof["tags"][(g, vk)].append(d.get("tag") or "")
    return prof


def peer_findings(F: dict, val, peers: dict | None) -> list[dict]:
    if not peers:
        return []
    cls = val("piping_class").strip().upper()
    out = []
    for k in PEER_FIELDS:
        v = val(k).strip()
        if not v or _PLACE.match(v) or k not in F:
            continue
        cnt = peers["groups"].get((k, cls))
        if not cnt:
            continue
        mine = _vkey(v)
        others = cnt.copy()
        others[mine] -= 1                                      # leave this datasheet out of its own peers
        n = sum(x for x in others.values() if x > 0)
        if n < PEER_MIN:
            continue
        top, tn = max(((vk, x) for vk, x in others.items() if x > 0), key=lambda t: t[1])
        ex = peers["example"][((k, cls), top)]
        if tn / n < PEER_SHARE or top == mine or material.same(ex, v) or material.equivalent(ex, v) or _toks(ex) <= _toks(v):
            continue                                           # same, or this one only says more ('PEEK with F316L backing')
        f = F[k]
        kb = knowledge.get("peer")
        out.append({"rule": "PC-01", "level": CONFIRM, "severity": SEVERITY[CONFIRM], "title": f"{f.get('display') or k} differs from the other {cls} datasheets",
                    "key": k, "short": f"'{v}' differs from {tn}/{n} {cls} datasheets ('{ex}'). Confirm.",
                    "comment": f"{tn} of {n} other datasheets in piping class {cls} give {f.get('display') or k} as '{ex}'; "
                                         f"this one says '{v}'. Confirm this tag really differs (service, size, vendor) or correct it.",
                    "basis": "Learned from all datasheets of this project (same piping class)", "kb": "peer", "kb_title": kb["title"],
                    "kb_text": kb["text"], "evidence": [{"doc": "Datasheet", "where": f"row {f.get('row')} {f.get('display') or k}",
                                                         "page": f.get("page"), "bbox": f.get("bbox"), "text": v},
                                                        {"doc": "Peers", "where": f"{tn}/{n} in {cls}", "page": None, "bbox": None,
                                                         "text": ", ".join(t for t in peers["tags"][((k, cls), top)][:6])}]})
    return out

