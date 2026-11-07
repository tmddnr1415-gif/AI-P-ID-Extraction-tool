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
- **Research limits.** The web search budget ran out, and the vendor hosts (yokogawa.com, wika.com, dam.bakerhughes.com) could not be fetched directly. **The WIKA section in particular is almost entirely general knowledge and must be verified.** See [Gaps](#gaps).

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
- **Remote seals.** EJA118E appears as discontinued on Yokogawa's US site. For new remote-seal DP level, confirm the current model offering in the AVL submittal (for example, EJA-E or EJX-A with diaphragm-seal options) [general knowledge — verify].
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
| **ADMAG AXG** (AXG1A high-grade transmitter / integral) | General-purpose and high-performance magmeter | Size **2.5–500 mm** (sensor combination), **2.5–400 mm** integral. High-accuracy option **±0.15 % of rate (25–200 mm)**. Standard accuracy not confirmed; see GS. | [Yokogawa ADMAG AXG](https://www.yokogawa.com/solutions/products-and-services/measurement/field-instruments-products/flow-meters/magnetic-flowmeters/admag-total-insight/admag-axg-admagti-magnetic-flowmeters/) [vendor marketing] |
| **ADMAG AXW** (AXW4A transmitter / integral) | Large-bore, water and wastewater, general | Accuracy **±0.35 % of reading** (AXW sensor combinations) | [Yokogawa ADMAG AXW](https://www.yokogawa.com/solutions/products-and-services/measurement/field-instruments-products/flow-meters/magnetic-flowmeters/admag-total-insight/admag-axw-admagti-magnetic-flowmeters/) [vendor marketing] |

- Magmeters need conductive liquids. They are not applicable to hydrocarbons, so their O&G use is limited to cooling water, produced water, chemical dosing and effluent [general knowledge — verify].

#### ROTAMASS Total Insight (TI) Coriolis

- The family GS is **GS 01U10B00-00EN-R** (2nd ed., Sep 2025). Accuracy is in section 2.2. The per-line GS documents are **GS 01U10B02 (Supreme)**, **GS 01U10B05 (Intense)** and **GS 01U10B03 (Giga)** ([Yokogawa GS 01U10B00-00EN-R](https://web-material3.yokogawa.com/FY2_GS01U10B00-00EN-R_2_0_284564.pdf)).
- **The TI accuracy figures were not retrieved.** The older ROTAMASS 3 series published **±0.1 % of reading + zero stability (liquid)** and **±0.5 % (gas)** ([Yokogawa technical report rd-te-n05401-002](https://web-material3.yokogawa.com/1/11309/tabs/rd-te-n05401-002.pdf)). Do not quote these figures for TI.
- Line names [general knowledge — verify]:
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
| **ZR22G + ZR802G** | Separate-type zirconia O2 (and humidity) analyzer: in-situ probe plus converter | O2 range **0.01–100 vol %**. Response **≤5 s to 90 %**. Heater replaceable on site. Cell-resistance self-diagnostics. Converter displays cell temperature and EMF. **Maximum process temperature not confirmed.** High-temperature probe versions exist for furnace gas >700 °C [general knowledge — verify]. | — | [Yokogawa ZR22G/ZR802G](https://www.yokogawa.com/solutions/products-and-services/measurement/analyzers/gas-analyzers/oxygen-analyzers/separate-type-oxygen-analyzer-zr22g-zr802g/) |
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
| **Release** | **CENTUM VP R7** announced in 2025. Exaopc pages list support for CENTUM VP R6.12 and R7.01. | [Yokogawa CENTUM VP](https://www.yokogawa.com/sk/solutions/products-and-services/control/control-and-safety-system/distributed-control-systems-dcs/centum-vp); [Exaopc page](https://yokogawa.com/solutions/products-platforms/solution-based-software/data-historian/centum-opc-server-exaopc) |
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
| Certification | **TÜV certified to IEC 61508 SIL 3**. SIL 3 in a **single-module configuration**, so redundancy is for availability, not for SIL. | [Yokogawa ProSafe-RS](https://www.yokogawa.com/tr/solutions/products-and-services/control/control-and-safety-system/process-safety-system-prosafe-rs/); [Yokogawa tech report](https://yokogawa.com/library/resources/yokogawa-technical-reports/safety-technologies-incorporated-in-the-safety-control-station) |
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
| **3300 XL 8 mm** (probes 330101/330102 3/8-24 UNF, 330103/330104 M10×1; non-armoured / armoured) | **7.87 V/mm (200 mV/mil)**; the 200 mV/mil figure was not seen directly (7.87 V/mm = 200 mV/mil × 39.37 mil/mm) | **2.0 mm (80 mil)**, from about **0.25 to 2.3 mm (10–90 mil)** from target | Specified at **1.27 mm (50 mil)** gap. Corresponds to about **−10 Vdc** gap voltage (1.27 mm × 7.87 V/mm ≈ 10 V) | **−17.5 to −26 Vdc** without barriers, **−23 to −26 Vdc** with barriers; **12 mA max** | Specs assume an **AISI 4140** steel target at 18–27 °C with a −24 Vdc supply. The standard 5 m system complies with **API 670 (4th ed.)** for mechanical configuration, linear range, accuracy and temperature stability. Backward compatible with non-XL 3300 5/8 mm parts, but a mixed system meets only non-XL specs. PPS probe tip. | [8 mm datasheet 141194 copy](https://core.instrumart.com/assets/bently-nevada-3300-xl-proximity-transducer-system-datasheet.pdf) [third-party copy]; [Scribd 141194](https://es.scribd.com/document/282524498/3300-Xl-8mm-Proximity-transducer-system-Datasheet-141194-Cda-000-0-1) [third-party copy] |
| **3300 XL 11 mm** | **3.94 V/mm (100 mV/mil) ±10 %** including interchangeability | **4.0 mm (160 mil)**, from about **0.5 to 4.5 mm (20–180 mil)** | **2.5 mm (100 mil)** | −17.5 to −26 Vdc, 12 mA max | DSL (deviation from the best-fit straight line) **< ±0.10 mm (±4 mil)**. Over the extended temperature range, scale factor stays within ±25 %. Used for **thrust/axial position and steam-turbine differential expansion** (DE), and where a longer range is needed. | [Baker Hughes datasheet 146256 Rev P](https://dam.bakerhughes.com/m/27a2d91f28aadd41/original/3300-XL-11mm-Proximity-Transducer-System-Datasheet-146256-pdf.pdf); [Instrumart 11 mm](https://www.instrumart.com/products/46464/bently-nevada-3300-xl-11mm-proximity-probe) |
| 3300 XL 25 mm / 35 mm / 50 mm | Lower scale factors | Long range (DE ramps, large axial growth) | — | — | 50 mm system: 5 or 9 m total | [Instrumart 25 mm extension cable](https://www.instrumart.com/products/47980/bently-nevada-3300-xl-25mm-extension-cable); 11 mm datasheet copy (above) |
| 3300 XL NSv | Smaller-tip probe for tight spaces (for example, small-centrifugal-compressor) | — | — | — | — | [Instrumart NSv extension cable](https://www.instrumart.com/products/34701/bently-nevada-3300-xl-nsv-extension-cable) |
| 3300 5 mm | Legacy small probe | — | — | — | Probe lengths 0.5, 1, 5, 9 m | [3300 5 mm copy](https://www.scribd.com/document/672181722/3300prox5mm) [third-party copy] |

**Engineering notes, proximity probes**

- **Target material.** Accuracy and interchangeability specs apply only to an **AISI 4140** target. Other shaft materials need calibration to the actual target, or a scale-factor correction ([8 mm datasheet copy](https://core.instrumart.com/assets/bently-nevada-3300-xl-proximity-transducer-system-datasheet.pdf)).
- **Gap voltage check during installation.** For the 8 mm system, the −10 Vdc gap voltage corresponds to the mid-linear-range 1.27 mm gap. Acceptable install ranges are usually about −9 to −11 V for radial probes. For thrust probes, the gap is set to suit the expected float direction and the active thrust face [general knowledge — verify].
- **Glitch and runout.** API 670 limits combined electrical plus mechanical runout in the probe track to **25 % of the allowable peak-to-peak vibration or 6 µm (0.25 mil), whichever is greater** [general knowledge — verify against API 670 5th ed.]. Specify a burnished probe track and degaussing in the machine data sheet (MDS).
- **Cable length is part of the calibration.** Do not cut or splice extension cables. A 5 m Proximitor will not linearize a 9 m system [general knowledge — verify].

### 2.2 Seismic transducers (Velomitor and accelerometers)

| Model | Function | Key specs | Source |
|---|---|---|---|
| **330500 Velomitor** | Piezoelectric velocity sensor (casing velocity) | **3.94 mV/(mm/s) (100 mV/in/s)** | [general knowledge — verify] |
| **330400** | Accelerometer for API 670 casing (gear-mesh, high-frequency) measurement | **10.2 mV/(m/s²) (100 mV/g)**; API 670 compliant | [general knowledge — verify] |
| 330425 | Accelerometer, 25 mV/g, larger amplitude range | — | [general knowledge — verify] |
| 190501 Velomitor CT | Low-frequency velocity sensor (cooling towers) | — | [general knowledge — verify] |

- The 3500/42M accepts **velocity and acceleration** channel types, alongside radial vibration, thrust, DE, eccentricity, REBAM (rolling element bearing activity monitoring) and shaft absolute ([3500/42M datasheet 143694](https://dam.bakerhughes.com/m/20b1fd1cd261c09f/original/3500-42M-Proximitor-Seismic-Monitor-Datasheet-143694-pdf.pdf)).

### 2.3 3500 machinery protection system

**Rack and architecture.** The 3500 is a rack-based protection system. A rack holds:

- one or two power supplies (3500/15),
- the TDI (3500/22M), which is the rack interface,
- monitor, Keyphasor, relay and communication modules.

The system overview is in the **3500 System datasheet 162096** ([Baker Hughes 162096](https://dam.bakerhughes.com/m/3e2d1931acef5630/original/3500-System-Datasheet-162096-pdf.pdf); [Instrumart copy](https://core.instrumart.com/assets/3500-System-Datasheet.pdf)). The datasheet index is document 141526 ([3500 manuals/datasheets index](https://dam.bakerhughes.com/m/3f24df10f181094b/original/3500_manuals_datasheets_141526g-pdf.pdf)).

- **Rack sizes:** a 19-inch full rack with **14 monitor slots**, and a mini rack with **7 slots** [general knowledge — verify].
- **SIL:** the 3500 can be supplied for applications up to **SIL 3**, with TMR configurations available. This is a system-level statement, not a per-module certificate ([Bently 3500 brochure as cited in 3500 PDF copy](https://www.scribd.com/document/343169343/3500-pdf) [third-party copy]; [Baker Hughes 3500 page](https://www.bakerhughes.com/bently-nevada/monitoring-systems/machinery-protection/3500-machinery-protection-systems)).

| Module | Function | Key facts | Source |
|---|---|---|---|
| **3500/15** | Power supply (AC or DC) | Redundant pair recommended; **mandatory** in racks with the 3500/53 | [3500/53 spec copy](https://m.rms-dcs.com:443/uploads/3500-53.pdf) [third-party copy] |
| **3500/22M TDI** | Transient Data Interface: rack interface plus System 1 data | Primary interface for the 3500 configuration software, with a **direct interface to System 1** (no external comms processor). Rack configuration uses a proprietary protocol. **Not** a Modbus gateway; use the 3500/92. | [3500 System datasheet](https://dam.bakerhughes.com/m/3e2d1931acef5630/original/3500-System-Datasheet-162096-pdf.pdf) |
| **3500/25** | Enhanced Keyphasor module | Half-height; powers and terminates **up to 2 Keyphasor transducers**. Two modules in one slot give **4 Keyphasors per rack**. | [3500/25 datasheet 141532](https://dam.bakerhughes.com/m/22d0219c69acbaf5/original/3500-25-Enhanced-Keyphasor-Module-Datasheet-141532-pdf.pdf); [Instrumart copy](https://core.instrumart.com/assets/3500-25-Datasheet.pdf) |
| **3500/32M** | 4-channel relay module | **DPDT** relays; AND/OR voting logic; latching or non-latching. **3500/33** is the 16-channel version (SPDT [general knowledge — verify]). Only relay modules may be used for shutdown. Analog and Modbus outputs are for annunciation and trending only. | [3500 System datasheet](https://dam.bakerhughes.com/m/3e2d1931acef5630/original/3500-System-Datasheet-162096-pdf.pdf) |
| **3500/40M** | Proximitor monitor (4 ch) | Radial vibration, thrust, eccentricity, DE [general knowledge — verify] | — |
| **3500/42M** | Proximitor/Seismic monitor (**4 channels**, programmed in pairs) | Channel types: radial vibration, thrust position, DE, eccentricity, REBAM, velocity, acceleration, shaft absolute, circular acceptance region. Input sensitivity **3.94 mV/µm (100 mV/mil)** or **7.87 mV/µm (200 mV/mil)**. Input impedance **10 kΩ** (standard I/O). About **7.7 W** typical. Alert setpoint per value; Danger on any two values. | [3500/42M datasheet 143694](https://dam.bakerhughes.com/m/20b1fd1cd261c09f/original/3500-42M-Proximitor-Seismic-Monitor-Datasheet-143694-pdf.pdf); [Instrumart copy Rev V](https://core.instrumart.com/assets/3500-42M-Datasheet.pdf) |
| **3500/45** | Position monitor | Axial (thrust) position, differential expansion, ramp DE, valve position [scope: general knowledge — verify]. Datasheet 135545. | [3500 index 141526](https://dam.bakerhughes.com/m/3f24df10f181094b/original/3500_manuals_datasheets_141526g-pdf.pdf) |
| **3500/46M** | Hydro monitor | — | [general knowledge — verify] |
| **3500/50M** | Tachometer module (speed, rotor acceleration, zero speed) | — | [general knowledge — verify] |
| **3500/53** | Electronic overspeed detection | Designed to meet **API 670 and API 612** overspeed requirements. Modules combine as **2-out-of-2 or 2-out-of-3 (recommended)** voting. Redundant power supplies required. Module P/N 133388-01; manual 134939-01. A competitor (Istec) states that the 3500/53 depends on the rack for SIL and is **not a stand-alone SIL device**. | [3500/53 spec copy](https://m.rms-dcs.com:443/uploads/3500-53.pdf) [third-party copy]; [Istec comparison](https://www.istec.com/?p=36050) [competitor claim] |
| **3500/60, /61, /65** | Temperature monitors (RTD/TC; /61 with recorder outputs; /65 16-channel) | — | [general knowledge — verify] |
| **3500/62** | Process variable monitor (4–20 mA inputs) | — | [general knowledge — verify] |
| **3500/64M** | Dynamic pressure monitor (combustion dynamics on gas turbines) | — | [general knowledge — verify] |
| **3500/70M, /72M** | Reciprocating compressor: impulse/velocity and rod position (rod drop) | — | [general knowledge — verify] |
| **3500/92** | Communication gateway | **Modbus TCP and Modbus serial** (RS-232/422/485); acts as server/slave only | [Instrumart 3500/92](https://www.instrumart.com/products/46393/bently-nevada-350092-communication-gateway); [3500 System datasheet](https://dam.bakerhughes.com/m/3e2d1931acef5630/original/3500-System-Datasheet-162096-pdf.pdf) |
| **3500/93, /94** | Display interface modules (VGA or touchscreen) | — | [general knowledge — verify] |

**Engineering notes, 3500**

- **DCS interface.** Use hard-wired relays (3500/32M or /33) for trips to the SIS or ESD. Use the 3500/92 Modbus TCP gateway for values and alarms to the DCS. Use the 3500/22M TDI for System 1 only (sources above).
- **4–20 mA recorder outputs.** These are available on the monitor I/O modules. Use them for DCS trending where the Modbus gateway is not accepted, not for trip duty [general knowledge — verify].
- **Overspeed.** For steam turbines under API 612 or 670, use 3500/53 in **2oo3** with three dedicated speed probes, separate from the Keyphasor. Alternatively, use a certified stand-alone overspeed system. Bently's 3701 ADAPT ESD offers SIL 3 overspeed (see 2.4).

### 2.4 Orbit 60, ADAPT, 3701

| Product | Function | Key facts | Source |
|---|---|---|---|
| **Orbit 60 Series** | Next-generation protection and condition monitoring platform (3500 successor path) | **SIL 2** certification is the consistently documented level ("SIL 2 certification for confidence through redundancy measures"). Trade press claims SIL 2 and 3 plus API 670 compliance. Baker Hughes said in 2019 that SIL 3 overspeed would follow, being offered then in the 3701 ESD. Operating temperature **−30 to +65 °C** (system); the SIM is rated −30 to +70 °C, altitude <2000 m. The SIM is non-interfering, so system SIL 2 does not require it to be SIL certified. Built-in cybersecurity is emphasized. Approvals are in guide 108M1756. | [Orbit 60 fact sheet](https://dam.bakerhughes.com/asset/8588eaac-d1af-4d4e-81a3-9b61dff5c3c6/Orbit60-Fact-Sheet_Web-Version.pdf); [Protection Processor Module DS 142M8515](https://dam.bakerhughes.com/m/1832f7859078b618/original/ORBIT-60-SERIES-Protection-Processor-Module-Datasheet-142M8515.pdf); [SIM DS 142M9054](https://dam.bakerhughes.com/m/eee1b773db43667/original/ORBIT-60-SERIES-System-Interface-Module-Datasheet-142M9054.pdf); [Turbomachinery Magazine](https://www.turbomachinerymag.com/view/bently-nevadas-new-platform); [Chemical Engineering](https://www.chemengonline.com/monitoring-platform-built-cybersecurity/) |
| **ADAPT 3701** | Compact protection and condition monitoring for a single machine. Variants: /40 general machinery, /44 aero-derivative GT, /46 hydro [variants: general knowledge — verify]. The **3701 ESD** offers SIL 3 overspeed per the Baker Hughes 2019 statement. | — | [Turbomachinery Magazine](https://www.turbomachinerymag.com/view/bently-nevadas-new-platform) (3701 ESD SIL 3 overspeed); others [general knowledge — verify] |

### 2.5 System 1, Ranger, Trendmaster

- **System 1.** Bently's condition-monitoring and diagnostic software (orbit, shaft centreline, Bode, waterfall, and so on). It connects directly to the 3500/22M TDI ([3500 System datasheet](https://dam.bakerhughes.com/m/3e2d1931acef5630/original/3500-System-Datasheet-162096-pdf.pdf)) and to Orbit 60 and ADAPT [general knowledge — verify].
- **Ranger Pro.** A wireless (ISA100-based [general knowledge — verify]) vibration and temperature sensor for balance-of-plant machines that are not API 670 critical [general knowledge — verify].
- **Trendmaster Pro / SPA.** Online scanning (surveillance) system for semi-critical pumps and fans using Trendmaster Proximitor/Interface Modules (TIMs) [general knowledge — verify]. Legacy; check lifecycle status.
- **Classification.** Machines are usually classed as **critical** (3500 or Orbit 60 protection with System 1), **essential** (online scanning or wireless) and **balance-of-plant** (portable route-based collection). The project's machinery monitoring philosophy should map each class to a platform [general knowledge — verify].

### 2.6 API 670 compliance checklist

The API 670 text was not retrieved. Items below are drawn from vendor datasheets, secondary sources and general knowledge, and must be checked against the **current edition** (5th ed., 2014, with errata [general knowledge — verify]) and the purchaser's MDS. API 670 covers radial shaft vibration, casing vibration, axial position, speed, rod drop, phase reference, overspeed and critical temperatures ([Emerson white paper](https://s1-live.emerson.com/documents/automation/white-paper-measurement-types-in-machinery-monitoring-ams-en-39660.pdf)).

| Check | Typical requirement | Source |
|---|---|---|
| Radial probes per bearing | **Two (X–Y), 90° apart**, usually at ±45° from vertical (10:30 and 1:30 o'clock) to clear the bearing split line | [Emerson white paper](https://s1-live.emerson.com/documents/automation/white-paper-measurement-types-in-machinery-monitoring-ams-en-39660.pdf); [Reliabilityweb](https://reliabilityweb.com/articles/entry/temporary_mounting_of_proximity_probes) |
| Axial (thrust) position | **Two axial probes** per thrust bearing, observing the shaft end or an integral collar, within about 300 mm (12 in) of the thrust collar. Trip logic **2oo2 voting** (both probes in Danger) | [general knowledge — verify] |
| Phase reference | One **Keyphasor** probe per shaft (a second is often specified as a spare); a once-per-turn notch or projection | [general knowledge — verify]; module capacity from [3500/25 DS](https://dam.bakerhughes.com/m/22d0219c69acbaf5/original/3500-25-Enhanced-Keyphasor-Module-Datasheet-141532-pdf.pdf) |
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

> **WARNING.** The search budget ran out, and wika.com was unreachable from this environment. **Every WIKA statement below is [general knowledge — verify]** unless a link is given, and none could be given. Use this section only as an orientation map of WIKA model families and the governing standards. Confirm each model number and limit against the current WIKA data sheet (PM, TM, AC, TW, IN, SP, CT series data-sheet numbers) before use.

### 3.1 Pressure gauges

**Governing standards**

| Standard | Accuracy designation | Notes |
|---|---|---|
| **EN 837-1** (Bourdon tube gauges) | Accuracy **classes 0.1, 0.25, 0.6, 1.0, 1.6, 2.5, 4.0** (% of full scale) | Defines safety levels **S0** (no safety device), **S1** (with blow-out device), and **S3** (solid baffle wall between the measuring element and the dial, plus a blow-out back). S3 is the "solid-front" or "safety pattern" design. [general knowledge — verify] |
| **ASME B40.100** | Grades **4A (±0.1 %), 3A (±0.25 %), 2A (±0.5 %), 1A (±1 %), A (±1 % middle half, ±2 % elsewhere), B (2-3-2 %), C, D** | "Solid-front" case with a blow-out back is the US safety-case term. [general knowledge — verify] |

**Typical WIKA Bourdon-tube gauge families** [general knowledge — verify]

| Model | Function | Key specs | Typical use |
|---|---|---|---|
| **232.50 / 233.50** | Stainless steel case and wetted parts. 232.50 is dry; **233.50 is liquid-filled** (glycerine or silicone). | NS 63, 100, 160 mm. Class 1.0 (NS 100/160) or 1.6 (NS 63). Ranges up to about 1,600 bar (higher via 232.50.100 or HP variants). IP65. Safety level S1 (blow-out device). | General process gauges on O&G skids; liquid-filled for vibration and pulsation |
| **232.30 / 233.30** | Safety-pattern (solid-front) stainless steel gauge to **EN 837-1 S3**: solid baffle wall plus blow-out back | NS 63, 100, 160. Class 1.0. | Often required by O&G specifications for gas service and for ranges above about 25 bar or 400 psi |
| **232.36 / 233.36** | Safety pattern with increased overpressure safety (gauge protected up to about 2×–5× FS, depending on version) | — | Services where overpressure is expected |
| **212.20 / 213.53** | Brass wetted parts, economy | — | Utilities (air, water) |
| **PG23LT / PG28** | Gauges with integrated transmitter signal (intelliGAUGE) | — | Local + remote reading |
| **432.50 / 433.50** | Diaphragm-element gauge (low ranges, viscous or crystallizing media, high overload) | — | Low-pressure or open-flange diaphragm service |
| **532.5x / 632.50** | Absolute and capsule gauges for very low pressure (mbar) | — | Vacuum and draft |
| **7xx (DELTA-plus 7xx.xx)** | Differential pressure gauges | — | Filter ΔP |
| **PGS23 / PSM** | Switch gauges (gauge with contacts) | — | Local alarm |

- **Specifying a "safety pattern gauge" in a TBE.** Ask for the EN 837-1 safety code (S3) explicitly, or for "ASME B40.100 solid-front with blow-out back". A "blow-out disc" alone is S1, not S3.

### 3.2 Diaphragm seals

| Model family | Type | Notes |
|---|---|---|
| **990.10 / 990.12** | Threaded-connection diaphragm seal, upper body + lower body | Cleanable; flushing connections optional |
| **990.27 / 990.28 / 990.29** | Flange-type seals with flush (integral) diaphragm (pancake or flanged) | ASME B16.5 or EN 1092-1 flanges. Common on vessel and tank level DP. |
| **990.41** | Flange with **extended diaphragm (tube) / extended flush**, to sit flush with the vessel ID through an insulated nozzle | Viscous or solidifying media |
| **990.22 / 990.15** | In-line (flow-through) seals | Slurries, sanitary |
| **9xx with capillary** | Capillary (armoured SS) to a remote transmitter or gauge | Capillary length drives response time and temperature error |

**Fill fluids** (indicative; check data sheet IN 00.18 or the current WIKA fill-fluid sheet):

| Fill fluid | Indicative range | Notes |
|---|---|---|
| Silicone oil (standard, for example KN2) | about −40 to +200 °C (vacuum limits lower) | General purpose |
| High-temperature silicone (for example KN17) | up to about +300 to +400 °C at positive pressure | Heat-transfer service; not for vacuum at high temperature |
| Low-temperature silicone | down to about −70 °C | Cold climates, LNG periphery |
| Halocarbon oil | about −40 to +175 °C | **Oxygen and chlorine** (oxidizer-compatible) service |
| Neobee M-20 / food-grade | about −10 to +200 °C | Food and pharma (FDA) |
| Glycerine-water | limited range | Low-cost |

**Engineering notes**

- **Temperature error.** The fill expands with temperature, which shifts the zero. The error grows with fill volume (capillary length, seal size) and falls with a larger, more compliant diaphragm. Request WIKA's **diaphragm seal system calculation** (temperature error, response time) for each tag.
- **Response time** grows with capillary length and fill viscosity, especially at low temperatures. Long capillaries with high-viscosity fills can take tens of seconds. Avoid them in fast control or SIL loops.
- **Vacuum service.** Check the minimum allowed absolute pressure versus temperature for the chosen fill.
- **Head effect.** Mount the transmitter at or below the lower seal for vacuum service. Account for the capillary fill head in the calibration.
- **Balanced systems.** Use equal capillary lengths and the same seal type on both sides for DP level, to cancel ambient temperature errors.
- **Hydrogen permeation.** For H2 service, specify **gold-plated diaphragms**.

### 3.3 Thermowells and ASME PTC 19.3 TW

| Model | Type |
|---|---|
| **TW10** | Flanged thermowell, solid-machined from bar or forging (ASME B16.5 / EN 1092-1 flanges) |
| **TW15** | Threaded thermowell |
| **TW20** | Socket-weld thermowell |
| **TW25** | Weld-in thermowell (for example, for high-pressure or high-velocity service) |
| **TW30 / TW35** | Van Stone and other forms |
| **TW40** | Fabricated (welded from tube) thermowells for low-pressure service |

**Engineering notes, thermowell wake-frequency (ASME PTC 19.3 TW-2016)**

- **The standard.** ASME PTC 19.3 TW-2016 (which superseded TW-2010, which in turn replaced the 1974 Murdock method) checks four things:
  1. **Frequency limit** (resonance avoidance).
  2. **Dynamic stress** (fatigue).
  3. **Static stress** (pressure and drag).
  4. **Hydrostatic pressure** rating.
- **Natural frequency.** The calculation uses the installed natural frequency, corrected for mounting compliance, added fluid mass and sensor mass.
- **In-line resonance.** In-line resonance occurs at about twice the shedding frequency. The well may operate through the in-line resonance only if the **Scruton number Sc > 2.5** (typically gas service) and the dynamic stress is acceptable. Otherwise the shedding frequency must stay below about **0.4 × fnc** (low-Sc case, typically liquids).
- **Transverse resonance** must always be avoided: **fs < 0.8 × fnc**.
- **Common fixes:** shorten the insertion length, increase the root or tip diameter, use a tapered stem, or add a **velocity collar** (support collar). WIKA also offers the **ScrutonWell** helical-strake design, which suppresses vortex shedding so that long wells can pass the TW-2016 check without a collar.
- **Velocity collars.** These need a tight fit in the nozzle, which means site machining. That makes them unpopular with many operators. Check the project specification.
- **Calculation service.** WIKA provides a PTC 19.3 TW calculation service and online tools. Request the calculation report per tag, with the process data (max velocity, density, viscosity, P, T), as a VDR item.

### 3.4 Thermometers (bimetal, gas-actuated)

| Model | Type | Key specs |
|---|---|---|
| **Bimetal 52 / 54 / 55 series** | Bimetal dial thermometers. **55** is the stainless industrial series (every-angle or back connection, optional liquid damping). | Class 1 per **EN 13190**; NS 63 to 160 mm; typical range −70 to +600 °C |
| **Gas-actuated 73 series** | Inert-gas filled expansion thermometer; rigid stem or **capillary** for remote mounting; available with switch contacts | Class 1 (EN 13190); wide range up to about +700 °C; vibration resistant |
| **Model 74 / 75** | Other gas-actuated variants (with transmitter, for example TGT73) | — |

- **Selection.** Gas-actuated thermometers are preferred over bimetal where vibration is present or remote reading is needed. Always use a thermowell for process service.

### 3.5 Temperature transmitters and TC/RTD assemblies

| Model | Function | Key specs |
|---|---|---|
| **T32 (T32.1S head / T32.3S rail)** | HART temperature transmitter | **TÜV certified for SIL 2** (single) per IEC 61508 in the "S" version; dual-sensor input; sensor-drift monitoring; Ex i and Ex d approvals |
| **T15 / T16 / T24** | Basic and digital transmitters | — |
| **T53** | FOUNDATION Fieldbus / PROFIBUS PA temperature transmitter | — |
| **TC10 / TC12 / TC80** | Thermocouple assemblies (TC10 for thermowell mounting; TC80 high-temperature) | Types K, J, N, E, T, R, S, B per IEC 60584 |
| **TR10 / TR12 / TR11** | RTD assemblies (Pt100 per IEC 60751, class A/B/AA) | — |
| **TC/TR + TW** | Assembled sensor + transmitter + thermowell packages | — |
| **Multipoint (TC96 / TC95 / Flex-R)** | Reactor and column profiling thermocouples | Hydrotreater and hydrocracker reactors |

### 3.6 Pressure transmitters

| Model | Function | Notes |
|---|---|---|
| **IS-3 (IS-3x)** | Intrinsically safe industrial pressure transmitter (ATEX, IECEx) | Skids and OEM packages |
| **UPT-20 / UPT-21** | Universal process transmitter (gauge, absolute), HART, display | Process-grade, cost-effective |
| **DPT-10** | Differential pressure transmitter | — |
| **IPT-10 / IPT-11** | Process transmitter with Ex d / Ex i | Can be combined with WIKA diaphragm seals |
| **S-20 / A-10** | General industrial (OEM) transmitters | Non-process |
| **PSD-4, PSA-31, MW / MA / MV switches** | Electronic and mechanical pressure switches | For example the MA and MV series for O&G; SIL-rated versions exist |

- For EPC control and SIL loops, WIKA process transmitters are usually second-tier compared with Yokogawa, Emerson, E+H and ABB. WIKA's strength is **diaphragm seal + transmitter assemblies** (factory-filled and calibrated systems).

### 3.7 Level (KSR) and flow (WIKA flow)

**Level: KSR Kuebler (a WIKA Group company)**

| Model | Function |
|---|---|
| **BNA** | Bypass magnetic level indicator (chamber + float + roller or flap indicator); options for reed-chain transmitter (**FLM**), magnetostrictive transmitter, or switches; can mount GWR in the chamber |
| **BMD** | Mini bypass level indicator variant |
| **FLR / FLS** | Float switches |
| **FLM** | Magnetostrictive level transmitter |

- **Selection.** For magnetic level indicators (MLIs), confirm the float design (SG, pressure and temperature margin; float collapse pressure), the chamber design code (ASME VIII / B31.3), and whether a TÜV / PED (Pressure Equipment Directive) stamp is required.

**Flow: WIKA flow products (formerly Euromisure / WIKA flow)**

| Model | Function |
|---|---|
| **FLC-OP** | Orifice plates (ISO 5167 / ASME MFC-3M) |
| **FLC-FL** | Orifice flange assemblies (meter runs) |
| **FLC-RO** | Restriction orifices (single-stage and multi-stage) |
| **FLC-VT / FLC-FN** | Venturi tubes and flow nozzles |
| **FLC-WG** | Wedge-type flow elements |
| **FLC-AP** | Averaging Pitot tubes |

- **Restriction orifice note.** For high-ΔP gas letdown, multi-stage ROs limit noise and choked flow. Request the sizing calculation and the noise level (dBA at 1 m).

### 3.8 Test and calibration

| Model family | Function |
|---|---|
| **CPG1500** | Precision digital pressure gauge (reference) |
| **CPH6xxx / CPH7xxx** | Hand-held pressure calibrators |
| **CPC (CPC2000 / CPC4000 / CPC6050 / CPC8000)** | Pressure controllers (portable and benchtop) |
| **CPB (CPB3800 / CPB5000)** | Deadweight testers (primary pressure standard) |
| **CTD / CTB / CTH / CTP** | Temperature calibration (dry-well calibrators, baths, thermometers, reference probes) |
| **CPP** | Hand test pumps |

### 3.9 WIKA engineering notes

1. **Gauge range selection.** Normal operating pressure should be about 25–75 % of full scale for a steady load, and up to about 50 % for a pulsating load. The maximum static load is about 75 % of FS (EN 837-2 guidance).
2. **Overpressure.** Standard gauges withstand about 1.3 × FS. Higher overpressure needs a safety-pattern or overload-protected version (for example 232.36), or a gauge protector or isolator.
3. **Pulsation and vibration.**
   - Use liquid-filled cases (233.50) for vibration.
   - Use **snubbers or dampers** (restrictor screws in the socket, or a 910.12 snubber) for pulsation.
   - Use **gauge isolators** (910.13 and similar) for overpressure spikes.
4. **Steam.** Install a **siphon** (910.15, pigtail or U-type) to keep live steam off the Bourdon tube (above about 100 °C medium temperature).
5. **Temperature limits.** Medium temperature for a stainless-steel gauge is about ≤+200 °C (dry) and about ≤+100 °C (filled). Above that, use a siphon, a cooling element, or a diaphragm seal with a cooling tower.
6. **Diaphragm seal sizing.**
   - Pick the diaphragm diameter so that the seal's "displacement volume" covers the instrument's needs. Small seals on low ranges give large temperature errors.
   - Minimize the capillary length.
   - Choose the fill for both the process and the ambient temperature extremes.
   - Ask WIKA for the system calculation (temperature error, response time).
7. **Oxygen service.** Specify cleaned-for-oxygen (oil and grease free) and a halocarbon fill. Gauges for O2 carry the "Oxygen! Use no oil" dial marking (EN 837-1).
8. **Sour service.** For H2S service, specify **NACE MR0175 / ISO 15156** compliant wetted materials (for example Monel or 316L within limits), including the Bourdon tube.

---

## 4. Cross-vendor quick comparisons

| Need | Yokogawa | Bently Nevada | WIKA | Notes |
|---|---|---|---|---|
| DP flow transmitter, ±0.04 % | EJX110A (±0.04 %; ±0.025 % opt.) ([source](https://www.yokogawa.com/us/solutions/products-and-services/measurement/field-instruments-products/pressure-transmitters/differential-pressure/ejx110a/)) | — | DPT-10 (lower tier) [verify] | — |
| Mass flow from DP with P/T compensation | EJX910A (±1 % over 10:1) ([GS](https://www.insatech.com/media/50aacz2k/gs_ejx910a_gs01c25r01-01en_34ed.pdf)) | — | — | — |
| Remote-seal DP level | EJA118E ⚠ discontinued (US); EJA/EJX with seals [verify] | — | 990.xx seals + DPT/IPT, or seals for third-party transmitters [verify] | — |
| SIL temperature transmitter | YTA610/710, SIL 2 / 3 dual ([source](https://www.yokogawa.com/solutions/products-platforms/field-instruments/temperature-transmitters/field-mount/yta610-temperature-transmitter/)) | — | T32.xS SIL 2 [verify] | — |
| Combustion O2/CO (SIL) | TDLS8000, SIL 2 single / 3 dual ([GS](https://web-material3.yokogawa.com/24/15840/files/GS11Y01D01-01EN-01.pdf)) | — | — | — |
| Vibration and position protection | — | 3500 / Orbit 60 + 3300 XL ([3500 DS](https://dam.bakerhughes.com/m/3e2d1931acef5630/original/3500-System-Datasheet-162096-pdf.pdf)) | — | Yokogawa-MAC projects integrate 3500 via relays and the 3500/92 Modbus TCP gateway |
| Overspeed | — | 3500/53 2oo3; 3701 ESD SIL 3 | — | ProSafe-RS can host the trip logic, but speed sensing is normally a dedicated system |
| Local pressure indication | — | — | 232.30/233.30 S3 safety-pattern gauges [verify] | — |
| Thermowells and wake-frequency calculation | — | — | TW series + PTC 19.3 TW-2016 calculation, ScrutonWell [verify] | Required for every in-line well |
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
