"""Ball valve engineering knowledge — what a ball valve engineer knows before reading a datasheet.

One entry per topic: what it is, what to check on a datasheet, and the standard / clause it comes from.  The review
rules (matreview.py · expert.py) cite these entries by id, the tool shows them next to each finding (Expert tab ·
Knowledge view), and docs/valve/BALL_VALVE_KNOWLEDGE.md is generated from here (`python3 -m app.valve.knowledge`).

Scope: general, public engineering knowledge (standards' titles, scope and well-known requirements).  Where sources
disagree or a value is "typical practice", the entry says so — the project specification always governs.
Nothing here is a project value: project values (P-T, class notes, design conditions) are read from the documents.
"""
from __future__ import annotations

KB: dict[str, dict] = {
    # ---------------------------------------------------------------- standards
    "std.api6d": {
        "title": "API 6D / ISO 14313 — pipeline & process ball valves",
        "text": "Covers design, manufacture, testing and documentation of pipeline valves (ball, gate, plug, check). Key ball-valve "
                "items: trunnion or floating design by manufacturer, anti-static device, blow-out-proof stem, DBB / DIB seat "
                "functions, cavity relief, face-to-face per API 6D tables, hydrostatic shell & seat tests, supplementary "
                "tests in annexes (gas seat test, fire type-test reference, etc.).",
        "check": "Face-to-face reference, seat configuration (SPE/DPE), cavity relief, anti-static, blow-out-proof stem, test scope.",
        "ref": "API Spec 6D (25th ed.) / ISO 14313",
    },
    "std.iso17292": {
        "title": "ISO 17292 — metal ball valves for petroleum, petrochemical and allied industries",
        "text": "Floating and trunnion ball valves DN 8–DN 600 (NPS ¼–24), Class 150–2500, flanged / butt-weld / threaded / "
                "socket-weld ends. Requires anti-static and blow-out-proof stem; shell to ASME B16.34.",
        "check": "Size / class within scope, end connection, anti-static, blow-out-proof stem.",
        "ref": "ISO 17292",
    },
    "std.b1634": {
        "title": "ASME B16.34 — valves, flanged, threaded and welding end",
        "text": "Pressure-temperature ratings of the valve SHELL by material group (Standard / Special class), minimum wall "
                "thickness, material groups, shell test. Seats and seals are NOT rated by B16.34 — their limits come from "
                "the manufacturer's seat P-T curve.",
        "check": "Body material group and rating cover the design pressure at design temperature; seat rating separately.",
        "ref": "ASME B16.34",
    },
    "std.b165": {
        "title": "ASME B16.5 / B16.47 — flanges",
        "text": "B16.5 covers NPS ½–24; above NPS 24 flanges are B16.47 Series A (MSS SP-44) or Series B (API 605). Facing: "
                "RF (Class 150–2500), RTJ normally for Class 900 and above or where the piping class asks for it; RTJ "
                "face-to-face is longer than RF for the same valve.",
        "check": "Flange standard matches the size; facing (RF / RTJ) matches the piping class facing.",
        "ref": "ASME B16.5 · ASME B16.47 · ASME B16.10",
    },
    "std.b1610": {
        "title": "ASME B16.10 / API 6D — face-to-face and end-to-end",
        "text": "Face-to-face of flanged ball valves: ASME B16.10 tables (short / long pattern) or API 6D tables; RTJ and "
                "butt-weld lengths differ from RF. The datasheet should name the table so the piping layout fits.",
        "check": "Face-to-face reference stated and consistent with the end type.",
        "ref": "ASME B16.10 · API 6D",
    },
    "std.leak": {
        "title": "Seat leakage — API 598 / ISO 5208 / API 6D",
        "text": "ISO 5208 Rate A = no visually detectable leakage (soft-seated valves). Rate B and lower allow small leakage "
                "and are typical for metal-seated valves. API 598 allows zero leakage for soft-seated ball valves. "
                "'Tight Shut-Off' on a datasheet is normally read as Rate A.",
        "check": "Leakage class consistent with seat type and with the tightness requirement.",
        "ref": "API 598 · ISO 5208 · API 6D",
    },
    "std.fire": {
        "title": "Fire type-test — API 607 / API 6FA / ISO 10497",
        "text": "Type test of quarter-turn soft-seated valves (API 607 / ISO 10497) or API 6FA. Qualifies a design by size and "
                "pressure-class range; the certificate must cover the supplied size / class / materials. Usually required "
                "for hydrocarbon, flammable or toxic service.",
        "check": "Fire-safe requirement stated for flammable / toxic service; certificate qualification range.",
        "ref": "API 607 · API 6FA · ISO 10497",
    },
    "std.fe": {
        "title": "Fugitive emission — ISO 15848-1 / -2",
        "text": "ISO 15848-1 type test: tightness Class A / B / C (A tightest, helium, bellows-level), endurance classes "
                "(mechanical cycles CO1… / CC1…), temperature classes. ISO 15848-2 = production test. Projects often ask "
                "Class A or B type-tested packing for toxic / CO2 service.",
        "check": "Required class stated, type-test certificate covering size / class / stem seal design.",
        "ref": "ISO 15848-1 · ISO 15848-2",
    },
    "std.nace": {
        "title": "Sour service — NACE MR0175 / ISO 15156",
        "text": "Part 2: carbon & low-alloy steels (≤ 22 HRC, welds ≤ 250 HV10, HIC for plate). Part 3: corrosion-resistant "
                "alloys with environmental limits (temperature, H2S partial pressure, chloride, pH, elemental sulphur). "
                "Austenitic 316/316L: solution-annealed, ≤ 22 HRC, no cold work; the commonly quoted limit is 60 °C at "
                "pH2S ≤ 100 kPa (any chloride) — check the edition the project uses. 17-4PH (UNS S17400): double-aged "
                "H1150D, ≤ 33 HRC, with environmental limits; the 2020 edition further limits sustained stress to 50 % SMYS "
                "for some conditions. Bolting: exposed bolting must meet the limits (B7M / L7M / 2HM ≤ 22 HRC); "
                "non-exposed bolting may be standard B7 / B8M CL.2.",
        "check": "Every wetted metal (body, ball, stem, seat ring, springs, exposed bolting) within ISO 15156 limits.",
        "ref": "NACE MR0175 / ISO 15156-1/-2/-3",
    },
    "std.pressure_test": {
        "title": "Pressure testing — API 6D / API 598 / ISO 5208",
        "text": "Shell test at 1.5 × rated pressure at 38 °C; seat tests (hydro at 1.1 ×, low-pressure gas where specified). "
                "DIB / DBB functions are proven by the seat tests of each seat separately and of the cavity.",
        "check": "Test scope and gas test requirement for gas / CO2 service.",
        "ref": "API 6D · API 598 · ISO 5208",
    },
    "std.sil": {
        "title": "Safety valves — IEC 61508 / 61511, partial stroke",
        "text": "An ESD / SDV valve in a SIL loop needs reliability data (SIL capability / FMEDA certificate of the valve + "
                "actuator assembly), a fail-safe position (spring return) and often a partial stroke test to reach the "
                "required proof-test coverage.",
        "check": "SIL level, fail-safe action, PST, certificate of the assembly.",
        "ref": "IEC 61508 · IEC 61511",
    },
    # ---------------------------------------------------------------- design
    "des.floating_trunnion": {
        "title": "Floating vs trunnion-mounted ball",
        "text": "Floating ball: the line pressure pushes the ball onto the downstream seat; seat load and torque grow with "
                "size × pressure, so floating designs are used for small bores and lower classes. Trunnion: ball held by "
                "trunnions, spring-loaded seats move onto the ball; lower torque, DBB/DIB possible, standard for large / "
                "high-pressure valves. API 6D does not fix the limit. Typical practice (sources differ — the company spec "
                "governs): floating up to about NPS 6–8 in Class 150, NPS 4–6 in Class 300, NPS 2–4 in Class 600, NPS 1½–2 "
                "in Class 900 and above.",
        "check": "Type matches size × class and the PMS item; actuated large valves normally trunnion.",
        "ref": "API 6D · ISO 17292 · manufacturer catalogues",
    },
    "des.seats": {
        "title": "Seat configuration — SPE / DPE, DBB / DIB, cavity relief",
        "text": "SPE (self-relieving, single piston effect): cavity over-pressure vents past the seat. DPE (double piston "
                "effect): both seats seal from the cavity side too, giving DIB-1 — then a cavity relief valve is needed "
                "(thermal expansion of trapped liquid). DBB = two seats closed and the cavity can be bled. Liquid / "
                "dense-phase CO2 service traps fluid in the cavity: the relief path must be defined.",
        "check": "Seat configuration stated; DPE → cavity relief; bi-directional sealing for bi-directional service.",
        "ref": "API 6D (DBB / DIB definitions, cavity relief)",
    },
    "des.soft_seat": {
        "title": "Seat materials and temperature",
        "text": "PTFE ~200 °C, reinforced PTFE (RPTFE/RTFE, glass/carbon filled) ~200–230 °C, Devlon/nylon low temperature "
                "only (nylon ~90 °C), PEEK ~260 °C, metal seats (TCC / CrC / Stellite overlay) above that or for erosive / "
                "solids service. Soft seats lose pressure rating with temperature: the seat P-T curve governs, not the "
                "body rating. Dense CO2 swells and permeates polymers.",
        "check": "Seat material vs design temperature and shut-off ΔP; PMS seat notes.",
        "ref": "Manufacturer seat P-T data · ISO 17292 · API 6D",
    },
    "des.metal_seat": {
        "title": "Metal-seated ball valves",
        "text": "Used for high temperature, erosive / abrasive service, frequent cycling at high ΔP or where fire / soft-seat "
                "extrusion is a concern. Ball and seat hard-faced (tungsten carbide HVOF, chromium carbide, Stellite). "
                "Leakage normally Rate B or as agreed; torque higher.",
        "check": "Erosive / solids service → metal seat; leakage class to match.",
        "ref": "API 6D · ISO 5208",
    },
    "des.hardfacing": {
        "title": "Hard-facing (HF) of ball and seats",
        "text": "'316 SS / HF' means a 316 base with a hard overlay or coating on the sealing surfaces. The datasheet / vendor "
                "must state type (TCC HVOF, CrC, Stellite 6, ENP), thickness and hardness. ENP is a coating, not a sour "
                "barrier; overlays in sour service must follow ISO 15156-3.",
        "check": "HF type and thickness stated.",
        "ref": "API 6D · ISO 15156-3",
    },
    "des.stem": {
        "title": "Stem — blow-out proof, anti-static, sealing",
        "text": "Stem must be blow-out proof (inserted from inside or shoulder retained) and the valve anti-static (electrical "
                "continuity ball-stem-body, required by API 6D and ISO 17292). Stem seals: graphite packing / lip seals / "
                "O-rings; low-emission packing to ISO 15848.",
        "check": "Anti-static and blow-out-proof stem stated or covered by a general note.",
        "ref": "API 6D · ISO 17292",
    },
    "des.body": {
        "title": "Body construction",
        "text": "Side-entry split body (2- or 3-piece, bolted) or top-entry (in-line maintenance) or fully welded (buried / "
                "pipeline). Body-joint bolting and gaskets are a leakage path — include them in fugitive-emission and "
                "fire requirements.",
        "check": "Construction consistent with maintenance philosophy; body joint seals.",
        "ref": "API 6D",
    },
    "des.fittings": {
        "title": "Drain, vent and sealant injection",
        "text": "Larger trunnion valves usually have drain / vent connections on the body and emergency sealant injection "
                "fittings on the seats; whether they are wanted (and their plugs / valves) is a project decision.",
        "check": "State whether drain / vent / sealant injection are required.",
        "ref": "API 6D (optional features)",
    },
    "des.bore": {
        "title": "Full bore vs reduced bore, piggability",
        "text": "Full bore = ball bore equals the pipe ID class (API 6D minimum bore tables); reduced bore one size smaller. "
                "Piggable lines need full, round bore valves without cavities that trap the pig.",
        "check": "Piggable line → full bore; bore matches the PMS item.",
        "ref": "API 6D minimum bore tables",
    },
    "des.insulation": {
        "title": "Insulated / cold / heat-traced lines",
        "text": "Cold-insulated valves need an extended stem / bonnet (condensation and icing kept out of the operator), "
                "a vapour barrier at the stem; heat-traced valves need room for tracing around the body and actuator "
                "mounting clear of the insulation.",
        "check": "Cold insulation → extended stem; insulation thickness known to the vendor.",
        "ref": "Project insulation specification · BS 6364 (cryogenic) for very low temperatures",
    },
    "des.actuator": {
        "title": "Actuator, fail-safe action, sizing",
        "text": "Fail-close / fail-open needs a spring-return actuator (or accumulator); fail-last (stay-put) is double-acting "
                "or electric. Actuator torque ≥ maximum valve torque (break-to-open at full ΔP) × safety factor (typically "
                "1.25–1.5, project spec); the valve's MAST (maximum allowable stem torque) must exceed the actuator output.",
        "check": "Fail action vs spring; sizing factor; MAST check by vendor.",
        "ref": "Project actuator specification · API 6D (MAST)",
    },
    # ---------------------------------------------------------------- material
    "mat.temp_cs": {
        "title": "Carbon steel minimum temperature",
        "text": "A216 WCB / A105 are listed down to −29 °C without impact testing (ASME B31.3 / B16.34). Below that, or in "
                "low-temperature piping classes, use impact-tested A352 LCB/LCC or A350 LF2 / LF6, or stainless steel.",
        "check": "Body grade vs minimum design temperature and piping class.",
        "ref": "ASME B31.3 Table A-1 · 323.2 · ASME B16.34",
    },
    "mat.co2": {
        "title": "CO2 service",
        "text": "Dry CO2 is not corrosive to carbon steel; with free water it forms carbonic acid and corrodes rapidly. Dense / "
                "supercritical CO2 is an excellent solvent: it swells and permeates polymers and elastomers and causes "
                "rapid gas decompression (RGD) damage on depressurisation; Joule-Thomson cooling during blowdown can drive "
                "metal temperatures very low. Impurities (H2S, H2O, O2, SOx/NOx) change the material choice.",
        "check": "Water content / dehydration, corrosion allowance, RGD-qualified seals, minimum temperature on depressurisation.",
        "ref": "DNV-RP-F104 · ISO 27913 · NORSOK M-001",
    },
    "mat.rgd": {
        "title": "Elastomers — rapid gas decompression",
        "text": "O-rings and elastomeric seals in high-pressure gas / CO2 service must be qualified for RGD (ISO 23936-2, "
                "NORSOK M-710) in the actual fluid and temperature; FKM, HNBR and FFKM grades exist with RGD ratings.",
        "check": "Seal materials named and RGD-qualified.",
        "ref": "ISO 23936-2 · NORSOK M-710",
    },
    "mat.dual_grade": {
        "title": "Dual-grade 316/316L",
        "text": "Material certified to both 316 (strength) and 316L (≤ 0.030 % C, weldability / IGC resistance). 316L alone "
                "has lower allowable stress.",
        "check": "Dual certification stated when the PMS asks.",
        "ref": "ASTM A182 / A351 · project PMS",
    },
    "mat.certs": {
        "title": "Material certificates and PMI",
        "text": "EN 10204 3.1 = manufacturer's inspection certificate; 3.2 = also verified by an independent inspector. "
                "PMI confirms alloy of pressure parts. Projects usually ask 3.1 or 3.2 for pressure-retaining parts.",
        "check": "Certificate type per part, PMI scope.",
        "ref": "EN 10204 · API RP 578",
    },
    # ---------------------------------------------------------------- learned from the project
    "peer": {
        "title": "Consistency across the project's datasheets",
        "text": "Datasheets of the same piping class share materials, rating and facing because the class fixes them. When most "
                "datasheets of a class agree and one differs, it is either a deliberate exception (service, size, vendor) or a "
                "copy error. The tool learns the majority from every uploaded datasheet (latest revision of each tag).",
        "check": "A value that differs from ≥ 80 % of at least 5 datasheets in the same class.",
        "ref": "Project datasheets (learned)"},
}


def get(key: str) -> dict:
    return KB.get(key) or {"title": key, "text": "", "check": "", "ref": ""}


def markdown() -> str:
    lines = ["# Ball Valve 엔지니어링 지식 (도구가 쓰는 기준)", "",
             "> `app/valve/knowledge.py` 에서 만든 문서입니다 (`python3 -m app.valve.knowledge > docs/valve/BALL_VALVE_KNOWLEDGE.md`).",
             "> 일반 공개 지식입니다. 출처끼리 다르거나 '통상 관행' 인 값은 그렇게 적었고, 프로젝트 사양이 언제나 우선합니다.", ""]
    groups = [("std.", "표준"), ("des.", "설계"), ("mat.", "재질"), ("peer", "프로젝트에서 배우는 것")]
    for pre, name in groups:
        lines += [f"## {name}", ""]
        for k, e in KB.items():
            if k.startswith(pre):
                lines += [f"### {e['title']}  `{k}`", "", e["text"], "", f"- 데이터시트에서 볼 것: {e['check']}", f"- 근거: {e['ref']}", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    print(markdown())
