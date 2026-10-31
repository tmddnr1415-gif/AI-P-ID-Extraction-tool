# Ball Valve 엔지니어링 지식 (도구가 쓰는 기준)

> `app/valve/knowledge.py` 에서 만든 문서입니다 (`python3 -m app.valve.knowledge > docs/valve/BALL_VALVE_KNOWLEDGE.md`).
> 일반 공개 지식입니다. 출처끼리 다르거나 '통상 관행' 인 값은 그렇게 적었고, 프로젝트 사양이 언제나 우선합니다.

## 표준

### API 6D / ISO 14313 — pipeline & process ball valves  `std.api6d`

Covers design, manufacture, testing and documentation of pipeline valves (ball, gate, plug, check). Key ball-valve items: trunnion or floating design by manufacturer, anti-static device, blow-out-proof stem, DBB / DIB seat functions, cavity relief, face-to-face per API 6D tables, hydrostatic shell & seat tests, supplementary tests in annexes (gas seat test, fire type-test reference, etc.).

- 데이터시트에서 볼 것: Face-to-face reference, seat configuration (SPE/DPE), cavity relief, anti-static, blow-out-proof stem, test scope.
- 근거: API Spec 6D (25th ed.) / ISO 14313

### ISO 17292 — metal ball valves for petroleum, petrochemical and allied industries  `std.iso17292`

Floating and trunnion ball valves DN 8–DN 600 (NPS ¼–24), Class 150–2500, flanged / butt-weld / threaded / socket-weld ends. Requires anti-static and blow-out-proof stem; shell to ASME B16.34.

- 데이터시트에서 볼 것: Size / class within scope, end connection, anti-static, blow-out-proof stem.
- 근거: ISO 17292

### ASME B16.34 — valves, flanged, threaded and welding end  `std.b1634`

Pressure-temperature ratings of the valve SHELL by material group (Standard / Special class), minimum wall thickness, material groups, shell test. Seats and seals are NOT rated by B16.34 — their limits come from the manufacturer's seat P-T curve.

- 데이터시트에서 볼 것: Body material group and rating cover the design pressure at design temperature; seat rating separately.
- 근거: ASME B16.34

### ASME B16.5 / B16.47 — flanges  `std.b165`

B16.5 covers NPS ½–24; above NPS 24 flanges are B16.47 Series A (MSS SP-44) or Series B (API 605). Facing: RF (Class 150–2500), RTJ normally for Class 900 and above or where the piping class asks for it; RTJ face-to-face is longer than RF for the same valve.

- 데이터시트에서 볼 것: Flange standard matches the size; facing (RF / RTJ) matches the piping class facing.
- 근거: ASME B16.5 · ASME B16.47 · ASME B16.10

### ASME B16.10 / API 6D — face-to-face and end-to-end  `std.b1610`

Face-to-face of flanged ball valves: ASME B16.10 tables (short / long pattern) or API 6D tables; RTJ and butt-weld lengths differ from RF. The datasheet should name the table so the piping layout fits.

- 데이터시트에서 볼 것: Face-to-face reference stated and consistent with the end type.
- 근거: ASME B16.10 · API 6D

### Seat leakage — API 598 / ISO 5208 / API 6D  `std.leak`

ISO 5208 Rate A = no visually detectable leakage (soft-seated valves). Rate B and lower allow small leakage and are typical for metal-seated valves. API 598 allows zero leakage for soft-seated ball valves. 'Tight Shut-Off' on a datasheet is normally read as Rate A.

- 데이터시트에서 볼 것: Leakage class consistent with seat type and with the tightness requirement.
- 근거: API 598 · ISO 5208 · API 6D

### Fire type-test — API 607 / API 6FA / ISO 10497  `std.fire`

Type test of quarter-turn soft-seated valves (API 607 / ISO 10497) or API 6FA. Qualifies a design by size and pressure-class range; the certificate must cover the supplied size / class / materials. Usually required for hydrocarbon, flammable or toxic service.

