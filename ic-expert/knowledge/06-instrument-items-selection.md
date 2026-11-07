# 06 — Instrument Items: Selection, Sizing, Installation, Datasheets, Pitfalls (+ Other Major Vendors)

## How to use this file

- **Purpose.** This is the item-by-item engineering reference for the I&C expert chatbot. When an engineer pastes a spec, datasheet, instrument index line or P&ID extract and asks "is this the right instrument / what's missing / what should the datasheet say", retrieve the matching `## <item>` section and reason from it.
- **Structure of every item section.** Principle · Where it fits / doesn't · Key selection criteria · Typical accuracy / turndown / limits · Installation & hook-up · Datasheet must-have fields (ISA-20 / IEC 60770 / IEC 61987 style) · Common spec/review mistakes · Typical vendors/models.
- **Source discipline.** Every concrete number is followed by a link to where it was found. Numbers from vendor datasheets are *vendor reference-condition claims*, not installed performance. Statements marked **[general knowledge — verify]** are widely used engineering practice the author could not confirm against a source during this research; quote them as "typical practice", never as a code requirement. Standards are often paywalled; several figures here come from secondary summaries of the standard and are labelled accordingly — when a project decision hangs on the number, check the current edition of the standard itself.
- **Project specs override.** Company/project specs (Shell DEP, ExxonMobil GP, Aramco SAES, TotalEnergies GS, NORSOK I-001/I-002, etc.) frequently tighten or change these generic rules. Always ask which applies.
- **Related files.** Standards overviews, SIS/IEC 61511, hazardous area, and the "big" automation vendors (Emerson, Honeywell, Yokogawa, etc.) are covered in other files of this knowledge base; this file only covers them where needed for an item and lists the *other* vendors in `## Other vendors`.
- **Research limitation.** The first research pass ran out of search budget before vendor flagship models, MOV torque sizing, PSV pilot details, thermowell frequency limits and skin-TC practice were covered. A second pass (Nov 2026) added sources for MOV duty and torque, PSV orifice/accumulation/back-pressure, TW-2016 limits, F&G set points and coverage, instrument air, cabinets, glands, fieldbus, wireless, HIPPS, wet gas, radiometric licensing and most vendor lines. Many of these are still secondary sources (vendor pages, forums, published specs), and the text says so. Items still unsourced keep their flag.

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

