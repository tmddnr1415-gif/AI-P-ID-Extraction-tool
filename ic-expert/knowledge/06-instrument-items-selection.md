# 06 — Instrument Items: Selection, Sizing, Installation, Datasheets, Pitfalls (+ Other Major Vendors)

## How to use this file

- **Purpose.** This is the item-by-item engineering reference for the I&C expert chatbot. When an engineer pastes a spec, datasheet, instrument index line or P&ID extract and asks "is this the right instrument / what's missing / what should the datasheet say", retrieve the matching `## <item>` section and reason from it.
- **Structure of every item section.** Principle · Where it fits / doesn't · Key selection criteria · Typical accuracy / turndown / limits · Installation & hook-up · Datasheet must-have fields (ISA-20 / IEC 60770 / IEC 61987 style) · Common spec/review mistakes · Typical vendors/models.
- **Source discipline.** Every concrete number is followed by a link to where it was found. Numbers from vendor datasheets are *vendor reference-condition claims*, not installed performance. Statements marked **[general knowledge — verify]** are widely used engineering practice the author could not confirm against a source during this research; quote them as "typical practice", never as a code requirement. Standards are often paywalled; several figures here come from secondary summaries of the standard and are labelled accordingly — when a project decision hangs on the number, check the current edition of the standard itself.
- **Project specs override.** Company/project specs (Shell DEP, ExxonMobil GP, Aramco SAES, TotalEnergies GS, NORSOK I-001/I-002, etc.) frequently tighten or change these generic rules. Always ask which applies.
- **Related files.** Standards overviews, SIS/IEC 61511, hazardous area, and the "big" automation vendors (Emerson, Honeywell, Yokogawa, etc.) are covered in other files of this knowledge base; this file only covers them where needed for an item and lists the *other* vendors in `## Other vendors`.
- **Research limitation.** The web search budget ran out before vendor flagship models, MOV torque sizing, PSV pilot details, thermowell frequency limits and skin-TC practice could be searched; those parts are flagged.

## Table of contents