- 데이터시트에서 볼 것: Fire-safe requirement stated for flammable / toxic service; certificate qualification range.
- 근거: API 607 · API 6FA · ISO 10497

### Fugitive emission — ISO 15848-1 / -2  `std.fe`

ISO 15848-1 type test: tightness Class A / B / C (A tightest, helium, bellows-level), endurance classes (mechanical cycles CO1… / CC1…), temperature classes. ISO 15848-2 = production test. Projects often ask Class A or B type-tested packing for toxic / CO2 service.

- 데이터시트에서 볼 것: Required class stated, type-test certificate covering size / class / stem seal design.
- 근거: ISO 15848-1 · ISO 15848-2

### Sour service — NACE MR0175 / ISO 15156  `std.nace`

Part 2: carbon & low-alloy steels (≤ 22 HRC, welds ≤ 250 HV10, HIC for plate). Part 3: corrosion-resistant alloys with environmental limits (temperature, H2S partial pressure, chloride, pH, elemental sulphur). Austenitic 316/316L: solution-annealed, ≤ 22 HRC, no cold work; the commonly quoted limit is 60 °C at pH2S ≤ 100 kPa (any chloride) — check the edition the project uses. 17-4PH (UNS S17400): double-aged H1150D, ≤ 33 HRC, with environmental limits; the 2020 edition further limits sustained stress to 50 % SMYS for some conditions. Bolting: exposed bolting must meet the limits (B7M / L7M / 2HM ≤ 22 HRC); non-exposed bolting may be standard B7 / B8M CL.2.

- 데이터시트에서 볼 것: Every wetted metal (body, ball, stem, seat ring, springs, exposed bolting) within ISO 15156 limits.
- 근거: NACE MR0175 / ISO 15156-1/-2/-3

### Pressure testing — API 6D / API 598 / ISO 5208  `std.pressure_test`

Shell test at 1.5 × rated pressure at 38 °C; seat tests (hydro at 1.1 ×, low-pressure gas where specified). DIB / DBB functions are proven by the seat tests of each seat separately and of the cavity.

- 데이터시트에서 볼 것: Test scope and gas test requirement for gas / CO2 service.
- 근거: API 6D · API 598 · ISO 5208

### Safety valves — IEC 61508 / 61511, partial stroke  `std.sil`

An ESD / SDV valve in a SIL loop needs reliability data (SIL capability / FMEDA certificate of the valve + actuator assembly), a fail-safe position (spring return) and often a partial stroke test to reach the required proof-test coverage.

- 데이터시트에서 볼 것: SIL level, fail-safe action, PST, certificate of the assembly.
- 근거: IEC 61508 · IEC 61511

## 설계

### Floating vs trunnion-mounted ball  `des.floating_trunnion`

Floating ball: the line pressure pushes the ball onto the downstream seat; seat load and torque grow with size × pressure, so floating designs are used for small bores and lower classes. Trunnion: ball held by trunnions, spring-loaded seats move onto the ball; lower torque, DBB/DIB possible, standard for large / high-pressure valves. API 6D does not fix the limit. Typical practice (sources differ — the company spec governs): floating up to about NPS 6–8 in Class 150, NPS 4–6 in Class 300, NPS 2–4 in Class 600, NPS 1½–2 in Class 900 and above.

- 데이터시트에서 볼 것: Type matches size × class and the PMS item; actuated large valves normally trunnion.
- 근거: API 6D · ISO 17292 · manufacturer catalogues

### Seat configuration — SPE / DPE, DBB / DIB, cavity relief  `des.seats`

SPE (self-relieving, single piston effect): cavity over-pressure vents past the seat. DPE (double piston effect): both seats seal from the cavity side too, giving DIB-1 — then a cavity relief valve is needed (thermal expansion of trapped liquid). DBB = two seats closed and the cavity can be bled. Liquid / dense-phase CO2 service traps fluid in the cavity: the relief path must be defined.

