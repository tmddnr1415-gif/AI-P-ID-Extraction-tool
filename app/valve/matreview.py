"""Material review — the comments a materials / valve engineer writes on a ball valve datasheet.

Rule based and traceable.  Every finding says which rule fired, which standard or document clause it rests on,
and which values it used (datasheet row / note, PMS class page, Process Data page).  A rule fires only when the
values it needs are actually written in one of the documents; nothing is assumed (CLAUDE.md §4).

Three levels:
  Action   — a document limit is broken (PMS note, PMS P-T table, B16.34 temperature limit of the body grade):
             the datasheet must change.  → Issue List as 'Material Review' (Major).
  Confirm  — the combination is allowed only under conditions the datasheet does not show (bolting exposure,
             17-4PH heat treatment, seat P-T curve near its limit …): the vendor / engineer must confirm.
             → Issue List as 'Material Review' (Minor).
  Note     — professional remark for the review record, no action by itself (e.g. 316 in sour service is accepted
             by the PMS class within ISO 15156-3 limits).  → Material Review tab and Valve List column only.

General material knowledge (seat polymer service limits, grade families, ISO 15156 restrictions) lives in the tables
below with the clause it comes from.  Project values (P-T, class notes, design temperature) are read from the
documents at run time.
"""
from __future__ import annotations

import re

from app.valve import material, schema

ACTION, CONFIRM, NOTE = "Action", "Confirm", "Note"
SEVERITY = {ACTION: "Major", CONFIRM: "Minor", NOTE: "Info"}

# Typical upper service temperature of seat polymers (°C) — manufacturer data / API 6D & ISO 17292 practice.
# The vendor's seat P-T curve governs; a PMS / project note with its own limit overrides these values.
SEAT_LIMITS = [
    (re.compile(r"\bPEEK\b", re.I), "PEEK", 260),
    (re.compile(r"\bR-?P?TFE\b|REINFORCED\s+PTFE|GLASS\s*FILLED\s*PTFE|CARBON\s*FILLED\s*PTFE", re.I), "Reinforced PTFE (RPTFE/RTFE)", 230),
    (re.compile(r"\bP?TFE\b|\bPTFE\b", re.I), "PTFE (virgin)", 200),
    (re.compile(r"\bNYLON\b|\bPA\s*6\b|\bPA12\b", re.I), "Nylon", 93),
]
_METAL_SEAT = re.compile(r"metal[- ]?seat|\bMS\b|TCC|tungsten|stellite|chrom\w*\s+carbide", re.I)

# Minimum temperature without impact testing for common body grades (ASME B16.34 / B31.3 Table A-1 & Fig. 323.2.2A).
BODY_MIN_T = [(re.compile(r"\bWCB\b|\bWCC\b|\bA105\b|\bA216\b", re.I), "carbon steel A216 WCB / A105", -29)]
_LT_BODY = re.compile(r"\bLC[BC]\b|\bLF[236]\b|\bA352\b|\bA350\b", re.I)
_LT_PIPE = re.compile(r"\bA333\b|\bLTCS\b|\bITCS\b|\bA350\b|\bA352\b|LOW[- ]TEMP", re.I)
_CS = re.compile(r"\bWC[BC]\b|\bA105\b|\bA216\b|\bLC[BC]\b|\bLF\d\b|\bA350\b|\bA352\b|\bCARBON\s+STEEL\b|\bCS\b|\bITCS\b|\bLTCS\b|\bA106\b|\bA333\b|\bA672\b|API\s*5L", re.I)
_SS = re.compile(r"\b31[06]L?\b|\b304L?\b|CF[38]M?\b|\bF31[06]L?\b|\bSS\b|STAINLESS|\bA312\b|\bA358\b", re.I)
_PH174 = re.compile(r"17\s*-?\s*4\s*PH|\bA564\b|TYPE\s*630|\bS17400\b", re.I)
_H1150D = re.compile(r"H\s*1150\s*D|DOUBLE\s+H\s*1150|H1150\s*\+\s*H1150", re.I)
_HF = re.compile(r"/\s*F?HF\b|HARD\s*-?\s*FAC", re.I)
_HF_TYPE = re.compile(r"TCC|tungsten|chrom\w*\s+carbide|CrC|stellite|HVOF|ENP|electroless|nickel\s+plat|Ni-?B|colmonoy|WC-?Co", re.I)
_B8M2 = re.compile(r"B8M\s*(?:CL\.?|CLASS)\s*2", re.I)
_B7 = re.compile(r"\bB7\b(?!M)", re.I)
_B7M = re.compile(r"\b[BL]7M\b", re.I)
_ELASTOMER = re.compile(r"\bFKM\b|VITON|\bHNBR\b|\bNBR\b|\bEPDM\b|\bFFKM\b|O-?RING|ELASTOMER", re.I)
_RGD = re.compile(r"rapid\s+gas\s+decompression|explosive\s+decompression|\bRGD\b|\bAED\b|ISO\s*23936|NORSOK\s*M-?710", re.I)
_CO2 = re.compile(r"\bCO\s*2\b|CARBON\s+DIOXIDE", re.I)
_SOUR = re.compile(r"\bsour\b|\bH2S\b|NACE|MR\s*-?0175|15156", re.I)
_SEAT_NOTE = re.compile(r"(R?-?P?TFE|RTFE|RPTFE|PEEK|NYLON|DEVLON)[^.]*?MAX(?:IMUM)?\.?\s*TEMPERATURE\s*(?:OF\s*)?(-?\d+)\s*°?\s*C", re.I)
_DUAL = re.compile(r"DUAL\s+GRADE", re.I)