1. [Pressure & DP transmitters (incl. remote seals, manifolds)](#pressure--dp-transmitters-incl-remote-seals-manifolds)
2. [Pressure gauges & pressure switches](#pressure-gauges--pressure-switches)
3. [Flow — orifice plates / DP flow (ISO 5167)](#flow--orifice-plates--dp-flow-iso-5167)
4. [Flow — venturi, flow nozzle, averaging pitot (Annubar)](#flow--venturi-flow-nozzle-averaging-pitot-annubar)
5. [Flow — electromagnetic](#flow--electromagnetic)
6. [Flow — Coriolis](#flow--coriolis)
7. [Flow — vortex](#flow--vortex)
8. [Flow — ultrasonic (clamp-on, inline, flare, custody)](#flow--ultrasonic-clamp-on-inline-flare-custody)
9. [Flow — turbine](#flow--turbine)
10. [Flow — positive displacement](#flow--positive-displacement)
11. [Flow — thermal mass](#flow--thermal-mass)
12. [Flow — variable area](#flow--variable-area)
13. [Level — DP (incl. seals)](#level--dp-incl-seals)
14. [Level — displacer](#level--displacer)
15. [Level — guided wave radar](#level--guided-wave-radar)
16. [Level — non-contact radar (26 / 80 GHz)](#level--non-contact-radar-26--80-ghz)
17. [Level — nuclear (radiometric)](#level--nuclear-radiometric)
18. [Level — servo gauges & tank gauging (API MPMS Ch.3)](#level--servo-gauges--tank-gauging-api-mpms-ch3)
19. [Level — magnetic level gauge, sight glass](#level--magnetic-level-gauge-sight-glass)
20. [Level — vibrating fork switches](#level--vibrating-fork-switches)
21. [Temperature — TC vs RTD, transmitters](#temperature--tc-vs-rtd-transmitters)
22. [Temperature — thermowells (ASME PTC 19.3 TW-2016)](#temperature--thermowells-asme-ptc-193-tw-2016)
23. [Temperature — skin / tube-metal TCs](#temperature--skin--tube-metal-tcs)
24. [Analyzers & analyzer shelters](#analyzers--analyzer-shelters)
25. [Gas detection — point (catalytic, IR, H2S)](#gas-detection--point-catalytic-ir-h2s)
26. [Gas detection — open path](#gas-detection--open-path)
27. [Flame detection (UV, UV/IR, IR3)](#flame-detection-uv-uvir-ir3)
28. [F&G mapping & coverage (ISA-TR84.00.07)](#fg-mapping--coverage-isa-tr840007)
29. [Control valves](#control-valves)
30. [On-off & ESD valves (ZV/SDV/BDV), SOVs](#on-off--esd-valves-zvsdvbdv-sovs)
31. [Motor-operated valves (MOVs)](#motor-operated-valves-movs)
32. [Pressure safety valves (PSVs)](#pressure-safety-valves-psvs)
33. [Cabinets: system, marshalling, instrument](#cabinets-system-marshalling-instrument)
34. [Junction boxes](#junction-boxes)
35. [Cables & glands (incl. Ex d barrier glands)](#cables--glands-incl-ex-d-barrier-glands)
36. [Instrument air](#instrument-air)
37. [Hook-ups (general)](#hook-ups-general)
38. [Other vendors](#other-vendors)
39. [Gaps](#gaps)

---

## Pressure & DP transmitters (incl. remote seals, manifolds)

**Principle.** A process diaphragm transfers pressure via fill fluid to a sensor (capacitive, piezoresistive silicon, or resonant silicon). DP cells measure the difference between H and L sides; gauge/absolute variants reference atmosphere or vacuum. Output 4–20 mA + HART, or FF/PROFIBUS PA; increasingly WirelessHART for non-critical monitoring.

**Where it fits / doesn't.**
- Fits: pressure, DP for flow (orifice, venturi, Annubar), DP level and interface, filter ΔP, density (two-point DP).
- Doesn't fit well: very low DP with high static pressure (static pressure effect dominates), slurries/polymerising services without seals, cryogenic services with long wet impulse lines (vaporisation errors), hydrogen service with thin gold-less diaphragms (H2 permeation) **[general knowledge — verify]**.

**Key selection criteria.**
- Range / URL with the calibrated span sitting in the useful part of the cell (avoid >~10:1 effective turndown for control/SIS duty unless the datasheet total-performance number supports it) **[general knowledge — verify]**.
- Static pressure rating (DP cells: flange/body MWP; check against design pressure, not operating).
- Wetted materials: 316L standard; Hastelloy C-276, Monel, tantalum, gold-plated for H2; NACE MR0175/ISO 15156 for sour service.
- Fill fluid: silicone DC200 general; inert (halocarbon) for oxygen/chlorine; high-temp silicone for hot service.
- SIL capability (IEC 61508 certificate / FMEDA) if used in a SIF; separate tag from BPCS transmitter on the same tapping only if the SRS permits shared taps.
- Communication protocol and DCS/SIS compatibility.

**Typical accuracy / turndown / limits.**
- Top-tier example: Rosemount 3051S "Ultra" class quotes 0.025 % of span reference accuracy and 200:1 rangedown; "Classic" class 0.035 % and 150:1 ([Emerson 3051S PDS](https://emerson.com:443/documents/automation/product-data-sheet-rosemount-3051s-series-of-instrumentation-en-73154.pdf)). Reference accuracy is not installed accuracy; total probable performance including ambient and static-pressure effects is typically several times larger (one summary quotes ~±0.1 % of span total performance) ([Emerson 3051S PDS](https://emerson.com:443/documents/automation/product-data-sheet-rosemount-3051s-series-of-instrumentation-en-73154.pdf)).
- Yokogawa EJA-E / EJX-A series are the main competitors; their published accuracy (~±0.04–0.055 % span class) was **not confirmed in this research [general knowledge — verify]**.

**Installation & hook-up.**
- Impulse line slope: API RP 551 calls for a positive slope of at least 1:12 on all leads (as quoted in a practitioner forum, [CR4 thread](https://cr4.globalspec.com/thread/39151/impulse-tubing)); Yokogawa recommends at least 1/10 even for horizontal routing ([Yokogawa FAQ](https://yokogawa.com/us/library/resources/faqs/installing-impulse-piping)).
- Gas: taps on top of pipe, transmitter **above** taps, lines self-draining back to process ([PI Process Instrumentation — gas tap orientation](https://www.piprocessinstrumentation.com/instrumentation/flow-measurement/differential-pressure/article/15554364/tap-orientation-for-dp-flow-element-in-gas-service)).
- Liquid / steam: taps on the side (avoid bottom — sediment plugs taps), transmitter **below** taps, continuous downward slope ([Quiz Corner: DP tap orientation](https://www.piprocessinstrumentation.com/news-reports/article/15553820/quiz-corner-dp-tap-orientation)). The common "side tap ±45° below horizontal" for liquid / "within 45° of top" for gas is typical company-spec wording **[general knowledge — verify]**.
- Steam: condensate pots / tees at equal elevation, transmitter below; fill legs before commissioning **[general knowledge — verify]**.
- Manifolds: 3-valve for DP (two blocks + equalising), 5-valve for DP with vent/test, 2-valve for P (block + bleed). For SIS / natural gas, a 5-valve manifold with double equaliser avoids leakage across the cell **[general knowledge — verify]**. Close-coupled (direct mounted) manifolds reduce leak points.
- Root valves: project piping class decides (often gate/ball, DBB for high-pressure/toxic). The P&ID boundary (piping vs instrument scope) must be clear.
- Heat tracing / insulation of impulse lines where freezing, hydrate or wax risk; avoid overheating (vaporisation of liquid legs).
- Shortest possible, equal-length H/L impulse lines; tube 1/2" OD typical (3/8" minimum on clean services) **[general knowledge — verify]**.

**Remote seals.**
- Use for: corrosive, viscous, plugging, hot (> transmitter limit), sanitary, toxic (no impulse lines), or to eliminate wet-leg maintenance.
- Balanced system = identical capillary on both sides: seal temperature effect is minimised but the head temperature effect remains ([Rosemount 1199 manual](https://core.instrumart.com/assets/Rosemount-1199-manual.pdf)). "Tuned" assemblies (direct-mount on one side, capillary on the other) use the seal effect to oppose the head effect; Emerson claims 10–20 % less temperature-induced error — vendor figure ([Emerson tuned-system white paper](https://s1-live.emerson.com/documents/automation/white-paper-optimize-results-save-money-rosemount-tuned-system-assemblies-en-77256.pdf)).
- Diaphragm size, thickness, capillary length and ID all add temperature error and slow response ([Rosemount 1199 manual](https://core.instrumart.com/assets/Rosemount-1199-manual.pdf)).
- Vacuum: below ~6 psia (200 mmHgA) specify high-temperature fill and all-welded vacuum construction ([Emerson DP level](https://emerson.com/en-gb/automation/measurement-instrumentation/pressure-measurement/about-differential-pressure-dp-level-measurement)). Hot fills (e.g., Silicone 704/705, UltraTherm 805) for hot processes ([Spartan Controls tech note](https://www.spartancontrols.com/getattachment/e248b337-4372-48ec-aeae-c05a89399679/ReliablePressureMeasurementWithRemoteDiaphragm_TechnicalNote.pdf)).

**Datasheet must-haves (ISA-20 / IEC 60770 / IEC 61987).** Tag, service, P&ID, line/equipment no.; fluid & phase; operating/design P & T (min/norm/max); calibrated range & URL; output/protocol; accuracy class; body/flange/diaphragm/O-ring materials; fill fluid; process connection (1/2" NPT-F, flange on seals with rating & face); manifold type and material; seal type, capillary length, armour; electrical entry & gland; Ex certification (e.g., Ex db IIC T4 Gb or Ex ia); IP rating; SIL certificate; LCD; mounting bracket (2" pipe); NACE; tag plate; calibration & certificates (EN 10204 3.1).

**Common spec/review mistakes.**
- Range set on *operating* pressure leaving no room for upset; or URL too large (poor resolution).
- DP level with dry leg on a condensing vapour space (should be wet leg or seal).
- Static pressure rating of the cell below design pressure of a high-pressure separator.
- Remote seals with long capillary on outdoor hot/cold service with no temperature-effect calculation.
- SIS transmitter sharing a root valve with BPCS without SRS justification.
- Silicone fill specified for oxygen service.

**Typical vendors.** Emerson Rosemount 3051/3051S/2051, Yokogawa EJA-E/EJX-A, Endress+Hauser Cerabar/Deltabar (PMP/PMD/FMD), ABB 266 series, Siemens SITRANS P DS III / P320/P420, Honeywell SmartLine ST700/ST800, WIKA, Fuji FCX **[general knowledge — verify]**.

---

## Pressure gauges & pressure switches

**Principle.** Bourdon tube (C-type, helical/spiral for higher ranges), diaphragm or capsule for low pressures; mechanical movement drives a pointer. Switches use diaphragm/piston/Bourdon element acting on a microswitch.

**Where it fits / doesn't.** Gauges: local indication at pumps, compressors, PSV inlets, regulator outlets, hook-ups. Switches: increasingly replaced by transmitters + trip amplifiers in SIS because switches cannot be diagnosed online ("sleeping" contacts) **[general knowledge — verify]**. Still common on packaged equipment (lube oil, seal gas).

**Selection criteria.** EN 837-1/-3 or ASME B40.100 construction; dial 100 mm (4") or 150 mm (6"); safety pattern (solid front, blow-out back) for gas or > ~25 bar; liquid filling (glycerine/silicone) for vibration and pulsation; snubbers/restrictors for pulsating service; diaphragm seal for corrosive/viscous; overrange protection; normal operating pressure ~1/2–2/3 of full scale **[general knowledge — verify]**.

**Accuracy.** Class 1.0 (±1 % FS) typical process gauge; class 0.25/0.6 test gauges (EN 837-1) **[general knowledge — verify]**.

**Installation.** Gauge root valve + gauge valve (block & bleed); siphon (pigtail) for steam; mount vertical, readable from walkway; for switches, test connection and block valve for proof testing.

**Datasheet must-haves.** Range & units, dial size, case material/pattern, accuracy class, element & socket material, connection, fill, overrange, siphon/snubber, seal. For switches: set point & dead band (fixed/adjustable), increasing/decreasing action, contact type (SPDT/DPDT, hermetically sealed, gold contacts for low-energy IS circuits), Ex rating, proof pressure.

**Common mistakes.** Range too close to operating (needle at top of scale); no safety pattern on gas; gold-flashed contacts omitted for IS loops; switch set point inside the dead band of normal operation (chattering).

**Vendors.** WIKA, Ashcroft, Budenberg, Nuova Fima, Badotherm (seals), SOR, United Electric (One Series), Barksdale, Mercoid **[general knowledge — verify]**.

---

## Flow — orifice plates / DP flow (ISO 5167)

**Principle.** A concentric square-edged restriction creates a DP proportional to ρv²; flow ∝ √ΔP. Discharge coefficient Cd from the Reader-Harris/Gallagher equation in ISO 5167-2 / AGA-3 / ASME MFC-3M.

**Where it fits / doesn't.**
- Fits: clean liquids, gases, steam; large and high-pressure lines; when no-calibration "standards-based" uncertainty is acceptable; fiscal gas metering (AGA-3 / ISO 5167 meter runs) on legacy systems.
- Doesn't: high turndown (√ law limits single-DP-cell rangeability; one overview quotes ~3:1 turndown for orifices ([E2G DP meter overview](https://e2g.com/?p=21773))), dirty/two-phase, low Reynolds viscous liquids, where permanent pressure loss is expensive.

**Key selection & sizing criteria.**
- Concentric plate range of validity per ISO 5167-2: pipe 50 mm < D < 1000 mm, β 0.2–0.75; Re > 5,000 for β ≤ 0.45 (higher Re thresholds for larger β) (as summarised in [ABB orifice sizing doc](https://library.e.abb.com/public/f96286654e474bf7c1257b0c00551230/10_14-511-EN-01_2011.pdf)).
- Typical design target β ≈ 0.4–0.65 with full-scale DP 2500 mmH2O (100 inH2O) or 250 mbar, or as project spec **[general knowledge — verify]**.
- Uncertainty of Cd: ~0.5 % for β 0.2–0.6 at high Re per one overview ([E2G](https://e2g.com/?p=21773)) — check ISO 5167-2 clause on uncertainty.
- Tap type: flange taps (most common in O&G), corner taps, D–D/2 taps. Eccentric/segmental plates for liquids with solids or gas with condensate; quadrant-edge/conical-entrance for low Re (ISO/TR 15377) **[general knowledge — verify]**.
- Plate thickness vs DP (plate bending), drain/vent holes (affect accuracy), bevel orientation.
- Two transmitters with split ranges ("stacked DP") if turndown needed — or choose another technology.

**Straight lengths (ISO 5167-2 §6.2).**
- Required upstream lengths increase with β and with the disturbing fitting. Example quoted from the standard: two 90° bends in perpendicular planes at β = 0.55 need 44D upstream, or 22D with a flow conditioner ([Chemical Processing — Think straight about orifice plates](https://www.chemicalprocessing.com/processing-equipment/fluid-handling/article/11343758/think-straight-about-orifice-plates)).
- Secondary guides quote broad ranges of ~10–44D upstream and 5–8D downstream depending on fittings; use the actual table (ISO 5167-2:2022 §6.2 ([DIN TOC](https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:356393028/toc-3369891/download)); MFC-3M Table 2-3 ([E2G](https://e2g.com/?p=21773))). A design-stage shortcut is to lay out the run as if β = 0.7 so that a later re-bore doesn't violate straight runs ([ics-schneider guide](https://www.ics-schneider.de/messblende-auslegen-beta-verhaeltnis-und-bleibenden-druckverlust-richtig-abwaegen/?lang=en)).
- Thermowell/temperature element must be downstream (typically ≥5D, per ISO 5167 conditions) **[general knowledge — verify]**.
- Control valves must be **downstream** of the meter run whenever possible.

**Installation & hook-up.** As for DP transmitters (gas: taps top, transmitter above; liquid: taps side, transmitter below). Orifice flange assemblies (ASME B16.36) with jack screws; senior/junior fittings (Daniel) for on-line plate change in fiscal gas. Plate carrier/holder concentricity and gasket protrusion matter.

**Datasheet must-haves.** Fluid, phase, composition/MW, density, viscosity, Cp/Cv (gases), compressibility Z, normal/max/min flow, operating P & T, pipe size/schedule/ID, material; plate type, β, bore, thickness, bevel, drain/vent hole; tap type & orientation; DP at max flow; permanent pressure loss; sizing standard & edition; flange rating; upstream/downstream straight lengths available; expansibility factor, Re at min/norm/max.

**Common mistakes.** Sizing with the wrong ID (nominal not schedule); vent hole on gas plate omitted from Cd calc; no check of min-flow DP vs transmitter resolution; flow conditioner not shown on P&ID/isometric; meter in vertical downflow with liquid; DP range not matched to the square-root extraction location (transmitter vs DCS) — specify only one place.

**Vendors.** Emerson (Rosemount 1595 conditioning orifice, 405 compact, Daniel senior fittings), ABB, Endress+Hauser Deltatop, WIKA (FLC series), Yokogawa, McCrometer V-Cone (proprietary DP, short runs), local fabricators **[general knowledge — verify]**.

---

## Flow — venturi, flow nozzle, averaging pitot (Annubar)

**Venturi (ISO 5167-4).** Converging–throat–diverging; low permanent pressure loss (typically 10–20 % of DP) and tolerant of some solids **[general knowledge — verify]**. ISO 5167-4:2003 validity: pipes 50–1200 mm and pipe Re ≥ 2×10^5 ([ISO 5167-4 abstract](https://www.iso.org/standard/30192.html)); 2022 edition supersedes it and adds a pressure-loss annex ([ISO 5167-4:2022 preview](https://webstore.ansi.org/preview-pages/ISO/preview_ISO+5167-4-2022.pdf)). Machined-convergent venturis have shown Cd values outside the standard prediction by 2 % or more, and the standard recommends calibrating venturis for gas service over the flow range ([ISO 5167-4:2022 preview](https://webstore.ansi.org/preview-pages/ISO/preview_ISO+5167-4-2022.pdf)). Use: large water lines, cooling water, slurry-ish service, compressor suction where ΔP is precious, wet-gas venturis (ISO/TR 11583) **[general knowledge — verify]**.

**Flow nozzle (ISO 5167-3).** High-velocity steam, PTC-6 turbine testing **[general knowledge — verify]**.

**Averaging pitot (Annubar, Verabar, iTherm-type).** Multi-port probe across diameter; low pressure loss; hot-tap insertion possible; cheap in large lines. Accuracy typically ~±1 % of rate (calibrated better), turndown ~8–10:1 with one DP cell **[general knowledge — verify — no source found in this research]**. Needs long straight runs (vendor tables), vulnerable to vibration (probe natural frequency vs vortex shedding — vendor wake-frequency check required) **[general knowledge — verify]**.

**Datasheet must-haves.** As orifice plus: throat diameter, recovery cone angle, material, calibration (for venturi in gas); probe length, opposite-side support, hot-tap kit, wake-frequency calc (pitot).

**Common mistakes.** Treating venturi as "no straight run needed"; using an averaging pitot where the profile is distorted (downstream of a header tee) without a conditioner; no support for long probes in big ducts.

**Vendors.** Emerson Rosemount 485/585 Annubar and 3051SFA; Veris Verabar; Badger; Preso; Primary Flow Signal; Hydro-Flow; McCrometer; Endress+Hauser Deltatop; Systec (Deltaflow) **[general knowledge — verify]**.

---

## Flow — electromagnetic

**Principle.** Faraday's law: conductive liquid moving through a magnetic field induces voltage proportional to velocity; full-bore, no obstruction.

**Fits.** Water, produced water, cooling water, slurries, chemicals, firewater. **Doesn't fit:** hydrocarbons, gases, steam, demineralised water / condensate below the conductivity limit.

**Selection.**
- Minimum conductivity: 5 µS/cm for most Krohne primary heads ([Krohne installation guide](https://cdn.krohne.com/archive/TD_MID_INSTALL_e_72.pdf)); some vendor models need 3, 20 or 50 µS/cm — check the specific model ([Yokogawa AXF FAQ](https://www.yokogawa.com/ca/library/resources/faqs/what-is-the-minimum-required-conductivity-for-a-liquid-when-using-an-axf-magnetic-flow-meter)).
- Liner: PTFE/PFA (chemicals, high temp), hard/soft rubber (water, abrasive), polyurethane (abrasive), ceramic. Electrodes: 316L, Hastelloy C, titanium, tantalum, platinum.
- Velocity: typical design 1–5 m/s (abrasive slurry 2–3 m/s) **[general knowledge — verify]**.
- Grounding: rings or grounding electrode with non-conductive/lined pipe.

**Accuracy.** Commonly ±0.2–0.5 % of rate, e.g., ABB FEP500 0.3 % (optional 0.2 %) of measured value ([ABB FEP500 datasheet](https://library.e.abb.com/public/c4148da8f7404266a9e6dae3745d3783/DS_FEP500_EN_D.pdf)).

**Installation.** 5D upstream / 2D downstream from electrode axis is a typical vendor requirement ([Krohne installation guide](https://cdn.krohne.com/archive/TD_MID_INSTALL_e_72.pdf)); some designs allow 0D/0D ([Instrumart M2000 datasheet](https://core.instrumart.com/assets/M2000DatasheetMay2024.pdf)). Pipe must run full: vertical upflow or low point in horizontal; electrode axis horizontal; avoid pump suction (vacuum can collapse PTFE liners); remote converter cable length limits at low conductivity ([ICS Schneider note](https://www.ics-schneider.de/mid-bei-sehr-geringer-leitfaehigkeit-mindestleitfaehigkeit-elektrodenkontakt-und-messstabilitaet-pruefen/?lang=en)).

**Datasheet must-haves.** Fluid, conductivity (min), solids content, flow range, P/T, size, liner, electrode, grounding device, flange rating/material, converter (integral/remote, cable length), empty-pipe detection, power (AC/DC, 4-wire), Ex, IP68 for buried/submerged sensors.

**Common mistakes.** Specified on condensate/BFW (too low conductivity); PTFE liner under vacuum; no grounding rings on GRP pipe; meter at high point with air pockets; 4-wire power not provided in the cabinet design.

**Vendors.** Endress+Hauser Promag, Krohne Optiflux, ABB ProcessMaster/AquaMaster, Siemens SITRANS FM MAG, Yokogawa ADMAG AXF/AXG, Emerson Rosemount 8700 **[general knowledge — verify]**.

---

## Flow — Coriolis

**Principle.** Vibrating tube(s); mass flow causes a phase shift (twist) proportional to mass flow; resonant frequency gives density. Direct mass, density, temperature; viscosity on some models.

**Fits.** Mass balance, custody transfer of liquids (crude, condensate, LPG, LNG loading), chemical injection, blending, density/concentration, gas measurement in smaller lines. **Doesn't fit** (or needs care): very large lines (> DN 300–400, cost/weight), low-pressure gas (pressure drop), two-phase/entrained gas (performance degrades), heavy abrasive slurries.

**Selection.** Size on allowable pressure drop and accuracy at min flow (zero stability), not on line size. Check gas Mach/velocity and noise. Tube material (316L, alloy C-22, tantalum, super duplex). Single vs dual tube (single straight tube = drainable, lower accuracy).

**Accuracy.** Micro Motion ELITE: ±0.05 % liquid mass, ±0.35 % gas mass (catalogue) ([Micro Motion catalogue](https://pdf.directindustry.com/pdf/micro-motion/superior-gas-flow-density-measurement/14564-65076.html)). Emerson quotes AGA Report No. 11 gas spec as ±0.7 % and claims water-calibrated meters transfer to gas ([Micro Motion piecewise-linearisation brochure](https://s1-live.emerson.com/documents/automation/brochure-piecewise-linearization-to-enhance-calibration-for-gas-applications-micro-motion-en-4857948.pdf)). Do not quote liquid accuracy for gas service.

**Custody / legal metrology.** OIML R117-1 is for liquids other than water; OIML R137-1 is for gas meters; EU MID covers both ([Emerson MID guide](https://www.emersonautomationexperts.com/wp-content/uploads/2013/05/European-MID-Directive-for-Custody-Transfer-Measuring-Instruments.pdf)). AGA 11 / API MPMS 5.6 apply to Coriolis in gas/liquid custody **[general knowledge — verify]**.

**Installation.** No straight-run requirement for most designs **[general knowledge — verify]**; mount so tubes stay full (liquid: tubes down; gas: tubes up), avoid pipe stress and vibration, provide isolation valves for in-situ zero, keep away from strong vibration sources.

**Datasheet must-haves.** Fluid, phase, density range, viscosity, mass flow min/norm/max, allowable ΔP, P/T, accuracy at min flow, density accuracy, tube material, process connection, secondary containment rating, transmitter (integral/remote), outputs (mA/pulse/Modbus/HART), custody approval (OIML/MID/API), calibration (factory, gas, piecewise), heating jacket, Ex.

**Common mistakes.** Line-sized meter giving huge ΔP; sized at max flow and then outside zero-stability band at min flow; gas service with no pressure-drop check; using it on flashing liquid (LPG near bubble point) without back-pressure.

**Vendors.** Emerson Micro Motion (ELITE, F-series, H-series), Endress+Hauser Promass (Q, F, X), Krohne Optimass, Yokogawa Rotamass, ABB CoriolisMaster, Siemens SITRANS FC, Rheonik **[general knowledge — verify]**.

---

## Flow — vortex

**Principle.** Bluff body sheds vortices (Kármán street) at frequency ∝ velocity; sensed by piezo or capacitive sensor.

**Fits.** Steam (very common), clean gases, utility air, nitrogen, low-viscosity liquids. **Doesn't fit:** low Reynolds / viscous liquids, very low velocities, pulsating flow, dirty fluids building on shedder.

**Selection.** Verify minimum Reynolds number and minimum velocity for the claimed accuracy — vendors specify both ([industrialmonitordirect blog, secondary](https://industrialmonitordirect.com/blogs/knowledgebase/rosemount-8800d-vortex-meter-turndown-n2-vent-flow-sizing)). Often reduced-bore ("reducer") versions to keep velocity up at low flow. Integrated temperature (and pressure) for steam mass flow compensation.

**Accuracy / turndown.** Rosemount 8800: ±0.65 % of rate liquids, ±1 % gas/steam (uncompensated), 38:1 turndown claimed on one catalogue page ([Emerson 8800 catalogue](https://emerson.com/en-us/catalog/rosemount-8800-vortex)); another Emerson flyer states 15:1 ([Emerson 8800 Quad flyer](https://d1-live.emerson.com/documents/automation/flyer-rosemounttm-8800-quad-vortex-flow-meter-en-7073954.pdf)) — turndown is application-dependent.

**Installation.** Straight runs typically ~10–35D upstream / 5D downstream depending on fitting (vendor table) **[general knowledge — verify]**. Avoid vibration (pump/compressor discharge); control valve downstream; liquid: full pipe; steam: orientation per vendor (sensor body to the side to avoid condensate) **[general knowledge — verify]**. Quad/dual-sensor variants serve SIS or redundancy.

**Datasheet must-haves.** As other flow + min Re, min velocity, low-flow cutoff, sensor redundancy, temperature compensation, steam tables, vibration level at site.

**Common mistakes.** Sizing a line-size vortex on start-up/low-load steam where flow falls below cutoff; installed downstream of a reciprocating compressor; flare service (wrong technology — use ultrasonic).

**Vendors.** Emerson Rosemount 8800, Endress+Hauser Prowirl 200, Yokogawa digitalYEWFLO, Krohne Optiswirl, ABB VortexMaster/SwirlMaster, Siemens SITRANS FX **[general knowledge — verify]**.

---

## Flow — ultrasonic (clamp-on, inline, flare, custody)

**Principle.** Transit-time: difference between upstream/downstream acoustic transit times on one or more chordal paths. Doppler variant for dirty liquids (lower accuracy).

**Inline multipath (gas custody, AGA 9 / ISO 17089-1).**
- AGA Report No. 9 is performance-based: it specifies what the meter must achieve, not how it is built ([ASGMT AGA 9 overview 2022](https://asgmt.com/wp-content/uploads/2023/07/2022_An_Overview_and_Update_of_AGA_9_Ultrasonic_Meters.pdf)). Meter body ID must be within 1 % of the upstream tube ID, and scaled 4–20 mA output is not to be used for custody measurement — use serial digital to the flow computer ([ASGMT AGA 9 overview](https://asgmt.com/paper/an-overview-and-update-of-aga-9-3)).
- Third edition published 2017, with an appended version released 2021 ([ASGMT AGA 9 overview 2022](https://asgmt.com/wp-content/uploads/2023/07/2022_An_Overview_and_Update_of_AGA_9_Ultrasonic_Meters.pdf)).
- Flow calibration at an accredited lab, flow conditioner (e.g., CPA 50E, Zanker, NOVA) and meter run per vendor/AGA 9 tested configuration **[general knowledge — verify]**.
- Liquid custody: API MPMS Ch. 5.8 **[general knowledge — verify]**.

**Clamp-on.** Lower accuracy than inline because pipe wall thickness and bore uncertainties enter directly ([Fuji Electric — inline vs clamp-on](https://americas.fujielectric.com/?p=192056)). Siemens argues clamp-on can meet AGA 9 when mounted on a calibrated spool — vendor claim ([Siemens clamp-on gas custody](https://assets.new.siemens.com/siemens/assets/api/uuid:9670bb2c-83be-4c59-809a-01b79ead159b/di-pa-mi-gas-pipeline-custody-transfer-clamp-2022.pdf); [ASGMT clamp-on fundamentals](https://asgmt.com/wp-content/uploads/2023/07/2022_Fundamentals_of_Natural_Gas_Flow_Measurement_Using_Clamp_On_Ultrasonic_Flow_Meters.pdf)). Good for retrofit, check-metering, large water lines, no-shutdown installs; typical uncalibrated field accuracy ~1–3 % **[general knowledge — verify]**.

**Flare gas.** Transit-time ultrasonic is the technology of choice for flare flow ([Control Global — ultrasonic flare metering](https://www.controlglobal.com/articles/2018/why-and-how-to-use-ultrasonic-flowmeters-for-flare-flow-metering/)). Baker Hughes Panametrics XGF868i quotes velocities to 120 m/s ([XGF868i datasheet](https://dam.bakerhughes.com/m/5fd2c2563e141dd7/original/DigitalFlow-XGF868i-Datasheet-English.pdf)); normal flare velocity is often only 0.03–0.3 m/s ([PanaFlare XGF1100 datasheet](https://dam.bakerhughes.com/asset/2735f945-afc8-4178-8406-f4a3fbefb24d/PanaFlare-XGF1100-Datasheet-English.pdf)) — so the meter must cover ~1000:1+ range. Relevant standards: API MPMS 14.10, 22.3, ISO 17089-2, BS 7965 ([NFOGM flare best practice](https://nfogm.no/wp-content/uploads/2014/02/Flare-Measurement-Best-Practices.pdf)). Transducers installed by hot-tap with isolation valves; retractable.

**Datasheet must-haves.** Paths/chords, pipe ID/wall/material/lining (clamp-on), gas composition & MW range (sound speed), velocity range, P/T, diagnostics (SoS, profile factor, gain, SNR), flow calibration, flow conditioner, outputs (Modbus to flow computer), custody approvals, transducer retraction (flare), Ex.

**Common mistakes.** Using clamp-on for fiscal liquid without calibration; no flow conditioner/straight run; thermal-mass meter specified for flare with variable H2 content; flare meter not specified for low-pressure (attenuation) or high-velocity upset.

**Vendors.** Emerson Daniel (3410/3420 gas, 3810 liquid), Sick FLOWSIC600/600-XT (gas), FLOWSIC100 Flare; Krohne Altosonic (liquid/gas); Baker Hughes Panametrics (GF868/XGF868i, PanaFlare, Sentinel LNG); Siemens SITRANS FUS/FS230 clamp-on; Flexim (clamp-on); Endress+Hauser Prosonic **[general knowledge — verify]**.

---

## Flow — turbine

**Principle.** Rotor speed ∝ volumetric flow; pick-off gives pulses (K-factor).

**Fits.** Clean low-viscosity liquids (refined products, condensate) custody with prover; gas turbine meters (AGA 7) in distribution. **Doesn't:** viscous crude (linearity degrades), dirty fluids, two-phase, pulsating flow. Range within acceptable linearity/repeatability depends on density, viscosity and vapour pressure ([API 2534 historic standard](https://standards.globalspec.com/std/1305090/std-2534)).

**Standards.** API MPMS Ch. 5.3 (5th ed. 2005, reaffirmed 2014) ([SAI Global listing](https://infostore.saiglobal.com/en-us/standards/API-MPM-CH5-3-2005-97739_SAIG_API_API_2630687/)). Re-proving required when product, T, P, density or viscosity change ([ASGMT provers fundamentals](https://asgmt.com/wp-content/uploads/2023/07/2022_Fundamentals_Of_Meter_Provers_And_Proving_Methods.pdf)). Typical repeatability for custody turbine/prover systems ~0.02–0.05 % **[general knowledge — verify; not found in source]**.

**Installation.** Flow straightener + ~10D upstream / 5D downstream typical, strainer upstream, air eliminator, back pressure to prevent cavitation **[general knowledge — verify]**.

**Datasheet must-haves.** Viscosity range, linearity, repeatability, K-factor, pulse output type (dual pulse per API MPMS 5.5 for custody), strainer, straightener, bearing material, prover connection.

**Vendors.** Emerson Daniel, Faure Herman (Heliflu), TechnipFMC Smith Meter, Hoffer, Cameron NUFLO, Elster (gas) **[general knowledge — verify]**.

---

## Flow — positive displacement

**Principle.** Traps fixed volumes (oval gear, rotary vane, helical screw, piston, birotor).

**Fits.** Viscous liquids (crude, fuel oil, lube oil), chemical injection, loading/unloading custody (API MPMS Ch. 5.2), high accuracy at low Re. **Doesn't:** dirty fluids without strainer, gas (except rotary gas meters), where a jam blocking flow is unacceptable (provide bypass).

**Accuracy.** ±0.1–0.5 % of rate typical; turndown 10:1 or better; accuracy improves with viscosity **[general knowledge — verify]**.

**Mistakes.** No strainer/air eliminator; no bypass; pressure-drop not checked at max viscosity.

**Vendors.** TechnipFMC Smith Meter, Liquid Controls (IDEX), Brodie, Oval, Bopp & Reuther, Kral **[general knowledge — verify]**.

---

## Flow — thermal mass

**Principle.** Heat transfer from a heated sensor to the gas (constant-ΔT or constant-power) ∝ mass flow; insertion or inline.

**Fits.** Low-pressure gases, fuel gas to burners, compressed air, nitrogen, vent/flare where composition is stable. **Doesn't:** variable composition (especially H2-rich), wet gas, liquids.

**Limits.** Calibrated to one gas composition; composition change errors can be 2–5 % (high CO2), 2–15 % (high propane), 100–300 % (high H2) — figures from an ultrasonic vendor ([Fluenta comparison](https://www.fluenta.com/technology-comparison-thermal-mass-vs-ultrasonic-meters-for-flare-gas-measurement)). Vendor claims ±0.5 % of reading with 100:1 turndown and field-selectable gas mixes ([Sierra Instruments](https://info.sierrainstruments.com/oilgasflowmeters)); independent field demonstration of real-time composition correction was not confirmed per one regulatory draft report ([Scribd flare gas report](https://www.scribd.com/document/266069169/Flare-Waste-Gas-Flow-Rate)).

**Installation.** Insertion: long straight runs (vendor), velocity profile correction, hot-tap retractor. Moisture droplets cause spikes.

**Vendors.** Fluid Components International (FCI ST100), Sierra (QuadraTherm 640i/780i), Endress+Hauser t-mass, Magnetrol Thermatel, Kurz **[general knowledge — verify]**.

---

## Flow — variable area

**Principle.** Float rises in a tapered tube until weight balances drag; glass tube or metal tube with magnetic follower and optional transmitter.

**Fits.** Purge flows (DP/analyser purge), small utility flows, local indication, seal flush, injection checks; no power needed. **Doesn't:** high accuracy, pulsating flow, opaque fluids (glass), horizontal lines.

**Accuracy.** Typically class 1.6–2.5 % FS (VDI/VDE 3513 accuracy class) **[general knowledge — verify — VDI/VDE 3513 not found in search]**. Must be installed vertical, flow upward; calibrated for specific density/viscosity.

**Vendors.** Krohne H250, Yokogawa RAMC, ABB, Brooks, Kobold, Swagelok (purge rotameters) **[general knowledge — verify]**.

---

## Level — DP (incl. seals)

**Principle.** Hydrostatic head = ρgh. Closed vessels need the vapour space pressure on the low side via dry leg, wet leg, or remote seals (balanced/tuned/electronic remote sensors).

**Fits.** Separators, KO drums, columns, tanks; interface with two transmitters or by density difference; very robust & SIL-proven. **Doesn't:** variable density without compensation; foam; very low ρ (LNG/cryogenic needs care); very tall vessels with long capillary in big ambient swing.

**Selection.** Elevation/suppression calc (wet-leg fill density, seal fill SG), dry leg drainability, seal temperature error calc (vendor tool), density at min/max operating T, electronic remote sensors (two sensors with digital link, e.g., Rosemount 3051S ERS) to avoid capillaries in tall columns **[general knowledge — verify]**.

**Installation.** HP tap ≥ ~50 mm above vessel bottom or below LLLL with margin; LP tap above HHLL; transmitter at or below HP tap; condensate pots for wet legs in condensing service; heat trace capillaries only if specified by vendor **[general knowledge — verify]**.

**Datasheet must-haves.** Tap elevations (relative to tangent line), measuring range in mm and in mbar, LRV/URV with elevation/suppression, liquid SG min/max, vapour density, wet-leg fluid & SG, seal details (see pressure transmitters).

**Mistakes.** Range set from SG at design temperature but operating at different temp; dry leg in a condensing service; LRV/URV sign wrong for wet-leg (reverse acting); interface computed without upper-phase density spread.

---

## Level — displacer

**Principle.** Archimedes: buoyancy on a displacer hanging on a torque tube or spring; can do level, interface or density. Measures only over the displacer length ([InstrumentationTools](https://instrumentationtools.com/?p=29238)); typical displacer lengths 350–3000 mm (Foxboro/Eckardt example) ([Foxboro 167LP datasheet](https://www.hitma-instrumentatie.nl/media/3751/catalog/instrumentatie/documenten/Datasheet%20Foxboro%20Eckardt%20167LP.pdf)).

**Fits.** Interface on separators with clean fluids; legacy/brownfield replacement; high-pressure/temperature where mechanical simplicity preferred. **Doesn't:** variable density (reading follows SG; DLC3100 compensates with RTD or entered temperature) ([Fisher DLC3100 bulletin](https://emerson.com/documents/automation/product-bulletin-fisher-dlc3100-dlc3100-sis-digital-level-controller-en-1278940.pdf)); fouling, waxing, vibration; > ~3 m ranges.

**Failure modes.** Encrustation, torque tube freezing, broken hanger, stuck displacer, mass change by corrosion ([InstrumentationTools](https://instrumentationtools.com/?p=29238)).

**Installation.** External cage (side-side, side-bottom, top-bottom), isolation valves, drain & vent, cage connections matching vessel nozzles; often GWR replaces displacer inside the same cage.

**Datasheet must-haves.** Displacer length/volume/weight, upper/lower liquid SG at operating T, torque tube material & rating, cage material/connections/rating, mounting (left/right), controller/transmitter type.

**Vendors.** Emerson Fisher 249 + DLC3010/DLC3100, Baker Hughes Masoneilan 12400 series, Magnetrol (E3 Modulevel), Foxboro/Eckardt 144LD/167LP **[general knowledge — verify for Masoneilan/Magnetrol]**.

---

## Level — guided wave radar

**Principle.** TDR: microwave pulse travels along a probe (single rod/cable, twin, coaxial) and reflects at dielectric changes; time-of-flight → level; interface from second reflection.

**Fits.** Separators, KO drums, interface (oil/water), cages (displacer replacement), LPG, condensate, low-DC liquids, steam drums (with steam compensation). **Doesn't:** heavy coating/bridging on twin/coax probes, very long ranges in turbulent vessels without anchoring, emulsion layers (smeared interface).

**Selection.**
- Probe: coaxial for low DC, disturbing objects, turbulence, tall narrow nozzles or chambers; single lead/twin for viscous media ([Emerson GWR interface note](https://www.emerson.com/documents/automation/technical-note-guided-wave-radar-interface-measurement-en-78542.pdf)). 5300 single lead reportedly down to DC 1.2 ([Rosemount 5300 brochure](https://core.instrumart.com/assets/5300-brochure.pdf)).
- Interface: upper product low DC (<3), lower high DC (>20), upper DC known and constant ([Emerson GWR interface note](https://www.emerson.com/documents/automation/technical-note-guided-wave-radar-interface-measurement-en-78542.pdf)); thin-layer detection claims down to ~25 mm upper layer ([Emerson 5300](https://s1-live.emerson.com/cs-cz/automation/measurement-instrumentation/level/continuous-level-measurement/about-guided-wave-radar/about-rosemount-5300-level-transmitter)).
- Reference accuracy ~±3–5 mm ([Emerson level flyer](https://s1-auth.emerson.com/documents/automation/flyer-rosemount-process-level-instrumentation-data-en-us-191106.pdf)).
- Upper/lower dead zones (transition zones) must be outside the alarm/trip span **[general knowledge — verify]**.

**Installation.** In a chamber/stilling well, centring discs; chamber ≥ 3"/4" for single lead **[general knowledge — verify]**; nozzle height/diameter limits; avoid probe contact with walls/internals; vapour-space compensation for high-pressure steam (reference reflector).

**Datasheet must-haves.** Measuring range, probe type/length/material, DC of each phase (min), vapour composition/pressure, process connection, chamber details, interface requirement, dead zones, SIL, Ex, centring disc material.

**Mistakes.** Coax probe on waxy crude; GWR length cut to vessel without accounting for dead zone; interface where an emulsion band exists; not specifying chamber with the instrument (separate vendors → mismatch).

**Vendors.** Emerson Rosemount 5300/5301/5302/3300, Endress+Hauser Levelflex FMP5x/FMP2x, VEGA VEGAFLEX 8x, Krohne Optiflex, Magnetrol Eclipse 706, Siemens SITRANS LG **[general knowledge — verify]**.

---

## Level — non-contact radar (26 / 80 GHz)

**Principle.** FMCW or pulse radar through air from an antenna on top of the vessel.

**Frequency choice.** Beam angle depends on frequency and antenna size: an 80 mm antenna gives ~3° at 80 GHz vs ~10° at 26 GHz ([VEGA blog](https://www.vega.com/en/company/blog/2017/good-focusing-delivers-security)); narrower beam avoids agitators, heating coils, nozzle and wall buildup; 80 GHz offers ~120 dB dynamic range vs ~96 dB ([Control Global — 80 GHz](https://www.controlglobal.com/measure/level/article/11318576/liquid-radar-level-moves-up-to-80-ghz)). Low frequency (6 GHz) still has a role in heavy vapour/condensation and foam **[general knowledge — verify]**. VEGA's VEGAPULS 6X positions itself as one platform for 80/26/6 GHz ([VEGA blog](https://www.vega.com/en/company/blog/2017/good-focusing-delivers-security)).

**Fits.** Storage tanks, sumps, tall vessels, corrosive/sticky media, solids silos; through stilling wells for tank gauging. **Doesn't:** interface (generally), heavy foam, very low DC in turbulent conditions, in-vessel with dense internals (consider GWR).

**Installation.** Away from fill stream and wall (vendor distance), nozzle length vs antenna (80 GHz tolerates longer nozzles), stilling wells per vendor (slots, ID), purge connection for condensing/sticky service **[general knowledge — verify]**.

**Datasheet must-haves.** Frequency, antenna type/size/material, range, nozzle size/height, DC, vapour/foam/condensation, accuracy, SIL, Ex, still-well details, radio approval (country).

**Vendors.** VEGA VEGAPULS 6X/64, Endress+Hauser Micropilot FMR6x/FMR5x, Emerson Rosemount 5408/5900S, Krohne Optiwave, Siemens SITRANS LR **[general knowledge — verify]**.

---

## Level — nuclear (radiometric)

**Principle.** Gamma source (usually Cs-137, sometimes Co-60) on one side; scintillation detector on the other; attenuation ∝ material in path. Non-intrusive.

**Fits.** Delayed coker drums, high-T/P, highly corrosive/toxic, heavy fouling, slurry, vessels with no nozzles. Cs-137 is the usual coke-drum source; Co-60 is more energetic (less attenuation) but half-life 5.3 y vs 30 y ([Thermo Fisher — delayed coking](https://www.thermofisher.com/blog/mining/a-hybrid-approach-to-the-delayed-coking-process-part-3)). Operators report gamma continuous coke-drum level can be hard to calibrate; neutron backscatter is easier to permit ([AFPM Q&A #74](https://afpm.org/data-reports/technical-papers/qa-search/question-74-please-discuss-pros-and-cons-various-coke-drum)).

**Doesn't fit.** Where licensing/radiation protection is impractical, or a contact technology works.

**Datasheet must-haves.** Source isotope/activity, shielding/collimation, dose rate at 1 m/at surface, vessel wall thickness & ID & material, measuring range, detector type & length, source holder lock (shutter) and its position indicator, licensing jurisdiction, process density/buildup.

**Mistakes.** Licence/transport lead time not in schedule; shutter interlock with vessel entry not specified; internals/insulation changes after calibration.

**Vendors.** Berthold (LB 476 Level+ marketed for delayed coke drums), VEGA (FIBERTRAC/SOLITRAC/MINITRAC), Endress+Hauser Gammapilot ([E+H in Hydrocarbon Processing, Aug 2023](https://read.nxtbook.com/gulf_energy_information/hydrocarbon_processing/august_2023/pcia_thomas_endress_hauser_.html)), Thermo Fisher, Ronan **[model list general knowledge — verify]**.

---

## Level — servo gauges & tank gauging (API MPMS Ch.3)

**Principle.** Servo: displacer on a wire, servo motor keeps buoyancy constant; measures level, interface, density profile, bottom/water. Tank radar gauges (Rosemount 5900S, E+H NMR8x) used for custody and inventory. Hybrid systems add pressure (HTG) and multi-point temperature (MPT/ATT) for mass.

**Standards.** API MPMS Ch. 3.1B (ATGs in stationary tanks; 4th ed. Oct 2021 listed) ([standard.no](https://online.standard.no/en/api-mpms-31b)). Commonly quoted figures: factory calibration ±1 mm for custody ([APG sensors summary](https://apgsensors.com/api-18-2-custody-transfer-compliance-with-transmitters)); installed error ±3 mm; field verification tolerance ±4 mm vs manual dip at three levels ([OGC training handbook](https://online.flippingbook.com/view/520915846/18)) — secondary sources; verify Table 1 of 3.1B. API 3.1B recommends ±3 mm for inventory control per E+H ([E+H white paper](https://bdih-download.endress.com/file/005056A5E3831ED8BCFBA2A214177B92/WP01094S00EN0118.pdf)). Other: API MPMS 7 (temperature), OIML R85 (legal metrology ATGs), ISO 4266.

**Accuracy.** E+H Proservo NMS8x ±0.4 mm level ([E+H TI01248G](https://bdih-download.endress.com/files/DLA/005056A500261EDFB0FCCC9653A98A19/TI01248GEN_0824-00.pdf)); Honeywell Enraf Smart Servo 954: <±0.4 mm to 40 m, interface <±2 mm ([954 spec](https://www.euromekanik.se/app/uploads/954-Smart-Servo-Tech-Spec.pdf)); older 854 ATG density accuracy <±3 kg/m³ with density displacer ([854 brochure copy](https://www.slideshare.net/slideshow/producto-016484713/238897223)).

**LNG tanks.** Typical set: 2 × level gauges (servo or radar) + independent level for high-level alarm/trip (separate technology), LTD (level-temperature-density) gauge for rollover detection, multi-point temperature, skin TCs for cooldown **[general knowledge — verify]**.

**Installation.** Stilling well (slotted, 6–8" typical) fixed to tank bottom, reference datum plate, gauge on a stable roof location, calibration/verification hatch near gauge **[general knowledge — verify]**.

**Datasheet must-haves.** Tank type (fixed/floating/cryogenic), height, stilling well, product(s), density range, accuracy class & approval (OIML R85, NMi, PTB), interface/density functions, temperature element (spot/averaging, points), protocol to TMS (Modbus/HART/Enraf/GPU), SIL for high-level (API 2350 overfill).

**Vendors.** Honeywell Enraf (854/954, Flexline), Endress+Hauser (Proservo NMS8x, Micropilot NMR8x, Tankvision), Emerson Rosemount TankRadar (5900S/5900C, 2240S MTT), Varec, L&J, Whessoe (LNG) **[general knowledge — verify]**.

---

## Level — magnetic level gauge, sight glass

**Magnetic level gauge (MLG).** Float with magnet in a chamber flips bicolour flaps/followers; no glass, suitable for high pressure, toxic and LPG; can carry GWR or magnetostrictive transmitter and reed switches on the chamber **[general knowledge — verify]**. Float must be designed for minimum SG and design pressure (buoyancy margin) and interface SG difference — float SG limits were not found in this research **[gap]**.

**Sight glasses.** Reflex (water-free, colour contrast for liquid/vapour), transparent (interface, with illuminator), tubular (low P only). Mica shields for steam > ~ 30 bar / caustic **[general knowledge — verify]**. Overlap between multiple gauges; ball-check gauge cocks to limit leakage on glass failure; many operators restrict glass on toxic/flammable service (prefer MLG).

**Mistakes.** MLG float SG set for lighter phase at design T, sinks/does not float at operating; gauge visible range not covering all alarm/trip levels; no overlap.

**Vendors.** KSR Kuebler, Magnetrol (Atlas/Aurora), Klinger, Penberthy, Jerguson, Krohne BM26, WIKA **[general knowledge — verify]**.

---

## Level — vibrating fork switches

**Principle.** Piezo-driven fork resonates; frequency shifts when immersed.

**Limits.** Typical minimum medium density 0.5 g/cm³ (0.4 optional) across vendors: E+H Liquiphant FTL50/51 ([E+H FTL51](https://www.nl.endress.com/en/field-instruments-overview/level-measurement/Vibronic-Liquiphant-FTL51)), Krohne Optiswitch ([Krohne](https://krohne.com/en/products/level-measurement/level-switches/vibration-level-switches/optiswitch-5150)), Siemens LVL200 ([Siemens](https://cache.industry.siemens.com/dl/files/042/109765042/att_1277064/v1/sitransl_lvl200_fi01_en.pdf)). SIL 2/3 versions exist ([E+H FTL51](https://www.nl.endress.com/en/field-instruments-overview/level-measurement/Vibronic-Liquiphant-FTL51)).

**Fits.** Overfill protection, pump dry-run, high/low alarms in tanks/sumps. **Doesn't:** very viscous / sticky / crystallising media, LNG below density limit, heavy solids.

**Installation.** Fork blades oriented vertically in horizontal pipe / so liquid drains; avoid nozzles longer than fork; not in fill stream **[general knowledge — verify]**.

**Mistakes.** Used on low-density LPG/LNG below 0.5 g/cm³ without checking; MIN/MAX safety mode (fail-safe direction) not specified.

---

## Temperature — TC vs RTD, transmitters

**Principles.** Thermocouple (Seebeck): types K, N, J, T, E, R/S/B. RTD: Pt100 (IEC 60751), 3- or 4-wire.

**Selection.**
- RTD Pt100 Class A: ±(0.15 + 0.002|t|) °C; wire-wound class A valid −100 to +450 °C, thin-film −30 to +300 °C ([Senmatic IEC 60751](https://www.senmatic.com/sensors/knowledge/iec-60751-sensor-tolerance-classes)). IEC 60751 revised 2008 and 2022 — check which tolerance classes apply ([JUMO](https://www.jumo.group/us/en/about-us/blog/pt100-accuracy-class)).
- Type K class 1: ±1.5 °C (−40…375 °C), ±0.004|t| above **[general knowledge — verify against IEC 60584-1]**; at 0 °C Pt100 class A is ~10× tighter ([boxic RTD vs TC](https://boxic24.com/english/ratgeber/rtd-versus-thermocouple-guide)).
- Rule of thumb: RTD up to ~400–600 °C where accuracy matters; TC above, or for vibration/fast response/skin/furnace ([boxic](https://boxic24.com/english/ratgeber/rtd-versus-thermocouple-guide)).
- Type N preferred to K above ~1000 °C (stability) and K "green rot" in reducing atmospheres **[general knowledge — verify]**.
- MI (mineral-insulated) sheathed sensors, spring-loaded into thermowell.
- Dual-element sensors for BPCS/SIS separation only if SRS allows; separate thermowells for SIS are common company requirement **[general knowledge — verify]**.
- Head-mounted transmitter (sensor matching / Callendar-Van Dusen constants, sensor drift alert, dual input hot backup).

**Datasheet must-haves.** Element type & class, single/dual, wiring (3/4-wire), sheath dia/material, insertion length, thermowell reference, transmitter (range, protocol, Ex, SIL), head/enclosure, cold-junction method, calibration.

**Mistakes.** TC extension wiring wrong type/polarity; 2-wire RTD; type K on long-term 800–1000 °C service; no spring loading; immersion length too short (stem conduction error — typical rule ≥10× sheath dia plus sensitive length) **[general knowledge — verify]**.

**Vendors.** Emerson Rosemount 644/3144P/248, Endress+Hauser iTEMP/Omnigrad/iTHERM, WIKA, Yokogawa YTA, ABB SensyTemp, JUMO, Okazaki, Thermo-Electra, Pyrotech **[general knowledge — verify]**.

---

## Temperature — thermowells (ASME PTC 19.3 TW-2016)

**Purpose.** Pressure boundary + mechanical protection allowing sensor replacement.

**Wake frequency.** PTC 19.3 TW-2010 was a complete rewrite following the Monju sodium-leak thermowell failure; TW-2016 adds clearer definitions, e.g., minimum tip thickness 3.0 mm (§4.1) ([Process Worldwide — TW-2016 changes](https://www.process-worldwide.com/what-has-changed-with-the-2016-revision-of-the-asme-ptc-193-tw-standard-a-589267/)). Passing through in-line resonance (fs/fn ≈ 0.5) is permissible for gaseous media if it is outside continuous operation; flexural fatigue stress limit assessed over 10^11 cycles ([Process Worldwide](https://www.process-worldwide.com/what-has-changed-with-the-2016-revision-of-the-asme-ptc-193-tw-standard-a-589267/)). One blog states the cross-flow criterion as fs < 0.8 fn — unverified ([Fabrico](https://www.fabrico.io/blog/thermowell-design/)). Calculation applies to solid-drilled (bar-stock/forged) wells; not to fabricated (welded tube) wells or unusual shank designs ([WIKA DS IN 00.15](https://cn.shop.wika.com/upload/DS_IN0015_en_co_1353.pdf)).

**Checks (TW-2016).** Frequency limit; dynamic stress; static stress; hydrostatic pressure; at all operating cases (min/norm/max velocity, density, T) **[general knowledge — verify]**.

**Fixes when failing.** Shorten U-length, increase root/tip diameter, tapered stem, remove/avoid velocity collars (shimming is unreliable), helical strakes (outside PTC 19.3 scope; vendor-validated), relocate to lower-velocity line **[general knowledge — verify]**.

**Datasheet must-haves.** Type (flanged, threaded, socket-weld, Van Stone), material, U-length, insertion depth, root/tip diameters, bore, flange rating/face, line size/schedule, fluid velocity & density for wake-frequency, calc report reference, NACE, PMI, hydrotest, test connection.

**Mistakes.** Wake-frequency only done at normal flow; thermowell length chosen for pipe centre in large gas lines (too long); using velocity collar; no calc for compressor discharge/high-velocity steam.

**Vendors.** WIKA, Endress+Hauser, Emerson Rosemount 0091/0096, Okazaki, Thermo-Electra, Pyrotech, Ashcroft **[general knowledge — verify]**.

---

## Temperature — skin / tube-metal TCs

**Use.** Fired heater tube-metal temperature (TMT), reactor shell hot spots, cryogenic tank cool-down, pipeline/heat-trace monitoring.

**Practice.** MI-sheathed TC (type K/N) welded via knife-edge or pad to tube; heat shield over the junction to reduce flame radiation error; expansion loops to accommodate tube growth; route through heater wall with sealed penetrations **[general knowledge — verify — not researched; budget exhausted]**. Infrared pyrometry used to cross-check TMT. Errors of tens of °C are common when shields are omitted **[general knowledge — verify]**.

**Mistakes.** Weld pad causing local hot spot/cracking on alloy tubes; no expansion loop; junction in direct flame view; wrong extension cable.

**Vendors.** Okazaki, Thermo-Electra, Pyrotech/Daily Thermetrics, Gayesco, WIKA **[general knowledge — verify]**.

---

## Analyzers & analyzer shelters

**Typical O&G/LNG analyzers.** Process GC (C1–C6+, BTU/Wobbe, NGL), H2S/total sulphur (lead acetate tape, UV, GC-SCD), moisture/water dew point (TDLAS, ceramic/aluminium oxide, chilled mirror), hydrocarbon dew point, O2 (paramagnetic, zirconia, TDLAS), CO/CO2 (NDIR), Hg (LNG pre-treatment), oil-in-water, pH/conductivity, CEMS for stack emissions **[general knowledge — verify]**.

**Selection criteria.** Measurement purpose (control, quality, custody, safety, environmental) drives cycle time, accuracy and redundancy; sample system lag time (target typically < 60 s total for control) **[general knowledge — verify]**; validation/calibration method (bottled gas, auto-cal); maintenance access.

**Sample systems.** Fast loop with return to lower-pressure point, take-off probe (retractable, wake-frequency checked like a thermowell), pressure reduction at the tap for gas (avoid Joule–Thomson condensation; heated regulators), heat-traced tubing to stay above dew point, filtration/coalescing, stream switching (double block & bleed), vent/drain to flare/closed drain, sample conditioning per API RP 555 / ISO 10715 (natural gas sampling) **[general knowledge — verify]**.

**Shelters (ASH).** Walk-in shelters with HVAC, positive-pressure ventilation (dilution, typically ≥ 6 air changes/h quoted in many specs) **[general knowledge — verify]**, gas detection at shelter inlet & inside (flammable, toxic, O2 depletion for N2/carrier gas), utility panel (instrument air, N2, carrier gas H2/He bottles outside in a rack), Ex classification of interior (IEC 60079-13 pressurised rooms / IEC 61285 analyser house safety) **[general knowledge — verify]**. Location: close to take-off to minimise lag, outside hazardous high-risk zones where possible.

**Datasheet must-haves.** Components and ranges, accuracy/repeatability, cycle time, stream count, sample conditions (P/T/phase/contaminants), sample system P&ID, utilities, outputs (Modbus/OPC/4-20 mA per component), validation, shelter specification, Ex.

**Mistakes.** Sample tap downstream of a point where phase changes; no heat tracing on gas sample above HC dew point; lag time not calculated; analyser outputs used in SIS without a SIL case; bottle storage inside the shelter.

**Vendors.** ABB (NGC8200, PGC5000, AO2000), Emerson Rosemount (700XA/570XA GC, CT5100 QCL), Yokogawa (GC8000, TDLS8000), Siemens (MAXUM II, ULTRAMAT/OXYMAT), Servomex, AMETEK Process Instruments, Mettler-Toledo (pH/DO/conductivity), Endress+Hauser (Liquiline, SpectraSensors TDLAS), Galvanic, Michell/PST, Analytical Systems Keco (sample systems), Intertec / Bertrand / Shelter-builders **[general knowledge — verify]**.

---

## Gas detection — point (catalytic, IR, H2S)

**Catalytic bead (pellistor).** Oxidises combustible gas on a heated bead; responds to most flammables including hydrogen ([ISHN — comparing catalytic and IR](https://www.ishn.com/articles/106148-comparing-catalytic-and-infrared-sensors)). Needs oxygen; can be permanently poisoned by silicones, inhibited (recoverably) by H2S ([Honeywell TN-144](https://automation.honeywell.com/content/dam/his-sandbox/products/gas-and-flame-detection/documents/Technical-Note-144_Handling-LEL-Sensor-Poisons_03-99.pdf)); damaged by over-range > 100 % LEL ([WWD — IR vs catalytic](https://www.wwdmag.com/instrumentation/infrared-vs-catalytic-bead-technology-pros-and-cons)). Fit: hydrogen areas, generator enclosures, battery rooms.

**Point IR.** NDIR absorption at hydrocarbon bands; immune to poisoning, fail-safe (detects beam blockage), works without O2; cannot detect H2 ([ISHN](https://www.ishn.com/articles/106148-comparing-catalytic-and-infrared-sensors)). Calibrated for a reference gas (methane, propane) — cross-sensitivity curves matter for heavier HCs/LNG vapour mixtures **[general knowledge — verify]**. Default choice for O&G process areas.

**Toxic H2S.**
- Electrochemical: good low-ppm response; electrolyte dries in hot/dry climates; slower in extreme cold ([Process Online — EC vs semiconductor](https://www.processonline.com.au/content/instrumentation/article/choices-in-gas-detection-electrochemical-versus-semiconductor-sensors-742785121)).
- MOS: long life in hot/dry climates; slow at < 50 ppm ([MSA white paper](https://assetlibrary.msasafety.com/asset/d361c8b5-4f4c-4062-bd53-2ce915b32a9e/White-Paper-Upgrading-from-MOS-to-Electrochemical-Sensors-for-H2S-Gas-Detection.pdf)); "sleep" effect — sensitivity loss without periodic gas exposure ([Emerson white paper](https://www.emerson.com/documents/automation/white-paper-electrochemical-vs-semiconductor-gas-detection-en-5351906.pdf)). Middle East practice historically MOS; trend toward EC with compensation **[general knowledge — verify]**.
- Typical alarm set points 5/10 ppm (TLV/STEL-based) per company spec **[general knowledge — verify]**.

**Others.** O2 depletion (EC) near N2 systems; CO; NH3; Cl2; H2 dedicated (catalytic or EC/MEMS); acoustic (ultrasonic) leak detectors for high-pressure gas releases independent of wind dilution **[general knowledge — verify]**.

**Selection & installation.** Height by gas density (heavier: ~0.3–0.5 m above grade/deck; lighter: near ceiling/highest point; LNG cold vapour initially heavy) **[general knowledge — verify]**; HVAC inlets (shutting dampers); weather/splash guard, calibration port/remote gassing; 4–20 mA with fault < 4 mA (NAMUR NE43); SIL 2-capable; performance standards EN 60079-29-1 / IEC 60079-29-1 (flammable), EN 45544 (toxic) **[general knowledge — verify]**.

**Alarm levels (flammable).** Commonly 20 % LEL low / 50–60 % LEL high; voting 2ooN for executive action **[general knowledge — verify — project F&G philosophy governs]**.

**Datasheet must-haves.** Target gas & calibration gas, range, alarm set points, technology, response time T90, Ex/IP, SIL, performance cert (60079-29-1), output, accessories (sunshade, splash guard, flow cell, calibration adaptor, remote sensor), mounting height.

**Mistakes.** IR specified for hydrogen; catalytic in area with silicone sealants; H2S EC sensors without humidity/temperature suitability in desert sites; detectors placed per "1 per X m²" grid without mapping; HVAC intake detectors not interlocked to dampers.

**Vendors.** Det-Tronics (PointWatch Eclipse PIRECL, GT3000), MSA (General Monitors S5000, Ultima X5000, Observer-i acoustic), Dräger (Polytron 8000 series, PIR 7000), Honeywell (Searchpoint Optima Plus, Sensepoint XCD), Emerson Rosemount (Net Safety, 928/935, 975), Crowcon, Simtronics, Teledyne/Oldham **[general knowledge — verify]**.

---

## Gas detection — open path

**Principle.** IR beam between transmitter and receiver; measures integrated concentration in LEL·m.

**Typical specs.** Det-Tronics OPECL: 0–5 LEL·m, 5–120 m path ([OPECL spec](https://www.thebigredguide.com/datasheets/det-tronics-opecl-detector/co-290-ga/90-1159-9.1-OPECL.pdf)); successor FlexSight LS2000 with extended range up to 200 m ([Det-Tronics LS2000](https://www.det-tronics.com/products/flexsight-ls2000-optical-infrared-gas-detector/)); Spectrex SafEye 0–5 LEL·m, 0–2 option ([Spectrex](https://spectrex.net/en-us/flame-gas-detectors/gas-detectors/open-path-gas-detector-hydrocarbons)); Honeywell Searchline Excel 0–5 LEL·m to 200 m ([Searchline Excel release note](https://manualedistruzioni.it/honeywell/gas-detector/searchline-excel-open-path/release-note/1n8ph)).

**Fits.** Perimeter/fence lines, along pipe racks, compressor/pump rows, wellhead areas, between modules offshore. **Doesn't:** spaces where beam gets blocked (vehicles, scaffolding, vapour/steam fog), or where concentration at a point is needed.

**Installation.** Rigid mounting (alignment drift from structure deflection/thermal), heated optics where icing, avoid sun into receiver, beam blocked → fault (not alarm) **[general knowledge — verify]**.

**Mistakes.** Path through areas with routine steam plumes; alarm set point in %LEL instead of LEL·m; mounted on handrails/light structures.

---

## Flame detection (UV, UV/IR, IR3)

**Types.** UV (fast, sensitive to arc welding/lightning, blinded by smoke/oil films); UV/IR (both bands — fewer false alarms, still UV-blinded by smoke); multi-spectrum IR (IR3/MSIR — longest range for hydrocarbon fires, good false-alarm immunity); hydrogen flame needs UV or special H2 IR detectors (non-luminous flame, no CO2 band) **[general knowledge — verify]**.

**Ranges (vendor, FM-approved style tests).** Det-Tronics X3301 multispectrum IR: 81 m (265 ft) on-axis for 0.3 × 0.3 m n-heptane pan, while X5200 UV/IR and X2200 UV are listed at ~26 m (85 ft) for the same fire ([Det-Tronics flame detection solutions](https://www.det-tronics.com/Content/Documents/Flame-Detection-Solutions.pdf); [X3301 news](https://www.det-tronics.com/news/news/enhanced-x3301-multispectrum-infrared-flame-detector/)). Earlier X3301 literature showed 210 ft; confirm against the current FM approval ([X3301 specs](https://www.det-tronics.com/Content/Documents/90-1143-10.2-X3301-Specifications.pdf)). Performance standard: FM 3260 / EN 54-10 **[general knowledge — verify]**.

**Selection/installation.** Cone of vision (typically 90° horizontal) and range de-rate off-axis; coverage mapped in 3D; tilt downward to avoid sky/sun; consider obstructions; automatic optical integrity test (oi); avoid mounting where vibration or condensation **[general knowledge — verify]**.

**Mistakes.** UV detectors near welding areas/flare sightline; IR3 specified for hydrogen-only fires; quoting max range for a different fuel/fire size than the design fire; no mapping.

**Vendors.** Det-Tronics (X3301/X3302/X5200/X2200, FlexVu), MSA General Monitors (FL4000H, FL500), Spectrex/Honeywell (SharpEye 40/40), Dräger (Flame 2570/3000), Emerson Rosemount 975 series, Simtronics **[general knowledge — verify]**.

---

## F&G mapping & coverage (ISA-TR84.00.07)

- ISA-TR84.00.07 (2010; revised edition with Annex B on geographic and scenario coverage assessment) gives guidance on evaluating F&G system effectiveness ([Wikipedia ISA 84.00.07](https://en.wikipedia.org/wiki/ISA_84.00.07); [Chemical Processing — 2022 revisions](https://chemicalprocessing.com/articles/2022/fire-and-explosion-protection-take-note-of-revisions-to-tr-84-00-07)).
- **Geographic coverage:** fraction of a zone (at a given elevation) in which the array would detect a fire/gas release, depending only on detector array and obstructions ([Kenexis — Understanding F&G mapping](https://www.kenexis.com/wp-content/uploads/2014/05/UnderstandingFireAndGasMapping.pdf)).
- **Scenario coverage:** fraction of release scenarios (weighted by frequency, size, direction, wind) that would be detected ([Kenexis](https://www.kenexis.com/wp-content/uploads/2014/05/UnderstandingFireAndGasMapping.pdf)); can use dispersion (Phast, CFD) ([CCPS LACPS 2014 worked example](https://proceedings.aiche.org/ccps/conferences/ccps-latin-american-conference-on-process-safety/2014/proceeding/paper/3d-fire-and-gas-detector-coverage-mapping-application-isa-tr840007-worked-example)). Geographic remains the prevailing semi-quantitative practice ([IChemE Hazards 26 paper](https://www.icheme.org/media/11785/hazards-26-paper-48-towards-bespoke-3d-fire-and-gas-mapping-integration-of-risk-based-approach-and-cfd-modelling.pdf)).
- Targets typically by area grade (e.g., 90 % / 80 % / 60 % for high/medium/low risk) — these are common practice/company numbers, not in this research **[general knowledge — verify]**. Gas mapping often uses a design cloud (e.g., 5 m sphere for prescriptive coverage) **[general knowledge — verify]**.
- Effectiveness = coverage × safety availability × mitigation effectiveness; F&G functions can be SIL-rated via IEC 61511 performance targets **[general knowledge — verify]**.
- Review: check mapping was done on the latest 3D model, detector cones are obstructed by real equipment, voting assumptions (1ooN vs 2ooN) align with C&E, and that the mapping report's detector list matches the F&G layout and instrument index.

---

## Control valves

**Body types.**
- Globe (single-seat, cage-guided, balanced plug; angle bodies for flashing/erosive): best throttling, widest trim options (anti-cav, low-noise), high ΔP. Heavier, more costly in large sizes.
- Rotary: segmented ball (V-ball), eccentric plug, high-performance (triple-offset) butterfly, full ball — high capacity, lower cost in large sizes, rangeability high, lower FL (cavitate/choke earlier), lower xT **[general knowledge — verify]**.

**Sizing (ISA-75.01.01 / IEC 60534-2-1).**
- FL (liquid pressure recovery factor) predicts recovery from vena contracta to outlet; choked ΔP uses FL, FF (critical pressure ratio factor) and vapour pressure; the smaller of actual and choked ΔP is used for Cv ([Fisher Catalog 12 section 2](https://www.emerson.com/is/content/emerson/en/final-control/flow-controls/documents/cat12_s2.pdf)). xT is the terminal pressure drop ratio for gas choking and is not strictly related to FL ([Baumann ISA primer ch.5](https://www.isa.org/getmedia/c37b8eb0-dbf9-4cb8-a29a-aac88db297a0/Baumann-ControlValvePrimer_Chapter5.pdf)).
- Opening: size for ~60–80 % open at max flow and not far below ~20 % at min ([Valve Magazine — sizing 101](https://www.valvemagazine.com/articles/size-matters-control-valve-sizing-101)). Check all cases (min/norm/max/start-up/upset).
- Allocate meaningful ΔP to the valve (blog suggests 25–35 % of system dynamic loss — unverified) ([industrialmonitordirect](https://industrialmonitordirect.com/blogs/knowledgebase/control-valve-selection-linear-vs-equal-percentage-characteristics)).

**Characteristic.** Goal is a near-linear *installed* characteristic ([Valve Magazine](https://www.valvemagazine.com/articles/size-matters-control-valve-sizing-101)). Equal % for systems where valve ΔP falls significantly with flow (lots of piping), linear when valve takes most ΔP; Shinskey suggests linear for flow/level/pressure/composition and equal % for temperature ([Control Global — Shinskey](https://controlglobal.com/articles/2015/linear-or-equal-percentage-valves-when-should-i-use-which)); equal % gain increases with opening, linear constant ([Control Global 2006](https://www.controlglobal.com/articles/2006/167)).

**Cavitation & flashing.** Cavitation: P at vena contracta < Pv, recovers above Pv → damage, noise; mitigate with anti-cavitation multistage trim (e.g., CAV4, Masoneilan LO-dB/VRT, CCI DRAG), staging ΔP, hardened trim. Flashing: P2 < Pv → outlet two-phase erosion; mitigate with angle body, hardened/Stellite trim, larger outlet, valve close to vessel **[general knowledge — verify]**. Use vendor σ (cavitation index) or IEC 60534-8-4 (liquid noise) ([IEC 60534-8-4 SIST](https://standards.iteh.ai/catalog/standards/sist/db6d6492-7585-4b8b-8709-dfd303c0874e/sist-en-60534-8-4-2007)).

**Noise.** 85 dBA at 1 m downstream and 1 m from pipe wall is a typical project limit for continuously operating valves; ~90 dBA at 4 m for intermittent atmospheric vent valves is quoted in some specs ([Control & Instrumentation — valve noise](https://www.controlandinstrumentation.com/valves/control-valve-noise.html); [Red-Bag noise spec](https://red-bag.com/specifications/463-bn-sp-k03-design-specification-for-the-limitation-of-control-valve-noise.html)). IEC 60534-8-3 is the prediction method for aerodynamic noise (reference point 1 m downstream / 1 m from pipe) ([Masoneilan Noise Control Handbook](https://dam.bakerhughes.com/m/403871c7a460561b/original/Masoneilan-Noise-Control-Handbook-English.pdf); [DIN EN 60534-8-3](https://din.de/en/wdc-beuth:din21:143694944)). Keep a margin (e.g., ≥3 dBA) below the limit for prediction uncertainty — practice cited in secondary sources **[verify]**. Also check outlet Mach number (gas ≤ ~0.3 typical for globe outlet / ≤0.5–0.7 per vendor) and acoustic-induced vibration (AIV) of downstream piping per Energy Institute guidelines **[general knowledge — verify]**.

**Seat leakage (ANSI/FCI 70-2 / IEC 60534-4).** Class IV: 0.01 % of rated capacity (metal seat) ([Automation Forum](https://automationforum.co/seat-leakage-classification-of-control-valve/)); Class V: 5×10⁻⁴ ml/min water per inch seat dia per psi ΔP (2006) ([Automation Forum](https://automationforum.co/seat-leakage-classification-of-control-valve/); [CFIHOS picklist](https://cfihos.kraken.im/picklists/seat-leakage-class)); Class VI: soft seat, table of bubbles/ml per min vs seat diameter ([SVF leakage classes](https://svf.net/wp-content/uploads/2021/10/ANSI-Leakage-Classes.pdf)). Specify Class V/VI only where needed (cost, wear); for tight shut-off on ESD use an on-off valve per API 598/ISO 5208.

**Actuator sizing.** Spring-diaphragm (most common) or piston; size for max shut-off ΔP (not normal ΔP) plus seat load for leakage class, packing friction, unbalance; at minimum air supply (e.g., 4 barg if header normally 7 barg) **[general knowledge — verify]**; check stroking speed (boosters/QEV for anti-surge — typically < 2 s full stroke required for anti-surge valves) **[general knowledge — verify]**.

**Fail action.** FC/FO/FL (fail-last, with lock-up) set by process safety (HAZOP); state on P&ID and datasheet; spring return preferred; double-acting needs volume tank if fail position required.

**Positioner & accessories.** Digital positioner (HART/FF), with diagnostics; limit switches/position transmitter; SOV for trip of control valve (if used in SIF — needs SIL capability and failure-mode analysis); air filter regulator; volume booster; lock-up valve.

**Datasheet must-haves (ISA-75 / IEC 60534-7 style).** Fluid, case table (min/norm/max/shut-off with P1, ΔP, T, flow, ρ/MW, Pv, Pc, viscosity, k), calculated Cv & % opening, FL/xT/Fd, noise prediction (dBA), outlet velocity/Mach, body type/size/rating/end connection, trim type & characteristic, rated Cv, seat leakage class, body/trim/seat/packing materials, packing type (low-E ISO 15848-1 fugitive emissions), bonnet (extended for cryo/hot), actuator type/size/spring range/air supply min/max, fail action, stroke time, handwheel, positioner/protocol, accessories, SIL, NACE, Ex, painting, tests (hydro, seat leak, ISO 15848 FE).

**Common mistakes.** Line-sized valve; size from normal flow only; no shut-off ΔP case for actuator; noise checked only at max case; flashing service in globe straight-through body with soft carbon steel; Class VI requested on high-temperature service; fail action inconsistent between P&ID, C&E and datasheet; positioner protocol not matching DCS I/O.

**Vendors.** Emerson Fisher (GX, EZ, ET, Vee-Ball, Control-Disk; DVC6200), Baker Hughes Masoneilan (21000, 41005, Camflex; SVI II/SVI 1000), Flowserve Valtek (Mark One, MaxFlo; Logix 3800), Samson (3241, 3251; TROVIS 3730), IMI CCI (DRAG, severe service), IMI Orton/Truflo, Valmet/Neles (Finetrol, R-series rotary, ND9000), Koso (Kent Introl), Metso-style, Yokogawa (DCS only), Copes-Vulcan (SPX) **[general knowledge — verify]**.

---

## On-off & ESD valves (ZV/SDV/BDV), SOVs

**Naming.** ZV/XV = remotely operated on-off; SDV/ESDV = shutdown; BDV = blowdown (fail-open to flare); EIV = emergency isolation; HIPPS valves **[general knowledge — verify — tag convention varies by client]**.

**Valve types.** Trunnion-mounted ball (API 6D, ISO 17292) most common; metal-seated for dirty/high-temp or high-cycle; soft-seated (PTFE/PEEK/Devlon) for tight shut-off; triple-offset butterfly for large low-pressure; axial (Mokveld) for HIPPS/fast stroke **[general knowledge — verify]**.

**Tight shut-off.** Leakage per API 598 / ISO 5208 Rate A (zero visible) typical requirement for ESDVs; DBB/DIB capability per API 6D **[general knowledge — verify]**. Separate leakage testing in SRS for SIF credit (allowable leak rate after closure).

**Fire-safe.** API 607 (quarter-turn & non-metallic-seated valves) and API 6FA (API 6A/6D valves) both use 30-minute fire exposure; flame temperatures reported as ~750–1000 °C ([Projectmaterials — API 607 vs 6FA](https://www.blog.projectmaterials.com/quick-answers/epc/api-607-vs-api-6fa/)); ISO 10497 is the ISO counterpart ([Valve Magazine — fire testing](https://www.valvemagazine.com/articles/the-past-present-and-future-of-fire-testing)). Actuator/accessories fire protection (passive fire protection jacket, UL 1709 / ISO 22899) for ESDVs that must operate during fire **[general knowledge — verify]**.

**Closure time.** API RP 14C (7th ed.) is quoted as requiring total shutdown response of any safety device within 45 s — a system limit, not a valve stroke time ([Eng-Tips thread](https://eng-tips.com/threads/esdv-closure-times-to-prevent-surge.373109)). "1 s per inch of valve size" is an informal screening rule ([Eng-Tips](https://www.eng-tips.com/threads/esdv-closing-speed.286856)). Large valves stroke slower under pressure than in shop test; set closure time from process safety time and **surge analysis** (too fast → water hammer) ([Eng-Tips](https://eng-tips.com/threads/esdv-closure-times-to-prevent-surge.373109)). BDV opening time set by depressurisation study (API 521: e.g., to 50 % design pressure / 6.9 barg in 15 min) **[general knowledge — verify]**.

**Actuators.** Spring-return pneumatic (scotch-yoke or rack & pinion) or hydraulic; size for MAST (max allowable stem torque) and breakaway torque × safety factor (often 1.25–1.5 at minimum supply) **[general knowledge — verify]**; spring end torque sized for closing without air. Fail-safe via spring; for BDV fail-open. Volume tank for double-acting fail position (sized for e.g. 3 strokes) **[general knowledge — verify]**.

**SOVs & redundancy.** De-energise-to-trip, 3-way, direct-acting or pilot, low-power for IS; SIL-certified. Configurations: 1oo1; 1oo2 (two SOVs in series venting — either trips; higher safety, more spurious trips); 2oo2 (parallel — both must trip; better availability); 2oo3 for both ([Samson PST/SOV document](https://france.samsongroup.com/document/w02390en.pdf)). Exhaust capacity sized for closure time; quick exhaust valves on large actuators. Manual reset (latching) where restart must be deliberate.

**Partial stroke testing.** PST improves PFDavg and/or extends proof test interval ([Wikipedia — PST](https://www.wikipedia.com/wiki/Partial_stroke_testing)); claimed diagnostic coverage values ~60–80 %, ~70 % commonly assumed but must be justified per application ([Emerson — credit for PST](https://www.emersonautomationexperts.com/2011/safety/credit_for_part/)); PST does not prove tight shut-off — full stroke proof test still required ([Emerson — positioners & PST](https://www.emersonautomationexperts.com/?p=44389)). PFDavg ≈ DC·λD·TI_PST/2 + (1−DC)·λD·TI_FST/2 ([Emerson](https://www.emersonautomationexperts.com/?p=44389)). PST implemented via SIL-rated smart positioner/valve controller (e.g., Fisher DVC6200 SIS, Neles ValvGuard, Masoneilan SVI II ESD) or SOV pulse-test **[general knowledge — verify]**.

**Datasheet must-haves.** Valve type/size/rating/bore, shut-off ΔP, leakage class/standard, fire-safe cert, materials (NACE), seat type, actuator type & sizing (torques, SF, min supply), fail action, stroke times (open/close), SOV make/model/voting/SIL, limit switches (type, Ex, SIL), PST device, local control panel, manual override, PFP, SIL certification of assembly (FMEDA), fugitive emission class.

**Common mistakes.** Using a control valve as SDV; actuator sized at normal air pressure; closure time specified without surge check; limit switches used as SIF input without SIL capability; SOV exhaust port undersized; BDV restriction orifice missing; fail position for BDV specified FC.

**Vendors.** Valves: Cameron (Baker Hughes / SLB), Emerson (KTM, Vanessa triple-offset), Valmet/Neles, Flowserve (Valbart, NAF), Petrolvalves, Perar, PBV, Mokveld (axial), Tormene, Adams. Actuators: Emerson Bettis, Rotork (GP/CP/RC), Biffi, Valmet, Eltav, Prisma **[general knowledge — verify]**. SOVs: ASCO (Emerson), IMI Norgren/Herion/Maxseal, Parker, Bifold, Rotork Midland-ACS **[general knowledge — verify]**.

---

## Motor-operated valves (MOVs)

**Types.** Multi-turn (gate, globe, sluice; output via thrust/torque bases), part-turn (ball, butterfly, plug, via worm gearbox), linear. Intelligent non-intrusive actuators with integral starter, local controls, Bluetooth setup, fieldbus/4–20 mA **[general knowledge — verify]**.

**Duty classes (EN 15714-2).** Class A on-off, B inching/positioning, C modulating, D continuous modulating ([Bernard Controls actuator guide](https://www.bernardcontrols.com/ressources/files/2/4584,A300_03US_Electric-actuator-guide_U.pdf)). Starts-per-hour figures (e.g., up to 1,200 starts/h for modulating S4 duties) are manufacturer-specific, not from the standard text ([Bernard classification](https://www.bernardcontrols.com/en/our-solutions/classification-gps-actuator)). EN 15714-2:2009 superseded in 2021 per AFNOR listing ([AFNOR](https://www.boutique.afnor.org/en-gb/standard/nf-en-157142/industrial-valves-actuators-part-2-electric-actuators-for-industrial-valves/fa143236/34530)).

**Torque/thrust sizing.** Valve vendor provides breakaway (BTO/BTC), run and end torques at max ΔP; apply safety factor (commonly 1.25–1.5 or per client) at minimum voltage (e.g., −10 % supply) and check against valve MAST; select operating time (stroke speed, e.g., 10–12 in/min for gate valves) based on process and surge **[general knowledge — verify — not researched; search budget exhausted]**.

**ESD MOVs.** If an MOV is part of an ESD/SIF: SIL-rated actuator (e.g., Rotork IQ3 SIL, AUMA SA..-SIL) with dedicated ESD input overriding local/remote control and (optionally) thermostat/torque switch bypass; power supply from UPS/essential board; fire protection of actuator & cables (fire-resistant cable IEC 60331); fail-as-is is the normal MOV behaviour — fail-safe requires stored-energy (spring) actuators **[general knowledge — verify]**.

**Datasheet must-haves.** Valve type/size, torque/thrust data, MAST, operating time, duty class & starts/h, motor power/voltage/phase/frequency, starter type, local controls, control interface (hardwired/Modbus/PROFIBUS/FF/HART), ESD function, position feedback, enclosure IP68 & Ex, handwheel, temperature, SIL, cable entries, gearbox.

**Common mistakes.** Sizing on run torque; no MAST check; fail-safe assumed for MOV; modulating duty with on-off actuator; no ESD override philosophy; voltage drop on long cables at starting.

**Vendors.** Rotork (IQ3/IQT3/CK), AUMA (SA/SQ + AC.2 controls), Emerson Bettis/EIM (TEC2), Bernard Controls, Flowserve Limitorque (MX/QX), Biffi, SIPOS (now AUMA), Schiebel **[general knowledge — verify]**.

---

## Pressure safety valves (PSVs)

**Types.** Conventional spring-loaded, balanced bellows, pilot-operated (pop/modulating), rupture discs (alone or in combination). Thermal relief valves (TRVs, ¾×1") for blocked-in liquid.

**Sizing (API 520 Part I / ASME VIII / ISO 4126).** Required orifice area for governing scenario (blocked outlet, fire, control valve failure, tube rupture, etc. per API 521); select API 526 standard orifice letters (D–T) **[general knowledge — verify]**; Kd/Kb/Kw/Kc corrections; set pressure ≤ MAWP; accumulation 10 % (single), 16 % (multiple), 21 % (fire) **[general knowledge — verify — ASME VIII]**.

**Inlet pressure loss.** The non-recoverable inlet line loss should not exceed 3 % of set pressure (API 520 Part II; also ASME VIII Div. 1 Appendix M); API 520 Pt II allows exceeding 3 % if an engineering analysis shows stable operation, and OSHA cites the 3 % rule as RAGAGEP ([Process Engineering Associates — 3 % rule](https://processengr.com/?p=4225)). Remedy if exceeded: larger inlet line, remote-sensed pilot, adjust blowdown **[general knowledge — verify]**.

**Back pressure.** Conventional valves: built-up back pressure ≤ 10 % of set (at 10 % overpressure) commonly cited; superimposed variable back pressure → bellows or pilot ([Projectmaterials — safety valves](https://blog.projectmaterials.com/valves/safety-valve-asme-api/)). Balanced bellows tolerate total back pressure up to ~30–50 % of set with capacity correction Kb (manufacturer-dependent) **[verify against vendor Kb curves]**. Pilot valves operate closer to set (high operating/set ratio, e.g., ~95 %+) and tolerate high back pressure, but are less suited to dirty/polymerising service unless filtered/purged **[general knowledge — verify]**.

**Installation.** PSV at high point, inlet line short and free-draining, outlet to closed flare header self-draining (no pockets), CSO/LO isolation valves with full bore per philosophy, spare PSV (installed spare with interlocked/three-way changeover) **[general knowledge — verify]**. Reaction forces for open discharge (API 520 Pt II).

**Datasheet must-haves (API 526/520 Annex).** Tag/scenario, fluid & state, required capacity, MW/Z/k, set pressure, CDTP, back pressure (superimposed constant/variable, built-up), overpressure, operating P/T, relieving T, orifice letter & area (calc/selected), inlet/outlet size & rating, body/bonnet/spring/bellows/trim materials, cap/lever, test gag, nozzle type, Kd, NACE, code stamp (ASME UV), noise, inlet ΔP %, rupture disc combination, PSV certification.

**Common mistakes.** Inlet loss not calculated for remote PSVs; bellows vent plugged/not routed to safe location; conventional valve on header with variable superimposed back pressure; orifice selected below required; two-phase relief sized as liquid only; CDTP not corrected for back pressure/temperature.

**Vendors.** Emerson (Anderson Greenwood, Crosby), Curtiss-Wright Farris, Baker Hughes Consolidated, LESER, Taylor Valve, Mercer, Spirax Sarco (utility), Fike / BS&B / Rembe (rupture discs) **[general knowledge — verify]**.

---