- 데이터시트에서 볼 것: Seat configuration stated; DPE → cavity relief; bi-directional sealing for bi-directional service.
- 근거: API 6D (DBB / DIB definitions, cavity relief)

### Seat materials and temperature  `des.soft_seat`

PTFE ~200 °C, reinforced PTFE (RPTFE/RTFE, glass/carbon filled) ~200–230 °C, Devlon/nylon low temperature only (nylon ~90 °C), PEEK ~260 °C, metal seats (TCC / CrC / Stellite overlay) above that or for erosive / solids service. Soft seats lose pressure rating with temperature: the seat P-T curve governs, not the body rating. Dense CO2 swells and permeates polymers.

- 데이터시트에서 볼 것: Seat material vs design temperature and shut-off ΔP; PMS seat notes.
- 근거: Manufacturer seat P-T data · ISO 17292 · API 6D

### Metal-seated ball valves  `des.metal_seat`

Used for high temperature, erosive / abrasive service, frequent cycling at high ΔP or where fire / soft-seat extrusion is a concern. Ball and seat hard-faced (tungsten carbide HVOF, chromium carbide, Stellite). Leakage normally Rate B or as agreed; torque higher.

- 데이터시트에서 볼 것: Erosive / solids service → metal seat; leakage class to match.
- 근거: API 6D · ISO 5208

### Hard-facing (HF) of ball and seats  `des.hardfacing`

'316 SS / HF' means a 316 base with a hard overlay or coating on the sealing surfaces. The datasheet / vendor must state type (TCC HVOF, CrC, Stellite 6, ENP), thickness and hardness. ENP is a coating, not a sour barrier; overlays in sour service must follow ISO 15156-3.

- 데이터시트에서 볼 것: HF type and thickness stated.
- 근거: API 6D · ISO 15156-3

### Stem — blow-out proof, anti-static, sealing  `des.stem`

Stem must be blow-out proof (inserted from inside or shoulder retained) and the valve anti-static (electrical continuity ball-stem-body, required by API 6D and ISO 17292). Stem seals: graphite packing / lip seals / O-rings; low-emission packing to ISO 15848.

- 데이터시트에서 볼 것: Anti-static and blow-out-proof stem stated or covered by a general note.
- 근거: API 6D · ISO 17292

### Body construction  `des.body`

Side-entry split body (2- or 3-piece, bolted) or top-entry (in-line maintenance) or fully welded (buried / pipeline). Body-joint bolting and gaskets are a leakage path — include them in fugitive-emission and fire requirements.

- 데이터시트에서 볼 것: Construction consistent with maintenance philosophy; body joint seals.
- 근거: API 6D

### Drain, vent and sealant injection  `des.fittings`

Larger trunnion valves usually have drain / vent connections on the body and emergency sealant injection fittings on the seats; whether they are wanted (and their plugs / valves) is a project decision.

- 데이터시트에서 볼 것: State whether drain / vent / sealant injection are required.
- 근거: API 6D (optional features)

### Full bore vs reduced bore, piggability  `des.bore`

Full bore = ball bore equals the pipe ID class (API 6D minimum bore tables); reduced bore one size smaller. Piggable lines need full, round bore valves without cavities that trap the pig.

- 데이터시트에서 볼 것: Piggable line → full bore; bore matches the PMS item.
- 근거: API 6D minimum bore tables

### Insulated / cold / heat-traced lines  `des.insulation`

Cold-insulated valves need an extended stem / bonnet (condensation and icing kept out of the operator), a vapour barrier at the stem; heat-traced valves need room for tracing around the body and actuator mounting clear of the insulation.

- 데이터시트에서 볼 것: Cold insulation → extended stem; insulation thickness known to the vendor.
- 근거: Project insulation specification · BS 6364 (cryogenic) for very low temperatures

### Actuator, fail-safe action, sizing  `des.actuator`

Fail-close / fail-open needs a spring-return actuator (or accumulator); fail-last (stay-put) is double-acting or electric. Actuator torque ≥ maximum valve torque (break-to-open at full ΔP) × safety factor (typically 1.25–1.5, project spec); the valve's MAST (maximum allowable stem torque) must exceed the actuator output.