# knowledge entry (knowledge.KB) each rule rests on
KB_OF = {"MR-01": "des.soft_seat", "MR-02": "des.soft_seat", "MR-03": "std.b1634", "MR-04": "mat.temp_cs", "MR-05": "des.body",
         "MR-06": "mat.co2", "MR-07": "std.nace", "MR-08": "std.nace", "MR-09": "des.hardfacing", "MR-10": "mat.dual_grade",
         "MR-11": "std.nace", "MR-12": "mat.rgd", "MR-13": "std.fire", "MR-14": "mat.co2", "MR-15": "std.nace"}


def _num(v):
    m = re.search(r"-?\d+(?:\.\d+)?", str(v or ""))
    return float(m.group(0)) if m else None


def _interp(pt, t):
    """Pressure rating at t from the PMS P-T table (linear between the listed points), None outside it."""
    pts = sorted(pt)
    if not pts or t > pts[-1][0]:
        return None
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, p0), (t1, p1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            return p0 + (p1 - p0) * (t - t0) / (t1 - t0) if t1 > t0 else min(p0, p1)
    return None


def review(ds: dict, general_notes: dict | None = None, pms_class: dict | None = None,
           process_rows: list | None = None, pd_row: dict | None = None, requirements: list | None = None) -> list[dict]:
    """ds: datasheet (fields list or key->field dict, notes).  pms_class: the class pms.find_class chose.
    process_rows: process.check rows (Process Data values per item).  pd_row: the tag's raw Process Data row (remarks).
    Returns [{rule, level, severity, title, key, comment, basis, evidence:[{doc, where, page, bbox, text}]}]."""
    F = {f["key"]: f for f in ds["fields"]} if isinstance(ds["fields"], list) else ds["fields"]
    val = lambda k: (schema.effective(F[k]) if k in F else "") or ""       # noqa: E731
    notes = ds.get("notes") or []
    gn = {str(k): v for k, v in (general_notes or {}).items()}
    c = pms_class or {}
    out = []

    def ev_field(k):
        f = F.get(k) or {}
        return {"doc": "Datasheet", "where": f"row {f.get('row')} {f.get('display') or k}" if f.get("row") else (f.get("display") or k),
                "page": f.get("page"), "bbox": f.get("bbox"), "text": val(k)}

    def ev_note(n, gen=False):
        return {"doc": "Datasheet", "where": f"{'Gen Note' if gen else 'Note'} {n}", "page": None, "bbox": None,
                "text": (gn.get(str(n)) if gen else next((x["text"] for x in notes if str(x["no"]) == str(n)), ""))[:220]}

    def ev_pms(where, text, page=None, bbox=None):
        return {"doc": "PMS", "where": f"class {c.get('code')} · {where}", "page": page or c.get("header_page"), "bbox": bbox, "text": text[:220]}

    def add(rule, level, title, key, comment, basis, evidence):
        from app.valve import knowledge
        kb = KB_OF.get(rule, "")
        k = knowledge.get(kb) if kb else {"title": "", "text": ""}
        out.append({"rule": rule, "level": level, "severity": SEVERITY[level], "title": title, "key": key,
                    "comment": comment, "basis": basis, "kb": kb, "kb_title": k["title"], "kb_text": k["text"],
                    "evidence": [e for e in evidence if e]})

    # ---- what the documents say about the service -------------------------------------------------------------
    pdv = {r["key"]: r for r in process_rows or [] if r.get("pd") not in (None, "")}
    dt = _num(pdv["design_temp"]["pd"]) if "design_temp" in pdv and "C" in (pdv["design_temp"].get("pd_unit") or "C").upper() else None
    dp = _num(pdv["design_pressure"]["pd"]) if "design_pressure" in pdv and "bar" in (pdv["design_pressure"].get("pd_unit") or "").lower() \
        and "a" not in (pdv["design_pressure"].get("pd_unit") or "").lower().replace("bar", "") else None
    ev_dt = ({"doc": "Process Data", "where": "Design Temperature", "page": pdv["design_temp"].get("pd_page"),
              "bbox": pdv["design_temp"].get("pd_bbox"), "text": f"{pdv['design_temp']['pd']} {pdv['design_temp'].get('pd_unit') or ''}"}
             if dt is not None else None)
    fluid = (pdv.get("fluid") or {}).get("pd") or val("fluid") or val("fluid.nor")       # not 'service' — that is a line route
    remarks = " ".join(str((pd_row or {}).get("values", {}).get(k, {}).get("v") or "") for k in ("remarks", "notes"))
    notes_text = " ".join(n["text"] for n in notes)
    gen_text = " ".join(str(t) for t in gn.values())
    nace_req = bool(c.get("nace")) or val("nace").upper().startswith("Y") or val("sour_service").upper().startswith("Y") \
        or bool(re.search(r"\bsour\b", remarks, re.I))
    co2 = bool(_CO2.search(fluid) or _CO2.search(val("service")))
    body, ball, stem, seat = val("body_material"), val("ball_material"), val("stem_material"), val("seat_material")
    seat_txt = seat + " " + " ".join(n["text"] for n in notes if re.search(r"seat\s*material", n["text"], re.I))

    # MR-01 / MR-02  seat polymer vs design temperature --------------------------------------------------------
    kind = next(((name, lim) for pat, name, lim in SEAT_LIMITS if pat.search(seat_txt)), None) if seat.strip() else None
    if kind and not _METAL_SEAT.search(seat_txt):
        name, lim = kind
        doc_lim = None
        for no, t in (c.get("class_notes") or {}).items():
            m = _SEAT_NOTE.search(t)
            if m and next((n for p, n, _ in SEAT_LIMITS if p.search(m.group(1))), None) == name:
                doc_lim = (float(m.group(2)), no, t)
        if dt is not None and doc_lim and dt > doc_lim[0]:
            add("MR-01", ACTION, "Seat material above PMS temperature limit", "seat_material",
                f"Seat '{seat}' ({name}) is limited to {doc_lim[0]:g} °C by PMS class {c.get('code')} note {doc_lim[1]}, "
                f"but the Process Data design temperature is {dt:g} °C. Change the seat to a material rated for "
                f"{dt:g} °C (e.g. PEEK up to ~260 °C, or metal seat) or confirm the design temperature.",
                f"PMS {c.get('code')} General Class Note {doc_lim[1]}", [ev_field("seat_material"), ev_dt, ev_pms(f"note {doc_lim[1]}", doc_lim[2])])
        elif dt is not None and dt > lim:
            add("MR-02", ACTION, "Seat material above its service temperature", "seat_material",
                f"Seat '{seat}' ({name}) has a typical maximum service temperature of about {lim} °C; the Process Data design "
                f"temperature is {dt:g} °C. Select a seat material rated for the design temperature (PEEK / metal seat) "
                f"or obtain the vendor's seat P-T curve proving {dt:g} °C at the design pressure.",
                "Seat polymer service limit (vendor seat P-T curve governs); datasheet note: non-metallic parts suitable for design condition",
                [ev_field("seat_material"), ev_dt])
        elif dt is not None and dt >= lim - 30:
            add("MR-02", CONFIRM, "Seat close to its temperature limit", "seat_material",
                f"Design temperature {dt:g} °C is within 30 °C of the typical {name} seat limit (~{lim} °C"
                + (f"; PMS note {doc_lim[1]}: {doc_lim[0]:g} °C" if doc_lim else "") + "). Soft seats lose pressure rating with "
                "temperature: the vendor shall submit the seat P-T curve covering the design temperature and the "
                "maximum shut-off differential pressure.",
                "Seat P-T rating (ASME B16.34 covers the shell only; seat rating is the manufacturer's)", [ev_field("seat_material"), ev_dt])

    # MR-03  pressure / temperature inside the PMS class P-T table -----------------------------------------------
    pt = c.get("pt") or []
    if dt is not None and len(pt) >= 3:
        tmax = max(t for t, _ in pt)
        if dt > tmax:
            add("MR-03", ACTION, "Design temperature outside PMS class range", "piping_class",
                f"Process Data design temperature {dt:g} °C exceeds the highest temperature of PMS class {c.get('code')} "
                f"P-T table ({tmax:g} °C, {c.get('pt_basis') or 'ASME B16.5'}). The piping class / valve rating does not cover the service.",
                f"PMS {c.get('code')} Temperature / Pressure Limits", [ev_dt, ev_pms("P-T limits", f"max {tmax:g} °C")])
        elif dp is not None:
            pr = _interp(pt, dt)
            if pr is not None and dp > pr * 1.0001:
                add("MR-03", ACTION, "Design pressure above PMS class rating", "rating",
                    f"At the design temperature {dt:g} °C the PMS class {c.get('code')} allows {pr:.1f} barg "
                    f"({c.get('pt_basis') or 'ASME B16.5'}), but the Process Data design pressure is {dp:g} barg. One of the two "
                    "documents is wrong: confirm the design pressure or move the line to a higher-rated class.",
                    f"PMS {c.get('code')} Temperature / Pressure Limits",
                    [ev_dt, {"doc": "Process Data", "where": "Design Pressure", "page": pdv["design_pressure"].get("pd_page"),
                             "bbox": pdv["design_pressure"].get("pd_bbox"), "text": f"{dp:g} barg"}, ev_pms("P-T limits", str(pt))])

    # MR-04  low temperature body / line ---------------------------------------------------------------------------
    lt_line = _LT_PIPE.search(val("pipe_material")) or "LOW TEMP" in (c.get("material") or "").upper()
    for pat, name, tmin in BODY_MIN_T:
        if pat.search(body) and not _LT_BODY.search(body) and lt_line:
            add("MR-04", ACTION, "Carbon steel body in a low-temperature line", "body_material",
                f"Body '{body}' ({name}) is usable without impact testing only down to {tmin} °C, but the line is low-temperature "
                f"carbon steel ({val('pipe_material') or c.get('material')}). Use an impact-tested low-temperature grade "
                "(A352 LCC/LCB or A350 LF2/LF6) matching the line.",
                "ASME B16.34 / B31.3 Table A-1 minimum temperature & 323.2 impact test", [ev_field("body_material"), ev_field("pipe_material")])

    # MR-05  body vs connected pipe material family -----------------------------------------------------------------
    pipe = val("pipe_material")
    if body and pipe and not re.search(r"note", body + pipe, re.I):
        b_ss, b_cs, p_ss, p_cs = bool(_SS.search(body)) and not _CS.search(body), bool(_CS.search(body)), \
            bool(_SS.search(pipe)) and not _CS.search(pipe), bool(_CS.search(pipe))
        if (b_ss and p_cs) or (b_cs and p_ss):
            add("MR-05", CONFIRM, "Body and pipe are different material families", "body_material",
                f"Body '{body}' and line pipe '{pipe}' are different families (stainless / carbon steel). Confirm the "
                "dissimilar-metal joint (welding procedure / transition pup piece, galvanic insulation if required) and "
                "that the body material follows the piping class.",
                "PMS class material / ASME B31.3 dissimilar welds", [ev_field("body_material"), ev_field("pipe_material")])

    # MR-06  carbon steel in CO2 (carbonic acid corrosion) ----------------------------------------------------------
    if co2 and _CS.search(body) and not _SS.search(body):
        ca = c.get("ca") or val("corrosion_req")
        ca_v = _num(ca)
        lvl = CONFIRM if not ca_v else NOTE
        add("MR-06", lvl, "Carbon steel body in CO2 service", "body_material",
            f"Carbon steel body '{body}' in CO2 service: free water forms carbonic acid and corrodes carbon steel quickly. "
            + (f"Corrosion allowance is {ca}" if ca else "No corrosion allowance is stated")
            + " — confirm the CO2 is dehydrated (no free water at any operating case, including start-up / depressurisation) "
              "or upgrade to stainless steel.",
            "CO2 corrosion of carbon steel (NORSOK M-001 / DNV-RP-F104 dense-phase CO2 practice)",
            [ev_field("body_material"), ev_field("corrosion_req") if "corrosion_req" in F else None,
             ev_pms("Corrosion Allowance", str(c.get("ca"))) if c.get("ca") else None])

    # MR-07  sour service — austenitic 316 (ISO 15156-3 A.2) ---------------------------------------------------------
    if nace_req:
        parts = [(k, val(k)) for k in ("body_material", "ball_material", "stem_material") if re.search(r"31[06]|CF[38]M", val(k))]
        if parts:
            hot = dt is not None and dt > 60
            add("MR-07", NOTE, "316/316L in sour service", parts[0][0],
                "316/316L (" + ", ".join(k.split("_")[0] for k, _ in parts) + ") is acceptable for NACE MR0175 / ISO 15156 service "
                "in the solution-annealed condition, ≤ 22 HRC, without cold work, within the environmental limits of "
                "ISO 15156-3 Table A.2 (temperature, H2S partial pressure, chloride, no elemental sulphur)."
                + (f" The design temperature is {dt:g} °C (above 60 °C): the materials selection report shall confirm the "
                   "H2S partial pressure / chloride content are inside the table." if hot else "")
                + (f" PMS class {c.get('code')} lists this service and requires NACE ({c.get('nace')})." if c.get("nace") else ""),
                "NACE MR0175 / ISO 15156-3 Table A.2", [ev_field(parts[0][0]), ev_dt if hot else None])

    # MR-15  carbon / low-alloy steel body in sour service (ISO 15156-2) ---------------------------------------------
    if nace_req and _CS.search(body) and not _SS.search(body):
        add("MR-15", NOTE, "Carbon steel body in sour service", "body_material",
            f"Body '{body}' (carbon / low-temperature carbon steel) in NACE service: acceptable per ISO 15156-2 A.2.1 when "
            "hardness is ≤ 22 HRC (parent metal) and ≤ 250 HV10 on welds / repair welds (PWHT where required), and the "
            "material certificate states NACE MR0175 / ISO 15156 compliance. Bolting and trim follow their own rules.",
            "NACE MR0175 / ISO 15156-2 A.2.1", [ev_field("body_material")])

    # MR-08  17-4PH stem in sour service -------------------------------------------------------------------------------
    stem_txt = stem + " " + val("act_stem_material")
    if _PH174.search(stem_txt):
        ok = _H1150D.search(stem_txt + " " + notes_text)
        add("MR-08", NOTE if ok or not nace_req else CONFIRM, "17-4PH (A564 Type 630) stem", "stem_material",
            "Stem in 17-4PH (UNS S17400, A564 Type 630). "
            + ("For NACE service ISO 15156-3 accepts it only in the double-aged H1150D condition, max 33 HRC, and within the "
               "table's environmental limits (H2S partial pressure / pH). " if nace_req else "")
            + ("H1150D is stated." if ok else "The datasheet does not state the heat treatment — require 'H1150D, ≤ 33 HRC' "
                                               "on the datasheet and the material certificate."),
            "NACE MR0175 / ISO 15156-3 Annex A (precipitation-hardened martensitic SS, UNS S17400) — check the project edition; "
            "the 2020 edition also limits sustained stress to 50 % SMYS for some conditions", [ev_field("stem_material")])

    # MR-09  hard-facing type not stated -------------------------------------------------------------------------------
    hf = [k for k in ("ball_material", "stem_material") if _HF.search(val(k))]
    if hf and not _HF_TYPE.search(" ".join(val(k) for k in hf) + " " + notes_text):
        add("MR-09", NOTE, "Hard-facing type not stated", hf[0],
            f"'{val(hf[0])}': hard-facing (HF) is required but its type and thickness are not stated. Vendor to state the "
            "overlay (e.g. tungsten carbide HVOF, chromium carbide, Stellite, ENP) and its qualification"
            + ("; for NACE service the overlay / coating shall meet ISO 15156-3 (ENP is not a sour-service barrier)." if nace_req else "."),
            "API 6D / ISO 14313 · ISO 15156-3 (overlays)", [ev_field(hf[0])])

    # MR-10  PMS dual-grade 316/316L certification ------------------------------------------------------------------
    dual = next(((no, t) for no, t in (c.get("class_notes") or {}).items() if _DUAL.search(t)), None)
    if dual:
        for k in ("body_material", "ball_material", "stem_material"):
            v = val(k).upper()
            if re.search(r"316L|CF3M", v) and not re.search(r"316(?!L)|CF8M", v):
                add("MR-10", CONFIRM, "316L only — PMS requires dual-grade 316/316L", k,
                    f"{F[k].get('display') or k} '{val(k)}' states 316L only. PMS class {c.get('code')} note {dual[0]} requires "
                    "all 316/316L to be dual-grade certified (316L chemistry with 316 strength). State 'dual certified "
                    "316/316L' or confirm the 316L allowable stress is used for the pressure design.",
                    f"PMS {c.get('code')} General Class Note {dual[0]}", [ev_field(k), ev_pms(f"note {dual[0]}", dual[1])])

    # MR-11  bolting in sour service ------------------------------------------------------------------------------------
    bolt_notes = [n for n in notes if re.search(r"stud|bolt", n["text"], re.I)]
    for n in bolt_notes:
        t = n["text"]
        if nace_req and _B8M2.search(t):
            spec = bool(_SOUR.search(t))                    # the bolting spec itself is written 'NACE MR0175' → spec author's choice
            add("MR-11", NOTE if spec else CONFIRM, "B8M Class 2 bolting with NACE", "bolting_gasket",
                f"Note {n['no']}: A193 B8M Class 2 is strain-hardened (up to ~35 HRC). ISO 15156 accepts it only for bolting "
                "that is NOT exposed to the sour environment (uninsulated, atmospheric flange bolting). If the joint is "
                "insulated, buried, inside an enclosure or the bolts are wetted, use B8M Class 1 or B7M / L7M (≤ 22 HRC)."
                + (" The note lists it with NACE MR0175, so it is taken as non-exposed flange bolting — keep the joints "
                   "uninsulated." if spec else ""),
                "NACE MR0175 / ISO 15156-2 §A.2.2.4 (exposed vs non-exposed bolting)", [ev_note(n["no"])])
        elif nace_req and _B7.search(t) and not _B7M.search(t):
            add("MR-11", CONFIRM, "B7 bolting with NACE", "bolting_gasket",
                f"Note {n['no']}: A193 B7 / A194 2H (up to ~35 HRC) is acceptable only as non-exposed bolting. For exposed "
                "bolting in sour service use B7M / 2HM (≤ 22 HRC) or L7M.",
                "NACE MR0175 / ISO 15156-2 §A.2.2.4", [ev_note(n["no"])])
        elif _B7M.search(t):
            add("MR-11", NOTE, "Sour-service bolting", "bolting_gasket",
                f"Note {n['no']}: B7M / L7M bolting (≤ 22 HRC) — suitable for exposed bolting in sour service.",
                "NACE MR0175 / ISO 15156-2 §A.2.2.4", [ev_note(n["no"])])
        break                                               # one bolting note per datasheet

    # MR-12  elastomers / soft seals in CO2 (rapid gas decompression) ----------------------------------------------
    if co2:
        rgd_no = next((no for no, t in gn.items() if _RGD.search(t)), None)
        seals = " ".join(val(k) for k in ("seal_material", "packing_material", "gasket_material"))
        if _ELASTOMER.search(seals + " " + notes_text) or rgd_no:
            add("MR-12", NOTE if not _ELASTOMER.search(seals) else CONFIRM, "Seals in CO2 — rapid gas decompression", "seal_material",
                "CO2 dissolves in elastomers and swells PTFE; on depressurisation it causes blistering (RGD/AED). O-rings and "
                "elastomer seals (trunnion / stem / body joints, often not on the datasheet) shall be RGD-qualified to "
                "ISO 23936-2 / NORSOK M-710 for CO2 with H2S impurities; vendor to state each seal material."
                + (f" Required by Gen Note {rgd_no}." if rgd_no else ""),
                "ISO 23936-2 / NORSOK M-710" + (f" · Gen Note {rgd_no}" if rgd_no else ""),
                [ev_field("seal_material") if "seal_material" in F else None, ev_note(rgd_no, True) if rgd_no else None])

    # MR-13  fire-safe soft-seated valve --------------------------------------------------------------------------------
    fs = val("fire_safe").upper()
    if kind and (fs.startswith(("Y", "REQ")) or "607" in fs or "6FA" in fs):
        add("MR-13", NOTE, "Fire-safe soft-seated valve", "fire_safe",
            f"Soft seat ({kind[0]}) with fire-safe requirement: the polymer burns away in a fire, so tightness relies on a "
            "secondary metal-to-metal seat and graphite stem / body seals. Vendor shall submit the API 607 / ISO 10497 "
            "fire-test certificate of the same design, size range and pressure class.",
            "API 607 / ISO 10497 qualification range", [ev_field("fire_safe")])

    # MR-14  service not listed in the PMS class -------------------------------------------------------------------
    sv = c.get("services") or []
    if sv and fluid and fluid.strip():
        f_up = re.sub(r"[^A-Z0-9 ]", " ", fluid.upper())
        words = {w for w in f_up.split() if len(w) > 2} | {f_up.replace(" ", "")}     # 'REFRIGER ANT' = a wrapped word
        alias = {"CO2": "CARBON DIOXIDE", "H2S": "HYDROGEN SULPHIDE", "N2": "NITROGEN", "RELIEF": "VENT", "RELF": "VENT",
                 "FLARE": "VENT", "REFRIGERANT": "PROPANE"}
        listed = " ".join(s.upper() for s in sv)
        hit = any(alias.get(w, w) in listed for w in words) or (co2 and "CARBON DIOXIDE" in listed)
        if not hit:
            add("MR-14", CONFIRM, "Service fluid not listed in PMS class", "piping_class",
                f"Process fluid '{fluid}' is not in the service list of PMS class {c.get('code')} ({', '.join(sv)}). "
                "Confirm the class is the right one for this fluid (materials selection report).",
                f"PMS {c.get('code')} Service list", [{"doc": "Process Data", "where": "Service Fluid", "page": (pdv.get('fluid') or {}).get('pd_page'),
                                                       "bbox": (pdv.get('fluid') or {}).get('pd_bbox'), "text": fluid}, ev_pms("Service", ", ".join(sv))])
    return out


def summary(items: list[dict]) -> str:
    """'[Action] MR-01 Seat material above PMS temperature limit · [Confirm] MR-11 …' for the Valve List column."""
    order = {ACTION: 0, CONFIRM: 1, NOTE: 2}
    return " · ".join(f"[{i['level']}] {i['title']}" for i in sorted(items, key=lambda i: order[i["level"]]))
