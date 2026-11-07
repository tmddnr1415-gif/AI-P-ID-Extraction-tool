# Vendor Knowledge: Yokogawa, Bently Nevada (Baker Hughes), WIKA

Technical facts for vendor selection and spec-compliance checks on oil & gas, LNG and petrochemical EPC projects.

---

## How to use this file

- **Scope.** This file covers three vendors that often appear on the same EPC Approved Vendor List (AVL):
  - **Yokogawa:** field instruments, analyzers, DCS/SIS, and Main Automation Contractor (MAC) awards.
  - **Bently Nevada:** machinery protection and condition monitoring.
  - **WIKA:** mechanical pressure and temperature instruments, thermowells, diaphragm seals, small transmitters, and calibration equipment.
- **Source tags.** A link follows each number to show where it came from.
  - **[general knowledge — verify]** means the item comes from domain knowledge and was not confirmed against a vendor document while this file was built. Check it against the current datasheet or General Specification (GS) before it goes into a datasheet, a bid tabulation (TBE) or a SIL calculation.
  - **[vendor marketing]** means the figure comes only from a product web page, not a GS or datasheet.
  - **[third-party copy]** means the document was a reseller or repost copy of an official datasheet. The revision may not be current.
- **Revisions change.** Vendor GS and datasheets are revised often. Accuracy figures depend on the reference conditions, the span or turndown, the conformance basis (for example Yokogawa EJX states ±3σ), and the options ordered. Always quote the GS number and edition in the TBE.
- **Discontinued models.** These are flagged ⚠ DISCONTINUED. Do not propose them for new-build projects. They matter mainly for brownfield replacement and spares.
- **Research limits.** The vendor hosts (yokogawa.com, wika.com and its regional hosts, dam.bakerhughes.com) and most distributor hosts could not be fetched directly; facts were taken from web-search extracts of the linked documents. A second research pass (Nov 2026) added WIKA data-sheet sources and confirmed several Bently Nevada and Yokogawa figures; remaining unverified items keep the tag. See [Gaps](#gaps).

---

## Table of contents

1. [Yokogawa](#1-yokogawa)
   - 1.1 [Company and branding (OpreX)](#11-company-and-branding-oprex)
   - 1.2 [DPharp pressure and DP transmitters (EJA-E, EJX-A)](#12-dpharp-pressure--dp-transmitters)
   - 1.3 [Temperature transmitters (YTA)](#13-temperature-transmitters-yta)
   - 1.4 [Flow: ADMAG magmeters, ROTAMASS Coriolis, vortex, ultrasonic](#14-flow)
   - 1.5 [Level](#15-level)
   - 1.6 [Analyzers (TDLS8000, GC8000, zirconia O2, liquid)](#16-analyzers)
   - 1.7 [Field Wireless (ISA100.11a)](#17-field-wireless-isa10011a--iec-62734)
   - 1.8 [CENTUM VP DCS](#18-centum-vp-dcs)
   - 1.9 [ProSafe-RS SIS](#19-prosafe-rs-sis)
   - 1.10 [STARDOM, FA-M3, Exaopc, PRM, FieldMate](#110-stardom-fa-m3-exaopc-prm-fieldmate)
   - 1.11 [Yokogawa as Main Automation Contractor (MAC)](#111-yokogawa-as-main-automation-contractor-mac)
   - 1.12 [Yokogawa engineering notes](#112-yokogawa-engineering-notes)
2. [Bently Nevada (Baker Hughes)](#2-bently-nevada-baker-hughes)
   - 2.1 [3300 XL proximity transducer systems](#21-3300-xl-proximity-transducer-systems)
   - 2.2 [Seismic transducers](#22-seismic-transducers-velomitor--accelerometers)
   - 2.3 [3500 machinery protection system](#23-3500-machinery-protection-system)
   - 2.4 [Orbit 60, ADAPT and 3701](#24-orbit-60-adapt-3701)
   - 2.5 [System 1, Ranger and Trendmaster](#25-system-1-ranger-trendmaster)
   - 2.6 [API 670 compliance checklist](#26-api-670-compliance-checklist)
   - 2.7 [Typical machine-train protection architecture](#27-typical-machine-train-protection-architecture)
3. [WIKA](#3-wika)
   - 3.1 [Pressure gauges](#31-pressure-gauges)
   - 3.2 [Diaphragm seals](#32-diaphragm-seals)
   - 3.3 [Thermowells and the ASME PTC 19.3 TW calculation](#33-thermowells--asme-ptc-193-tw)
   - 3.4 [Thermometers](#34-thermometers-bimetal-gas-actuated)
   - 3.5 [Temperature transmitters and TC/RTD assemblies](#35-temperature-transmitters-and-tcrtd-assemblies)
   - 3.6 [Pressure transmitters and switches](#36-pressure-transmitters)
   - 3.7 [Level (KSR) and flow (WIKA flow)](#37-level-ksr-and-flow-wika-flow)
   - 3.8 [Test and calibration](#38-test--calibration)
   - 3.9 [WIKA engineering notes](#39-wika-engineering-notes)
4. [Cross-vendor quick comparisons](#4-cross-vendor-quick-comparisons)
5. [Gaps](#gaps)

---

## 1. Yokogawa

### 1.1 Company and branding (OpreX)

- **OpreX** is Yokogawa's umbrella brand for its industrial automation business. It has five categories: **OpreX Transformation, OpreX Control, OpreX Measurement, OpreX Execution and OpreX Lifecycle** ([Yokogawa PRM page](https://www.yokogawa.com/solutions/products-platforms/oprex/oprex-transformation/oprex-asset-management-and-integrity/field-device-management-prm)).
  - CENTUM VP and ProSafe-RS sit under OpreX Control. Field instruments and analyzers sit under OpreX Measurement. PRM sits under OpreX Transformation (Asset Management and Integrity family) (same source).
- **Functional-safety stance for transmitters.** Yokogawa states that all of its pressure transmitters are designed and certified to IEC 61508:2010 Parts 1–7 and IEC 61511:2004 Parts 1–3 ([Yokogawa AU EJA110E page](https://www.yokogawa.com/au/solutions/products-and-services/measurement/field-instruments-products/pressure-transmitters/differential-pressure/eja110e/)).
  - They are certified for **single-transmitter use in SIL 2** and **dual-transmitter use in SIL 3** with no special option required (same source).
- **Proprietary handheld protocol.** Yokogawa transmitters support **BRAIN** alongside HART, FOUNDATION Fieldbus H1 and PROFIBUS PA. FieldMate lists BRAIN, FF H1, HART, PROFIBUS, ISA100.11a and Modbus ([FieldMate page](https://yokogawa.com/solutions/products-platforms/field-instruments/device-smart-communicators-2/mobile-field-device-management-fieldmate)).

### 1.2 DPharp pressure and DP transmitters

DPharp is Yokogawa's silicon resonant sensor technology [general knowledge — verify]. It is used in two series:

- **EJA-E**, the mainstream series.
- **EJX-A**, the premium series.

Both are 4–20 mA HART, FF and PROFIBUS PA capable, depending on the model code [general knowledge — verify].

| Model | Function | Key specs | Approvals / SIL | Typical use | Source |
|---|---|---|---|---|---|
| **EJA110E** | DP transmitter | Reference accuracy **±0.055 % of span**; **±0.04 %** option. Static-pressure (secondary variable) ±0.5 % of span. Stability **±0.1 % of URL / 10 years**. Over-pressure effect ±0.03 % URL. Turndown **100:1**. | Exida and TÜV SIL 2 single / SIL 3 dual | DP flow (orifice, venturi), DP level, filter ΔP | [Yokogawa EJA110E](https://www.yokogawa.com/solutions/products-and-services/measurement/field-instruments-products/pressure-transmitters/differential-pressure/eja110e); [im-tek reseller spec table](https://im-tek.com/yokogawa-eja110e-differential-pressure-transmitter) [third-party copy]. Note: the "±…% of span" wording is confirmed only by the reseller. |
| **EJA530E** | In-line gauge pressure | Accuracy **±0.055 %**. Stability **±0.1 % / 10 years**. Response time **90 ms**. | SIL 2 / SIL 3 (as above) | Line and vessel gauge pressure, pump discharge | [Yokogawa EU EJA530E](https://www.yokogawa.com/eu/solutions/products-and-services/measurement/field-instruments-products/pressure-transmitters/gauge-pressure/eja530e/) |
| **EJA118E** ⚠ DISCONTINUED (US site) | DP with **two remote diaphragm seals** | Accuracy **±0.2 %**. Response **200 ms**. Wetted diaphragm options include 316L SS, Hastelloy C-276, tantalum and titanium. | — | DP level on corrosive, viscous or hot services | [Yokogawa EJA118E page](https://www.yokogawa.com/solutions/products-and-services/measurement/field-instruments-products/pressure-transmitters/liquid-level/eja118e); [Yokogawa US discontinued list](https://yokogawa.com/us/solutions/discontinued/eja118e); [GS 01C31H01 (EJA118 copy)](https://www.insatech.com/media/jpepcp5x/gs_eja118ez_gs01c31h01-11en_17ed.pdf) [third-party copy] |
| **EJX110A** | Premium DP | Accuracy **±0.04 %**; **±0.025 %** option. Stability **±0.1 % / 15 years**. | SIL 2 / SIL 3 | Custody-adjacent DP flow, critical control loops | [Yokogawa US EJX110A](https://www.yokogawa.com/us/solutions/products-and-services/measurement/field-instruments-products/pressure-transmitters/differential-pressure/ejx110a/) |
| **EJX910A** | Multivariable (DP + static P + process temperature input) with mass-flow computation | Mass flow **±1.0 % of rate over 10:1 flow range** (assumes 100:1 DP range), liquids and gases, uncalibrated orifice. Totalized mass flow 1.0 %. DP accuracy ±0.04 % of span. Specs stated at **±3σ** conformance. | — (check GS) | Steam, gas and liquid flow with live P/T compensation from one device (orifice, nozzle, venturi) | [GS 01C25R01-01EN, 34th ed. copy](https://www.insatech.com/media/50aacz2k/gs_ejx910a_gs01c25r01-01en_34ed.pdf) [third-party copy]; [Yokogawa EJX910A page](https://www.yokogawa.com/us/solutions/products-and-services/measurement/field-instruments-products/pressure-transmitters/mass-flow/ejx910a/) |

**Selection notes, DPharp**

- **EJA-E or EJX-A.** Choose EJX where the spec calls for ±0.04 % or better, or for 15-year stability to stretch calibration intervals. Otherwise EJA-E normally satisfies a typical ±0.075 % to ±0.1 % project requirement (sources above).
- **Remote seals.** EJA118E appears as discontinued on Yokogawa's US site. The current DPharp seal offering is the **EJXC80A / EJAC80E Diaphragm Seal System**: a GP or DP transmitter with one or two seals, direct- or remote-mounted; the direct-mount DP version uses the EJX110A or EJA110E, and a **compensating capillary** option reduces ambient-temperature drift. Response time differs between Yokogawa pages (120 ms vs 200 ms) ([Yokogawa EJXC80A/EJAC80E diaphragm seal](https://yokogawa.com/solutions/products-platforms/field-instruments/pressure-transmitters/liquid-level/ejxc80a-ejac80e-diaphragm-seal); [direct-mounted page](https://yokogawa.com/us/solutions/products-and-services/measurement/field-instruments-products/pressure-transmitters/liquid-level/ejxc80a-ejac80e-direct-mounted)).
- **EJX910A is not a fiscal flow computer.** For custody transfer, use a separate API MPMS 21.1 flow computer. STARDOM FCN/FCJ can perform that role (see 1.10).
- **SIL applicability.** Like YTA, SIL use may depend on the firmware revision and manufacturing date. Request the SIL certificate and the safety manual for the exact model code [general knowledge — verify].

### 1.3 Temperature transmitters (YTA)

| Model | Function | Key specs | SIL | Source |
|---|---|---|---|---|
| **YTA610** | Field-mount, dual-input temperature transmitter (HART) | Pt100 accuracy **±0.14 °C (±0.25 °F)**. Dual-sensor input. Accepts sensor-specific Callendar-Van Dusen coefficients for sensor matching. | Certified to IEC 61508:2010 / IEC 61511; **SIL 2 single / SIL 3 dual**, no special option | [Yokogawa YTA610](https://www.yokogawa.com/solutions/products-platforms/field-instruments/temperature-transmitters/field-mount/yta610-temperature-transmitter/) |
| **YTA710** | Premium field-mount, single or dual input | Linearization for 20 sensor and input types. Dual input enables **failed-sensor backup, averaging or differential temperature**. CVD sensor matching. | SIL eligible only from firmware **R1.03.01 or later** and a manufacturing-date cutoff. Yokogawa pages disagree: Dec 2016 vs Mar 2017 for HART. Check the serial number against Yokogawa's SIL applicability table. | [Yokogawa YTA710](https://www.yokogawa.com/solutions/products-and-services/measurement/field-instruments-products/temperature-transmitters/field-mount/yta710-temperature-transmitter/) |

- Older YTA110, YTA310 and YTA320 models are legacy. Check their status before specifying them [general knowledge — verify].

### 1.4 Flow

#### ADMAG TI magnetic flowmeters (AXG, AXW)

| Model | Function | Key specs | Source |
|---|---|---|---|
| **ADMAG AXG** (AXG1A high-grade transmitter / integral) | General-purpose and high-performance magmeter | Size **2.5–500 mm** (sensor combination), **2.5–400 mm** integral. **Standard accuracy ±0.3 % of rate** (0.15–10 m/s) ([Yokogawa US ADMAG AXG](https://www.yokogawa.com/us/solutions/products-and-services/measurement/field-instruments-products/flow-meters/magnetic-flowmeters/admag-axg-admagti-magnetic-flowmeters/); [ADMAG TI bulletin BU01E21A01-01EN](https://web-material3.yokogawa.com/23/10881/file_name/BU01E21A01-01EN.pdf)). With option HF2 at 80–200 mm: ±0.35 % of rate ±1 mm/s ([GS 01E22A11-03JA](https://web-material3.yokogawa.com/GS01E22A11-03JA.pdf)). High-accuracy option **±0.15 % of rate (25–200 mm)**. Figures are shipping accuracy on Yokogawa's water rig (same GS). | [Yokogawa ADMAG AXG](https://www.yokogawa.com/solutions/products-and-services/measurement/field-instruments-products/flow-meters/magnetic-flowmeters/admag-total-insight/admag-axg-admagti-magnetic-flowmeters/) [vendor marketing]; English GS 01E22A01-01EN not read |
| **ADMAG AXW** (AXW4A transmitter / integral) | Large-bore, water and wastewater, general | Accuracy **±0.35 % of reading** (AXW sensor combinations) | [Yokogawa ADMAG AXW](https://www.yokogawa.com/solutions/products-and-services/measurement/field-instruments-products/flow-meters/magnetic-flowmeters/admag-total-insight/admag-axw-admagti-magnetic-flowmeters/) [vendor marketing] |

- Magmeters need conductive liquids. They are not applicable to hydrocarbons, so their O&G use is limited to cooling water, produced water, chemical dosing and effluent [general knowledge — verify].

#### ROTAMASS Total Insight (TI) Coriolis

- The family GS is **GS 01U10B00-00EN-R** (2nd ed., Sep 2025). Accuracy is in section 2.2. The per-line GS documents are **GS 01U10B02 (Supreme)**, **GS 01U10B05 (Intense)** and **GS 01U10B03 (Giga)** ([Yokogawa GS 01U10B00-00EN-R](https://web-material3.yokogawa.com/FY2_GS01U10B00-00EN-R_2_0_284564.pdf)).
- **TI accuracy (product page, [vendor marketing]):** mass flow **liquid up to ±0.1 %** for all lines; **gas up to ±0.35 %** (Prime, Supreme, Giga) and **up to ±0.50 %** (Nano) ([Yokogawa US ROTAMASS TI](https://www.yokogawa.com/us/solutions/products-and-services/measurement/field-instruments-products/flow-meters/coriolis-flow-meters/rotamass-total-insight-coriolis-mass-flow-and-density-meters/)). Per-line GS: Prime **GS 01U10B04** ([GS 01U10B04-00EN-R](https://web-material3.yokogawa.com/FY2_GS01U10B04-00EN-R_7_0_284298.pdf)), Hygienic **GS 01U10B06** ([GS 01U10B06-00EN-R](https://web-material3.yokogawa.com/FY2_GS01U10B06-00EN-R_7_0_284296.pdf)). Use the GS §2.2 tables (with zero stability) for TBE figures.
- The older ROTAMASS 3 series published **±0.1 % of reading + zero stability (liquid)** and **±0.5 % (gas)** ([Yokogawa technical report rd-te-n05401-002](https://web-material3.yokogawa.com/1/11309/tabs/rd-te-n05401-002.pdf)). Do not quote these figures for TI.
- Line names (Nano, Prime, Supreme, Intense, Hygienic, Giga — six lines per the product page above; descriptions below are [general knowledge — verify]):
  - **Nano:** small flows.
  - **Prime:** cost-optimized.
  - **Supreme:** high accuracy.
  - **Intense:** high pressure, for example compressed natural gas (CNG) and hydrogen dispensing.
  - **Hygienic.**
  - **Giga:** large line sizes, for example marine bunkering and loading.
- Custody-transfer variants have a dedicated GS ([RCCx3 Custody GS ed.12](https://automation.yodify.com/Documentation/Document/JlG2Q/RCCx3-GS-Custody-EN-ed12.pdf)) [third-party copy].

#### Vortex: digitalYEWFLO (DY) ⚠ DISCONTINUED → VY series

| Model | Key specs | Source |
|---|---|---|
| **digitalYEWFLO DY** ⚠ DISCONTINUED | Liquid **±0.75 % of reading** (Reynolds-number dependent; typical ±0.5 % not guaranteed). Gas and steam **±1.0 % of reading**. Reduced-bore **R1**: flange 25–200 mm, detector 15–150 mm. **R2**: flange 40–200 mm, detector 15–100 mm. Reduced-bore liquid accuracy ±1.0 %. | [Yokogawa DY discontinued page](https://www.yokogawa.com/uk/solutions/discontinued/digitalyewflo-dy/); [GS 01F06A00-01EN](https://automation.yodify.com/Documentation/Document/LJelL/GS01F06A00-01EN-023.pdf) [third-party copy] |
| **VY series** (successor, launched 2022) | Liquid **±0.75 % of reading**. Gas and steam **±1 % of reading**. Keeps the YEWFLO detection structure, so it drops into the same piping locations. | [Yokogawa VY series](https://yokogawa.com/us/solutions/products-and-services/measurement/field-instruments-products/flow-meters/vortex-flow-meters/vortex-flowmeters-vy-series); [GS 01F07A00-01EN](https://web-material3.yokogawa.com/1/39714/details/GS01F07A00-01EN.pdf) |

- Yokogawa's own material notes that vortex accuracy depends on installation conditions, including straight runs and Reynolds number (VY page above).
- The integral-reducer (reduced-bore) design keeps the velocity above the low-flow cut-off on oversized lines (DY page above).

#### Ultrasonic

- **US300FM** clamp-on transit-time ⚠ **DISCONTINUED 31 May 2017** ([Yokogawa US300FM](https://yokogawa.com/solutions/discontinued/us300fm-ultrasonic-flowmeter)).
  - Pipe sizes **25–6,500 mm**; velocity **0.01–25 m/s**.
  - Accuracy **1–3 % of reading** (application dependent).
  - Needs ≥10 D of straight pipe upstream.
  - Fluid temperature **−30 to +130 °C**.
  - Main unit IP65.
  - GS 01G05B03-01E ([GS copy](https://en.sekorm.com/doc/720458.html)) [third-party copy].
- "US300" and "US350" were not found as current models. Yokogawa has no confirmed current in-house ultrasonic flowmeter in the sources gathered (see [Gaps](#gaps)).

### 1.5 Level

- Yokogawa's level page lists **non-contact radar, ultrasonic, DP-type and guided-pulse level meters** ([Yokogawa level meters](https://yokogawa.com/bh/solutions/products-and-services/measurement/field-instruments-products/level-meters)). It does not say whether the radar and GWR units are in-house designs or partner (OEM) products.
- **DP level is Yokogawa's core level technology.** The EJX110A is marketed as a level transmitter too ([EJX110A level page](https://www.yokogawa.com/solutions/products-and-services/measurement/field-instruments-products/level-meters/level-transmitters/ejx110a)). Remote-seal DP covers interface and density level.
- Yokogawa's software library hosts DD/DTM files for third-party GWR and radar: **Magnetrol Eclipse 706/705, K-TEK MT5000, E+H Levelflex FMP5x / Micropilot FMR5x** ([Yokogawa library – Magnetrol 706 DD](https://www.yokogawa.com/ro/library/documents-downloads/software/magnetrol-eclipse-model-706-guided-wave-radar-level-transmitter)). This shows host integration, not supply.
- **Practical implication for MAC packages.** Radar, GWR, servo and tank-gauging instruments on Yokogawa-MAC projects are normally sourced from specialist vendors (Emerson Rosemount, E+H, VEGA, AMETEK Magnetrol, Honeywell Enraf). Yokogawa integrates them via HART, FF or Modbus [general knowledge — verify].

### 1.6 Analyzers

| Model | Function | Key specs | SIL | Source |
|---|---|---|---|---|
| **TDLS8000** | In-situ tunable diode laser spectrometer (cross-stack or cross-duct) | **O2 range** 0–1 % (min) to 0–25 % (max); repeatability ±1 % of reading or ±0.01 % O2, whichever is greater; linearity ±1 % FS. **CO** 0–200 to 0–10,000 ppm; repeatability ±2 % of reading or ±1 ppm; linearity ±1 % FS. NH3 max range differs by source: 0–5,000 ppm in the 2016 GS vs 0–50,000 ppm on current pages. Also measures CH4, H2O and others depending on the laser. | **SIL 2 single / SIL 3 dual** capability (IEC 61508), covering digital I/O and HART/Modbus TCP. H2O (%) analyzer excluded from the SIL certificate. | [GS 11Y01D01-01EN](https://web-material3.yokogawa.com/24/15840/files/GS11Y01D01-01EN-01.pdf); [Yokogawa TDLS8000](https://www.yokogawa.com/ca/solutions/products-and-services/measurement/analyzers/gas-analyzers/tunable-diode-laser-spectrometer/tdls8000-tunable-diode-laser-spectrometer/) |
| **GC8000** | Process gas chromatograph | **Standard oven:** up to 5 valves and 2 detectors. **Large oven:** up to 7 valves and 2 detectors. Up to **3 ovens**. Detectors **TCD and FID, 1 ppm to 100 %**. Samples: gases or volatile liquids with boiling point ≤400 °C. Max analysis cycle 21,600 s. **12-inch colour touchscreen HMI** rated for Class I Div 1. Valves and detectors are shared with the GC1000 Mark II. | — | [Yokogawa Europe GC8000 catalogue (DirectIndustry)](https://pdf.directindustry.com/pdf/yokogawa-europe/gc8000-process-gas-chromatographs/19033-604596.html); [Yokogawa MEA GC8000](https://www.yokogawa.com/mea/solutions/products-and-services/measurement/analyzers/gas-analyzers/process-gas-chromatographs/process-gas-chromatograph-gc8000/); [Control Global](https://www.controlglobal.com/measure/pressure/article/11381051/52-years-of-gc-solutions-help-create-a-new-process-gc) |
| **ZR22G + ZR802G** | Separate-type zirconia O2 (and humidity) analyzer: in-situ probe plus converter | O2 range **0.01–100 vol %**. Response **≤5 s to 90 %**. Heater replaceable on site. Cell-resistance self-diagnostics. Converter displays cell temperature and EMF. **High-temperature service:** with the **ZO21P-H high-temperature probe adapter** (for sample gas about 700–1,400 °C) the sample temperature is **0–1,400 °C with a SiC sampling probe** or **0–800 °C with a SUS 310S probe**; auxiliary ejector E7046EC/EN for negative sample pressure ([GS 11M12A01 copy](https://www.scribd.com/document/484707623/GS11M12A01-E-H) [third-party copy]; [Yokogawa reheating-furnace application note](https://yokogawa.com/cis/library/resources/application-notes/measurement-and-monitoring-of-o2-concentrations-in-steel-mill-reheating-furnaces)). The direct-insertion detector's own maximum gas temperature was not confirmed. | — | [Yokogawa ZR22G/ZR802G](https://www.yokogawa.com/solutions/products-and-services/measurement/analyzers/gas-analyzers/oxygen-analyzers/separate-type-oxygen-analyzer-zr22g-zr802g/) |
| **FLXA402** | 4-wire, multi-channel liquid analyzer | Up to **5 sensors**: pH/ORP, conductivity, inductive conductivity, DO. Continuous pH electrode diagnostics (impedance, asymmetry, slope). **SENCOM 4.0** smart digital sensors (plug-and-play, hot swap). | — | [Yokogawa FLXA402](https://www.yokogawa.com/eu/solutions/products-and-services/measurement/analyzers/liquid-analyzers/ph-analyzers/multi-channel-4-wire-analyzer-flxa402/); [SENCOM smart digital sensor](https://www.yokogawa.com/us/solutions/products-platforms/process-analyzers/liquid-analyzers/smart-digital-sensor/) |
| **FLXA202 / FLXA21** | 2-wire loop-powered liquid analyzer | Details not retrieved | — | [Yokogawa liquid analyzers](https://www.yokogawa.com/de/solutions/products-and-services/measurement/analyzers/liquid-analyzers/) |

- **Typical applications** [general knowledge — verify]:
  - **TDLS8000:** fired-heater combustion O2/CO (safety and efficiency), FCC regenerator, flare, and ammonia-slip measurement after SCR.
  - **GC8000:** LNG feed and product composition, fuel-gas BTU, and column overhead purity.
  - **Zirconia:** boilers and furnaces.
- **Analyzer houses.** Yokogawa supplies complete analyzer shelters. For example, it won the analyzer-house order for PETRONAS RAPID ([digitalrefining.com](https://www.digitalrefining.com/news/1004556,yokogawa-wins-order-to-supply-analyzer-house-for-rapid-project.html)).

### 1.7 Field Wireless (ISA100.11a / IEC 62734)

- **YFGW410 Field Wireless Management Station:** system manager, security manager and gateway, based on **ISA100.11a / IEC 62734** ([Yokogawa YFGW410](https://www.yokogawa.com/au/solutions/products-and-services/measurement/field-instruments-products/field-wireless/wireless-infrastructure/yfgw410-field-wireless-management-station/)).
  - Capacity is about **200 devices at a 1 s update** and about **500 devices at a 5 s update** ([Bulletin BU01W01A12-01EN](https://automation.yodify.com/Documentation/Document/QwYLY/BU01W01A12-01EN.pdf)) [third-party copy].
  - It handles up to **20 YFGW510/520 access points** (same source).
- **CENTUM VP integration:** one **ALE111** Ethernet communication module handles up to **128 wireless devices** and **4 gateways** ([Yokogawa technical report](https://yokogawa.com/library/resources/yokogawa-technical-reports/the-control-system-integrated-with-field-wireless-devices)).
- **PRM** manages ISA100 Wireless devices alongside HART and FF ([Yokogawa PRM page](https://www.yokogawa.com/solutions/products-platforms/oprex/oprex-transformation/oprex-asset-management-and-integrity/field-device-management-prm)).
- **Engineering note.** ISA100 and WirelessHART are not interoperable. A Yokogawa wireless network uses ISA100 devices, and Emerson-led sites use WirelessHART. Specify one standard per site in the project instrumentation philosophy [general knowledge — verify]. Wireless is normally limited to monitoring and non-critical loops, never SIF (safety instrumented function) inputs [general knowledge — verify].

### 1.8 CENTUM VP DCS

| Item | Facts | Source |
|---|---|---|
| **Release** | **CENTUM VP R7** released in 2025 (CENTUM 50th-anniversary year), positioned as a first step to autonomous operations. **R7.01.10 (Oct 2025)** added dynamic reconfiguration of the PROFINET communication I/O card. Exaopc pages list support for CENTUM VP R6.12 and R7.01. No R7-specific FCS hardware change was found. | [Yokogawa CENTUM VP](https://www.yokogawa.com/sk/solutions/products-and-services/control/control-and-safety-system/distributed-control-systems-dcs/centum-vp); [Exaopc page](https://yokogawa.com/solutions/products-platforms/solution-based-software/data-historian/centum-opc-server-exaopc) |
| **FCS hardware** | **AFV30D** (19-inch rack-mount) and **AFV40D** (cabinet-mount): duplexed field control units for Vnet/IP and FIO. Dual-redundant Vnet/IP and power. | [Yokogawa library doc 0000029120](https://library.yokogawa.com/document/download/AxkHnJ89/0000029120//EN); [GS 33J60E10-01EN copy](https://www.scribd.com/document/550685564/GS33J60E10-01EN) [third-party copy] |
| **N-IO FCU** | **A2FV50D** handles both N-IO and FIO, with a dual-redundant Vnet/IP interface. Processor **CP471** needs CENTUM VP **R6.05+**. | [GS 33J62E10-01EN](https://web-material3.yokogawa.com/GS33J62E10-01EN_007.pdf) |
| **N-IO** | Each channel is software-configurable as AI, AO, DI or DO. Signal conditioners are built into the baseplate, so external conditioning is usually unnecessary. The same baseplate supports single or dual-redundant configuration. **I/O modules with built-in IS barriers** are available. Reduces footprint and marshalling. | [Yokogawa CENTUM VP (N-IO)](https://www.yokogawa.com/in/solutions/products-and-services/control/distributed-control-systems-dcs/centum-vp) [vendor marketing] |
| **FF H1** | **ALF111** FF H1 module, supported on AFV30D/AFV40D | [ALF111 GS copy](https://www.scribd.com/document/688064246/ALF-111) [third-party copy] |
| **Control network** | **Vnet/IP**: dual-redundant, Ethernet-based, 1 Gbps [general knowledge — verify] | GS 33J60E10 (above) |
| **Third-party integration** | The **Unified Gateway Station (UGS)** connects STARDOM FCN/FCJ and third-party controllers to CENTUM VP | [STARDOM tech report](https://yokogawa.com/us/library/resources/yokogawa-technical-reports/fcn-and-fcj-autonomous-controllers-in-stardom) |
| **HMI / engineering** | HIS (Human Interface Station) for operation. ENG / Automation Design Suite (AD Suite) for engineering, shared with ProSafe-RS. | [ProSafe-RS page](https://www.yokogawa.com/tr/solutions/products-and-services/control/control-and-safety-system/process-safety-system-prosafe-rs/) |

- **FCS terminology** [general knowledge — verify]:
  - **FCS:** Field Control Station.
  - **FCU:** Field Control Unit, the CPU node.
  - **FIO:** legacy Field-network I/O (ANB10/ANR10 nodes).
  - **N-IO:** the newer universal I/O.
  - **AFV10D:** the older FCU, now superseded by AFV30D/AFV40D.

### 1.9 ProSafe-RS SIS

| Item | Facts | Source |
|---|---|---|
| Certification | **TÜV certified to IEC 61508 SIL 3**. SIL 3 in a **single-module configuration**, so redundancy is for availability, not for SIL. TÜV Rheinland certificate **968/EZ 196.51/21** (issued 24 Feb 2021) covers **ProSafe-RS R4.06**: IEC 61508 up to SIL 3, IEC 62061 SILCL 3, reviewed against IEC 61511 and EN 50156-1; valid only for the listed hardware/software revisions. Latest release listed: **R4.12.00 (Jan 2026)**. | [TÜV certificate 968/EZ 196.51/21](https://web-material3.yokogawa.com/1/30962/files/968_EZ_196_51_21_en_el.pdf); [Yokogawa EU ProSafe-RS](https://www.yokogawa.com/eu/solutions/products-and-services/control/control-and-safety-system/safety-instrumented-systems-sis/process-safety-system-prosafe-rs/); [Yokogawa ProSafe-RS](https://www.yokogawa.com/tr/solutions/products-and-services/control/control-and-safety-system/process-safety-system-prosafe-rs/); [Yokogawa tech report](https://yokogawa.com/library/resources/yokogawa-technical-reports/safety-technologies-incorporated-in-the-safety-control-station) |
| Controller | **SCS (Safety Control Station)**. Logic in IEC 61131-3 FBD, ladder, and [general knowledge — verify] structured text. Architecture derived from the CENTUM FCS. | Tech report (above) |
| DCS integration | SCS sits on the same **Vnet/IP** network as CENTUM VP. **No gateway** is needed for SIS↔DCS data, and the HIS operates and monitors the SCS. Integrity of the integrated architecture comes from memory protection of safety areas and priority execution of safety functions. | Tech report and ProSafe-RS page (above) |
| Overrides | Maintenance overrides from the HIS are blocked unless a **hardware permission switch** is in the permit position | Tech report (above) |
| Engineering | **SENG** (Safety Engineering PC) is the dedicated ProSafe-RS engineering station, with password and key-switch protected download [general knowledge — verify] | — |
| Variants | **ProSafe-RS Lite** for smaller SIS. **ProSafe-SLS**: older hard-wired, solid-state SIS for SIL 4 / burner-management-type applications [general knowledge — verify]. | — |

- **Separation debate.** Integrating the SIS on the DCS network is acceptable under IEC 61511 provided the independence, cyber-security (IEC 62443) and common-cause requirements are addressed. Many operator specifications still require a separate engineering workstation and a firewall or one-way data path. Check the project's SIS philosophy [general knowledge — verify].

### 1.10 STARDOM, FA-M3, Exaopc, PRM, FieldMate

| Product | Function | Key facts | Source |
|---|---|---|---|
| **STARDOM FCN / FCJ** | Network-based controller and RTU | **FCN:** modular; all key parts can be duplexed. **FCJ:** all-in-one with limited I/O. IEC 61131-3 programming. Can act as an **API MPMS Ch. 21.1 electronic flow measurement** system while running control. Modbus master and slave at the same time. **FCN/FCJ R4.40 and VDS R9.10 released 10 Sep 2024.** | [Yokogawa tech report](https://yokogawa.com/us/library/resources/yokogawa-technical-reports/fcn-and-fcj-autonomous-controllers-in-stardom); [Yokogawa PLC/RTU page](https://yokogawa.com/solutions/products-platforms/control-system/process-control-plc-rtu) |
| **FA-M3** | Range-free PLC (factory and machine automation) | Used alongside STARDOM. Architecture not retrieved. | [Yokogawa PLC/RTU page](https://yokogawa.com/solutions/products-platforms/control-system/process-control-plc-rtu) |
| **Exaopc** | CENTUM OPC server | OPC **DA, A&E, HDA, Security, Batch**. Separate **Exaopc OPC UA** package (DA, A&C). Connects to CENTUM VP over Vnet/IP. **R3.82 (Nov 2025)**. Clients include Exaquantum (PIMS) and Exapilot. | [Yokogawa Exaopc](https://yokogawa.com/solutions/products-platforms/solution-based-software/data-historian/centum-opc-server-exaopc); [GS 36J02A10-01E](https://ymx.yokogawa.com/content/S636721774743944845/GS36J02A10-01E_044.pdf) |
| **PRM** (Plant Resource Manager) | Asset management | FF, HART, ISA100 Wireless and PROFIBUS; EDDL and FDT device integration. **R4.04 released Nov 2020**; no newer release was found. | [Yokogawa PRM](https://www.yokogawa.com/solutions/products-platforms/oprex/oprex-transformation/oprex-asset-management-and-integrity/field-device-management-prm); [PRM R4.04 press release](https://yokogawa.com/news/press-releases/2020/2020-10-15) |
| **FieldMate** | PC/tablet device configuration tool | BRAIN, FF H1, HART, PROFIBUS, ISA100.11a, Modbus; FDT/DTM. Synchronizes device data with PRM for commissioning history. | [Yokogawa FieldMate](https://yokogawa.com/solutions/products-platforms/field-instruments/device-smart-communicators-2/mobile-field-device-management-fieldmate) |

### 1.11 Yokogawa as Main Automation Contractor (MAC)

Only publicly announced awards are listed. Dates and roles are as given in the source.

| Project | Region | Role | Date | Source |
|---|---|---|---|---|
| **Commonwealth LNG**, Louisiana (US$13 bn); EPC Technip Energies | USA | MAC (Yokogawa Corporation of America) | Jul 2026 | [Control Global](https://www.controlglobal.com/industry-news/news/55391672/yokogawa-yokogawa-named-main-automation-contractor-for-13-billion-commonwealth-lng-project-in-louisiana); [LNG Prime](https://lngprime.com/contracts-and-tenders/yokogawa-bags-commonwealth-lng-gig/191593/) |
| **LNG Canada Phase 2**; JGC-Fluor JV | Canada | Main Automation Vendor (US subsidiary) | 4 Nov 2026 | [Yokogawa Korea press release](https://www.yokogawa.com/kr/news/press-releases/2026/2026-11-04/) |
| **BP Sharjah**: replacement of the Rosemount RS3 DCS with CENTUM VP (hot cutover) | UAE | MAC | Selected 2007 | [Yokogawa reference](https://www.yokogawa.com/mea/library/resources/references/yokogawa-receives-award-for-hot-cutover-of-bp-sharjah-plant-dcs/) |
| **Saudi Aramco Rabigh Refinery**: control-system replacement (hot cutover), oil blending, MVC (multivariable control), heater pass balance | KSA | DCS replacement contractor (MAC role not stated) | — | [Yokogawa reference](https://www.yokogawa.com/th/library/resources/references/saudi-aramco-rabigh-refinery-control-system-replacement-hot-cutover) |
| **Petro Rabigh**: automation supply, engineering and commissioning across 10 EPC packages | KSA | MAC (per Yokogawa refining material; undated) | — | [Yokogawa refining & petrochemical](https://www.yokogawa.com/industries/oil-gas/refining-petrochemical/) — verify the exact reference |
| **PETRONAS RAPID** (Pengerang) | Malaysia | MAC/FEED (FEED completed 2014), CENTUM VP, analyzer house | 2014+ | [digitalrefining.com](https://www.digitalrefining.com/news/1004556,yokogawa-wins-order-to-supply-analyzer-house-for-rapid-project.html) |

- **Qatar North Field East (NFE).** The searches found **no Yokogawa MAC award**. LNG Prime reports that **Honeywell** was selected as the main instrument and control contractor for NFE's four mega-trains (33 mtpa) ([LNG Prime](https://lngprime.com/?p=5847)). Do not attribute NFE to Yokogawa without a source.
- **Middle East (Aramco, ADNOC, QatarEnergy, KNPC), 2023–2026.** A second search found **no publicly announced Yokogawa MAC award** for these clients. Yokogawa's 2024 MEA corporate profile lists MAC among its services and notes a new Saudi regional office opened in 2023 ([Yokogawa MEA 2024 profile](https://web-material3.yokogawa.com/15/28517/overview/YMA%20Profile%20October_21-2024%20_002_.pdf)). Older regional orders found: PDO (Oman) gas plant as **main instrument vendor (MIV)**, not MAC ([Gulf Oil & Gas](https://www.gulfoilandgas.com/webpro1/main/mainnews.asp?id=109)); Marafiq (KSA) power-plant control system, c. 2012 ([MEP Middle East](https://www.mepmiddleeast.com/news/article-9647-yokogawa-wins-saudi-control-system-order)).
- **Ichthys LNG** (Australia) is a Yokogawa LNG reference ([Yokogawa video reference](https://yokogawa.com/ca/library/videos/references-videos/lng-supply-chain-ichthys-lng-project)). Its scope was not detailed.

### 1.12 Yokogawa engineering notes

1. **Accuracy basis.** EJX specs are stated at ±3σ conformance ([EJX910A GS](https://www.insatech.com/media/50aacz2k/gs_ejx910a_gs01c25r01-01en_34ed.pdf)). When comparing with other vendors, make sure the statistical basis and the "% of span" vs "% of URL" basis are the same.
2. **Turndown penalty.** Above a stated turndown, reference accuracy degrades by formula. For EJX910A DP above span X: ±(0.005 + 0.0035·URL/span) % of span (same GS). Compute the total probable error (TPE) at the calibrated span, not at the URL.
3. **SIL by serial number.** YTA710 SIL eligibility depends on the firmware revision (≥R1.03.01) and the manufacturing date ([YTA710 page](https://www.yokogawa.com/solutions/products-and-services/measurement/field-instruments-products/temperature-transmitters/field-mount/yta710-temperature-transmitter/)). Include the "SIL certificate per serial number" in the vendor document requirements (VDR).
4. **Discontinued models found in this search:** EJA118E (US), digitalYEWFLO DY (→ VY), US300FM (2017). Reject them in a TBE for new-build work unless a lifecycle statement is provided.
5. **Wireless host sizing.** Size by update rate: about 200 devices at 1 s or about 500 at 5 s per YFGW410, and 128 devices per ALE111 on CENTUM (sources in 1.7).

---

## 2. Bently Nevada (Baker Hughes)

Bently Nevada is the de-facto reference for API 670 machinery protection on compressors, steam and gas turbines, and critical pumps. The main competing platforms are Emerson AMS 6500, Brüel & Kjær Vibro (now part of NSK) VC-6000/SETPOINT, Metrix SETPOINT, Prüftechnik and Istec [general knowledge — verify].

### 2.1 3300 XL proximity transducer systems

**System concept.** A transducer system has three matched parts: **probe + extension cable + Proximitor sensor** (driver). The probe length plus the extension-cable length must equal the Proximitor's rated **total system length**. Standard total lengths are **5 m or 9 m**. A **1 m system uses no extension cable** ([3300 XL 11 mm datasheet copy](https://www.scribd.com/document/446294972/3300xl-11mm-pdf) [third-party copy]; [3300 XL 8 mm datasheet copy](https://core.instrumart.com/assets/bently-nevada-3300-xl-proximity-transducer-system-datasheet.pdf) [third-party copy]).

- Example combinations: 0.5 m probe + 4.5 m cable = 5 m; 1 m probe + 4 m cable = 5 m; 1 m probe + 8 m cable = 9 m. Extension cables come in about 3.0 to 8.5 m lengths ([Instrumart 3300 XL extension cable](https://instrumart.com/products/44328)).

| System | Scale factor | Linear range | Recommended gap | Power | Notes | Source |
|---|---|---|---|---|---|---|
| **3300 XL 8 mm** (probes 330101/330102 3/8-24 UNF, 330103/330104 M10×1; non-armoured / armoured) | **7.87 V/mm (200 mV/mil) ±5 %** incl. interchangeability, 5 m system, 0–45 °C; **9 m system ±6.5 %** ([3300 XL specs (manualmachine)](https://manualmachine.com/bentlynevada/3300xl/6538697-specifications) [third-party copy]; [PROXPAC XL DS](https://core.instrumart.com/assets/PROXPAC-datasheet.pdf) [third-party copy]) | **2.0 mm (80 mil)**, from about **0.25 to 2.3 mm (10–90 mil)** from target, i.e. about **−1 to −17 Vdc** output | Specified at **1.27 mm (50 mil)** gap. Corresponds to about **−10 Vdc** gap voltage (1.27 mm × 7.87 V/mm ≈ 10 V) | **−17.5 to −26 Vdc** without barriers, **−23 to −26 Vdc** with barriers; **12 mA max** | Specs assume an **AISI 4140** steel target at 18–27 °C with a −24 Vdc supply. The standard 5 m system complies with **API 670 (4th ed.)** for mechanical configuration, linear range, accuracy and temperature stability. Backward compatible with non-XL 3300 5/8 mm parts, but a mixed system meets only non-XL specs. PPS probe tip. | [8 mm datasheet 141194 copy](https://core.instrumart.com/assets/bently-nevada-3300-xl-proximity-transducer-system-datasheet.pdf) [third-party copy]; [Scribd 141194](https://es.scribd.com/document/282524498/3300-Xl-8mm-Proximity-transducer-system-Datasheet-141194-Cda-000-0-1) [third-party copy] |
| **3300 XL 11 mm** | **3.94 V/mm (100 mV/mil) ±10 %** including interchangeability | **4.0 mm (160 mil)**, from about **0.5 to 4.5 mm (20–180 mil)** | **2.5 mm (100 mil)** | −17.5 to −26 Vdc, 12 mA max | DSL (deviation from the best-fit straight line) **< ±0.10 mm (±4 mil)**. Over the extended temperature range, scale factor stays within ±25 %. Used for **thrust/axial position and steam-turbine differential expansion** (DE), and where a longer range is needed. | [Baker Hughes datasheet 146256 Rev P](https://dam.bakerhughes.com/m/27a2d91f28aadd41/original/3300-XL-11mm-Proximity-Transducer-System-Datasheet-146256-pdf.pdf); [Instrumart 11 mm](https://www.instrumart.com/products/46464/bently-nevada-3300-xl-11mm-proximity-probe) |
| 3300 XL 25 mm / 35 mm / 50 mm | Lower scale factors | Long range (DE ramps, large axial growth) | — | — | 50 mm system: 5 or 9 m total | [Instrumart 25 mm extension cable](https://www.instrumart.com/products/47980/bently-nevada-3300-xl-25mm-extension-cable); 11 mm datasheet copy (above) |
| 3300 XL NSv | Smaller-tip probe for tight spaces (for example, small-centrifugal-compressor) | — | — | — | — | [Instrumart NSv extension cable](https://www.instrumart.com/products/34701/bently-nevada-3300-xl-nsv-extension-cable) |
| 3300 5 mm | Legacy small probe | — | — | — | Probe lengths 0.5, 1, 5, 9 m | [3300 5 mm copy](https://www.scribd.com/document/672181722/3300prox5mm) [third-party copy] |

**Engineering notes, proximity probes**

- **Target material.** Accuracy and interchangeability specs apply only to an **AISI 4140** target. Other shaft materials need calibration to the actual target, or a scale-factor correction ([8 mm datasheet copy](https://core.instrumart.com/assets/bently-nevada-3300-xl-proximity-transducer-system-datasheet.pdf)).
- **Gap voltage check during installation.** For the 8 mm system, the −10 Vdc gap voltage corresponds to the mid-linear-range 1.27 mm gap. Acceptable install ranges are usually about −9 to −11 V for radial probes. For thrust probes, the gap is set to suit the expected float direction and the active thrust face [general knowledge — verify].
- **Glitch and runout.** The rule "combined electrical + mechanical runout ≤ **25 % of the allowed peak-to-peak vibration or 6 µm (0.25 mil), whichever is greater**" is confirmed in **API 610 11th ed. §6.6.10 e)** ([Sulzer test procedure TP-0028](https://www.sulzer.com/en/-/media/files/q_documents_pe/tp/tp-0028.pdf)); Bently Nevada states **API 617** has identical runout requirements ([Bently Orbit article "Understanding and mitigating runout"](https://dam.bakerhughes.com/m/3ad476e660980e3a/original/3Q05_Understanding-Mitigating-Runout-pdf.pdf)). **Correction:** an earlier version attributed the rule to API 670; the API 670 clause wording was not found, so cite the machine standard (API 610/617/612) in the MDS. Specify a burnished probe track and degaussing in the MDS.
- **Cable length is part of the calibration.** Do not cut or splice extension cables. A 5 m Proximitor will not linearize a 9 m system [general knowledge — verify].

### 2.2 Seismic transducers (Velomitor and accelerometers)

| Model | Function | Key specs | Source |
|---|---|---|---|
| **330500 Velomitor** | Piezoelectric velocity sensor (casing velocity) | **3.94 mV/(mm/s) (100 mV/in/s) ±5 %**; frequency response **4.5 Hz–5 kHz (±3 dB)**, 6 Hz–2.5 kHz (±0.9 dB). Datasheet 141632. | [Baker Hughes 330500 page](https://www.bakerhughes.com/bently-nevada/sensors/velocity-sensors/330500-piezovelocity-sensor); [330500 DS (Instrumart copy)](https://core.instrumart.com/assets/330500-Datasheet.pdf) [third-party copy] |
| **330400** | Accelerometer for API 670 casing (gear-mesh, high-frequency) measurement | **10.2 mV/(m/s²) (100 mV/g) ±5 %**; range **490 m/s² (50 g) peak**, 10 Hz–15 kHz; designed to meet API 670 accelerometer requirements | [330400/330425 DS (Instrumart copy)](https://core.instrumart.com/assets/330400-330425-Datasheet.pdf) [third-party copy]; [DirectIndustry excerpt](https://pdf.directindustry.com/pdf/condition-monitoring-protection/330400-330425-accelerometer-acceleration-transducers/12479-1063426.html) |
| 330425 | Accelerometer, **2.5 mV/(m/s²) (25 mV/g)**, larger amplitude range | — | [330400/330425 DS (Instrumart copy)](https://core.instrumart.com/assets/330400-330425-Datasheet.pdf) [third-party copy] |
| 190501 Velomitor CT | Low-frequency velocity sensor (cooling towers [application: general knowledge — verify]) | 3.94 mV/(mm/s) | [190501 DS (Instrumart copy)](https://core.instrumart.com/assets/190501-Datasheet.pdf) [third-party copy] |

- The 3500/42M accepts **velocity and acceleration** channel types, alongside radial vibration, thrust, DE, eccentricity, REBAM (rolling element bearing activity monitoring) and shaft absolute ([3500/42M datasheet 143694](https://dam.bakerhughes.com/m/20b1fd1cd261c09f/original/3500-42M-Proximitor-Seismic-Monitor-Datasheet-143694-pdf.pdf)).

### 2.3 3500 machinery protection system

**Rack and architecture.** The 3500 is a rack-based protection system. A rack holds:

- one or two power supplies (3500/15),
- the TDI (3500/22M), which is the rack interface,
- monitor, Keyphasor, relay and communication modules.

The system overview is in the **3500 System datasheet 162096** ([Baker Hughes 162096](https://dam.bakerhughes.com/m/3e2d1931acef5630/original/3500-System-Datasheet-162096-pdf.pdf); [Instrumart copy](https://core.instrumart.com/assets/3500-System-Datasheet.pdf)). The datasheet index is document 141526 ([3500 manuals/datasheets index](https://dam.bakerhughes.com/m/3f24df10f181094b/original/3500_manuals_datasheets_141526g-pdf.pdf)).

- **Rack sizes (3500/05, datasheet 141525):** **19-inch EIA full rack with 14 module slots** and **12-inch mini-rack with 7 module slots**; power supplies and the TDI occupy the left-most positions in addition to these. Mini-rack needs 3500/01 software **v2.70 or later**. Rail, panel-cutout and bulkhead mounting ([3500/05 DS (manualmachine)](https://manualmachine.com/bentlynevada/350005/6557163-data-sheet) [third-party copy]; [Instrumart 3500/05](https://www.instrumart.com/products/46320)).
- **SIL:** the 3500 can be supplied for applications up to **SIL 3**, with TMR configurations available. This is a system-level statement, not a per-module certificate ([Bently 3500 brochure as cited in 3500 PDF copy](https://www.scribd.com/document/343169343/3500-pdf) [third-party copy]; [Baker Hughes 3500 page](https://www.bakerhughes.com/bently-nevada/monitoring-systems/machinery-protection/3500-machinery-protection-systems)).

| Module | Function | Key facts | Source |
|---|---|---|---|
| **3500/15** | Power supply (AC or DC) | Redundant pair recommended; **mandatory** in racks with the 3500/53 | [3500/53 spec copy](https://m.rms-dcs.com:443/uploads/3500-53.pdf) [third-party copy] |
| **3500/22M TDI** | Transient Data Interface: rack interface plus System 1 data | Primary interface for the 3500 configuration software, with a **direct interface to System 1** (no external comms processor). Rack configuration uses a proprietary protocol. **Not** a Modbus gateway; use the 3500/92. | [3500 System datasheet](https://dam.bakerhughes.com/m/3e2d1931acef5630/original/3500-System-Datasheet-162096-pdf.pdf) |
| **3500/25** | Enhanced Keyphasor module | Half-height; powers and terminates **up to 2 Keyphasor transducers**. Two modules in one slot give **4 Keyphasors per rack**. | [3500/25 datasheet 141532](https://dam.bakerhughes.com/m/22d0219c69acbaf5/original/3500-25-Enhanced-Keyphasor-Module-Datasheet-141532-pdf.pdf); [Instrumart copy](https://core.instrumart.com/assets/3500-25-Datasheet.pdf) |
| **3500/32M** | 4-channel relay module | **DPDT** relays; AND/OR voting logic; latching or non-latching. **3500/33** is the 16-channel version: **SPDT**, 100,000-cycle contact life, 5.8 W typical, datasheet 162291 ([Instrumart 3500/33](https://core.instrumart.com/products/46328/bently-nevada-350033-relay-module)). Only relay modules may be used for shutdown. Analog and Modbus outputs are for annunciation and trending only. | [3500 System datasheet](https://dam.bakerhughes.com/m/3e2d1931acef5630/original/3500-System-Datasheet-162096-pdf.pdf) |
| **3500/40M** | Proximitor monitor (4 ch) | Radial vibration, axial (thrust) position, eccentricity, DE; accepts 3300 XL Proximitor inputs. Datasheet 143488. | [3500 System DS (Instrumart copy)](https://core.instrumart.com/assets/3500-System-Datasheet.pdf); [3500/40M DS (Instrumart copy)](https://core.instrumart.com/assets/3500-40M-Datasheet.pdf) [third-party copy] |
| **3500/42M** | Proximitor/Seismic monitor (**4 channels**, programmed in pairs) | Channel types: radial vibration, thrust position, DE, eccentricity, REBAM, velocity, acceleration, shaft absolute, circular acceptance region. Input sensitivity **3.94 mV/µm (100 mV/mil)** or **7.87 mV/µm (200 mV/mil)**. Input impedance **10 kΩ** (standard I/O). About **7.7 W** typical. Alert setpoint per value; Danger on any two values. | [3500/42M datasheet 143694](https://dam.bakerhughes.com/m/20b1fd1cd261c09f/original/3500-42M-Proximitor-Seismic-Monitor-Datasheet-143694-pdf.pdf); [Instrumart copy Rev V](https://core.instrumart.com/assets/3500-42M-Datasheet.pdf) |
| **3500/45** | Position monitor | The 3500 System datasheet directs DE applications to the 3500/45 ([3500 System DS](https://core.instrumart.com/assets/3500-System-Datasheet.pdf)). Other scope (ramp DE, valve position) [general knowledge — verify]. Datasheet 135545. | [3500 index 141526](https://dam.bakerhughes.com/m/3f24df10f181094b/original/3500_manuals_datasheets_141526g-pdf.pdf) |
| **3500/46M** | Hydro monitor | — | [general knowledge — verify] |
| **3500/50M** | Tachometer module | **2 channels** (Proximitor or magnetic pickup): speed, rotor acceleration, reverse rotation. **Not designed for overspeed detection** (use 3500/53). Datasheet 134938. | [3500 System DS (Instrumart copy)](https://core.instrumart.com/assets/3500-System-Datasheet.pdf); [3500 index 141526](https://dam.bakerhughes.com/m/3f24df10f181094b/original/3500_manuals_datasheets_141526g-pdf.pdf) |
| **3500/53** | Electronic overspeed detection | Designed to meet **API 670 and API 612** overspeed requirements. Modules combine as **2-out-of-2 or 2-out-of-3 (recommended)** voting. Redundant power supplies required. Module P/N 133388-01; manual 134939-01. Bently material states a **three-channel 3500/53 solution can be fully TÜV SIL 3 certified**, and TÜV certified the 3500 system for up to SIL 3 (c. 2003). A competitor (Istec) states that the 3500/53 depends on the rack for SIL and is **not a stand-alone SIL device**. No current certificate or response-time figure was found. | [3500/53 spec copy](https://m.rms-dcs.com:443/uploads/3500-53.pdf) [third-party copy]; [Istec comparison](https://www.istec.com/?p=36050) [competitor claim]; [Bently special-applications deck](https://www.slideshare.net/slideshow/b2b03monitoringspecialappsr2ppt/252915281) [third-party copy]; [3500 TÜV article copy](https://www.scribd.com/doc/154761142/1q03-3500-tuv) [third-party copy] |
| **3500/60, /61, /65** | Temperature monitors (RTD/TC; /61 with recorder outputs; /65 16-channel) | — | [general knowledge — verify] |
| **3500/62** | Process variable monitor (4–20 mA inputs) | — | [general knowledge — verify] |
| **3500/64M** | Dynamic pressure monitor (combustion dynamics on gas turbines) | — | [general knowledge — verify] |
| **3500/70M, /72M** | Reciprocating compressor: impulse/velocity and rod position (rod drop) | — | [general knowledge — verify] |
| **3500/92** | Communication gateway | **Modbus TCP and Modbus serial** (RS-232/422/485); acts as server/slave only | [Instrumart 3500/92](https://www.instrumart.com/products/46393/bently-nevada-350092-communication-gateway); [3500 System datasheet](https://dam.bakerhughes.com/m/3e2d1931acef5630/original/3500-System-Datasheet-162096-pdf.pdf) |
| **3500/93, /94, /95** | System display options (3500/93 datasheet 137412) | Display technology details [general knowledge — verify] | [3500 index 141526](https://dam.bakerhughes.com/m/3f24df10f181094b/original/3500_manuals_datasheets_141526g-pdf.pdf) |

**Engineering notes, 3500**

- **DCS interface.** Use hard-wired relays (3500/32M or /33) for trips to the SIS or ESD. Use the 3500/92 Modbus TCP gateway for values and alarms to the DCS. Use the 3500/22M TDI for System 1 only (sources above).
- **4–20 mA recorder outputs.** These are available on the monitor I/O modules. Use them for DCS trending where the Modbus gateway is not accepted, not for trip duty [general knowledge — verify].
- **Overspeed.** For steam turbines under API 612 or 670, use 3500/53 in **2oo3** with three dedicated speed probes, separate from the Keyphasor. Alternatively, use a certified stand-alone overspeed system. Bently's 3701 ADAPT ESD offers SIL 3 overspeed (see 2.4).

### 2.4 Orbit 60, ADAPT, 3701

| Product | Function | Key facts | Source |
|---|---|---|---|
| **Orbit 60 Series** | Next-generation protection and condition monitoring platform (3500 successor path) | **SIL 2** certification is the consistently documented level ("SIL 2 certification for confidence through redundancy measures"; fact sheet © 2025). The Baker Hughes Orbit 60 page says it was designed to meet **SIL 2 without component redundancy**, and that **SIL 3 overspeed, currently offered in the 3701 ESD, will be released on Orbit 60 "in the near future"** ([Baker Hughes Orbit 60 page](https://www.bakerhughes.com/bently-nevada/monitoring-systems/machinery-protection/orbit-60-series)). No exida/TÜV SIL 3 certificate for Orbit 60 was found: treat Orbit 60 as **SIL 2** for SIF design. Trade press claims SIL 2 and 3 plus API 670 compliance. Baker Hughes said in 2019 that SIL 3 overspeed would follow, being offered then in the 3701 ESD. Operating temperature **−30 to +65 °C** (system); the SIM is rated −30 to +70 °C, altitude <2000 m. The SIM is non-interfering, so system SIL 2 does not require it to be SIL certified. Built-in cybersecurity is emphasized. Approvals are in guide 108M1756. | [Orbit 60 fact sheet](https://dam.bakerhughes.com/asset/8588eaac-d1af-4d4e-81a3-9b61dff5c3c6/Orbit60-Fact-Sheet_Web-Version.pdf); [Protection Processor Module DS 142M8515](https://dam.bakerhughes.com/m/1832f7859078b618/original/ORBIT-60-SERIES-Protection-Processor-Module-Datasheet-142M8515.pdf); [SIM DS 142M9054](https://dam.bakerhughes.com/m/eee1b773db43667/original/ORBIT-60-SERIES-System-Interface-Module-Datasheet-142M9054.pdf); [Turbomachinery Magazine](https://www.turbomachinerymag.com/view/bently-nevadas-new-platform); [Chemical Engineering](https://www.chemengonline.com/monitoring-platform-built-cybersecurity/) |
| **ADAPT 3701** | Compact protection and condition monitoring for a single machine. Variants: **/40 Machinery Dynamics Monitor**, **/44 Aeroderivative GT Monitor**, **/46 Hydro Monitor** (shared PoV input module); configured with BNMC software (ordered separately). **3701/55 ESD**: emergency shutdown device / safety PLC with integrated overspeed detection, **IEC 61508 SIL 3 certified**, **10 ms input-to-relay response**. | — | [3701/40 DS (Instrumart copy)](https://core.instrumart.com/assets/3701-40-Datasheet.pdf) [third-party copy]; [3701/44 DS 100M8649](https://dam.bakerhughes.com/m/7589288537788a5d/original/3701-44-ADAPT-Aeroderivative-Monitor-Datasheet-100M8649-pdf.pdf); [ADAPT 3701/55 fact sheet](https://dam.bakerhughes.com/m/d4fe82417ccafbf/original/ADAPT-3701_55-Factsheet.pdf); [Turbomachinery Magazine](https://www.turbomachinerymag.com/view/bently-nevadas-new-platform) |

### 2.5 System 1, Ranger, Trendmaster

- **System 1.** Bently's condition-monitoring and diagnostic software (orbit, shaft centreline, Bode, waterfall, and so on). It connects directly to the 3500/22M TDI ([3500 System datasheet](https://dam.bakerhughes.com/m/3e2d1931acef5630/original/3500-System-Datasheet-162096-pdf.pdf)) and to Orbit 60 and ADAPT [general knowledge — verify].
- **Ranger Pro.** A wireless (ISA100-based [general knowledge — verify]) vibration and temperature sensor for balance-of-plant machines that are not API 670 critical [general knowledge — verify].
- **Trendmaster Pro / SPA.** Online scanning (surveillance) system for semi-critical pumps and fans using Trendmaster Proximitor/Interface Modules (TIMs) [general knowledge — verify]. Legacy; check lifecycle status.
- **Classification.** Machines are usually classed as **critical** (3500 or Orbit 60 protection with System 1), **essential** (online scanning or wireless) and **balance-of-plant** (portable route-based collection). The project's machinery monitoring philosophy should map each class to a platform [general knowledge — verify].

### 2.6 API 670 compliance checklist

The API 670 text was not retrieved. Items below are drawn from vendor datasheets and secondary sources, and must be checked against the **current edition** (5th ed., November 2014 — [API 670 5th ed. notice](https://www.api.org/~/media/files/publications/whats%20new/670_e5%20pa.pdf); errata status [general knowledge — verify]) and the purchaser's MDS. API 670 covers radial shaft vibration, casing vibration, axial position, speed, rod drop, phase reference, overspeed and critical temperatures ([Emerson white paper](https://s1-live.emerson.com/documents/automation/white-paper-measurement-types-in-machinery-monitoring-ams-en-39660.pdf)).

| Check | Typical requirement | Source |
|---|---|---|
| Radial probes per bearing | **Two (X–Y), 90° apart**, usually at ±45° from vertical (10:30 and 1:30 o'clock) to clear the bearing split line. Baker Hughes: "typically, each radial bearing requires a pair of X-Y proximity probes". Radial vibration monitor full-scale range **0–125 µm (0–5 mil)** pk-pk per a 5th-ed. compliance summary. | [GE/Baker Hughes compressor application guide](https://www.bakerhughes.com/sites/bakerhughes/files/2022-01/GEA31971A%20Centrifugal%20Compress%20App%20Note_R4.pdf); [B&K Vibro API 670 5th ed. comments](https://www.bkvibro.com/fileadmin/mediapool/Internet/Product_Sheets/Condition_Monitoring/SETPOINT/1365855____API_670_Comments-Compliance.pdf); [Emerson white paper](https://s1-live.emerson.com/documents/automation/white-paper-measurement-types-in-machinery-monitoring-ams-en-39660.pdf); [Reliabilityweb](https://reliabilityweb.com/articles/entry/temporary_mounting_of_proximity_probes) |
| Axial (thrust) position | **Two axial probes per thrust bearing** ([GE/Baker Hughes guide](https://www.bakerhughes.com/sites/bakerhughes/files/2022-01/GEA31971A%20Centrifugal%20Compress%20App%20Note_R4.pdf)). Voting: **2oo2** (both probes in Danger) is common practice [general knowledge — verify], but Baker Hughes notes **API 670 allows the end user to choose 1oo2** for axial position (same guide). Location within about 300 mm (12 in) of the thrust collar [general knowledge — verify]. | see cell |
| Phase reference | One **Keyphasor** (once-per-turn) probe per shaft; Baker Hughes recommends a **spare Keyphasor** (and a spare axial probe) | [GE/Baker Hughes guide](https://www.bakerhughes.com/sites/bakerhughes/files/2022-01/GEA31971A%20Centrifugal%20Compress%20App%20Note_R4.pdf); module capacity from [3500/25 DS](https://dam.bakerhughes.com/m/22d0219c69acbaf5/original/3500-25-Enhanced-Keyphasor-Module-Datasheet-141532-pdf.pdf) |
| Transducer system | **8 mm** probe system (5 m or 9 m) with 7.87 V/mm; **AISI 4140** reference target; API 670 accuracy and interchangeability | [3300 XL 8 mm DS copy](https://core.instrumart.com/assets/bently-nevada-3300-xl-proximity-transducer-system-datasheet.pdf) |
| Gap | Set at the mid linear range: about **−10 Vdc** (1.27 mm) for the 8 mm system | Calculated from the DS (see 2.1) |
| Radial vibration voting | Trip on **dual-path** logic: Danger on one probe AND Alert (or Danger) on the other probe of the same bearing, or as specified | [general knowledge — verify] |
| Overspeed | Three independent speed sensors, **2oo3** voting, SIL as per the SRS (safety requirements specification), response time per API 670 / machine OEM | [3500/53 spec copy](https://m.rms-dcs.com:443/uploads/3500-53.pdf) |
| Relays | Trip relays normally de-energized or energized per the purchaser; DPDT; trip multiply and bypass functions | [3500 System DS](https://dam.bakerhughes.com/m/3e2d1931acef5630/original/3500-System-Datasheet-162096-pdf.pdf) |
| Power supply | Redundant | [3500/53 spec copy](https://m.rms-dcs.com:443/uploads/3500-53.pdf) |
| Casing (seismic) | Accelerometer on gearboxes (gear mesh) and for gas-turbine casing velocity, via integration | [general knowledge — verify] |

### 2.7 Typical machine-train protection architecture

The following is [general knowledge — verify]. Adapt it to the MDS and the machine OEM's API 617, 612, 616 or 610 data.

**Centrifugal compressor driven by a steam turbine (API 617 / 612)**

- **Radial vibration.** Two 8 mm probes (X–Y) at each journal bearing. That gives four bearings × 2 = 8 radial channels on 3500/42M (or 40M) modules.
- **Axial position.** Two 8 mm or 11 mm probes per thrust bearing (compressor and turbine), feeding 3500/42M or /45 thrust channels.
- **Phase and speed.** One Keyphasor (plus a spare) on each shaft (3500/25). Gearbox trains need a Keyphasor per shaft speed.
- **Overspeed.** Three speed probes on a toothed wheel, feeding 3500/53 ×3 in 2oo3 voting. Alternatively, the turbine governor's or a third-party certified overspeed system.
- **Differential expansion (large steam turbines).** 25 mm or 50 mm probes, or ramp DE, on 3500/45.
- **Bearing temperatures.** Duplex RTDs in the thrust and journal pads, to 3500/61 or 3500/65, or to the DCS or SIS.
- **Outputs.**
  - Relays (3500/32M) to the SIS or UCP for trip.
  - 3500/92 Modbus TCP to the DCS for values and alarms.
  - 3500/22M to System 1.
  - Buffered outputs (BNC) on the front panel for portable analyzers.

**Gas turbine (aero-derivative).** Casing accelerometers or velocity sensors per the OEM (often the OEM's own protection), proximity probes on driven equipment, and dynamic-pressure monitoring (3500/64M) where the OEM requires it.

**Critical pumps (API 610).** Either two radial probes per bearing plus axial probes on sleeve-bearing pumps, or casing velocity/acceleration on rolling-element pumps.

**Reciprocating compressors (API 618).** 3500/70M (frame and crosshead acceleration) and 3500/72M (rod drop or position).

---

## 3. WIKA

> **Source note.** wika.com and its regional upload hosts could not be fetched from this environment; facts below come from web-search extracts of WIKA data sheets. Many links point to WIKA's own regional hosts (wika.com.au, kz.wika.com, cn.shop.wika.com) or to distributor copies (ICS Schneider, Mensor, BKW Instruments, Yodify, Instrumart) and are marked [third-party copy] where not WIKA-hosted. Data-sheet revisions differ between copies, so always quote the current revision from wika.com in the TBE. Items still tagged [general knowledge — verify] were not found in any source.

### 3.1 Pressure gauges

**Governing standards**

| Standard | Accuracy designation | Notes |
|---|---|---|
| **EN 837-1** (Bourdon tube gauges) | Accuracy **classes 0.1, 0.25, 0.6, 1.0, 1.6, 2.5, 4.0** (% of full scale) [class list: general knowledge — verify] | Safety levels: **S0** = no blow-out device; **S1** = blow-out device (plug) in the case; **S2** = blow-out back but **no** solid baffle wall; **S3** = **solid baffle wall** between measuring element and dial **plus blow-out back**, so that on a Bourdon-tube burst parts and medium can escape only to the rear ([WIKA blog, safety-version selection](https://blog.wika.com/knowhow/stainless-steel-pressure-gauge-in-safety-version-selection-help/); [ICS Schneider S3 article](https://www.ics-schneider.de/sicherheitsmanometer-s3-berstwand-und-ausblasrichtung-richtig-waehlen/?lang=en); [Tubes International UHP gauges](https://www.tubes-international.com/products/hydraulics-and-high-pressure/uhp-equipment/uhp-pressure-gauges/)). The EN 837-1 text itself was not retrieved. |
| **EN 837-2** (selection and installation) | — | For **gaseous or vaporous media from 25 bar operating pressure, an S3 gauge is recommended**; liquid-filled gauges ≤25 bar typically S1 ([WIKA PM 02.04 extract via WIKA blog](https://blog.wika.com/knowhow/stainless-steel-pressure-gauge-in-safety-version-selection-help/); [SAMSON EN 837-2 selection table](https://southafrica.samsongroup.com/document/t00090en.pdf)). Blow-out devices need about **20 mm** free space behind the case (WIKA operating instructions, per [ICS Schneider OI copy](https://www.ics-schneider.de/wp-content/uploads/2021/11/oi_pressuregaugesns40_en.pdf)) [third-party copy]. |
| **ASME B40.100** (current edition **2022**, superseding 2013 — [ASME B40.100-2022 ToC](https://www.asme.org/getmedia/e36d3d8e-8d61-4380-869f-e47dc907dd82/B40-100_2022_ToC.pdf)) | **4A ±0.1 %**, **3A ±0.25 %**, **2A ±0.5 %**, **1A ±1 %** of span over the whole scale; **Grade A: 2-1-2 %** (±2 % first and last quarter, ±1 % middle half); **Grade B: 3-2-3 %** ([Ashcroft accuracy grades blog](https://blog.ashcroft.com/what-are-asme-accuracy-grades-for-mechanical-pressure-gauges); [Boshart KB](https://support.boshart.com/what-is-3-2-3-gauge-accuracy-and-how-is-it-different-from-full-scale-accuracy); [Instrumart grade table](https://instrumart.com/pages/539/pressure-gauge-accuracy-grades)). Grades C and D: [general knowledge — verify]. **Correction:** an earlier version of this file gave Grade B as "2-3-2 %"; the sources give **3-2-3 %**. | "Solid-front" case with a blow-out back is the US safety-case term [general knowledge — verify]. Secondary sources only; ASME text not retrieved. |

**WIKA Bourdon-tube gauge families**

| Model | Function | Key specs | Typical use | Source |
|---|---|---|---|---|
| **232.50 / 233.50** (data sheet **PM 02.02**) | Stainless steel case and wetted parts. 232.50 is dry; **233.50 is liquid-filled**, for high dynamic pressure loads and vibration. | **NS 63, 100, 160**. **EN 837-1 class 1.0 (NS 100/160), class 1.6 (NS 63)**. Ranges **0…0.6 to 0…1,600 bar** (0…10 to 0…20,000 psi). **IP65**. Temperature effect max **±0.4 %/10 K** vs +20 °C. Safety level **S1**: blow-out device at 12 o'clock (NS 63) or on the case back (NS 100/160). | General process gauges on O&G skids; liquid-filled for vibration and pulsation | [WIKA AU PM 02.02](https://www.WIKA.com.au/upload/DS_PM0202_en_co_3672.pdf); [ICS Schneider 232.50 page](https://www.ics-schneider.de/produkte/wika-232-50-druckmessgeraet-mit-rohrfeder/?lang=en) [third-party copy]; [RS datasheet copy](https://docs.rs-online.com/e3fd/A700000007855161.pdf) [third-party copy]. ASME B40.100 grade differs by revision — check current PM 02.02. Medium-temperature limits not retrieved. |
| **232.30 / 233.30** (data sheet **PM 02.04**) | Safety-pattern stainless steel gauge, **EN 837-1 safety level S3**: **solid baffle wall + blow-out back** | Ranges **0…0.6 to 0…1,600 bar**. Bourdon tube **316L**. Ranges ≤16 bar need a **compensating valve** to vent the case. 233.30 = liquid-filled for vibration/dynamic loads. NS 63 and NS 100 confirmed in distributor listings; accuracy class: [general knowledge — verify] (class 1.0). | Gas and vapour service ≥25 bar per EN 837-2 recommendation (above) | [WIKA AU PM 02.04 (de)](https://www.WIKA.com.au/upload/DS_PM0204_de_de_3678.pdf); [PM 02.04 copy](https://www.mmintercom.com/upload/catalog/product/15064/pm%2002.04_e.pdf) [third-party copy]; [ICS Schneider 232.30](https://www.ics-schneider.de/produkte/bourdon-tube-pressure-gauge-stainless-steel-safety-version-models-232-30-233-30/?lang=en) [third-party copy]; [Lemu NS 100 listing](https://www.lemu.dk/en/catalog/products/23230-pressure-gauge--06-bar-ns-100-stainless-steel-case-g12-stainless-steel-down/7824209886) |
| **232.36 / 233.36** | Safety pattern with increased overpressure safety (about 2×–5× FS, depending on version) | — | Services where overpressure is expected | [general knowledge — verify] |
| **212.20 / 213.53** | Brass wetted parts, economy | — | Utilities (air, water) | [general knowledge — verify] |
| **PG23LT / PG28** | Gauges with integrated transmitter signal (intelliGAUGE) | — | Local + remote reading | [general knowledge — verify] |
| **432.50 / 433.50** | Diaphragm-element gauge (low ranges, viscous or crystallizing media, high overload) | — | Low-pressure or open-flange diaphragm service | [general knowledge — verify] |
| **532.5x / 632.50** | Absolute and capsule gauges for very low pressure (mbar) | — | Vacuum and draft | [general knowledge — verify] |
| **7xx (DELTA-plus 7xx.xx)** | Differential pressure gauges | — | Filter ΔP | [general knowledge — verify] |
| **PGS23 / PSM** | Switch gauges (gauge with contacts) | — | Local alarm | [general knowledge — verify] |

- **Specifying a "safety pattern gauge" in a TBE.** Ask for the EN 837-1 safety level **S3** explicitly, or for "ASME B40.100 solid-front with blow-out back". A blow-out plug alone is **S1**, and a blow-out back without a baffle wall is only **S2** ([WIKA blog](https://blog.wika.com/knowhow/stainless-steel-pressure-gauge-in-safety-version-selection-help/)).

### 3.2 Diaphragm seals

| Model family | Type | Notes | Source |
|---|---|---|---|
| **990.10 / 990.12** | Threaded-connection diaphragm seal, upper body + lower body | Cleanable; flushing connections optional | [general knowledge — verify] |
| **990.27** (data sheet **DS 99.27**) | Flange connection with **flush welded diaphragm** | Standard flanges (ASME/EN), mounted in place of a blind flange; for aggressive, viscous, crystallizing or hot media. Common on vessel and tank level DP. | [WIKA AU DS 99.27](https://www.WIKA.com.au/upload/DS_DS9927_en_co_1240.pdf); [WIKA 990.27 page](https://www.WIKA.com.au/990_27_en_co.WIKA) |
| **990.29** | Flange type with **extended diaphragm** (through an insulated nozzle) | Viscous or solidifying media | Named in a WIKA cross-reference list seen in search extracts; the exact document was not pinned [verify against DS 99.29] |
| **990.41** | Flange connection with **internal (non-flush) diaphragm**, large working volume; flushing connections available; suits small process connections | **Correction:** an earlier version listed 990.41 as an "extended diaphragm" seal; sources describe it as an internal-diaphragm design | [ICS Schneider 990.41](https://www.ics-schneider.de/produkte/wika-990-41-diaphragm-seal-with-flange-connection/?lang=en) [third-party copy]; [VYTL Controls 990.41](https://www.vytlcontrols.com/diaphragm-seals/flanged-connection/pid9933/990-41-flange-connection-diaphragm-seal/) [third-party copy] |
| **990.22 / 990.15** | In-line (flow-through) seals | Slurries, sanitary | [general knowledge — verify]; WIKA also lists in-line model **981.10** ([WIKA India 981.10](https://www.wika.com/en-in/981_10.WIKA)) |
| **9xx with capillary** | Capillary (armoured SS) to a remote transmitter or gauge | Capillary length drives response time and temperature error (see notes) | [WIKA blog, capillaries](https://blog.wika.com/us/knowhow/why-use-capillary-tubes-pressure-measurement/) |

**Fill fluids** (WIKA "KN" codes; check the current WIKA fill-fluid table and the seal data sheet — the system limit is set by the joining method, the fill and the instrument together, per WIKA data sheets as quoted in search results):

| Fill fluid | Range found | Notes | Source |
|---|---|---|---|
| **KN2** silicone oil (standard) | **Conflict:** −20 to +200 °C (WIKA diaphragm-seal catalogue) vs −40 to +300 °C (Yokogawa/WIKA seal document). Flash point >300 °C. | General purpose | [WIKA product review (disai copy)](https://www.disai.net/wp-content/uploads/catalogos_pdf/CAT%20WIKA%20BR_DS_GB_6514.pdf) [third-party copy]; [Yokogawa EJA/EJX with WIKA seals](https://www.metisafrica.com/wp-content/uploads/docs/YO-SEP-WIKA.pdf) [third-party copy]; [WIKA Ex additional information](https://www.wika.com/media/Operating-instructions/Additional-operating-instructions/Ex/ai_ex_dss_en_de.pdf) |
| **KN17** silicone oil (PD5) — **low-temperature** fill | **−90 to +180 °C**; flash point 100 °C | Cold climates, LNG periphery. **Correction:** an earlier version called KN17 a high-temperature silicone; sources show it is the low-temperature fill. | [WIKA product review (disai copy)](https://www.disai.net/wp-content/uploads/catalogos_pdf/CAT%20WIKA%20BR_DS_GB_6514.pdf) [third-party copy]; [WIKA diaphragm-seal OI](https://www.metisafrica.com/wp-content/uploads/2025/02/oi_diaphragm_seal_systems_en_de_fr_es.pdf) [third-party copy] |
| **KN32** high-temperature silicone oil | Flash point >214 °C; operating range not retrieved | Heat-transfer / hot service; check vacuum limits | [WIKA Ex additional information](https://www.wika.com/media/Operating-instructions/Additional-operating-instructions/Ex/ai_ex_dss_en_de.pdf) |
| **KN21** halocarbon oil | **−40 to +175 °C**; **−40 to +80 °C** at low absolute pressure; **oxygen max 160 bar** | **Oxygen and chlorine** service; order with degreased (/K-type) cleaning for O2 | [WIKA product review (disai copy)](https://www.disai.net/wp-content/uploads/catalogos_pdf/CAT%20WIKA%20BR_DS_GB_6514.pdf) [third-party copy]; [Yokogawa/WIKA seal doc](https://www.metisafrica.com/wp-content/uploads/docs/YO-SEP-WIKA.pdf) [third-party copy] |
| **KN59** Neobee M-20 (food grade) | Flash point >170 °C; WIKA operating range not retrieved. Non-WIKA guide: Neobee M-20 −10 to 400 °F (≈ −23 to +204 °C) | Food and pharma; FDA 21 CFR 172.856 basis [general knowledge — verify] | [WIKA Ex additional information](https://www.wika.com/media/Operating-instructions/Additional-operating-instructions/Ex/ai_ex_dss_en_de.pdf); [Reotemp fill guide](https://reotemp.com/wp-content/uploads/2017/08/Diaphragm-seal-fill-guide-PTC-0817.pdf) (non-WIKA) |
| Glycerine-water | limited range | Low-cost | [general knowledge — verify] |

- **Vacuum fills.** WIKA data sheet **IN 00.25** covers diaphragm-seal systems for vacuum and names KN2, KN17, KN21, KN32, KN59 and KN92 as vacuum-capable, each with its own min-pressure/max-temperature curve ([WIKA IN 00.25](https://kz.wika.com/upload/DS_IN0025_en_co_58173.pdf)).

**Engineering notes**

- **Temperature error.** The fill expands or contracts with temperature, creating an error that is a function of the total fill volume of the system ([WIKA blog](https://blog.wika.com/us/knowhow/why-use-capillary-tubes-pressure-measurement/)). Longer capillaries increase it; a larger diaphragm reduces it ([Siemens remote-seal guide](https://support.industry.siemens.com/cs/attachments/109771077/FI01-us-kap01-pressure-remote-seals.pdf)). A smaller capillary bore reduces temperature error but raises friction and response time (WIKA blog, above). Request WIKA's **diaphragm seal system calculation** (temperature error, response time) for each tag. No WIKA mbar/10 K figures were retrieved.
- **Response time** grows with capillary length and fill viscosity ([WIKA blog](https://blog.wika.com/us/knowhow/why-use-capillary-tubes-pressure-measurement/); [Siemens guide](https://support.industry.siemens.com/cs/attachments/109771077/FI01-us-kap01-pressure-remote-seals.pdf)). Long capillaries with high-viscosity fills at low temperature can take tens of seconds [magnitude: general knowledge — verify]. Avoid them in fast control or SIL loops.
- **Head effect.** Fill density changes with temperature, shifting head pressure; this adds to the seal temperature effect ([WIKA blog](https://blog.wika.com/us/knowhow/why-use-capillary-tubes-pressure-measurement/)). Mount the transmitter at or below the lower seal for vacuum service and account for the capillary fill head in the calibration [general knowledge — verify].
- **Vacuum service.** Check the minimum allowed absolute pressure versus temperature for the chosen fill ([WIKA IN 00.25](https://kz.wika.com/upload/DS_IN0025_en_co_58173.pdf)).
- **Balanced systems.** Use equal capillary lengths and the same seal type on both sides for DP level, to cancel ambient temperature errors [general knowledge — verify]. Yokogawa's equivalent EJXC80A/EJAC80E offers a compensating capillary along the low-side capillary for the same purpose ([Yokogawa EJXC80A/EJAC80E](https://yokogawa.com/solutions/products-platforms/field-instruments/pressure-transmitters/liquid-level/ejxc80a-ejac80e-diaphragm-seal)).
- **Hydrogen permeation.** For H2 service, specify **gold-plated diaphragms** [general knowledge — verify].

### 3.3 Thermowells and ASME PTC 19.3 TW

| Model | Type | Source |
|---|---|---|
| **TW10** (data sheet **TW 95.10**) | Flanged thermowell. Designs: TW10-F full-penetration weld; TW10-P / -R double weld seam; TW10-S / -B screw-welded; **TW10-W forged, no welded joint**. Flanges per **ASME B16.5, EN 1092-1 or DIN 2527**. | [WIKA TW 95.10](https://kz.wika.com/upload/DS_TW9510_en_co_108854.pdf); [ICS Schneider TW10-B/-S](https://www.ics-schneider.de/produkte/tw10-b-tw10-s-einteiliges-schutzrohr-mit-gewindeflansch-schraubgeschweisste-ausfuehrung/?lang=en) [third-party copy] |
| **TW15** (TW 95.15) | Threaded thermowell: TW15-H hexagon, TW15-R milled wrench flats, TW15-M round with hexagon | [WIKA TW 95.15](https://cn.shop.wika.com/upload/DS_TW9515_en_co_726.pdf) |
| **TW20** | Socket-weld thermowell | [WIKA TW20 (Mensor copy)](https://www.mensor.com/media/Data-sheets/Temperature/Thermowells/ds_tw.sw_tw20_en_us.pdf) [third-party copy] |
| **TW25** | Weld-in thermowell, machined from solid; tapered, straight or stepped | [WIKA TW25 (Mensor copy)](https://www.mensor.com/media/Data-sheets/Temperature/Thermowells/ds_tw.wi_tw25_en_us.pdf) [third-party copy] |
| **TW30** | Listed as "TW.SC / TW30 Sanitary" in one search extract (WIKA TW catalogue copy, e.g. [RG Group WIKA TW catalogue](https://www.rg-group.com/images/document/WIKA/Wika-TW-Catalog.pdf) [third-party copy]; verify). **Correction:** an earlier version described TW30/TW35 as "Van Stone"; no source supported that. | — |
| **TW40** (TW 95.40) | **Fabricated** flanged thermowell per **DIN 43772 forms 2F, 3F** (TW40-8, -9, later -D, -E) | [WIKA TW 95.40](https://www.wika.com/media/Data-sheets/Temperature/Thermowells/ds_tw9540_en_co.pdf) |

**Engineering notes, thermowell wake-frequency (ASME PTC 19.3 TW-2016)**

- **The standard.** ASME PTC 19.3 TW-2016 (which superseded TW-2010, which in turn replaced the 1974 Murdock method) [history: general knowledge — verify] checks four things: frequency limit (resonance avoidance), dynamic stress (fatigue), static stress (pressure and drag), and hydrostatic pressure rating [general knowledge — verify].
- **Scope of WIKA's calculation.** WIKA applies the TW-2016 calculation only to **solid-machined** tapered, straight or stepped wells (TW10, TW15, TW20 …); it is **not applicable to fabricated (welded-tube) wells** such as TW40. Inputs: process T and P, nozzle ID and shielded length, pipe/vessel ID and wall; dynamic viscosity optional ([WIKA PTC 19.3 TW-2016 calculation page](https://www-prod.wika.com/en-us/software_thermowell_5.WIKA)).
- **Calculation service and software.** WIKA offers a web-based calculator (**version 3.0**) for single-well TW-2016 calculations, with a free single-calculation version (same source). Request the calculation report per tag, with the process data, as a VDR item.
- **Natural frequency.** The calculation uses the installed natural frequency, corrected for mounting compliance, added fluid mass and sensor mass [general knowledge — verify].
- **In-line and transverse resonance.** The well may pass through in-line resonance only if the **Scruton number Sc > 2.5** and the dynamic stress is acceptable; otherwise fs below about **0.4 × fnc**. Transverse resonance must be avoided: **fs < 0.8 × fnc** [general knowledge — verify against PTC 19.3 TW-2016 §6].
- **ScrutonWell.** Data sheet **SP 05.16**: helical strakes reduce vortex-induced vibration excitation by **more than 90 %**, making the dynamic part of the calculation redundant; only the static TW-2016 calculation is used for dimensioning, and **support collars are eliminated** ([WIKA SP 05.16](https://kz.wika.com/upload/DS_SP0516_en_co_66463.pdf)). An NEL Glasgow test reported **1.2 mm** deflection for a ScrutonWell vs **27 mm** for a standard well ([Fluid Handling Pro](https://fluidhandlingpro.com/endurance-test-for-vortex-breakers/)). WIKA advises against ScrutonWell in scaling service, excessive pulsation or mechanical resonance ([WIKA thermowell FAQ](https://www.WIKA.com.au/service_faq_thermowells_protection_tubes_en_co.WIKA)).
- **Velocity collars** need a tight fit in the nozzle, which means site machining; many operators dislike them. Check the project specification [general knowledge — verify].

### 3.4 Thermometers (bimetal, gas-actuated)

All rows in this sub-section are [general knowledge — verify]; no sources were retrieved.

| Model | Type | Key specs |
|---|---|---|
| **Bimetal 52 / 54 / 55 series** | Bimetal dial thermometers. **55** is the stainless industrial series (every-angle or back connection, optional liquid damping). | Class 1 per **EN 13190**; NS 63 to 160 mm; typical range −70 to +600 °C |
| **Gas-actuated 73 series** | Inert-gas filled expansion thermometer; rigid stem or **capillary** for remote mounting; available with switch contacts | Class 1 (EN 13190); wide range up to about +700 °C; vibration resistant |
| **Model 74 / 75** | Other gas-actuated variants (with transmitter, for example TGT73) | — |

- **Selection.** Gas-actuated thermometers are preferred over bimetal where vibration is present or remote reading is needed. Always use a thermowell for process service.

### 3.5 Temperature transmitters and TC/RTD assemblies

| Model | Function | Key specs | Source |
|---|---|---|---|
| **T32 (T32.1S head / T32.3S rail)**, data sheet **TE 32.04** | HART temperature transmitter | Optional **TÜV-certified SIL version** (T32.xS.xxx-S), full IEC 61508 assessment by **TÜV Rheinland**: **SIL 2 single, SIL 3 redundant**; type **B** device, systematic capability **SC 3**. Some sensor types are excluded from the SIL option. Accuracy per DIN EN 60770 depends on sensor type — read the current TE 32.04 table (latest found 12/2023). **Correction:** an earlier version said SIL 2 (single) only. | [TE 32.04 (Yodify copy)](https://industrial.yodify.com/Documentation/Document/emop3/DS-TE3204-en-co-59707.pdf) [third-party copy]; [ICS Schneider TE 32.04](https://www.ics-schneider.de/wp-content/uploads/2023/08/ds_te3204_en_co.pdf) [third-party copy]; [T32.xS SIL declaration (manualsdir)](https://www.manualsdir.com/manuals/465780/wika-t32xs.html?page=17) [third-party copy] |
| **T15 / T16 / T24** | Basic and digital transmitters | — | [general knowledge — verify] |
| **T53** | FOUNDATION Fieldbus / PROFIBUS PA temperature transmitter | — | [general knowledge — verify] |
| **TR10 family** (RTD) | TR10-A measuring insert (**TE 60.01**); TR10-B for additional thermowell (**TE 60.02**); TR10-C threaded (TE 60.03); TR10-F flanged (**TE 60.06**); TR10-L Ex d (**TE 60.12**) | **Pt100 / Pt1000**; classes per IEC 60751 (A, AA). **2-wire with class A or AA is not permissible/advisable** (lead resistance). WIKA refers to technical information **IN 00.17** for Pt100 detail. | [TR10-B TE 60.02 (BKW copy)](https://www.bkwinstruments.co.uk/wp-content/uploads/2025/09/ds_te6002_en_co_TR10_B.pdf) [third-party copy]; [TR10-C TE 60.03](https://www.bkwinstruments.co.uk/wp-content/uploads/2025/09/ds_te6003_en_co_TR10_C.pdf) [third-party copy]; [TR10-F](https://www.bkwinstruments.co.uk/wp-content/uploads/2015/05/TR10-F.pdf) [third-party copy]; [TR10-L](https://www.bkwinstruments.co.uk/wp-content/uploads/2015/05/TR10-L.pdf) [third-party copy] |
| **TC10 family** (thermocouple) | TC10-B for additional thermowell: data sheet **TE 65.02** (cross-referenced from TR10-B) | Types K, J, N, E, T, R, S, B per IEC 60584 [general knowledge — verify] | [TR10-B TE 60.02](https://www.bkwinstruments.co.uk/wp-content/uploads/2025/09/ds_te6002_en_co_TR10_B.pdf) [third-party copy] |
| **TC12 / TC80 / TR12 / TR11** | Other TC/RTD assemblies (TC80 high-temperature) | — | [general knowledge — verify] |
| **Multipoint (TC96 / TC95 / Flex-R)** | Reactor and column profiling thermocouples | Hydrotreater and hydrocracker reactors | [general knowledge — verify] |

### 3.6 Pressure transmitters

| Model | Function | Notes | Source |
|---|---|---|---|
| **IS-3** (data sheet **PE 81.58**) | Pressure transmitter for hazardous areas (intrinsically safe) | Long-term stability **≤ ±0.2 % of span/year**; zero and span adjustable ±5 %. Basic accuracy table not retrieved. | [ICS Schneider PE 81.58](https://www.ics-schneider.de/wp-content/uploads/2023/08/ds_pe8158_en_co.pdf) [third-party copy]; [Scribd PE 81.58](https://www.scribd.com/document/462675839/DS-PE8158-en-co-62113-pdf) [third-party copy] |
| **UPT-20 / UPT-21** (data sheet **PE 86.05**) | Universal process transmitter (gauge, absolute), display | Accuracy at reference conditions **0.15 % of span**; **4–20 mA HART** option; turndown limits: see data sheet | [WIKA AU PE 86.05](https://www.WIKA.com.au/upload/DS_PE8605_en_co_57612.pdf); [Crossco UPT-20](https://www.crossco.com/wp-content/uploads/2019/07/WIKA_UPT20.pdf) [third-party copy] |
| **DPT-10** | Differential pressure transmitter | — | [general knowledge — verify] |
| **IPT-10 / IPT-11** | Process transmitter with Ex d / Ex i | Can be combined with WIKA diaphragm seals | [general knowledge — verify] |
| **S-20 / A-10** | General industrial (OEM) transmitters | Non-process | [general knowledge — verify] |
| **PSD-4, PSA-31, MW / MA / MV switches** | Electronic and mechanical pressure switches | SIL-rated versions exist | [general knowledge — verify] |

- For EPC control and SIL loops, WIKA process transmitters are usually second-tier compared with Yokogawa, Emerson, E+H and ABB. WIKA's strength is **diaphragm seal + transmitter assemblies** (factory-filled and calibrated systems) [general knowledge — verify].

### 3.7 Level (KSR) and flow (WIKA flow)

**Level: KSR Kuebler (a WIKA Group company)**

| Model | Function | Source |
|---|---|---|
| **BNA** (data sheet **LM 10.01**) | Bypass magnetic level indicator: chamber + float + magnetic display. Versions include **BNA-S** (standard, stainless chamber) and **BNA-C** (compact). The 2015 LM 10.01 lists a temperature range of **−196…+150 °C** for the model shown; KSR's NPP sheet gives chamber ratings **Ø60.3×2 mm max 40 bar** and **Ø60.3×2.77 mm max 64 bar**. Latest LM 10.01 found: 05/2021. | [ICS Schneider LM 10.01](https://www.ics-schneider.de/wp-content/uploads/2023/08/ds_lm1001_en_co.pdf) [third-party copy]; [KSR BNA NPP data sheet](https://cn.shop.wika.com/upload/DS_BNA_NPP_en_ks_85274.pdf) |
| **BMD** | **Magnetic display (indicator rail) for the BNA**, not a separate bypass: **BMD-S** standard <200 °C, **BMD-F** high-temperature >200 °C. **Correction:** an earlier version called BMD a "mini bypass" variant. | [KSR BNA NPP data sheet](https://cn.shop.wika.com/upload/DS_BNA_NPP_en_ks_85274.pdf) |
| **FLR / FLS / FLM** | Float switches; reed-chain / magnetostrictive level transmitters mountable on the BNA | [general knowledge — verify] |

- **Selection.** For magnetic level indicators (MLIs), confirm the float design (SG, pressure and temperature margin; float collapse pressure), the chamber design code (ASME VIII / B31.3), and whether a TÜV / PED stamp is required [general knowledge — verify].

**Flow: WIKA flow products**

| Model | Function | Source |
|---|---|---|
| **FLC-OP** (data sheet **FL 10.01**, with **FLC-FL** flange and **FLC-AC** annular chamber) | Orifice plates per **ISO 5167-2**, clean liquids and gases; repeatability **0.1 % of flow rate**; beta **0.46–0.84**; accuracy **≤ ±2 % of full-scale flow** (French copy) | [WIKA FL 10.01](https://kz.wika.com/upload/DS_FL1001_en_co_50631.pdf); [FL 10.01 (fr)](https://kz.wika.com/upload/DS_FL1001_fr_fr_53441.pdf) |
| **FLC-FL** | Orifice flanges, data sheet **FL 10.12** (not retrieved) | Cross-reference in [ICS Schneider FL 10.15](https://www.ics-schneider.de/wp-content/uploads/2026/06/ds_fl1015_en_co.pdf) [third-party copy] |
| **FLC-RO-ST / FLC-RO-MS** (data sheet **FL 10.06**) | Restriction orifices, **single-step (ST)** and **multi-step (MS)**; multi-step splits the ΔP to avoid problems of a single large drop | [WIKA FL 10.06](https://cn.shop.wika.com/upload/DS_FL1006_en_co_50634.pdf); [WIKA RO page](https://www.WIKA.com.au/flc_ro_ms_flc_ro_st_en_co.WIKA) |
| **FLC-VT / FLC-FN / FLC-WG / FLC-AP** | Venturi tubes, flow nozzles, wedge elements, averaging Pitot tubes | [general knowledge — verify] |

- **Restriction orifice note.** For high-ΔP gas letdown, multi-stage ROs limit noise and choked flow. Request the sizing calculation and the noise level (dBA at 1 m) [general knowledge — verify].

### 3.8 Test and calibration

All rows are [general knowledge — verify]; not researched in this pass.

| Model family | Function |
|---|---|
| **CPG1500** | Precision digital pressure gauge (reference) |
| **CPH6xxx / CPH7xxx** | Hand-held pressure calibrators |
| **CPC (CPC2000 / CPC4000 / CPC6050 / CPC8000)** | Pressure controllers (portable and benchtop) |
| **CPB (CPB3800 / CPB5000)** | Deadweight testers (primary pressure standard) |
| **CTD / CTB / CTH / CTP** | Temperature calibration (dry-well calibrators, baths, thermometers, reference probes) |
| **CPP** | Hand test pumps |

### 3.9 WIKA engineering notes

1. **Gauge range selection.** Normal operating pressure should be about 25–75 % of full scale for a steady load, and up to about 50 % for a pulsating load. The maximum static load is about 75 % of FS (EN 837-2 guidance) [general knowledge — verify].
2. **Overpressure.** Standard gauges withstand about 1.3 × FS [general knowledge — verify]. Higher overpressure needs an overload-protected version (for example 232.36), or a gauge protector such as the adjustable overpressure protector **910.13** (data sheet **AC 09.04**) ([WIKA accessories catalogue (DirectIndustry)](https://pdf.directindustry.com/pdf/wika-alexander-wiegand-se-co-kg/instrumentation-valves-accessories/6196-713134.html)).
3. **Pulsation and vibration.**
   - Use liquid-filled cases (233.50) for vibration and dynamic loads ([WIKA AU PM 02.02](https://www.WIKA.com.au/upload/DS_PM0202_en_co_3672.pdf)).
   - Use a **snubber 910.12** (data sheet **AC 09.03**) against pressure surges and pulsation ([910.12 DS (Yodify copy)](https://industrial.yodify.com/Documentation/Document/P1XJK/WIKA-910-12-Pressure-Snubber-DS.pdf) [third-party copy]; [WIKA AC 09.03](https://kz.wika.com/upload/DS_AC0903_en_co_805.pdf)).
4. **Steam.** Install a **siphon 910.15** (data sheet **AC 09.06**, compact and U-form; one listing gives max **420 bar / 100 °C**) to keep live steam off the Bourdon tube ([WIKA AC 09.06 (Mensor copy)](https://www.mensor.com/media/Data-sheets/Pressure/Valves-and-protective-devices/ds_ac0906_en_co.pdf) [third-party copy]). The ~100 °C medium-temperature threshold for needing a siphon is [general knowledge — verify].
5. **Temperature limits.** Medium temperature for a stainless-steel gauge is about ≤+200 °C (dry) and about ≤+100 °C (filled) [general knowledge — verify; not found in PM 02.02 extracts]. Above that, use a siphon, a cooling element, or a diaphragm seal with a cooling tower.
6. **Diaphragm seal sizing.** Pick the diaphragm diameter so that the seal's displacement volume covers the instrument's needs; minimize capillary length; choose the fill for both process and ambient extremes; ask WIKA for the system calculation (see 3.2 for sources).
7. **Oxygen service.** Specify cleaned-for-oxygen (oil and grease free) and a halocarbon (KN21) fill (see 3.2). Gauges for O2 carry the "Oxygen! Use no oil" dial marking (EN 837-1) [general knowledge — verify].
8. **Sour service.** For H2S service, specify **NACE MR0175 / ISO 15156** compliant wetted materials, including the Bourdon tube [general knowledge — verify].

---

## 4. Cross-vendor quick comparisons

| Need | Yokogawa | Bently Nevada | WIKA | Notes |
|---|---|---|---|---|
| DP flow transmitter, ±0.04 % | EJX110A (±0.04 %; ±0.025 % opt.) ([source](https://www.yokogawa.com/us/solutions/products-and-services/measurement/field-instruments-products/pressure-transmitters/differential-pressure/ejx110a/)) | — | DPT-10 (lower tier) [general knowledge — verify] | — |
| Mass flow from DP with P/T compensation | EJX910A (±1 % over 10:1) ([GS](https://www.insatech.com/media/50aacz2k/gs_ejx910a_gs01c25r01-01en_34ed.pdf)) | — | — | — |
| Remote-seal DP level | EJA118E ⚠ discontinued (US); EJXC80A/EJAC80E seal system ([source](https://yokogawa.com/solutions/products-platforms/field-instruments/pressure-transmitters/liquid-level/ejxc80a-ejac80e-diaphragm-seal)) | — | 990.27 flush-flange seals ([DS 99.27](https://www.WIKA.com.au/upload/DS_DS9927_en_co_1240.pdf)); WIKA seals are also offered on Yokogawa EJA/EJX ([Yokogawa/WIKA seal doc](https://www.metisafrica.com/wp-content/uploads/docs/YO-SEP-WIKA.pdf)) | — |
| SIL temperature transmitter | YTA610/710, SIL 2 / 3 dual ([source](https://www.yokogawa.com/solutions/products-platforms/field-instruments/temperature-transmitters/field-mount/yta610-temperature-transmitter/)) | — | T32.xS SIL 2 single / SIL 3 redundant, TÜV Rheinland ([TE 32.04 copy](https://industrial.yodify.com/Documentation/Document/emop3/DS-TE3204-en-co-59707.pdf)) | — |
| Combustion O2/CO (SIL) | TDLS8000, SIL 2 single / 3 dual ([GS](https://web-material3.yokogawa.com/24/15840/files/GS11Y01D01-01EN-01.pdf)) | — | — | — |
| Vibration and position protection | — | 3500 / Orbit 60 + 3300 XL ([3500 DS](https://dam.bakerhughes.com/m/3e2d1931acef5630/original/3500-System-Datasheet-162096-pdf.pdf)) | — | Yokogawa-MAC projects integrate 3500 via relays and the 3500/92 Modbus TCP gateway |
| Overspeed | — | 3500/53 2oo3; 3701/55 ESD SIL 3 ([fact sheet](https://dam.bakerhughes.com/m/d4fe82417ccafbf/original/ADAPT-3701_55-Factsheet.pdf)) | — | ProSafe-RS can host the trip logic, but speed sensing is normally a dedicated system |
| Local pressure indication | — | — | 232.30/233.30 S3 safety-pattern gauges ([PM 02.04](https://www.WIKA.com.au/upload/DS_PM0204_de_de_3678.pdf)) | — |
| Thermowells and wake-frequency calculation | — | — | TW series + PTC 19.3 TW-2016 calculation ([WIKA calculator](https://www-prod.wika.com/en-us/software_thermowell_5.WIKA)), ScrutonWell ([SP 05.16](https://kz.wika.com/upload/DS_SP0516_en_co_66463.pdf)) | Required for every in-line well |
| DCS / SIS | CENTUM VP (R7) / ProSafe-RS (SIL 3) | — | — | — |

---

## Gaps

1. **WIKA: no vendor-sourced data.** wika.com was unreachable and the search budget ran out. All WIKA model numbers, limits, fill-fluid ranges, gauge model lists, T32 SIL status, IS-3/UPT-20 specs, KSR (BNA/BMD) and FLC-xx model codes, and the S0/S1/S3 definitions are general knowledge.
   - Verify against WIKA data sheets PM 02.02 (232.50), PM 02.04 (232.30), IN 00.06 (seals), TW 95.10 (PTC 19.3), TE 32.04 (T32) and others [document numbers also unverified].
   - Verify against the EN 837-1, ASME B40.100 and ASME PTC 19.3 TW-2016 texts.
2. **API 670 text not retrieved.** Probe counts, axial voting, Keyphasor requirements, runout limits, gap-voltage install tolerances and overspeed response time come from secondary sources or general knowledge. Verify against API 670 5th ed. (or the edition in the project specification).
3. **Bently seismic sensors.** The 330400 (100 mV/g) and 330500 Velomitor (3.94 mV/(mm/s)) specs could not be confirmed. Several 3500 module descriptions (/40M, /45 scope, /50M, /6x, /70M, /72M, /93, /94) and the full and mini rack slot counts are also unverified.
4. **3500/53 SIL certificate.** No module-specific SIL certificate was found. Orbit 60 SIL 3 (overspeed) is claimed in trade press, but only SIL 2 is confirmed in Baker Hughes datasheets.
5. **Yokogawa ROTAMASS TI accuracy.** Not retrieved; it is in GS 01U10B00-00EN-R §2.2 and the per-line GS documents.
6. **Yokogawa ADMAG AXG standard accuracy** (only the ±0.15 % high-accuracy option was confirmed) and **ZR22G maximum process temperature**.
7. **Yokogawa ultrasonic and radar.** No current in-house ultrasonic flowmeter was identified after the US300FM, which was discontinued in 2017. "US300" and "US350" could not be confirmed as model names. No radar or GWR OEM partnership announcement was found; only third-party DD files appear in Yokogawa's library.
8. **CENTUM VP R7.** No R7-specific hardware or N-IO specifications were retrieved. Vnet/IP bandwidth and the SENG description are general knowledge.
9. **Middle East MAC awards.** No recent publicly announced Yokogawa MAC award for ADNOC, Aramco or QatarEnergy LNG was found. Qatar NFE automation went to Honeywell per LNG Prime. The Petro Rabigh MAC reference needs its exact source page.
10. **EJA-E / EJX-A static-pressure ratings, wetted materials and hazardous-area certificates** (ATEX, IECEx, FM, CSA) were not captured. Pull them from the GS for each model code.
11. **Unreachable hosts.** yokogawa.com, wika.com and dam.bakerhughes.com were blocked for direct fetching in this environment. Several sources are reseller or third-party copies of datasheets (marked), so their revision may not be current.