- 데이터시트에서 볼 것: Fail action vs spring; sizing factor; MAST check by vendor.
- 근거: Project actuator specification · API 6D (MAST)

## 재질

### Carbon steel minimum temperature  `mat.temp_cs`

A216 WCB / A105 are listed down to −29 °C without impact testing (ASME B31.3 / B16.34). Below that, or in low-temperature piping classes, use impact-tested A352 LCB/LCC or A350 LF2 / LF6, or stainless steel.

- 데이터시트에서 볼 것: Body grade vs minimum design temperature and piping class.
- 근거: ASME B31.3 Table A-1 · 323.2 · ASME B16.34

### CO2 service  `mat.co2`

Dry CO2 is not corrosive to carbon steel; with free water it forms carbonic acid and corrodes rapidly. Dense / supercritical CO2 is an excellent solvent: it swells and permeates polymers and elastomers and causes rapid gas decompression (RGD) damage on depressurisation; Joule-Thomson cooling during blowdown can drive metal temperatures very low. Impurities (H2S, H2O, O2, SOx/NOx) change the material choice.

- 데이터시트에서 볼 것: Water content / dehydration, corrosion allowance, RGD-qualified seals, minimum temperature on depressurisation.
- 근거: DNV-RP-F104 · ISO 27913 · NORSOK M-001

### Elastomers — rapid gas decompression  `mat.rgd`

O-rings and elastomeric seals in high-pressure gas / CO2 service must be qualified for RGD (ISO 23936-2, NORSOK M-710) in the actual fluid and temperature; FKM, HNBR and FFKM grades exist with RGD ratings.

- 데이터시트에서 볼 것: Seal materials named and RGD-qualified.
- 근거: ISO 23936-2 · NORSOK M-710

### Dual-grade 316/316L  `mat.dual_grade`

Material certified to both 316 (strength) and 316L (≤ 0.030 % C, weldability / IGC resistance). 316L alone has lower allowable stress.

- 데이터시트에서 볼 것: Dual certification stated when the PMS asks.
- 근거: ASTM A182 / A351 · project PMS

### Material certificates and PMI  `mat.certs`

EN 10204 3.1 = manufacturer's inspection certificate; 3.2 = also verified by an independent inspector. PMI confirms alloy of pressure parts. Projects usually ask 3.1 or 3.2 for pressure-retaining parts.

- 데이터시트에서 볼 것: Certificate type per part, PMI scope.
- 근거: EN 10204 · API RP 578

## Tag 번호

### Tag numbering (learned per Area / Unit)  `tag.numbering`

An instrument / valve tag is prefix (unit or system number) + function code (ISA-5.1 style letters: ESDV emergency shutdown, SDV shutdown, BDV blowdown, XV on/off, MOV motor-operated) + loop number (+ A/B for parallel valves). New-build and existing (brownfield) plants keep their own schemes, so the tool learns the format per Area and Unit from the project's tags: where the prefix comes from (Unit, title System, P&ID system), number length and fixed leading digits, separator and suffixes. ESD / shutdown valves normally fail closed and blowdown valves fail open. The project tagging procedure governs when it is available.

- 데이터시트에서 볼 것: Tag prefix matches its system / unit; number follows the Area / Unit pattern; function code matches the fail action; no duplicates.
- 근거: ISA-5.1 · project tagging procedure · learned from the project's datasheets

## 프로젝트에서 배우는 것

### Consistency across the project's datasheets  `peer`

Datasheets of the same piping class share materials, rating and facing because the class fixes them. When most datasheets of a class agree and one differs, it is either a deliberate exception (service, size, vendor) or a copy error. The tool learns the majority from every uploaded datasheet (latest revision of each tag).

- 데이터시트에서 볼 것: A value that differs from ≥ 80 % of at least 5 datasheets in the same class.
- 근거: Project datasheets (learned)