**Wet-gas and multiphase metering (basics).** The Lockhart–Martinelli parameter X relates liquid to gas loading through superficial velocities and densities, and GVF = 1/[1 + X(ρg/ρl)^½] ([OGJ — wet-gas meter designs](https://www.ogj.com/general-interest/companies/article/17239431/meter-designs-provide-wetgas-measurement-alternatives)). Wet gas is usually taken as GVF above about 90–95 % ([OGJ](https://www.ogj.com/general-interest/companies/article/17239431/meter-designs-provide-wetgas-measurement-alternatives)). Multiphase terminology traces to the NFOGM *Handbook of Multiphase Metering* (1995) ([Alaska DOC metering principles](https://www.commerce.alaska.gov/web/Portals/18/Pub/MeterPrinciples113004.pdf)). ISO/TR 12748:2015 covers wet-gas flow measurement and its uncertainty ([ISO/TR 12748 listing](https://iteh.eu/catalog/standards/iso/91df86a9-d46d-4926-b341-5117a600021c/iso-tr-12748-2015)), and ASME MFC-19G covers wet-gas metering ([ASME MFC-19G copy](https://www.scribd.com/document/616377831/MFC-19G-Edtn-2008)). A venturi in wet gas over-reads (the "over-reading" correction) and needs a wet-gas correlation ([NEL — venturi meters in wet gas, NFOGM 2003](https://nfogm.no/wp-content/uploads/2019/02/2003-04-Venturi-Meters-in-Wet-Gas-Flow-Stewart-National-Engineering-Laboratory.pdf)). Claimed multiphase-meter uncertainties against test separators (5–10 %, some claims to 2 %) are vendor/secondary figures and not verified here **[verify]**.

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

**Accuracy.** Micro Motion ELITE: ±0.05 % liquid mass, ±0.35 % gas mass (catalogue) ([Micro Motion catalogue](https://pdf.directindustry.com/pdf/micro-motion/superior-gas-flow-density-measurement/14564-65076.html)). Emerson quotes AGA Report No. 11 gas spec as ±0.7 % and claims water-calibrated meters transfer to gas ([Micro Motion piecewise-linearisation brochure](https://s1-live.emerson.com/documents/automation/brochure-piecewise-linearization-to-enhance-calibration-for-gas-applications-micro-motion-en-4857948.pdf)). Do not quote liquid accuracy for gas service. **Conflict resolved (model-dependent):** Emerson's ELITE product data sheet and technical overview give **±0.25 % of rate** gas mass accuracy for standard ELITE/CMF meters ([Micro Motion ELITE PDS](https://s1-live.emerson.com/documents/automation/product-data-sheet-micro-motion-elite-coriolis-flow-density-meters-en-66748.pdf); [Micro Motion technical overview](https://emerson.com/documents/automation/product-data-sheet-micro-motion-technical-overview-specification-summary-en-66168.pdf)), while high-capacity models are listed at **±0.35 % of rate** for gas ([Micro Motion high-capacity brochure](https://d1-auth.emerson.com/documents/automation/brochure-high-capacity-coriolis-micro-motion-en-64962.pdf)). The older catalogue's ±0.35 % figure above therefore reflects an older or larger model. Quote the figure for the exact model code.

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

**Accuracy / turndown.** Rosemount 8800: ±0.65 % of rate liquids, ±1 % gas/steam (uncompensated), 38:1 turndown claimed on one catalogue page ([Emerson 8800 catalogue](https://emerson.com/en-us/catalog/rosemount-8800-vortex)); another Emerson flyer states 15:1 ([Emerson 8800 Quad flyer](https://d1-live.emerson.com/documents/automation/flyer-rosemounttm-8800-quad-vortex-flow-meter-en-7073954.pdf)) — turndown is application-dependent. **Conflict resolved (variant-dependent):** distributor listings of Emerson data give 38:1 for the standard and CriticalProcess 8800 variants and 15:1 for the Quad vortex ([NECI 8800 listing](https://neci.com/products/measurement-instrumentation/flow/vortex/rosemount-8800-criticalprocess-vortex-flow-meters/); [Experitec 8800 Quad listing](https://experitec.com/solutions/measurement-instrumentation/flow/vortex/rosemount-8800-quad-vortex-flow-meter/)). Achievable turndown on a given duty is still limited by minimum Re and velocity.

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

**Frequency choice.** Beam angle depends on frequency and antenna size: an 80 mm antenna gives ~3° at 80 GHz vs ~10° at 26 GHz ([VEGA blog](https://www.vega.com/en/company/blog/2017/good-focusing-delivers-security)); narrower beam avoids agitators, heating coils, nozzle and wall buildup; 80 GHz offers ~120 dB dynamic range vs ~96 dB ([Control Global — 80 GHz](https://www.controlglobal.com/measure/level/article/11318576/liquid-radar-level-moves-up-to-80-ghz)). Low frequency (6 GHz) still has a role in heavy vapour/condensation and foam **[general knowledge — verify]**. VEGA's VEGAPULS 6X positions itself as one platform for 80/26/6 GHz ([VEGA blog](https://www.vega.com/en/company/blog/2017/good-focusing-delivers-security)). VEGA says the 6X replaces earlier per-frequency models (e.g., VEGAPULS 64/69), works on liquids and bulk solids, covers ranges up to 120 m, has a SIL option that can be switched off, and has IEC 62443-4-2 IT security ([VEGA radar overview](https://vega.com/en-us/radar); [VEGAPULS 6X product page](https://vega.com/en-ca/products/product-catalog/level/radar/vegapuls-6x)).

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

**Licensing.** Sources in nuclear gauges normally fall into IAEA Category 3 or 4 of the five-category scheme (RS-G-1.9). Category 4 sources could cause temporary injury only after mishandling over many weeks, which is unlikely ([IAEA SSG-58 page](https://www.iaea.org/node/90542); [SAHPRA guideline on industrial gauges](https://sahpra.org.za/wp-content/uploads/2024/02/SAHPGL-RDN-RN-08_v2-Guideline-for-the-Safe-Use-of-Industrial-Gauges-Containing-Radioactive-Sources.pdf)). IAEA SSG-58, *Radiation Safety in the Use of Nuclear Gauges*, covers safety assessment, radiation protection programmes and training ([IAEA](https://www.iaea.org/node/90542)). In the US a gauge user needs an NRC or Agreement State licence, and fixed industrial gauges (level, density) typically use Cs-137 ([NRC — industrial gauges](https://www.nrc.gov/materials/miau/industrial.html); [NRC glossary — source categories](https://www.nrc.gov/reading-rm/basic-ref/glossary/category-of-radioactive-sources.html)). One state guide notes that only the source and source holder (shutter, shielding) are subject to licensing, not the detector ([Florida Reg Guide 1.2](https://www.floridahealth.gov/environmental-health/radiation-control/radmat/Reg_Guide_1-2_R2_FG_2-15-08.pdf)). Outside the US the national regulator applies; check import, transport and radiation-safety-officer requirements early.

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

**Frequency-ratio limit and Scruton number.** Secondary sources describe the TW-2016 rule as follows. When the Scruton number N_Sc > 2.5, fluid damping suppresses in-line resonance, so operation is allowed up to fs/fn < 0.8 ([thermowell calculator citing TW-2016](https://designcalculators.netlify.app/thermowellwakefreq)). A WIKA calculation printout shows a "ratio limit 0.8" alongside a Scruton number of 2.89 ([WIKA wake-frequency white paper](https://www.wika.com/media/Others/EN-US/wp017_thermowell_wakefrequency_en_us.pdf)). For low-Scruton fluids (typically liquids, N_Sc < 2.5), the well must stay below the in-line resonance band. One field case study uses a lock-in zone of 0.4 fn < fs < 0.6 fn ([Mangan helical thermowell case study](https://manganinc.com/wp-content/uploads/2024/08/Helical-Case-Study-s.pdf)). The exact low-Scruton limit (commonly quoted as fs/fn < 0.4) was not confirmed against the standard text **[verify in PTC 19.3 TW-2016 §6]**.

**Checks (TW-2016).** Frequency limit; dynamic stress; static stress; hydrostatic pressure; at all operating cases (min/norm/max velocity, density, T) **[general knowledge — verify]**.

**Fixes when failing.** Shortening is described as the most effective fix and the method recommended by PTC 19.3 TW-2016. Increasing root/tip diameter (within nozzle limits) and velocity collars are the other options ([Tempsens — TW-2016 design criteria](https://tempsens.com/blog/design-criteria-of-thermowell-dimensions-asme-ptc-19-3-2016/)).
- **Velocity collars** are outside the scope of TW-2016. They give rigid support only with an interference fit to the nozzle, which is hard to achieve and expensive to install ([Tempsens](https://tempsens.com/blog/design-criteria-of-thermowell-dimensions-asme-ptc-19-3-2016/); [WIKA ScrutonWell datasheet](https://kz.wika.com/upload/DS_SP0516_en_co_66463.pdf)). Many operators and EPCs therefore refuse collars. Whether a given client accepts them is a project-spec matter, and no client document was found here **[verify against client spec]**.
- **Helical strakes** (e.g., WIKA ScrutonWell): WIKA claims >90 % reduction in oscillation amplitude, with only the static calculation done per the standard ([WIKA ScrutonWell datasheet](https://kz.wika.com/upload/DS_SP0516_en_co_66463.pdf); [WIKA NEL endurance tests](https://blog.wika.com/us/products/temperature-products/endurance-tests-scrutonwell-design-vortex-breaker/)). An independent case study found that a helical well's higher natural frequency moved it into a different lock-in band at higher flow, so strakes are not a blanket fix ([Mangan case study](https://manganinc.com/wp-content/uploads/2024/08/Helical-Case-Study-s.pdf)).
- Relocating to a lower-velocity line is also an option **[general knowledge — verify]**.

**Datasheet must-haves.** Type (flanged, threaded, socket-weld, Van Stone), material, U-length, insertion depth, root/tip diameters, bore, flange rating/face, line size/schedule, fluid velocity & density for wake-frequency, calc report reference, NACE, PMI, hydrotest, test connection.

**Mistakes.** Wake-frequency only done at normal flow; thermowell length chosen for pipe centre in large gas lines (too long); using velocity collar; no calc for compressor discharge/high-velocity steam.

**Vendors.** WIKA, Endress+Hauser, Emerson Rosemount 0091/0096, Okazaki, Thermo-Electra, Pyrotech, Ashcroft **[general knowledge — verify]**.

---

## Temperature — skin / tube-metal TCs

**Use.** Fired heater tube-metal temperature (TMT), reactor shell hot spots, cryogenic tank cool-down, pipeline/heat-trace monitoring.

**Practice.**
- Thermocouples are attached to the tube with stainless-steel weld pads or attachment blocks ([Control Global — Ask the experts](https://www.controlglobal.com/articles/2007/040)).
- Welds on knife-edge pads can penetrate the pad and damage the junction, and flat pads can leave air gaps that distort the reading ([US patent 3874239 — surface thermocouple](https://patents.google.com/patent/US3874239A/en)).
- A radiation shield over the junction should be insulated on the inside and not welded to the tube, so that it does not act as a fin ([US patent 5172979 — heater tube skin thermocouple](https://patents.justia.com/patent/5172979)).
- UOP (AFPM Q&A) says knife-edge skin TCs are useful for trends and step changes but are not reliably accurate indicators of the true tube-metal temperature. A shield can also create a local hot spot that causes carburisation and metal loss ([AFPM Q&A — monitoring heater tubes](https://www.afpm.org/data-reports/technical-papers/qa-search/question-7-how-do-you-monitor-and-protect-heater-tubes)).
- MI-sheathed type K/N cable, expansion loops for tube growth and sealed heater-wall penetrations are typical practice **[general knowledge — verify]**. Infrared pyrometry is used to cross-check TMT.

**Mistakes.** Weld pad causing local hot spot/cracking on alloy tubes; no expansion loop; junction in direct flame view; wrong extension cable.

**Vendors.** Okazaki, Thermo-Electra, Pyrotech/Daily Thermetrics, Gayesco, WIKA **[general knowledge — verify]**.

---

## Analyzers & analyzer shelters

**Typical O&G/LNG analyzers.** Process GC (C1–C6+, BTU/Wobbe, NGL), H2S/total sulphur (lead acetate tape, UV, GC-SCD), moisture/water dew point (TDLAS, ceramic/aluminium oxide, chilled mirror), hydrocarbon dew point, O2 (paramagnetic, zirconia, TDLAS), CO/CO2 (NDIR), Hg (LNG pre-treatment), oil-in-water, pH/conductivity, CEMS for stack emissions **[general knowledge — verify]**.

**Selection criteria.** Measurement purpose (control, quality, custody, safety, environmental) drives cycle time, accuracy and redundancy; sample system lag time (target typically < 60 s total for control) **[general knowledge — verify]**; validation/calibration method (bottled gas, auto-cal); maintenance access.

**Sample systems.** Fast loop with return to lower-pressure point, take-off probe (retractable, wake-frequency checked like a thermowell), pressure reduction at the tap for gas (avoid Joule–Thomson condensation; heated regulators), heat-traced tubing to stay above dew point, filtration/coalescing, stream switching (double block & bleed), vent/drain to flare/closed drain, sample conditioning per API RP 555 / ISO 10715 (natural gas sampling) **[general knowledge — verify]**.

**Shelters (ASH).** Walk-in shelters with HVAC, positive-pressure ventilation (dilution, typically ≥ 6 air changes/h quoted in many specs) **[general knowledge — verify]**, gas detection at shelter inlet & inside (flammable, toxic, O2 depletion for N2/carrier gas), utility panel (instrument air, N2, carrier gas H2/He bottles outside in a rack), Ex classification of interior (IEC 60079-13 pressurised rooms / IEC 61285 analyser house safety). IEC 61285:2015 sets the physical requirements for safe operation of analysers in an analyser house against fire, explosion, toxic and asphyxiant hazards ([AFNOR IEC 61285:2015](https://www.boutique.afnor.org/en-gb/standard/iec-612852015/industrialprocess-control-safety-of-analyser-houses/xs126756/246175)). Its table of contents puts ventilation in §5.5.6, and ventilation for explosion hazards originating inside the house in §6.4.2 ([IEC 61285 ed.3 preview](https://www.vde-verlag.de/iec-normen/preview-pdf/info_iec61285{ed3.0}b.pdf)). A 4th edition was at enquiry stage as prEN IEC 61285:2024 ([iTeh prEN IEC 61285:2024](https://standards.iteh.ai/catalog/standards/clc/d53220a4-b5cc-4522-ba2f-02c78d9e0583/pren-iec-61285-2024)). IEC TR 60079-16 covers artificial ventilation of analyser houses ([IEC webstore TR 60079-16](https://webstore.iec.ch/publication/630)). The numerical air-change rate (the "≥ 6 ACH" above) was not confirmed in either document **[verify]**. Location: close to take-off to minimise lag, outside hazardous high-risk zones where possible.

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
- Alarm set points: UK HSE offshore guidance uses 5 ppm H2S as its example detector level ([HSE offshore info sheet 6/2009](https://hse.gov.uk/offshore/infosheets/is6-2009.htm)). One vendor default table lists 10 / 20 ppm, but it does not name a standard ([Industrial Scientific default alarm settings](https://www.indsci.com/hubfs/Tip%20Sheets/default-instrument-alarm-settings.pdf)). MSA says alarm levels vary with national or corporate regulations ([MSA ALTAIR alarm thresholds](https://docs.msasafety.com/altair4xr/en-us/ALTAIR%204X%20R%20OPM%2010175896/Factory_set_Alarm_Thresh.htm)). Treat 5/10 ppm or 10/20 ppm as company-philosophy choices; neither pair was found as a code requirement.

**Others.** O2 depletion (EC) near N2 systems; CO; NH3; Cl2; H2 dedicated (catalytic or EC/MEMS); acoustic (ultrasonic) leak detectors for high-pressure gas releases independent of wind dilution **[general knowledge — verify]**.

**Selection & installation.** Height by gas density (heavier: ~0.3–0.5 m above grade/deck; lighter: near ceiling/highest point; LNG cold vapour initially heavy) **[general knowledge — verify]**; HVAC inlets (shutting dampers); weather/splash guard, calibration port/remote gassing; 4–20 mA with fault < 4 mA (NAMUR NE43); SIL 2-capable; performance standards EN 60079-29-1 / IEC 60079-29-1 (flammable), EN 45544 (toxic) **[general knowledge — verify]**.

**Alarm levels (flammable).** UK HSE says offshore gas detection generally alarms and acts at 20 % and 50–60 % LEL. Some dutyholders use 10 % and 25 % LEL for more sensitive detection, which HSE encourages ([HSE offshore info sheet 6/2009](https://hse.gov.uk/offshore/infosheets/is6-2009.htm)). Voting (e.g., 2ooN for executive action) comes from the project F&G philosophy and C&E **[general knowledge — verify]**.

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

**Ranges (vendor, FM-approved style tests).** Det-Tronics X3301 multispectrum IR: 81 m (265 ft) on-axis for 0.3 × 0.3 m n-heptane pan, while X5200 UV/IR and X2200 UV are listed at ~26 m (85 ft) for the same fire ([Det-Tronics flame detection solutions](https://www.det-tronics.com/Content/Documents/Flame-Detection-Solutions.pdf); [X3301 news](https://www.det-tronics.com/news/news/enhanced-x3301-multispectrum-infrared-flame-detector/)). Earlier X3301 literature showed 210 ft; confirm against the current FM approval ([X3301 specs](https://www.det-tronics.com/Content/Documents/90-1143-10.2-X3301-Specifications.pdf)). **Conflict status:** the 210 ft (64 m) on-axis / 150 ft (45.7 m) off-axis n-heptane figures come from an older spec sheet ([X3301 spec sheet 90-1218](https://www.det-tronics.com/content/documents/90-1218-(X3301).pdf)). The 265 ft (81 m) figure is in the later "enhanced X3301" literature and the current solutions brochure ([Det-Tronics flame detection solutions 2026](https://www.det-tronics.com/wp-content/uploads/sites/8/2026/03/Flame-Detection-Solutions.pdf)). Both are for a 0.3 × 0.3 m n-heptane fire. Methane range is shorter, quoted at up to 125 ft on one spec sheet ([X3301 spec sheet 90-1218-1.1](https://www.det-tronics.com/Content/documents/90-1218-1.1-x3301-flame-detector-spec-sheet.pdf)). Quote the figure from the datasheet revision and FM approval that match the supplied hardware. Performance standard: FM 3260 / EN 54-10 **[general knowledge — verify]**.

**Selection/installation.** Cone of vision: the X3301, for example, specifies a 90° horizontal × 75° vertical field of view, with at least 70 % of the on-axis detection distance at the edge of the field ([X3301 specifications](https://www.det-tronics.com/Content/Documents/90-1143-10.2-X3301-Specifications.pdf)). Map the de-rated cone in 3D, not the on-axis range. Tilting downward to avoid sky/sun, allowing for obstructions, using an automatic optical integrity test (oi) and avoiding mounts with vibration or condensation are typical practice **[general knowledge — verify]**.

**Mistakes.** UV detectors near welding areas/flare sightline; IR3 specified for hydrogen-only fires; quoting max range for a different fuel/fire size than the design fire; no mapping.

**Vendors.** Det-Tronics (X3301/X3302/X5200/X2200, FlexVu), MSA General Monitors (FL4000H, FL500), Spectrex/Honeywell (SharpEye 40/40), Dräger (Flame 2570/3000), Emerson Rosemount 975 series, Simtronics **[general knowledge — verify]**.

---

## F&G mapping & coverage (ISA-TR84.00.07)

- ISA-TR84.00.07 (2010; revised edition with Annex B on geographic and scenario coverage assessment) gives guidance on evaluating F&G system effectiveness ([Wikipedia ISA 84.00.07](https://en.wikipedia.org/wiki/ISA_84.00.07); [Chemical Processing — 2022 revisions](https://chemicalprocessing.com/articles/2022/fire-and-explosion-protection-take-note-of-revisions-to-tr-84-00-07)).
- **Geographic coverage:** fraction of a zone (at a given elevation) in which the array would detect a fire/gas release, depending only on detector array and obstructions ([Kenexis — Understanding F&G mapping](https://www.kenexis.com/wp-content/uploads/2014/05/UnderstandingFireAndGasMapping.pdf)).
- **Scenario coverage:** fraction of release scenarios (weighted by frequency, size, direction, wind) that would be detected ([Kenexis](https://www.kenexis.com/wp-content/uploads/2014/05/UnderstandingFireAndGasMapping.pdf)); can use dispersion (Phast, CFD) ([CCPS LACPS 2014 worked example](https://proceedings.aiche.org/ccps/conferences/ccps-latin-american-conference-on-process-safety/2014/proceeding/paper/3d-fire-and-gas-detector-coverage-mapping-application-isa-tr840007-worked-example)). Geographic remains the prevailing semi-quantitative practice ([IChemE Hazards 26 paper](https://www.icheme.org/media/11785/hazards-26-paper-48-towards-bespoke-3d-fire-and-gas-mapping-integration-of-risk-based-approach-and-cfd-modelling.pdf)).
- Targets by area grade: Kenexis says grades "commonly come close to" 90 % coverage for Grade A, 80 % for B and 60 % for C. Grade A is high-pressure/highly flammable inventory and Grade C is mostly atmospheric ([Kenexis — Understanding F&G mapping](https://www.kenexis.com/wp-content/uploads/2014/05/UnderstandingFireAndGasMapping.pdf)). A summary of the TR revision gives the same 90/80/60 % for Grades A/B/C ([Chemical Processing — 2022 revisions](https://chemicalprocessing.com/articles/2022/fire-and-explosion-protection-take-note-of-revisions-to-tr-84-00-07)). These are typical values, not mandatory TR requirements; the project F&G philosophy sets the actual targets. Kenexis refers to the 2nd edition, TR84.00.07-2018 ([Kenexis F&G mapping brochure](https://www.kenexis.com/wp-content/uploads/2026/07/Kenexis-Fire-Gas-Mapping-Brochure-07_24_26.pdf)). Gas mapping often uses a design cloud (e.g., 5 m sphere for prescriptive coverage) **[general knowledge — verify]**.
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

**LNG / cryogenic valves.** An extended bonnet keeps the stem packing out of the cold zone, because conventional packing stiffens and leaks at cryogenic temperature ([Kosen — why extended bonnets](https://www.cnmfrs.com/news/kosenvalve/media-hub/why-extended-bonnet-designs-used-in-cryogenic-valves.html)). BS 6364 is the common cryogenic valve standard, and BS EN 12567 covers LNG isolation valves ([SIGTTO — selection and testing of valves for LNG](https://www.sigtto.org/media/2008/selection-and-testing-of-valves-for-lng.pdf)). Cold-box and non-cold-box bonnet extension lengths differ. One vendor table gives 500 mm (cold box) vs 400 mm (non-cold box) for NPS 2, which is a vendor figure ([BMT cryogenic valves catalogue](https://vhflxtlmezgpqwinbgji.supabase.co/storage/v1/object/public/catalogs/bmt-cryogenic-valves-r7.pdf)). Liquid lock (trapped cavity liquid) must be addressed, typically with cavity relief ([SIGTTO](https://www.sigtto.org/media/2008/selection-and-testing-of-valves-for-lng.pdf)). BS 6364 type testing is commonly done with helium at −196 °C (secondary source; [projectmaterials — cryogenic valves](https://blog.projectmaterials.com/quick-answers/valves/what-is-cryogenic-valve/)).

**Fail action.** FC/FO/FL (fail-last, with lock-up) set by process safety (HAZOP); state on P&ID and datasheet; spring return preferred; double-acting needs volume tank if fail position required.

**Positioner & accessories.** Digital positioner (HART/FF), with diagnostics; limit switches/position transmitter; SOV for trip of control valve (if used in SIF — needs SIL capability and failure-mode analysis); air filter regulator; volume booster; lock-up valve.

**Datasheet must-haves (ISA-75 / IEC 60534-7 style).** Fluid, case table (min/norm/max/shut-off with P1, ΔP, T, flow, ρ/MW, Pv, Pc, viscosity, k), calculated Cv & % opening, FL/xT/Fd, noise prediction (dBA), outlet velocity/Mach, body type/size/rating/end connection, trim type & characteristic, rated Cv, seat leakage class, body/trim/seat/packing materials, packing type (low-E ISO 15848-1 fugitive emissions), bonnet (extended for cryo/hot), actuator type/size/spring range/air supply min/max, fail action, stroke time, handwheel, positioner/protocol, accessories, SIL, NACE, Ex, painting, tests (hydro, seat leak, ISO 15848 FE).

**Common mistakes.** Line-sized valve; size from normal flow only; no shut-off ΔP case for actuator; noise checked only at max case; flashing service in globe straight-through body with soft carbon steel; Class VI requested on high-temperature service; fail action inconsistent between P&ID, C&E and datasheet; positioner protocol not matching DCS I/O.

**Vendors.** Emerson Fisher (GX, EZ, ET, Vee-Ball, Control-Disk; DVC6200), Baker Hughes Masoneilan (21000, 41005, Camflex; SVI II/SVI 1000), Flowserve Valtek (Mark One, MaxFlo; Logix 3800), Samson (3241, 3251; TROVIS 3730), IMI CCI (DRAG, severe service), IMI Orton/Truflo, Valmet/Neles (Finetrol, R-series rotary, ND9000), Koso (Kent Introl), Copes-Vulcan **[general knowledge — verify]**.

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

**HIPPS.** API 521 accepts HIPPS in place of a relief device only where a relief device is impractical, for example very high flow rates or where flaring is environmentally unacceptable, and the user must justify it ([E2G — applying HIPPS](https://e2g.com/industry-insights-ar/applying-high-integrity-pressure-protection-systems-hipps-in-petrochemical-plants-reducing-overpressure-risk-through-instrumented-solutions/)). A documented HIPPS SIF can remove that scenario from the design flare load ([ASME/API HIPPS paper](https://www.scribd.com/document/466191371/Colin-Easton-Paper)). Typical architecture is 2oo3 pressure transmitters ([Control & Instrumentation — HIPPS](https://www.controlandinstrumentation.com/systems/high-integrity-pressure-protection-system.html)) with two final isolation valves at SIL 3 (RRF 1,000–10,000) ([epcland — HIPPS](https://epcland.com/?p=44459)). Isolation-valve closure is typically quoted below about 2 s ([E2G](https://e2g.com/industry-insights-ar/applying-high-integrity-pressure-protection-systems-hipps-in-petrochemical-plants-reducing-overpressure-risk-through-instrumented-solutions/)) or about 2–3 s ([Offshore — reliable HIPPS](https://www.offshore-mag.com/pipelines/article/16757228/advanced-solutions-key-to-reliable-hipps)). The governing criterion is that the total response time of sensor, logic and valve is less than the process safety time, all designed under IEC 61511. These are secondary sources; check the API 521 and IEC 61511 clauses in the edition the project uses.

**Datasheet must-haves.** Valve type/size/rating/bore, shut-off ΔP, leakage class/standard, fire-safe cert, materials (NACE), seat type, actuator type & sizing (torques, SF, min supply), fail action, stroke times (open/close), SOV make/model/voting/SIL, limit switches (type, Ex, SIL), PST device, local control panel, manual override, PFP, SIL certification of assembly (FMEDA), fugitive emission class.

**Common mistakes.** Using a control valve as SDV; actuator sized at normal air pressure; closure time specified without surge check; limit switches used as SIF input without SIL capability; SOV exhaust port undersized; BDV restriction orifice missing; fail position for BDV specified FC.

**Vendors.** Valves: Cameron (Baker Hughes / SLB), Emerson (KTM, Vanessa triple-offset), Valmet/Neles, Flowserve (Valbart, NAF), Petrolvalves, Perar, PBV, Mokveld (axial), Tormene, Adams. Actuators: Emerson Bettis, Rotork (GP/CP/RC), Biffi, Valmet, Eltav, Prisma **[general knowledge — verify]**. SOVs: ASCO (Emerson), IMI Norgren/Herion/Maxseal, Parker, Bifold, Rotork Midland-ACS **[general knowledge — verify]**.

---

## Motor-operated valves (MOVs)

**Types.** Multi-turn (gate, globe, sluice; output via thrust/torque bases), part-turn (ball, butterfly, plug, via worm gearbox), linear. EN 15714-2 covers all three movement types ([iTeh SIST EN 15714-2 sample](https://cdn.standards.iteh.ai/samples/25899/57ff2ff11eb348e6841254a22e84953b/SIST-EN-15714-2-2011.pdf)). Choose multi-turn for rising-stem gate/globe valves (thrust) and part-turn (direct or with a worm gearbox) for quarter-turn ball, butterfly and plug valves. Example ranges are Rotork IQ3 (multi-turn) and IQT3 (part-turn) intelligent non-intrusive actuators ([Rotork IQT3](https://rotork.com/products/electric-intelligent-actuators/iq3/iqt3); [Rotork IQ multi-turn](https://rotork.com/nl/products-and-services/electric-actuators/iq3-range-3rd-generation/iq-multi-turn)).

**Duty classes (EN 15714-2).** Class A on-off, B inching/positioning, C modulating, D continuous modulating ([Bernard Controls actuator guide](https://www.bernardcontrols.com/ressources/files/2/4584,A300_03US_Electric-actuator-guide_U.pdf)). Starts-per-hour figures (e.g., up to 1,200 starts/h for modulating S4 duties) are manufacturer-specific, not from the standard text ([Bernard classification](https://www.bernardcontrols.com/en/our-solutions/classification-gps-actuator)). EN 15714-2:2009 superseded in 2021 per AFNOR listing ([AFNOR](https://www.boutique.afnor.org/en-gb/standard/nf-en-157142/industrial-valves-actuators-part-2-electric-actuators-for-industrial-valves/fa143236/34530)).
- **Motor duty (IEC 60034-1 duty types as used by vendors).** AUMA rates Class A/B as short-time duty **S2 – 15 min** (S2-10 min for 1-phase; S2-30 min optional) and Class C (modulating) as intermittent duty **S4 – 25 %** (S4-50 % optional). It quotes these against EN 15714-2 / EN ISO 22153 ([AUMA SQ technical data](https://www.manualslib.com/manual/3180803/Auma-Sq-05-2.html?page=44); [MOV reference spec](https://www.scribd.com/document/597981545/Ref-spec-MOV-s)). The same reference spec calls for S4-25 % / Class C with up to 1,200 starts/h for modulating MOVs ([MOV reference spec](https://www.scribd.com/document/597981545/Ref-spec-MOV-s)).
- **Vendor starts/h examples.** Rotork IQ3 multi-turn is rated S2 & S3 / Class A & B up to 60 starts/h, and the modulating IQM up to 1,200 starts/h (S4 / Class C) ([Rotork IQ multi-turn](https://rotork.com/nl/products-and-services/electric-actuators/iq3-range-3rd-generation/iq-multi-turn)). The IQT3M part-turn modulating version is rated up to 1,800 starts/h ([Rotork IQT3M](https://rotork.com/products/electric-intelligent-actuators/iq3/iqt3m-modulating)). Bernard Controls' Class A ratings run from about 15 down to 5 cycles/h as torque increases ([Bernard Controls catalogue](https://www.bernardcontrols.com/ressources/documents/1/5045e19-2270-2017_12_BernardControls_Actuation_Highres.pdf)). A modulating or inching duty needs a Class B/C (S4) actuator, not an on-off (S2) unit.

**Torque/thrust sizing.** The valve vendor provides breakaway (BTO/BTC), run and end torques at max ΔP. No single standard sets the safety factor, and published practice varies:
- Minimum ×1.25 per manufacturer recommendation ([industrialmonitordirect — MOV replacement checklist](https://industrialmonitordirect.com/blogs/knowledgebase/mov-replacement-specs-cross-vendor-comparison-checklist)).
- 30 % margin in one vendor sizing guide ([Assured Automation — actuator sizing](https://blog.assuredautomation.com/simplifying-actuator-sizing-for-quarter-turn-valves-a-practical-guide/)).
- 20 % minimum, increased to suit the application. This appeared in one of these two articles, not pinned to one: [Valve Magazine — sizing actuators](https://www.valvemagazine.com/articles/sizing-actuators-it-s-all-about-communication) or [Supply House Times — actuator selection](https://supplyht.com/articles/102906-understanding-valve-actuator-selection) **[verify attribution]**.
- Up to ×2 for ESD duty in one project calc ([Scribd key calculation](https://www.scribd.com/document/803411338/Key-Calulation)).

The commonly quoted 25–30 % therefore sits inside the published range, and the client spec governs. One utility MOV spec requires rated output torque at **90 % of nominal voltage** ([MOV reference spec](https://www.scribd.com/document/597981545/Ref-spec-MOV-s)). Gear-plus-motor sizing accounts for mechanical advantage, efficiency, minimum supply voltage and required speed ([industrialmonitordirect](https://industrialmonitordirect.com/blogs/knowledgebase/mov-replacement-specs-cross-vendor-comparison-checklist)). Always check actuator stall torque/thrust against the valve MAST. Operating time (stroke speed, e.g., 10–12 in/min for gate valves) is chosen from process and surge requirements; no source was found for that speed **[general knowledge — verify]**.

**ESD MOVs.** If an MOV is part of an ESD/SIF, use a SIL-rated actuator. Rotork IQ actuators with the SIL Safety Function Control Module are SIRA-certified for SIL 2, with "Stayput" and "ESD" as the safety functions; see the IQ3 SIL safety manual PUB002-110 ([Rotork IQ SIL literature](https://instrumentationdemo.yodify.com/Documentation/Document/q1mXJ/pub002-104-00-0516.pdf); [Rotork IQT3](https://rotork.com/products/electric-intelligent-actuators/iq3/iqt3)). AUMA offers SA..-SIL equivalents **[verify]**. Typical practice, not sourced here **[general knowledge — verify]**:
- A dedicated ESD input that overrides local/remote control, optionally with thermostat/torque-switch bypass.
- Power from a UPS or essential board.
- Fire protection for the actuator and cables (fire-resistant cable to IEC 60331).
- Fail-as-is is the normal MOV behaviour; fail-safe needs a stored-energy (spring) actuator.

**Datasheet must-haves.** Valve type/size, torque/thrust data, MAST, operating time, duty class & starts/h, motor power/voltage/phase/frequency, starter type, local controls, control interface (hardwired/Modbus/PROFIBUS/FF/HART), ESD function, position feedback, enclosure IP68 & Ex, handwheel, temperature, SIL, cable entries, gearbox.

**Common mistakes.** Sizing on run torque; no MAST check; fail-safe assumed for MOV; modulating duty with on-off actuator; no ESD override philosophy; voltage drop on long cables at starting.

**Vendors.** Rotork (IQ3/IQT3/CK), AUMA (SA/SQ + AC.2 controls), Emerson Bettis/EIM (TEC2), Bernard Controls, Flowserve Limitorque (MX/QX), Biffi, SIPOS (now AUMA), Schiebel **[general knowledge — verify]**.

---

## Pressure safety valves (PSVs)

**Types.** Conventional spring-loaded, balanced bellows, pilot-operated (pop/modulating), rupture discs (alone or in combination). Thermal relief valves (TRVs, ¾×1") for blocked-in liquid.

**Sizing (API 520 Part I / ASME VIII / ISO 4126).** Required orifice area for governing scenario (blocked outlet, fire, control valve failure, tube rupture, etc. per API 521); select the smallest API 526 standard orifice letter whose effective area is ≥ the required area; Kd/Kb/Kw/Kc corrections.
- **API 526 effective areas (in²):** D 0.110, E 0.196, F 0.307, G 0.503, H 0.785, J 1.287, K 1.838, L 2.853, M 3.60, N 4.34, P 6.38, Q 11.05, R 16.00, T 26.00 ([Neutrium — orifice area to API 526](https://neutrium.net/articles/equipment/relief-valve-orifice-area-to-api-rp-526/); [Eng-Tips — API vs ASME area](https://eng-tips.com/threads/api-area-vs-asme-area.299220)).
- Some secondary tables give different R (15.70) and Q values, so check API 526 / API 520 Pt I for the edition in force.
- API effective areas are for preliminary sizing. Final verification uses the manufacturer's ASME-certified actual area and certified Kd ([industrialmonitordirect — actual vs effective area](https://industrialmonitordirect.com/blogs/knowledgebase/api-526-orifice-letter-selection-actual-vs-effective-area)).
- **Set pressure and accumulation (ASME VIII Div. 1, UG-125/UG-134), above MAWP:**
  - Single device: 10 %.
  - Multiple devices: 16 % or 4 psi (30 kPa), whichever is greater.
  - Fire (external heat): 21 %.
  - With multiple valves, the first is set ≤ MAWP and the others up to 105 % of MAWP. Sources: [Wisconsin admin. code quoting UG-134(a)](https://docs.legis.wisconsin.gov/code/admin_code/sps/safety_and_buildings_and_environment/326_360/341_c/_109?up=1); [Emerson Kunkle data supplement](https://d1-live.emerson.com/documents/automation/product-brochure-kunkle-data-supplement-for-safety-relief-products-kunkle-valve-en-en-5262480.pdf).
  - Note: since the 2021 BPVC edition, much of the pressure-relief device content has been moved to the new Section XIII, with Div. 1 keeping the overpressure limits. Check clause references (UG-125 ff. vs Part UG-150 ff.) for the code year in use **[general knowledge — verify]**.

**Inlet pressure loss.** The non-recoverable inlet line loss should not exceed 3 % of set pressure (API 520 Part II; also ASME VIII Div. 1 Appendix M); API 520 Pt II allows exceeding 3 % if an engineering analysis shows stable operation, and OSHA cites the 3 % rule as RAGAGEP ([Process Engineering Associates — 3 % rule](https://processengr.com/?p=4225)). Remedy if exceeded: larger inlet line, remote-sensed pilot, adjust blowdown **[general knowledge — verify]**.

**Back pressure.** Conventional valves: built-up back pressure ≤ 10 % of set (at 10 % overpressure) commonly cited; superimposed variable back pressure → bellows or pilot ([Projectmaterials — safety valves](https://blog.projectmaterials.com/valves/safety-valve-asme-api/)). API RP 521 wording, as quoted secondhand, says built-up back pressure on a conventional valve should not exceed 10 % of set at 10 % allowable overpressure. A higher limit is allowed for larger overpressure provided built-up back pressure does not exceed the allowable overpressure, e.g., 21 % in fire. Within these limits Kb = 1.0 for gas at critical flow and for liquids ([API RP 521 conventional PSV summary](https://gimjaeseung.tistory.com/entry/API-RP521-Conventional-Type-PSV-Guide)).
- **Balanced bellows: back-pressure limit (sources conflict, keep both).**
  - About 35 %: one source says the valve is unaffected until back pressure exceeds about 35 % of set ([uWaterloo EIC wiki — PRV](https://uwaterloo.atlassian.net/wiki/spaces/EIC/pages/31729255947/Pressure+Relief+Valve) **[verify attribution]**).
  - Up to about 50 %: forum guidance says bellows valves suit back pressures up to about 50 % of set with the Kb correction applied, with capacity falling sharply above that ([Eng-Tips — bellows back-pressure correction](https://eng-tips.com/threads/backpressure-correction-for-balanced-bellows.234234)).
  - Example Kb: a Consolidated (Baker Hughes) chart gives Kb ≈ 0.72 at 53 % back pressure and 10 % overpressure ([BHGE Kb chart](https://www.scribd.com/document/462416593/PSV-Kb-BHGE-pdf)).
  - Use API 520 Pt I's Kb figure only for preliminary sizing, then the manufacturer's Kb curve. Also check the bellows' mechanical back-pressure rating.
  - Vendor alternative: Crosby claims its balanced-diaphragm design extends the limit to 80 % of set ([Crosby balanced diaphragm flier](https://d1-live.emerson.com/documents/automation/product-brochure-crosby-balanced-diaphragm-flier-crosby-en-en-8675078.pdf)).
- **Pilot-operated:** pilot PRVs typically handle back pressure up to about 50 % of set without loss of capacity ([Enggcyclopedia — PRV types](https://enggcyclopedia.com/2011/06/type-pressure-relief-valves) **[verify attribution]**). Check a backflow preventer wherever back pressure can exceed inlet pressure **[general knowledge — verify]**. Operating closer to set (high operating/set ratio, e.g., ~95 %+) and poorer suitability for dirty or polymerising service unless filtered/purged are typical practice **[general knowledge — verify]**.

**Installation.** PSV at high point, inlet line short and free-draining, outlet to closed flare header self-draining (no pockets), CSO/LO isolation valves with full bore per philosophy, spare PSV (installed spare with interlocked/three-way changeover) **[general knowledge — verify]**. Reaction forces for open discharge (API 520 Pt II).

**Datasheet must-haves (API 526/520 Annex).** Tag/scenario, fluid & state, required capacity, MW/Z/k, set pressure, CDTP, back pressure (superimposed constant/variable, built-up), overpressure, operating P/T, relieving T, orifice letter & area (calc/selected), inlet/outlet size & rating, body/bonnet/spring/bellows/trim materials, cap/lever, test gag, nozzle type, Kd, NACE, code stamp (ASME UV), noise, inlet ΔP %, rupture disc combination, PSV certification.

**Common mistakes.** Inlet loss not calculated for remote PSVs; bellows vent plugged/not routed to safe location; conventional valve on header with variable superimposed back pressure; orifice selected below required; two-phase relief sized as liquid only; CDTP not corrected for back pressure/temperature.

**Vendors.** Emerson (Anderson Greenwood, Crosby), Curtiss-Wright Farris, Baker Hughes Consolidated, LESER, Taylor Valve, Mercer, Spirax Sarco (utility), Fike / BS&B / Rembe (rupture discs) **[general knowledge — verify]**.

---

## Cabinets: system, marshalling, instrument

**Types.** System cabinets (controllers, I/O cards — DCS/SIS/F&G), marshalling cabinets (field cable termination, cross-wiring, IS barriers/isolators, fuses, relays), power distribution cabinets, network/server cabinets, field instrument cabinets/enclosures (local panels). Universal I/O (Emerson CHARMs, Honeywell UIO, Yokogawa N-IO) reduces marshalling **[general knowledge — verify]**.

**Heat dissipation.** Sum per-cabinet heat load (I/O, power supplies at efficiency, barriers, relays) and check against HVAC design of the instrument equipment room/LER; cabinet internal temperature rise across fans/filters; typical design ambient 22 ± 2 °C in control room/LER with cabinet internal limit vendor-defined **[general knowledge — verify]**. Published spec practice:
- Submit heat dissipation calculations for any cabinet housing power supplies, PCs or other heat-generating components ([DCS spec excerpt](https://www.scribd.com/document/575140283/1-DCS-spec)).
- A SAMSS-style spec limits the internal heat rise to **10 °C** and requires cooling fans sized for **20 % more airflow** than credited in the calculation ([34-SAMSS-820 copy](https://www.scribd.com/document/494624754/424411678-34-samss-820)).
- Include the modules on installed spares in the heat load.
- Provide the heat load list to HVAC early (often underestimated by 20–30 % at FEED) **[general knowledge — verify]**.

**Segregation.** IS and non-IS wiring separated. Manufacturer guides quoting IEC 60079-14 / 60079-11 give at least 50 mm clearance between IS and non-IS terminals when separation is by distance, or else an insulating or earthed metal partition. IS cables and terminals may be identified light blue, and light blue must then not be used for other circuits ([Turck IS installation guide](https://www.turck.de/attachment/100000312.pdf); [HSA Ireland — IS instrumentation guidance](https://hsa.ie/eng/topics/atex/atex_delivery_guide/atex_verification_guide/delivery_guide/instrumentation_guidance_intrinsic%20safety%20.pdf); [Weidmüller — terminals in Ex areas](https://www.weidmueller.com/int/products/connectivity/terminal_blocks/terminal_blocks_in_explosion_protected_areas.jsp)). A 3 mm clearance from IS terminals to earthed parts is also quoted (EN 60079-11) ([Weidmüller](https://www.weidmueller.com/int/products/connectivity/terminal_blocks/terminal_blocks_in_explosion_protected_areas.jsp) **[verify attribution]**). Clause numbers were not checked against the standard text; separate SIS and BPCS cabinets (IEC 61511 independence) or at least segregated sections; power (> 50 V) segregated from signal; separate AC/DC.

**Power supply.** Redundant 24 VDC power supplies (N+1 or 1+1) fed from two independent UPS feeders with diode/active redundancy modules; monitoring contacts to DCS; field power fused per loop **[general knowledge — verify]**.

**Spare capacity.** Common project requirement: 20 % installed spares wired to terminal blocks plus 20 % uninstalled space (empty DIN rail and chassis rack) ([industrialmonitordirect — DCS cabinet I/O capacity](https://industrialmonitordirect.com/blogs/knowledgebase/estimating-dcs-marshalling-and-system-cabinet-io-capacity)). One DCS spec excerpt also requires 20 % usable spare slot space, with the controller sized to handle that extra 20 % of I/O ([DCS spec excerpt](https://www.scribd.com/document/575140283/1-DCS-spec)). The project/company spec governs; note the 20 % may be defined per I/O type, per card, per cabinet or per node — clarify.

**Datasheet / spec must-haves.** Dimensions, IP rating (IP42 indoor typical; IP54/IP65 outdoor), front/rear access, bottom/top entry, mounting plinth, colour, earthing (IS earth bar, instrument clean earth, safety earth), lighting, socket, door switch, thermostat/fan, heat load, weight, cable glands/plates, terminal type (disconnect/fuse/knife), tagging, labels, FAT/SAT.

**Common mistakes.** Heat load from vendor not updated after I/O growth; IS and non-IS terminals mixed in one rail; single power supply to SIS; no dedicated IS earth bar; spare percentage counted on channels, not on slots/cabinets.

**Vendors.** Rittal, Schneider (Spacial), nVent Hoffman, Pentair, Eldon; IS interfaces: Pepperl+Fuchs (K-System, HiC), MTL/Eaton, Phoenix Contact, Turck, R. STAHL **[general knowledge — verify]**.

---

## Junction boxes

**Types.** Single-pair (IS/non-IS), multi-pair, analogue/digital/fieldbus (with segment protectors), power. Material: GRP or 316 SS; Ex e (increased safety) for non-IS, Ex i for IS (often Ex e certified boxes used with blue IS terminals), Ex d rarely **[general knowledge — verify]**.

**Rules.** Separate JBs for IS and non-IS, for SIS and BPCS, for F&G; 20 % spare terminals and spare gland entries; drain/breather; earthing stud and cable screen/earth terminals; IP66 minimum outdoor; tag & signal type labels; located at accessible height, out of fire zones or protected **[general knowledge — verify]**.

**Fieldbus segment design (FOUNDATION fieldbus H1).**
- Limits: up to 32 devices per segment; total cable length (trunk plus all spurs) up to 1,900 m without repeaters (up to four repeaters allowed); spurs up to 120 m ([Wikipedia — FOUNDATION Fieldbus H1](https://en.wikipedia.org/wiki/Foundation_Fieldbus_H1); [Fluke — FF system and diagnostic basics](https://fluke.com/en-us/learn/blog/oscilloscopes/foundation-fieldbus-system-and-diagnostic-basics)). The allowed spur length shrinks as device count rises; use the IEC 61158-2 / FieldComm table.
- Practical loading: designs typically limit segments to about 10–12 devices including future additions, with at least 20 % spare, to keep voltage and macrocycle margin. The common "12–16" is at the upper end and was not found in a source ([Fluke](https://fluke.com/en-us/learn/blog/oscilloscopes/foundation-fieldbus-system-and-diagnostic-basics); [Wikipedia](https://en.wikipedia.org/wiki/Foundation_Fieldbus_H1)).
- FISCO (IS) total cable: about 1 km in IIC and 1.9 km in IIA/IIB, as quoted secondhand **[verify against IEC 60079-11/-25]**.
- Use short-circuit-protected device couplers (segment protectors) in the field JB so a spur fault does not take down the segment **[general knowledge — verify]**.

**Mistakes.** Ex e box with internal components (e.g., relays) not covered by certificate; mixed IS/non-IS; screen earthed at both ends causing ground loops; insufficient gland plate space for multicore + spare.

**Vendors.** R. STAHL, Eaton (CEAG/MTL), Hawke, Rose (Phoenix), Bartec, CMP, Hubbell Killark, Appleton (Emerson) **[general knowledge — verify]**.

---

## Cables & glands (incl. Ex d barrier glands)

**Cables.** Instrument cables per IEC 60502/BS EN 50288-7 (or equivalent): individually & overall screened pairs/triads, tinned copper, PVC/XLPE insulation, SWA/braided armour, LSZH or PVC sheath; flame retardant IEC 60332-1/-3 (bunched); fire-resistant IEC 60331 for F&G, ESD valves that must operate during fire, MOV ESD, PA/GA **[general knowledge — verify]**. IS cables light blue sheath; conductor size typically 1.0–1.5 mm² (multicore 0.75–1.0 mm²) **[general knowledge — verify]**. Thermocouple extension/compensating cables per IEC 60584-3 colour codes.

**Glands (IEC 60079-14).** Gland protection must match or exceed the equipment it enters ([Power & Cables — IECEx gland guide](https://www.powerandcables.com/iecex-cable-gland-selection/)). Older (pre-2013) flowchart: barrier glands required for Ex d enclosures with internal ignition source in IIC gas, or Zone 1 with enclosure volume > 2 dm³ (2 L) ([Source IEx — To barrier or not to barrier](https://www.sourceiex.com/Catalogs/To%20Barrier%20or%20Not%20to%20Barrier.pdf); [Appleton gland guide](https://www.appleton.emerson.com/documents/catalog-cable-gland-selection-guide-appleton-en-us-7436636.pdf)). Since the 2013 edition the decision hinges on cable construction (circular, compact, extruded bedding, non-hygroscopic fillers) and connected cable length ≥ 3 m; otherwise barrier glands ([Power & Cables](https://www.powerandcables.com/iecex-cable-gland-selection/)). The 2024 edition changed cable/gland selection again — check ([Element — IEC 60079-14:2024 changes](https://cdn.element.com/siteassets/media/pdfs/resources/understanding-the-changes-to-iec-60079-14-2024-edition.pdf)).
- Edition 6 (published August 2024) supersedes edition 5 (December 2013). It adds a new flowchart for selecting flameproof cable entry devices, a new normative annex with a pressure test for cables, and an informative annex of inspection tables ([Hazardex / IECEx — Edition 6 of IEC 60079-14](https://www.iecex.com/assets/Uploads/Hazardex/Hazardex-2024-November-Dr-Martin-Thedens-Edition-6-of-IEC-60079-14-is-here.pdf)).
- Vendors describe a shift from gland-only selection to assessing the cable plus cable-entry system together ([Lapp — Annex C new cable rules](https://camunacavi.lappgroup.com/news/news-of-the-current-year/iec-60079-14-annex-c-new-cable-rules-for-explosive-atmospheres.html)).
- EEMUA notes that the rules on when a barrier gland is needed changed significantly ([EEMUA — glands](https://www.eemua.org/current-issues/glands)). The background document is IEC SC31J-SD-001:Ed1/2021-03 ([Element](https://www.element.com/resources/white-papers/understanding-the-changes-to-iec-60079-142024)).
- Read the 2024 flowchart itself before relying on the 2013-era "≥ 3 m / compact cable" shortcut above. Many oil & gas company specs simply mandate barrier glands on all Ex d entries regardless **[general knowledge — verify]**.

**Wireless instruments (WirelessHART vs ISA100).**
- Both use IEEE 802.15.4 radios in the 2.4 GHz band (16 channels, 250 kbit/s) with TDMA. WirelessHART uses fixed 10 ms slots; ISA100.11a slots are configurable from 10 to 14 ms ([Emerson — comparison of WirelessHART and ISA100.11a](https://www.emerson.com/documents/automation/a-comparison-of-wirelesshart-isa100-11a-en-42598.pdf); [SINTEF report](https://sintef.brage.unit.no/sintef-xmlui/bitstream/11250/2430391/2/SINTEF+S18047.pdf)).
- WirelessHART is a simple specification with few options and security always on. ISA100.11a has many configurable layers, and its security can be disabled ([SINTEF](https://sintef.brage.unit.no/sintef-xmlui/bitstream/11250/2430391/2/SINTEF+S18047.pdf)).
- Standards: WirelessHART has been IEC 62591-1 since March 2010; ISA100.11a was approved by ANSI in 2011 and was on its way to becoming IEC 62734 as of 2012 (since published, 2014 **[general knowledge — verify]**) ([Emerson comparison](https://www.emerson.com/documents/automation/a-comparison-of-wirelesshart-isa100-11a-en-42598.pdf)).
- Achievable update rate falls as the network grows ([SINTEF](https://sintef.brage.unit.no/sintef-xmlui/bitstream/11250/2430391/2/SINTEF+S18047.pdf)). Use wireless for monitoring and non-critical loops, not fast control or SIS, unless the project's wireless philosophy says otherwise **[general knowledge — verify]**.

**Gland datasheet fields.** Type (E1FW/A2F etc.), Ex certification (db/eb), IP66/68, armour type, cable OD range (inner/outer), thread (M20/M25, NPT), material (brass nickel-plated, SS), shroud, earth tag, sealing washer.

**Common mistakes.** Thread type mismatch (NPT vs metric) between instrument and gland; non-barrier glands on IIC Ex d junction boxes in Zone 1; IP rating lost due to missing sealing washer; unused entries not closed with certified stopping plugs.

**Vendors.** Cables: Prysmian, Nexans, LS Cable, Tratos, Brugg, Taihan, Ducab. Glands: CMP, Hawke (Hubbell), Peppers, Bimed, Appleton, Cooper/Eaton **[general knowledge — verify]**.

---

## Instrument air

**Quality.** ISA-7.0.01: pressure dew point at line pressure ≥ 10 °C (18 °F) below the lowest temperature to which any part of the instrument air system is exposed, and not above 4 °C at line pressure ([Atlas Copco — instrument air quality](https://www.atlascopco.com/en-rs/compressors/air-compressor-blog/instrument-air-quality); [Air Best Practices — ISA 7.0.01](https://www.airbestpractices.com/standards/iso-and-cagi/understanding-isa70011996-instrument-air-standard)). ISA-7.0.01 is increasingly superseded in specs by ISO 8573-1 quality classes (e.g., Class 1.2.1 or 2.2.1) ([Air Best Practices](https://www.airbestpractices.com/standards/iso-and-cagi/understanding-isa70011996-instrument-air-standard)). Desert/cold sites typically specify −40 °C PDP at line pressure (desiccant dryers), which matches ISO 8573-1 humidity class 2 (PDP ≤ −40 °C). Class 2 also limits oil to 0.1 mg/m³ ([ISO 8573-1 class table](https://www.californiaairtools.com/app/download/7127321152/Air+Quality+classes+defined+in+ISO+8573.pdf); [Festo — ISO 8573 guide](https://www.festo.com/gb/en/e/about-festo/blog/in-practice/iso-8573-the-essential-guide-to-compressed-air-quality-id_2190127)). Note that one EXAIR blog misprints class 2 as "40 °F (40 °C)"; use the ISO table. ISA-7.0.01: maximum particle size 40 µm, verified after maintenance or modification. Lubricant content as close to zero as possible and never above 1 ppm w/w or v/v; automatic oilers are strongly discouraged ([Air Best Practices — ISA instrument air standard and adsorption dryers](https://airbestpractices.com/standards/energy-management/ansiisa-instrument-air-standard-and-adsorption-type-dryers); [ANSI preview ISA-S7.0.01-1996](https://webstore.ansi.org/preview-pages/ISA/preview_ANSI+ISA+S7.0.01-1996.pdf)).

**System design.**
- **Header pressure:** one practitioner source gives a typical header set point of 6.0–7.0 barg, a low-pressure alarm near 5.5 barg and a low-low alarm/ESD trip near 4.8 barg. It quotes the nominal supply range as 80–120 psi (5.5–8.3 bar) ([industrialmonitordirect — instrument air supply pressure](https://industrialmonitordirect.com/blogs/knowledgebase/instrument-air-supply-pressure-specifications-standards-and)). One company spec copy calls for at least 8.0 barg in the buffer vessel and 7.0 barg in the supply piping ([E-IN-200 copy](https://www.scribd.com/document/669241780/E-IN-200)). The older "7–8 barg normal, 4–5 barg minimum at consumers" is consistent with these but is still project-specific. Size actuators at the minimum header pressure.
- **Receiver hold-up:** size from retention time between starting pressure P1 and minimum pressure P2, i.e., V = t·Q·Patm/(P1−P2). A vendor worked example uses 15 min down to 75 psig (≈ 5.2 barg) ([industrialmonitordirect — receiver sizing](https://industrialmonitordirect.com/blogs/knowledgebase/air-receiver-tank-sizing-retention-time-p1-and-p2-explained)). Typical project values of 5–20 min (time for safe shutdown after compressor trip) were not found in a code; the plant design basis sets them **[general knowledge — verify]**.
- **Other layout practice:** ring headers; sub-headers with spare take-offs (~20 %); take-offs from top of header; drain points at low points; SS 316 or galvanised CS headers, SS tubing to consumers **[general knowledge — verify]**. Header sizing via consumption list (control valve steady-state bleed + stroking transient + purge + analyzers + PSV pilots) with diversity, plus leakage allowance (e.g., 10 %) **[general knowledge — verify]**.

**Consumer hook-up.** Isolation valve, filter-regulator (with gauge) per consumer, SS tubing; volume tank for fail-position or ESD valves.

**Mistakes.** PDP specified at atmospheric not line pressure; no receiver hold-up calc; air consumption list ignoring ESD valve simultaneous stroking; using nitrogen backup without O2-depletion consideration in enclosed spaces.

---

## Hook-ups (general)

- Hook-up drawings define tapping, root valve to instrument: valves, fittings, tubing, supports, and bill of materials per piping class/instrument material spec. Typical families: pressure (gas/liquid/steam), DP flow (gas above/liquid below), DP level (dry/wet leg/seal), temperature, analyser sample, pneumatic (air supply, signal), heat-traced/insulated hook-ups **[general knowledge — verify]**.
- Impulse/process tubing: 1/2" OD SS 316, wall per pressure; compression fittings twin-ferrule (Swagelok/Parker A-Lok) — no mixing of brands; 1:12 slope (see DP section — [CR4/API RP 551](https://cr4.globalspec.com/thread/39151/impulse-tubing)); supports every ~1–1.5 m **[general knowledge — verify]**.
- Instrument mounted on 2" stanchion, not on vibrating pipe; accessible from grade/platform (≤ ~1.5 m above walkway) **[general knowledge — verify]**.
- Close-coupling / direct mounting preferred for SIS transmitters to reduce plugging/leak points; hot services: impulse length to cool below transmitter max T (or use seals).
- Vents/drains routed to closed drain/flare for toxic or flammable services; DBB isolation on high-pressure/toxic.
- Heat tracing: self-regulating electric or steam; insulation boxes (Intertec-type) for transmitters in cold climates or hot sun **[general knowledge — verify]**.

**Mistakes.** Hook-up shows gas configuration for a liquid-service transmitter; piping class break at wrong point; root valve rating below line class; transmitter located above liquid taps (gas pockets).

---

## Other vendors

*(The large DCS/SIS/automation vendors such as Emerson, Honeywell and Yokogawa are covered in other knowledge files. Model names below are from general knowledge unless linked — **verify current portfolio before quoting**; product lines are renamed/merged frequently.)*

**Endress+Hauser (Switzerland/Germany).** Full field-instrument house, strong in Europe/Middle East and as main instrument vendor (MIV) on LNG and chemical projects. Flagships: Promass (Coriolis), Promag (magnetic), Prowirl 200 (vortex), Prosonic Flow (ultrasonic), t-mass (thermal); Cerabar/Deltabar (pressure/DP), Deltapilot (hydrostatic); Levelflex (GWR), Micropilot (radar), Liquiphant (forks, min density 0.5 g/cm³ ([E+H FTL51](https://www.nl.endress.com/en/field-instruments-overview/level-measurement/Vibronic-Liquiphant-FTL51))), Gammapilot (radiometric), Proservo NMS8x (servo, ±0.4 mm ([TI01248G](https://bdih-download.endress.com/files/DLA/005056A500261EDFB0FCCC9653A98A19/TI01248GEN_0824-00.pdf))) and Micropilot NMR8x with Tankvision (tank gauging); iTEMP/iTHERM (temperature); Liquiline (liquid analysis); SpectraSensors TDLAS and Kaiser Raman (gas analysis). Heartbeat Technology provides on-board diagnostics and in-situ verification against internal references, introduced with the FMCW Micropilot FMR60/62/67 and extended to Levelflex FMP5x ([Control Engineering — radar with diagnostics and verification](https://www.controleng.com/radar-level-transmitters-with-diagnostics-and-instrument-verification/)). Promass Q is positioned as the highest-accuracy Promass for mass, volume and density, with Multi-Frequency Technology for entrained gas ([E+H Promass Q300/500 TI](https://www.th.endress.com/_storage/asset/3066817/storage/master/file/12573980/download/Promass%20Q300_500.pdf)). Cerabar PMP71B is listed as the high-end pressure transmitter of the new B generation ([E+H Highlights 2021](https://portal.endress.com/dla/5000390/0548/000/08/EC00006Z11EN_1121_Highlights_2021_web.pdf)). The rest of the model list is **[general knowledge — verify]**.

**Siemens.** Process instrumentation under SITRANS: SITRANS P DS III / P320 / P420 (pressure), SITRANS F (FM MAG 5000/6000, FC Coriolis, FUS/FS230 clamp-on ultrasonic — custody claims for clamp-on ([Siemens clamp-on gas custody](https://assets.new.siemens.com/siemens/assets/api/uuid:9670bb2c-83be-4c59-809a-01b79ead159b/di-pa-mi-gas-pipeline-custody-transfer-clamp-2022.pdf))), SITRANS LR/LG (radar/GWR), SITRANS LVL200 forks ([Siemens LVL200](https://cache.industry.siemens.com/dl/files/042/109765042/att_1277064/v1/sitransl_lvl200_fi01_en.pdf)), SIPART PS2 (positioner), MAXUM II (process GC), ULTRAMAT/OXYMAT/CALOMAT (gas analysers). SITRANS P320 / P420 reference accuracy up to 0.065 % / 0.04 %. Both were developed to IEC 61508 for SIL applications (P420 SIL 2/3), with Remote Safety Handling for SIL validation from the control room and proof-test intervals up to 15 years cited ([Siemens SITRANS P320/P420](https://www.siemens.com/en-us/products/sitrans/p320-p420/)). Systems: SIMATIC PCS 7 / PCS neo, S7-1500H/F; SIMATIC Safety Integrated. PCS neo was not covered by the sources found **[general knowledge — verify]**.

**ABB.** Measurement: 266/ 2600T (pressure), ProcessMaster/AquaMaster (magnetic, FEP500 0.3 %/opt. 0.2 % ([ABB FEP500](https://library.e.abb.com/public/c4148da8f7404266a9e6dae3745d3783/DS_FEP500_EN_D.pdf))), CoriolisMaster, VortexMaster/SwirlMaster, SensyTemp (temperature), LMT magnetostrictive level, K-TEK magnetic level gauges, TZIDC/EDP300 positioners. Analytical: NGC8200 / PGC5000 GCs, AO2000 continuous gas analysers, LGR/ICOS laser analyzers, Navigator water analysers; Totalflow flow computers. 266-series pressure/DP transmitters list base accuracy ±0.04 %, optional ±0.025 % on 266MST ([ABB 266MST](https://new.abb.com/products/measurement-products/ja/圧力-差圧伝送器/差圧伝送器/266mst); [ABB 266MRT](https://new.abb.com/products/measurement-products/pressure/differential-pressure-transmitters/266mrt-differential-pressure-transmitter-with-remote-diaphragm-seals-and-multisensor-technology)). Systems: 800xA, Freelance, AC 800M HI for safety. CoriolisMaster and 800xA details were not covered by the sources found **[general knowledge — verify]**.

**Krohne (Germany).** Flow specialist: Optiflux (mag, 5 µS/cm min ([Krohne install guide](https://cdn.krohne.com/archive/TD_MID_INSTALL_e_72.pdf))), Optimass (Coriolis), Altosonic V12 / Optisonic (ultrasonic incl. custody liquid/gas), Optiswirl (vortex), H250 (variable area), Optiwave (radar), Optiflex (GWR), BM26 (magnetic level gauge), Optiswitch (forks ([Krohne](https://krohne.com/en/products/level-measurement/level-switches/vibration-level-switches/optiswitch-5150))). Also complete metering skids/systems (Krohne Oil & Gas, Summit flow computers) **[general knowledge — verify]**.

**VEGA (Germany).** Level and pressure specialist: VEGAPULS 6X (radar, multi-frequency platform ([VEGA blog](https://www.vega.com/en/company/blog/2017/good-focusing-delivers-security))), VEGAPULS 64 (80 GHz), VEGAFLEX 8x (GWR), VEGASWING (forks), VEGABAR (pressure/hydrostatic with ceramic CERTEC cell), radiometric FIBERTRAC/SOLITRAC/MINITRAC/POINTRAC, plics modular electronics **[general knowledge — verify]**. VEGAPULS 6X is one radar platform for W-band (80 GHz), K-band (26 GHz) and C-band (6 GHz), replacing the separate VEGAPULS 6x models. It ranges up to 120 m, has a SIL option and IEC 62443-4-2 security ([VEGA radar](https://vega.com/en-us/radar); [VEGAPULS 6X](https://vega.com/en-ca/products/product-catalog/level/radar/vegapuls-6x)).

**Rotork (UK).** Leading electric actuator vendor: IQ3 / IQT3 (intelligent multi-turn/part-turn, non-intrusive, SIL options), CK modular, SI/EH electro-hydraulic, CP/GP/RC pneumatic (scotch-yoke/rack-pinion), Fairchild regulators, Midland-ACS SOVs, YTC positioners, Bifold. Strong in MOVs for pipelines, tank farms and utilities. Sourced ratings: IQ3 multi-turn S2/S3 Class A/B up to 60 starts/h, IQM modulating up to 1,200 starts/h ([Rotork IQ multi-turn](https://rotork.com/nl/products-and-services/electric-actuators/iq3-range-3rd-generation/iq-multi-turn)); IQT3M up to 1,800 starts/h ([Rotork IQT3M](https://rotork.com/products/electric-intelligent-actuators/iq3/iqt3m-modulating)). The SIL option is SIRA-certified for SIL 2 (Stayput/ESD) ([Rotork IQ SIL](https://instrumentationdemo.yodify.com/Documentation/Document/q1mXJ/pub002-104-00-0516.pdf)). Non-actuator brand list **[general knowledge — verify]**.

**Valmet / Neles (Finland; formerly Metso).** Control and on-off valves: Neles Finetrol (eccentric rotary plug), R-series segment/ball valves, Jamesbury (soft-seated ball, butterfly), Mapag (high-temperature butterfly), Neles globe valves; ND9000 intelligent positioner; ValvGuard VG9000 (SIL 3 ESD controller with PST); Neles actuators B1C/ B1J. Common for ESD/HIPPS rotary valves and pulp/paper heritage. Neles ValvGuard VG9000 is an intelligent safety solenoid with PST, IEC 61508 compliant up to SIL 3 (TÜV Rheinland) ([Valmet VG9000](https://valmet.com/flowcontrol/valve-automation/valve-controllers/neles-valvguard-vg9000--intelligent-safety-solenoid); [VG9000 datasheet](https://www.valmet.com/globalassets/sharepoint/imported/9vg921en.pdf)). The rest of the model list is **[general knowledge — verify]**.

**Baker Hughes Masoneilan (US/France/Italy).** Control valves: 21000 (globe), 41005 (cage), 28000 Varimax, Camflex (eccentric rotary), 35002 (rotary), LO-dB and VRT noise/cavitation trims ([Masoneilan noise handbook](https://dam.bakerhughes.com/m/403871c7a460561b/original/Masoneilan-Noise-Control-Handbook-English.pdf)); SVI II AP / SVI 1000 positioners, 12400 digital level transmitter/controller (displacer). Baker Hughes also owns Consolidated (PSVs) and Panametrics (ultrasonic flow, moisture analysers ([XGF868i](https://dam.bakerhughes.com/m/5fd2c2563e141dd7/original/DigitalFlow-XGF868i-Datasheet-English.pdf))). SVI II ESD is marketed as a SIL 3 (IEC 61508, TÜV/exida) smart ESD device that stays live during and after a trip, with PST independent of the safety function ([Masoneilan SVI II ESD brochure](https://dam.bakerhughes.com/m/1c200beaf7552a1c/original/BHMN-SVI-II-ESD-BR-19512B-0820-English-pdf.pdf)). The 21000 and other valve models were not covered by the sources found **[model list general knowledge — verify]**.

**Flowserve (US).** Valtek Mark One/Mark Two (globe), MaxFlo (rotary), ShearStream, Valdisk (butterfly), Logix 3800 positioner; Valbart (trunnion ball), NAF, Durco/Atomac (lined plug valves), Worcester; Limitorque MX/QX (electric actuators), Automax; also pumps & seals. Common on refinery severe-service lists **[general knowledge — verify]**.

**Samson (Germany).** Globe control valves (Series 240 – 3241, 3251, 3254; Series 250/290), rotary (3310, Pfeiffer lined valves), self-operated regulators, TROVIS 3730/3793 positioners, TROVIS SAFE 3731 (SIL positioner/PST), Leusch/AIR TORQUE/Vetec/Ringo subsidiaries. Strong in chemical/LNG utilities and Europe/Asia; document on PST and SOV architectures ([Samson PST doc](https://france.samsongroup.com/document/w02390en.pdf)). TROVIS SAFE 3731-3 is a single-acting positioner for spring-return actuators, rated SIL 2 single and SIL 3 redundant (HFT = 1), with PST and emergency venting ([Samson TROVIS SAFE](https://www.samsongroup.com/en/news/in-focus/details/news/products/trovis-safe-positioners-for-onoff-valves-in-safety-instrumented-systems); [Samson 3731-3 safety manual](https://argentina.samsongroup.com/document/e8387xen.pdf)). Type 3241 and the rest of the list **[model list general knowledge — verify]**.

**IMI Critical Engineering — IMI CCI (Switzerland/US).** Severe-service specialist: DRAG multi-stage disk-stack trim for anti-cavitation/low-noise (anti-surge, high-ΔP letdown, LNG boil-off, compressor recycle, turbine bypass), 100D/ 600D DRAG valves, VLB/ Sulzer steam conditioning, IMI Orton/Truflo/Zikesch (ball/ESD valves), IMI Z&J (high-temp slide valves), IMI Remosa (FCC). DRAG routes flow through a multi-stage tortuous path to limit trim velocity, erosion, vibration and noise. IMI also offers 840-3D (globe) / 860-3D (angle) valves with 3D-printed DRAG trim and the 100D multi-stage multi-turn DRAG valve ([Hydrocarbon Processing Oct 2023 — innovations](https://read.nxtbook.com/gulf_energy_information/hydrocarbon_processing/october_2023/innovations.html); [IMI process automation](https://processautomation.imiplc.com/industries/petrochemicals/chemicals)). The rest of the list **[general knowledge — verify]**.

**Det-Tronics (US; part of Spectrum Safety Solutions since July 2024).** Carrier completed the $1.425 bn sale of its Industrial Fire business (Det-Tronics, Marioff, Autronica, Fireye) to Sentinel Capital Partners on 2 July 2024, forming Spectrum Safety Solutions ([ARC — Carrier closes sale to Spectrum Safety Solutions](https://www.arcweb.com/blog/carrier-announces-close-1425b-sale-its-industrial-fire-business-spectrum-safety-solutions); [Det-Tronics news](https://www.det-tronics.com/news/news/brand_press_release/)). Det-Tronics has since acquired R.C. Systems (2025) and Optronics (2026) ([PrivSource — R.C. Systems](https://www.privsource.com/acquisitions/deal/aYSv5X); [PrivSource — Optronics](https://www.privsource.com/acquisitions/deal/deSOYL)). F&G specialist: X3301 multispectrum IR flame detector (81 m n-heptane ([Det-Tronics](https://www.det-tronics.com/Content/Documents/Flame-Detection-Solutions.pdf))), X3302 (hydrogen), X5200 UV/IR, X2200 UV, PointWatch Eclipse PIRECL (point IR gas), OPECL / FlexSight LS2000 (open path ([LS2000](https://www.det-tronics.com/products/flexsight-ls2000-optical-infrared-gas-detector/))), GT3000 (toxic), Eagle Quantum Premier (EQP, FM-approved F&G controller). X3301 FoV is 90° × 75° at ≥ 70 % of on-axis range ([X3301 specs](https://www.det-tronics.com/Content/Documents/90-1143-10.2-X3301-Specifications.pdf)). Models other than X3301/LS2000 **[general knowledge — verify]**.

**MSA Safety (US) incl. General Monitors.** Fixed gas & flame: Ultima X5000 / S5000 (point gas incl. XCell EC sensors), General Monitors IR400/IR5500 (point/open path), Observer-i (ultrasonic gas leak), FL4000H / FL500 (flame), Senscient ELDS (laser open path for H2S/CH4) **[general knowledge — verify]**. MSA white paper on MOS→EC H2S ([MSA](https://assetlibrary.msasafety.com/asset/d361c8b5-4f4c-4062-bd53-2ce915b32a9e/White-Paper-Upgrading-from-MOS-to-Electrochemical-Sensors-for-H2S-Gas-Detection.pdf)).

**Dräger (Germany).** Polytron 8000 series (8100 EC, 8200/8310 catalytic, 8700/8720 IR), PIR 7000/7200 (point IR), Polytron Pulsar 2 (open path), Flame 1x00/2x00/3000 series (flame), REGARD 7000 controllers; also portable detectors and breathing apparatus. Polytron 8700 IR is an explosion-proof transmitter for combustible gases using the PIR 7000 infrared sensor ([Dräger fixed gas detection](https://www.draeger.com/en_uk/Productfinder/Fixed-Gas-Detection)). Other models **[general knowledge — verify]**.

**Servomex (UK; Spectris).** Gas analysis specialist: paramagnetic O2 (MultiExact, SERVOPRO), zirconia (FluegasExact), NDIR/gas-filter correlation, TDLAS (SERVOTOUGH Laser 3 Plus for O2/CO/H2O/NH3), SERVOFLEX portables; trace-moisture and purity analysers for LNG/air-separation (Delta F, Hummingbird sensors). SERVOTOUGH Laser 3 Plus is a compact cross-stack TDL analyser using wavelength-modulation spectroscopy. Variants: Combustion (O2, CO, CO+CH4), Process (O2/CO) and Environmental (NH3 slip, EPA PS18). Approvals: ATEX Cat 3 / IECEx Zone 2 / C1D2. It is a gas analyser, not a SIL-certified device ([Servomex — Laser 3 Plus range](https://www.servomex.com/news/laser-3-plus-range); [Automation.com launch note](https://www.automation.com/en-us/products/product04/servomex-launches-servotough-laser-3-plus-laser-an)). Other models **[general knowledge — verify]**.

**Mettler-Toledo / ABB analyzers (liquid analysis).** Mettler-Toledo Process Analytics: InPro pH/ORP, dissolved O2, conductivity sensors, ISM digital sensors, M400/M800 transmitters, Thornton (pure water). ABB: Navigator series, AquaMaster, TB/TBX conductivity and pH (see ABB above). Used for produced water, boiler feed water, cooling water, effluent **[general knowledge — verify]**.

**Schneider Electric / Triconex (now under AVEVA/Schneider).** Triconex Tricon CX (TMR — triple modular redundant, 2oo3 voting) and Trident/Tri-GP, safety-certified to IEC 61508 SIL 3; widely used for ESD, F&G, burner management, compressor/turbine control (Triconex compressor control, formerly via Invensys/Foxboro). Foxboro EcoStruxure (I/A) DCS. Schneider states Tricon is TÜV Rheinland certified to SIL 3 (also marine and nuclear 1E), with TMR architecture, online module replacement and a hot-spare slot. Tricon CX is TÜV safety- and cyber-certified for SIL 1–3 ([Schneider — Tricon](https://www.se.com/ww/en/work/products/industrial-automation-control/triconex-safety-systems/logic-solver/tricon.jsp); [Schneider — Tricon CX](https://se.com/au/en/work/products/industrial-automation-control/triconex-safety-systems/logic-solver/tricon-cx.jsp)). Ownership history and other products **[general knowledge — verify]**.

**HIMA (Germany).** Independent safety-system specialist: HIMax (SIL 3, scalable redundancy, non-stop operation), HIQuad X (successor of HIQuad), HIMatrix (compact/distributed), SILworX engineering; strong on independent SIS in LNG, refineries, pipelines and rail **[general knowledge — verify]**. HIMax uses XMR architecture for non-stop SIL 3 with scalable redundancy (quad/triple/dual/single), and modules can be replaced online. Its IEC 61508 assessment is by TÜV Rheinland ([HIMA catalogue](https://www.acomee.com.mx/catalogos/catalogosh/HIMA.pdf); [exida SAEL — HIMA HIMax](https://exida.com/SAEL-Safety/HIMA_HIMax)).

---

## Gaps

1. **Search budget exhausted mid-research.** The following were *not* searched and rest on general knowledge (all flagged in text): MOV torque safety factors & stroke speeds; PSV pilot-operated valve limits, API 526 orifice letters, ASME accumulation percentages, bellows back-pressure limits (secondary sources conflict, 30–50 %); thermowell TW-2016 frequency-ratio limits (0.8 fn unverified), velocity collar / strake guidance; skin-TC installation practice; analyzer shelter ventilation rates; instrument-air header pressures and receiver hold-up times; cabinet spare and heat-load practice; F&G coverage targets (e.g., 90/80/60 %); gas detector alarm set points; vendor flagship model lists in `## Other vendors` (and Det-Tronics' current corporate owner).
2. **Primary standard text not accessed.** ISO 5167-2 straight-length tables, IEC 60534-8-3, ANSI/FCI 70-2 class VI table, API MPMS 3.1B Table 1, AGA 9 performance limits, API 520 Pt II, IEC 60079-14:2024 gland rules, EN 15714-2 starts/h table, ASME PTC 19.3 TW-2016 — figures here are from secondary summaries and should be checked in the standard for any binding decision.
3. **Unverified numbers in vendor material.** Rosemount 8800 vortex turndown differs between Emerson documents (38:1 vs 15:1); Det-Tronics X3301 range differs between documents (210 ft vs 265 ft); Micro Motion gas accuracy (±0.35 % vs ±0.25 % vs ±0.20 % enhanced) — always quote the current datasheet for the exact model code.
4. **Not covered / thin.** Magnetic level gauge float SG limits; Annubar accuracy/turndown; VDI/VDE 3513 rotameter classes; IEC 60584 type K tolerance; Yokogawa EJA/EJX specs; clamp-on ultrasonic quantitative accuracy; turbine meter repeatability criteria (API MPMS 4.8/5.3); wet-gas and multiphase metering; acoustic leak detectors; HIPPS (API 17O / IEC 61511) beyond ESD basics; wireless instrumentation; fieldbus segment design; radiation licensing; LNG-specific cryogenic instrument practice (extended bonnets, cold-box instruments, LTD gauges).
5. **Network.** WebFetch to several hosts was blocked (e.g., processingmagazine.com — ENOTFOUND); allowing these would permit quoting primary content more precisely.
