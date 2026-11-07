# Vendors: Emerson and Honeywell — I&C Product Portfolio Reference

> Knowledge-base file 04. Scope: field instruments, final control elements, F&G, wireless, DCS/SIS and asset-management software from **Emerson** (Rosemount, Micro Motion, Fisher, Bettis, Crosby/Anderson Greenwood, DeltaV, Ovation, AMS) and **Honeywell** (SmartLine, Experion, Safety Manager, F&G, OneWireless, Enraf). Compiled November 2026.

---

## How to use this file

- **Purpose.** Gives an I&C chatbot the facts engineers use for vendor model selection and spec-compliance checks on oil & gas, LNG and petrochemical EPC projects: model families, measured variable, headline accuracy/turndown/stability, SIL capability, typical use, and where to find the governing document.
- **Source tags.** Every spec number is followed by a source link. Items that could not be confirmed during research are tagged **[general knowledge — verify]**. Treat those as leads, not facts. Do not put an unverified number into a datasheet, bid evaluation or SRS.
- **Spec hierarchy.** Vendor figures are *reference* accuracy at reference conditions unless stated. Installed ("total probable error") performance is always worse: add ambient-temperature effect, static-pressure effect, stability over the calibration interval, and primary-element uncertainty for flow. Use the vendor's current Product Data Sheet (PDS) and the specific order code (performance class) as the governing document.
- **SIL claims.** "SIL 3 capable" in vendor literature almost always means *systematic capability SC 3*, with random-hardware architecture limits of **SIL 2 at HFT = 0** and **SIL 3 at HFT = 1** (redundant use). Always check the IEC 61508 certificate (exida/TÜV) and safety manual: certificate number, firmware revision covered, required option code (e.g. Rosemount "QT"), λ values and proof-test coverage. Several sources found below show this pattern explicitly.
- **Document revisions disagree.** Several numbers differ between older and newer data sheets (e.g. Micro Motion H-/F-Series gas accuracy, Rosemount 2051 accuracy, Fisher GX size range). Where this was found it is flagged. Ask the user for the data-sheet revision when the answer matters.
- **Research constraints.** Vendor websites (emerson.com, process.honeywell.com) were not reachable for direct fetch from the research environment, and the web-search budget ran out before the Honeywell section could be researched. **The Honeywell section is therefore almost entirely [general knowledge — verify].** See "Gaps".

---

## Table of contents

1. [Emerson — corporate context](#1-emerson--corporate-context)
2. [Emerson — Rosemount pressure](#2-emerson--rosemount-pressure)
3. [Emerson — Rosemount temperature](#3-emerson--rosemount-temperature)
4. [Emerson — Rosemount level and tank gauging](#4-emerson--rosemount-level-and-tank-gauging)
5. [Emerson — Rosemount flow (DP, magnetic, vortex, ultrasonic)](#5-emerson--rosemount-flow-dp-magnetic-vortex-ultrasonic)
6. [Emerson — Micro Motion Coriolis](#6-emerson--micro-motion-coriolis)
7. [Emerson — Rosemount analytical](#7-emerson--rosemount-analytical)
8. [Emerson — Flame and gas detection](#8-emerson--flame-and-gas-detection)
9. [Emerson — Wireless (WirelessHART)](#9-emerson--wireless-wirelesshart)
10. [Emerson — Fisher control valves, trims, actuators, positioners](#10-emerson--fisher-control-valves-trims-actuators-positioners)
11. [Emerson — Bettis / EIM actuators](#11-emerson--bettis--eim-actuators)
12. [Emerson — Crosby / Anderson Greenwood pressure relief](#12-emerson--crosby--anderson-greenwood-pressure-relief)
13. [Emerson — DeltaV, DeltaV SIS, Ovation, AMS, Plantweb](#13-emerson--deltav-deltav-sis-ovation-ams-plantweb)
14. [Emerson — cross-cutting field-device features (HART, NE 43/107, approvals)](#14-emerson--cross-cutting-field-device-features)
15. [Honeywell — corporate context](#15-honeywell--corporate-context)
16. [Honeywell — SmartLine field instruments](#16-honeywell--smartline-field-instruments)
17. [Honeywell — Flow (VersaFlow, MagneW, Elster ultrasonic)](#17-honeywell--flow)
18. [Honeywell — Enraf tank gauging](#18-honeywell--enraf-tank-gauging)
19. [Honeywell — Experion PKS, Experion LX, ControlEdge](#19-honeywell--experion-pks-experion-lx-controledge)
20. [Honeywell — Safety Manager / Safety Manager SC](#20-honeywell--safety-manager--safety-manager-sc)
21. [Honeywell — Fire & Gas detection](#21-honeywell--fire--gas-detection)
22. [Honeywell — OneWireless, FDM, Uniformance, valve positioner, UOP](#22-honeywell--onewireless-fdm-uniformance-valve-positioner-uop)
23. [Emerson vs Honeywell — quick comparison](#23-emerson-vs-honeywell--quick-comparison)
24. [Gaps](#gaps)

---

## 1. Emerson — corporate context

- Brands relevant to I&C: **Rosemount** (pressure, temperature, level, DP flow, magnetic flow, vortex, tank gauging, analytical, flame & gas), **Micro Motion** (Coriolis, density), **Fisher** (control valves, regulators, FIELDVUE positioners), **Bettis / EIM** (valve actuators), **Crosby / Anderson Greenwood** (pressure relief), **DeltaV** (DCS & SIS), **Ovation** (power/water DCS), **AMS Device Manager**, **Plantweb** (digital ecosystem). [general knowledge — verify]
- Gas chromatographs previously carried the **Daniel** brand (e.g. "Daniel 700XA") and are now sold as **Rosemount 700XA**; old manuals still use the Daniel name ([manualmachine – Daniel 700XA reference](https://manualmachine.com/daniel/700xagaschromatographsystemreference/26863131-manuals--guides)).
- Corporate changes engineers ask about: Emerson acquired NI (2023) and completed the full acquisition of AspenTech (2025); Emerson sold its Climate Technologies (Copeland) business (2023). [general knowledge — verify]. These do not change the field-device product lines above.

---

## 2. Emerson — Rosemount pressure

### 2.1 Product table

| Model | Measures / function | Key specs (reference) | Approvals / SIL | Typical use | Source |
|---|---|---|---|---|---|
| **3051S** (Ultra / Ultra for Flow / Classic performance classes) | DP, GP, AP, level, DP flow (scalable platform) | **Ultra:** ±0.025 % of span, **200:1** rangedown, **15-year** stability, 15-year limited warranty. **Classic:** ±0.035 % of span, **150:1** rangedown, 15-year stability | IEC 61508 certified, SIL 2/3 [general knowledge — verify certificate]; Ex d/Ex ia global approvals [general knowledge — verify] | Custody/fiscal DP flow, critical control, SIS where premium performance is justified | [Emerson 3051S tank-gauging PDS](https://s1-auth.emerson.com/documents/automation/product-data-sheet-rosemount-3051s-pressure-transmitter-high-accuracy-pressure-measurement-for-tank-gauging-systems-en-104536.pdf); [Emerson 3051S PDS](https://emerson.com:443/documents/automation/product-data-sheet-rosemount-3051s-series-of-instrumentation-en-73154.pdf) |
| **3051** (3051C coplanar, 3051T in-line, 3051L level, 3051CF flow) | DP, GP, AP, level, DP flow | ±0.04 % of span (Emerson release ties ±0.04 % to spans down to **10:1** turndown); **150:1** rangedown; 10-year stability | Safety certified to IEC 61508 with FMEDA certificate; SIL 2 / SIL 3 (via third-party assessment). Older (2012) data sheets mention SIL 2 only | General-purpose workhorse for control and SIS | [Emerson 3051 PDS](https://d1-live.emerson.com/documents/automation/product-data-sheet-rosemount-3051-pressure-transmitter-en-73134.pdf); [Emerson news – 3051 enhancements](https://emerson.com/en-ca/news/automation/1207-rosemount3051); [Spartan 3051 flyer](https://www.spartancontrols.com/getattachment/343bb462-792d-418c-bb25-3e60edf11cf0/flyer-rosemount-3051-product-flyer-en-77014.pdf); [Instrumart 3051 2012 datasheet](https://instrumart.com/assets/Rosemount-3051-May-2012-datasheet.pdf) |
| **2051** (2051C, 2051T, 2051L, 2051CF) | DP, GP, AP, level, DP flow (value tier) | Standard ±0.075 % of span; **P8** high-accuracy option ±0.065 % of span; **100:1** rangeability (2010 PDS). A May 2024 PDS revision exists — check current values. 150:1 could **not** be confirmed | IEC 61508 option available [general knowledge — verify] | Utility, non-critical control, cost-sensitive packages | [Transcat 2051 PDS (2010)](https://www.transcat.ca/media/pdf/2051PDS.pdf); [Instrumart 2051T (100:1)](https://www.instrumart.com/products/24683/rosemount-2051t-pressure-transmitter); [Emerson 2051 PDS 00813-0100-4107 / doc 73206](https://emerson.com/documents/automation/product-data-sheet-rosemount-2051-pressure-transmitter-en-73206.pdf) |
| **3051SMV** (3051S MultiVariable) | DP + static pressure + process temperature; on-board fully compensated mass/energy flow | Static pressure: Ultra ±0.025 % span / 200:1; Classic ±0.035 % span / 150:1; 15-year stability. Mass flow: "Ultra for Flow" ±0.04 % of reading (distributor) vs ±0.65 % flow accuracy (older Emerson flyer) — these describe different configurations | HART and FOUNDATION Fieldbus variants | Gas/steam flow where density varies; Emerson states DP-only can give >6 % error from density change, DP+SP reduces to <3 % | [Instrumart 3051SMV datasheet](https://core.instrumart.com/assets/Rosemount-3051SMV-Datasheet.pdf); [Emerson 3051SMV flyer](https://d1-live.emerson.com/documents/automation/flyer-rosemount-3051s-multivariable-transmitter-en-5236912.pdf); [Spartan 3051SMV](https://www.spartancontrols.com/products/measurement-instrumentation/flow-measurement/differential-pressure-flow/rosemount-3051s-multivariable-flow-transmitter/); [Emerson 3051SMV config data sheet](https://d1-live.emerson.com/documents/automation/configuration-data-sheet-rosemount-3051s-multivariable-transmitter-en-73952.pdf) |
| **4088** (4088A / 4088B) | DP + SP + PT multivariable for upstream/midstream; Modbus RS-485 or BSAP/MVS | ±0.05 % of reading accuracy claimed (distributor); multidrop up to 32 transmitters per RS-485 bus | AGA/ASME/ISO/API/DIN compliance claimed by distributor; **API 21.1 compliance not confirmed** | Wellhead/EFM with flow computers/RTUs (e.g. ROC/FloBoss), plunger lift, custody transfer | [Spartan 4088](https://www.spartancontrols.com/products/remote-automation-scada/multivariable-transmitters/rosemount-4088-multivariable-transmitter/); [Experitec 4088](https://experitec.com/products/measurement-instrumentation/pressure-measurement/pressure-transmitters-and-transducers/rosemount-4088-multivariable-transmitter); [Emerson 4088 PDS](https://d1-live.emerson.com/documents/automation/product-data-sheet-rosemount-4088-multivariable-transmitter-en-78312.pdf) |
| **1199** diaphragm seal systems | Remote/direct seals for 3051S/3051/2051 | Configurations: direct mount, remote mount, **Tuned-System** (asymmetric capillaries, one seal direct-mounted), **Balanced** (equal capillaries). **Thermal Range Expander (TRE):** two fill fluids, −75 to 410 °C. Emerson claims Tuned-System reduces temperature effects 10–20 % and improves response time 80 %; TRE improves response up to 46 % | — | DP level on hot/viscous/corrosive/sanitary service, interface, density | [Emerson 1199 catalog](https://emerson.com/en-us/catalog/rosemount-sku-1199-diaphragm-seal-system); [Spartan remote-seal technical note](https://www.spartancontrols.com/getattachment/e248b337-4372-48ec-aeae-c05a89399679/ReliablePressureMeasurementWithRemoteDiaphragm_TechnicalNote.pdf); [Instrumart 1199 manual](https://core.instrumart.com/assets/Rosemount-1199-manual.pdf) |
| **3051S ERS** (Electronic Remote Sensors) | Two 3051S sensors wired electronically; DP calculated | Eliminates capillaries on tall vessels [general knowledge — verify specs] | — | Tall columns, splitters, cold climates where capillary temperature effect is large | [Instrumart 1199 manual (mentions ERS with TRE)](https://core.instrumart.com/assets/Rosemount-1199-manual.pdf) |
| **305 / 306 / 304 manifolds** | 305 integral (coplanar) manifold; 306 in-line manifold for 3051T/2051T; 304 conventional (traditional flange) manifold | 2-, 3-, 5-valve configurations; assembled and leak-tested to transmitter on request [general knowledge — verify] | — | Isolation/equalisation/vent of DP and GP transmitters | [general knowledge — verify] |

### 2.2 Selection notes — pressure

- **3051S vs 3051 vs 2051.** Choose by required total probable error and lifecycle, not just reference accuracy: 3051S Ultra (0.025 %, 200:1, 15-year stability) > 3051S Classic (0.035 %, 150:1) > 3051 (0.04 %, 150:1, 10-year stability) > 2051 (0.075 % std / 0.065 % P8, 100:1). Sources: as in table above.
- **Turndown vs accuracy.** Rangedown is the ability to re-range; accuracy degrades below a threshold turndown (for the 3051, the ±0.04 % figure holds to 10:1, per [Emerson news](https://emerson.com/en-ca/news/automation/1207-rosemount3051)). Do not quote headline accuracy at 100:1 rangedown.
- **Multivariable.** Use 3051SMV or 4088 where gas/steam density varies and a separate PT/TT plus DCS compensation is not wanted. 4088 targets RTU/flow-computer architectures (Modbus/BSAP); 3051SMV targets DCS (HART/FF) ([Spartan 4088](https://www.spartancontrols.com/products/remote-automation-scada/multivariable-transmitters/rosemount-4088-multivariable-transmitter/)).
- **Remote seals.** Seal systems are often the largest source of error in DP level. Prefer Tuned-System or ERS over long balanced capillaries on tall vessels, and TRE where fill-fluid viscosity at low ambient limits response ([Emerson 1199 catalog](https://emerson.com/en-us/catalog/rosemount-sku-1199-diaphragm-seal-system); [Spartan technical note](https://www.spartancontrols.com/getattachment/e248b337-4372-48ec-aeae-c05a89399679/ReliablePressureMeasurementWithRemoteDiaphragm_TechnicalNote.pdf)).
- **SIS.** Order with the IEC 61508 option (Rosemount commonly uses code **QT**) and check the certificate for SIL 2 @ HFT 0 / SIL 3 @ HFT 1 (pattern shown for the 644 in [exida 644 certificate](https://emerson.com/documents/automation/safety-certificate-rosemount-644-software-rev-1-1-x-en-5260914.pdf); assume similar for pressure but verify).

---

## 3. Emerson — Rosemount temperature

### 3.1 Product table

| Model | Function | Key specs | Approvals / SIL | Typical use | Source |
|---|---|---|---|---|---|
| **3144P** | Field-mount (dual-compartment) temperature transmitter, single or dual input; HART, FF | **5-year** long-term stability; dual-sensor **Hot Backup** (auto-switch to backup sensor on primary failure), averaging, differential; **Sensor Drift Alert**; transmitter–sensor matching (Callendar-Van Dusen) improves accuracy "up to 75 %" (vendor claim) | IEC 61508, SIL 2/3 (third-party); exida SAEL lists SIL 3 capability. 2004 release claims 5-year proof-test interval — verify against current safety manual | Critical control and SIS temperature, reactor/furnace, custody temperature | [Spartan 3144P](https://www.spartancontrols.com/products/measurement-instrumentation/temperature-measurement/temperature-transmitters/rosemount-3144p-temperature-transmitter); [exida SAEL 3144P](https://www.exida.com/SAEL-Safety/Rosemount-3144P-4-20mA-HART); [automation.com 3144P release](https://www.automation.com/article/emersons-rosemount-3144p-is-industrys-first-safety); [Emerson 3144P manual](https://s1-live.emerson.com/documents/automation/manual-rosemount-3144p-temperature-transmitter-en-104720.pdf) |
| **644** (644H head, 644F field, 644R rail) | Single or dual input (dual only on head mount, HART); HART selectable Rev 5 / Rev 7; FF; Profibus PA [general knowledge — verify PA] | 644R D/A accuracy ±0.03 % of span; **P8** enhanced accuracy option for Pt100 only | **SIL 3 capable** (SC3); exida certificate: **SIL 2 @ HFT=0, SIL 3 @ HFT=1**; ordering option **QT**; 644R single-sensor SIL AC = SIL 2. Certificate lists surveillance audit due 1 Dec 2026 | General temperature; SIS loops with head-mount | [Emerson 644 PDS](https://d1-live.emerson.com/documents/automation/product-data-sheet-rosemount-644-temperature-transmitter-en-73332.pdf); [exida 644 certificate](https://emerson.com/documents/automation/safety-certificate-rosemount-644-software-rev-1-1-x-en-5260914.pdf); [644R PDS](https://www.emerson.com/documents/automation/product-data-sheet-rosemount-644-rail-mount-temperature-transmitter-en-8046340.pdf); [644R FMEDA](https://emerson.com/documents/automation/functional-safety-certificate-fmeda-rosemount-644r-temperature-transmitter-en-8429878.pdf) |
| **3144** (original) / **248** | 3144 = predecessor of 3144P; 248 = value-tier head/rail transmitter | Formal discontinuation of the original 3144 was **not** confirmed; 3144P documents compare against "earlier Rosemount 3144 and 3244MV" | — | Brownfield replacement | [Emerson 3144P manual](https://s1-live.emerson.com/documents/automation/manual-rosemount-3144p-temperature-transmitter-en-104720.pdf); 248 specs [general knowledge — verify] |
| **648** wireless | WirelessHART temperature transmitter | Battery: SmartPower module, multi-year (648-specific life not confirmed) | — | Remote/monitoring points, X-well | [Emerson wireless catalog](https://www.emerson.com/en-us/catalog/wireless-temperature?fetchFacets=true) |
| **0065** (RTD) / **0185** (thermocouple) sensors | DIN-style sensor assemblies | 0065: −196 to 450 °C; 0185: −40 to 1000 °C (PDS 00813-0200-2654 Rev LD, 2020). Secondary ordering table: 0065 Pt100 IEC 751; 0185 IEC 584 Class 1. 0185: 316 SST tip, 321 SST MI cable. **IEC 60751 Class A option not confirmed** | Ex approvals as assembly with transmitter [general knowledge — verify] | Standard RTD/TC with thermowell | [pdf4pro – DIN-style sensor PDS](https://pdf4pro.com/view/product-data-sheet-rosemount-din-style-temperature-7a73b9.html); [manualmachine 0065/0185 QSG](https://manualmachine.com/rosemount/00650185sensorassembly/26861977-quick-start-guide) |
| **Thermowells** (Rosemount barstock series) | Barstock and fabricated thermowells | Wake-frequency calculation per **ASME PTC 19.3 TW-2016** offered as service [general knowledge — verify]; not confirmed in sources found | — | All intrusive temperature points | [general knowledge — verify] |
| **X-well technology** | Non-intrusive process temperature from pipe-surface + ambient measurement using a thermal-conductivity (Fourier's law) algorithm; 648 (WirelessHART) or 3144P (4–20 mA HART) with 0085 pipe-clamp sensor | "Similar accuracy to a thermowell" (vendor); Emerson also states accuracy is application dependent and degrades as process–ambient ΔT increases; suggested for **non-critical control and monitoring** | — | Where thermowell is undesirable: high velocity, small lines, corrosive service, retrofit without hot-tap | [Emerson X-well](https://www.Emerson.com/Rosemount-Xwell); [Emerson X-well about page](https://www.emerson.com/en-us/automation/measurement-instrumentation/temperature-measurement/about-rosemount-x-well-technology); [X-well brochure](https://s1-live.emerson.com/documents/automation/brochure-rosemount-x-well-technology-en-8721452.pdf) |

### 3.2 Selection notes — temperature

- **3144P vs 644.** 3144P: dual-compartment field housing, dual-sensor Hot Backup and drift alert, 5-year stability — usually specified for SIS and critical control. 644: head-mount, lower cost, HART 5/7 selectable, SIL 2 @ HFT 0 ([exida 644](https://emerson.com/documents/automation/safety-certificate-rosemount-644-software-rev-1-1-x-en-5260914.pdf); [Spartan 3144P](https://www.spartancontrols.com/products/measurement-instrumentation/temperature-measurement/temperature-transmitters/rosemount-3144p-temperature-transmitter)).
- **Dual-element sensors** with Hot Backup reduce spurious trips from single RTD/TC failure but do not count as hardware redundancy (HFT) for SIL unless the safety manual says so [general knowledge — verify].
- **X-well.** Treat as monitoring/non-critical control. Do not use for SIS or custody unless the user has a site validation; Emerson itself frames it this way ([Emerson X-well about](https://www.emerson.com/en-us/automation/measurement-instrumentation/temperature-measurement/about-rosemount-x-well-technology)).
- **Thermowell design.** Specify wake-frequency/stress calculation to ASME PTC 19.3 TW for every intrusive well on gas or high-velocity liquid lines [general knowledge — verify standard edition used by project].

---

## 4. Emerson — Rosemount level and tank gauging

### 4.1 Product table

| Model | Principle | Key specs | Approvals / SIL | Typical use | Source |
|---|---|---|---|---|---|
| **5408** / **5408:SIS** | Non-contacting radar, **FMCW 26 GHz** | Standard ±2 mm (±0.08 in); **ultra** accuracy ±1 mm; max range 150 m; 5408:SIS **25 m in safety mode**. (One distributor lists ±3 mm — Emerson figure governs) | 5408 and 5408:SIS **SIL 3 capable**, 1oo1 use for SIL 2 (IEC 61508) | Process vessels, storage tanks, SIS high-level | [Emerson 5408 catalog](https://www.emerson.com/en-us/catalog/rosemount-sku-5408-non-contacting-radar-transmitter); [5408 certificate](https://www.emerson.com/documents/automation/certificate-rosemount-5408-5408-sis-level-transmitters-en-202464.pdf); [5408 SIS flyer](https://emerson.com/documents/automation/flyer-rosemount-5408-non-contacting-radar-level-transmitter-how-do-i-know-rosemount-5408-a-good-fit-for-safety-applications-en-1572268.pdf); [Instrumart 5408](https://www.instrumart.com/products/44380/rosemount-5408-radar-level-transmitter) |
| **5300** (5301 level / 5302 level+interface / 5303 solids) | Guided wave radar (GWR) | ±3 mm (±0.12 in) accuracy, ±1 mm repeatability (distributor; model/conditions not stated). **Dynamic Vapor Compensation (DVC)** compensates vapour-space dielectric in steam; full benefit above **247 psia**. 5301 interface only with fully submerged probe | SIL 2 capable [general knowledge — verify certificate] | Separators, boilers/steam drums (with DVC), interface, chambers | [Caltrol 5300](https://caltrol.com/products/measurement-instrumentation/level-measurement/continuous-level-measurement/rosemount-5300-level-transmitter-guided-wave-radar/); [Emerson GWR high-pressure steam technical note](https://www.emerson.com/documents/automation/technical-note-using-guided-wave-radar-for-level-in-high-pressure-steam-applications-en-76264.pdf); [5300 DVC flyer](https://d1-live.emerson.com/documents/automation/flyer-rosemount-5300-guided-wave-radar-dynamic-vapor-compensation-en-5396720.pdf); [5300 PDS (manualmachine)](https://manualmachine.com/emerson/rosemount5302/22981367-product-data-sheet) |
| **3308** | Wireless GWR (WirelessHART), standalone | ±3 mm reference accuracy ("High Performance" profile code U); repeatability ±2 mm; range up to 17 m; battery ~9 years at 1-min update (reseller); high-performance version reported compliant with **API 18.2** custody transfer | — | Remote well-pad/oilfield tanks, custody (lease) | [Emerson 3308 PDS](https://d1-auth.emerson.com/documents/automation/product-data-sheet-rosemount-3308-series-wireless-guided-wave-radar-3308a-en-77242.pdf); [Control Global – API 18.2](https://www.controlglobal.com/measure/level/article/11303075/emersons-wirelesshart-radar-level-device-meets-api-182-standard); [Lakeside 3308](https://www.lakesidecontrols.com/products/measurement-instrumentation/industrial-wireless/wireless-level-measurement/rosemount-3308-wireless-level-transmitter-guided-wave-radar/) |
| **2140 / 2140:SIS** | Vibrating fork level detector (liquids) | "Fast drip" fork for quicker response horizontally; numerical response time not found | 2140:SIS: IEC 61508 Type B, low demand, **SIL 2 @ HFT=0, SIL 3 @ HFT=1** (Safety Manual Dec 2023). Wired HART device (claims of a WirelessHART 2140 unverified) | High/high-high and low-low level switches, pump protection | [2140:SIS safety manual](https://emerson.com/documents/automation/safety-manual-rosemount-2140-sis-level-detector-vibrating-fork-en-us-187108.pdf); [2140 PDS](https://www.emerson.com/documents/automation/rosemount-2140-2140-sis-level-detectors-en-187110.pdf); [2140 FMEDA](https://emerson.com/documents/automation/functional-safety-certificate-2140-level-switch-sil-2-fmeda-report-en-7634114.pdf) |
| **2130 / 2120** | Vibrating fork switches (non-HART) | — | 2130 FMEDA available | General point level | [2130 FMEDA](https://emerson.com/documents/automation/product-certificate-fmeda-report-rosemount-2130-level-switch-en-8070958.pdf) |
| **5900S** | Tank-gauging radar level gauge | **±0.5 mm** instrument accuracy (custody transfer); OIML and national type approvals. **SIL 2** with one or two 5900S/5900C; **SIL 3 with 5900S 2-in-1** (two independent radar electronics in one gauge) plus 2410 with SIL relay/analog output | OIML R85:2008, PTB, NMi etc. (via 2410 listing). Custody type-approval code must match on 5900S and 2410 | Bulk storage, refinery/terminal custody, independent overfill (API 2350) | [Emerson 5900S PDS](https://d1-live.emerson.com/documents/automation/product-data-sheet-rosemount-5900s-radar-level-gauge-en-104522.pdf); [Emerson 5900S about](https://www.emerson.com/en-ca/automation/measurement-instrumentation/tank-gauging-system/about-radar-level-measurement-for-tank-gauging/about-rosemount-5900s-radar-level-gauge); [Spartan 2410](https://www.spartancontrols.com/products/measurement-instrumentation/tank-gauging/tank-gauging-communications-and-accessories/rosemount-2410-tank-hub/) |
| **2410** Tank Hub | Tank-gauging data concentrator (Tankbus, intrinsically safe); single-tank and multi-tank versions | Single-tank version supports one 5900S 2-in-1 or two radar gauges | SIL 2 / SIL 3 certified with SIL relay/analog option | Collects level, temperature (2240S), water-bottom, pressure on a tank | [Applied Control 2410](https://www.appliedcontrol.com/products/measurement-instrumentation/industrial-wireless/wireless-tank-gauging/rosemount-2410-tank-hub); [Emerson tank gauging brochure](https://d1-auth.emerson.com/documents/automation/brochure-rosemount-tank-gauging-system-en-104480.pdf) |
| **3051S for tank gauging** | Hydrostatic/HTG pressure for density/mass | Ultra 0.025 % span, 200:1, 15-year stability | — | Hybrid tank gauging (density, mass) | [Emerson 3051S tank gauging PDS](https://s1-auth.emerson.com/documents/automation/product-data-sheet-rosemount-3051s-pressure-transmitter-high-accuracy-pressure-measurement-for-tank-gauging-systems-en-104536.pdf) |

### 4.2 Selection notes — level

- **GWR (5300) vs non-contacting radar (5408).** GWR is generally preferred for small vessels, chambers/bridles, interface, low-dielectric liquids, foam, turbulence and high-pressure steam (with DVC); non-contacting radar is preferred where a probe is undesirable (agitators, coating, very tall tanks, sticky media) [general engineering opinion — verify per application]. DVC for steam is a documented 5300 capability ([Emerson steam technical note](https://www.emerson.com/documents/automation/technical-note-using-guided-wave-radar-for-level-in-high-pressure-steam-applications-en-76264.pdf)).
- **5408:SIS range.** Safety-mode range is limited to 25 m vs 150 m standard ([Emerson 5408 catalog](https://www.emerson.com/en-us/catalog/rosemount-sku-5408-non-contacting-radar-transmitter)).
- **Process radar ≠ tank gauging.** 5408 (±2 mm / ±1 mm) is process-grade; for custody/inventory use 5900S (±0.5 mm, OIML R85) with 2410 hub ([Emerson 5900S PDS](https://d1-live.emerson.com/documents/automation/product-data-sheet-rosemount-5900s-radar-level-gauge-en-104522.pdf)). The 0.5 mm is instrument accuracy; total custody uncertainty also depends on tank calibration, temperature and installation.
- **Overfill protection (API 2350).** 5900S 2-in-1 provides independent level for control + overfill in one tank opening and reaches SIL 3 per Emerson ([Emerson 5900S about](https://www.emerson.com/en-ca/automation/measurement-instrumentation/tank-gauging-system/about-radar-level-measurement-for-tank-gauging/about-rosemount-5900s-radar-level-gauge)). Some end users still require physically separate technology for HH trip — check client philosophy.
- **Point level SIS.** 2140:SIS is SIL 2 at HFT 0; use 1oo2 for SIL 3 ([2140:SIS safety manual](https://emerson.com/documents/automation/safety-manual-rosemount-2140-sis-level-detector-vibrating-fork-en-us-187108.pdf)).

---

## 5. Emerson — Rosemount flow (DP, magnetic, vortex, ultrasonic)

### 5.1 DP flow

| Model | Type | Key specs | Typical use | Source |
|---|---|---|---|---|
| **485 Annubar** | Averaging pitot (T-shaped sensor) | ±0.75 % flow uncalibrated; up to ±0.5 % calibrated (flow test data mostly over **10:1** turndown) | Large-line gas/air/steam, low permanent pressure loss, hot-tap retrofit | [Emerson Annubar flow test data book](https://emerson.com/documents/automation/manual-rosemount-annubar-primary-flow-element-flow-test-data-book-en-74372.pdf); [Annubar brochure](https://emerson.com/documents/automation/brochure-rosemount-annubar-flow-meters-en-87398.pdf) |
| **585 Annubar** | Heavy-duty averaging pitot | ±1.50 % uncalibrated; up to ±0.5 % calibrated | High-temperature/high-pressure steam, heavy-duty service | [Emerson Annubar flow test data book](https://emerson.com/documents/automation/manual-rosemount-annubar-primary-flow-element-flow-test-data-book-en-74372.pdf) |
| **405 Compact** (405C conditioning orifice, 405P compact orifice, 405A compact Annubar) | Compact primary between flanges | Conditioning orifice technology reduces straight-run to **2D upstream / 2D downstream** of most disturbances (claim is for conditioning orifice; 405-specific figure not confirmed) | Short straight-run skids, retrofit | [Emerson DP primary elements PDS](https://www.emerson.com/documents/automation/product-data-sheet-rosemount-dp-flowmeters-primary-elements-en-87598.pdf); [Instrumart 405 datasheet](https://core.instrumart.com/assets/Rosemount-405-Datasheet.pdf) |
| **1595 conditioning orifice** | Four-hole conditioning orifice plate | Same 2D/2D straight-run principle [general knowledge — verify] | Replacing standard orifice where run is short | [general knowledge — verify] |
| **1195 / 3051SFP / 3051CFP / 2051CFP** | Integral orifice flowmeter (self-centring orifice body + transmitter) for **½–1½ in (15–40 mm)** lines | 1195 up to ±0.75 % of flow rate; max 450 °F (232 °C) standard direct-mount; case study ±0.8 % mass flow over 14:1 (distributors also state 8:1 for liquids — conflict) | Small-line fuel gas, chemical injection, utility | [Emerson 3051SFP](https://www.emerson.com/en-us/catalog/rosemount-sku-3051sfp-integral-orifice-flow-meter); [Emerson integral orifice case study](https://emerson.com/documents/automation/case-study-gas-supplier-improves-billing-accuracy-integral-orifice-differential-pressure-flow-meter-en-104842.pdf); [Emerson integral orifice manual](https://s1-live.emerson.com/documents/automation/manual-rosemount-integral-orifice-flowmeter-series-en-76146.pdf) |
| **3051SF / 3051CF / 2051CF** | Fully assembled DP flowmeters (transmitter + primary) | 3051CF: up to 1.65 % volumetric flow accuracy at 8:1 (configuration-dependent) | Complete pre-engineered DP flow assemblies | [Emerson DP primary elements PDS](https://www.emerson.com/documents/automation/product-data-sheet-rosemount-dp-flowmeters-primary-elements-en-87598.pdf) |

### 5.2 Magnetic flow (8700 series)

| Model | Function | Key specs | SIL | Source |
|---|---|---|---|---|
| **8705** flanged sensor (with 8732E/8732EM, 8712, 8750W transmitters) | Magmeter sensor, compatible with all 8700-series transmitters | Up to **±0.15 %** of volumetric rate over **13:1**; **±0.25 %** over **40:1** (0.25 % standard; 0.15 % high-accuracy option) | — | [PlantAutomation 8705](https://plantautomation-technology.com/products/emerson-automation-solutions/rosemount-8705-flanged-magnetic-flow-meter-sensors); [Caltrol 8705](https://caltrol.com/products/measurement-instrumentation/flow/magnetic/rosemount-8705-flanged-magnetic-flow-meter-sensors/) |
| **8732EM** transmitter | Field-mount magmeter transmitter (HART, FF, Modbus) | Same ±0.15/±0.25 % (stated for 8732E; 8732EM-specific statement not found) | exida FMEDA: **SIL 2 @ HFT=0, SIL 3 @ HFT=1** for 4–20 mA HART output (option codes A/B); certificate covers transmitter only | [8732EM FMEDA](https://d1-live.emerson.com/documents/automation/certificate-of-compliance-fmeda-report-rosemount-magnetic-flow-meter-model-8732em-en-79416.pdf) |
| NTEP custody | Rosemount magmeters have NTEP certification for some custody uses | — | — | [Emerson NTEP technical note](https://d1-live.emerson.com/documents/automation/technical-note-rosemount-magnetic-flow-meters-ntep-certification-for-custody-transfer-applications-en-8649176.pdf) |

### 5.3 Vortex (8800)

| Model | Key specs | SIL | Source |
|---|---|---|---|
| **8800D** (wafer, flanged, reducer, dual, quad, CriticalProcess) | ±0.65 % of volumetric rate (liquid), ±1.0 % (gas & steam) — figures published for Quad and CriticalProcess variants; **8800 MultiVariable (MTA/MCA option)**: ±0.70 % mass flow in water, ±2 % mass flow in saturated steam (integral temperature compensation) | 8800D FMEDA: SIL 2 @ HFT=0, SIL 3 @ HFT=1, 4–20 mA safety variable | [Emerson 8800 wafer](https://emerson.com/en-us/catalog/rosemount-8800-wafer); [8800 Quad flyer](https://d1-live.emerson.com/documents/automation/flyer-rosemounttm-8800-quad-vortex-flow-meter-en-7073954.pdf); [8800D FMEDA](https://s1-live.emerson.com/documents/automation/functional-safety-certificate-fmeda-report-rosemount-8800d-vortex-flow-meter-en-1624366.pdf) |
| **8800 Quad** | Four independent sensors/transmitters in one meter body | IEC 61508 up to **SIL 3 with 2oo3** voting | [control.com – Quad vortex](https://control.com/news/emerson-releases-brand-new-flow-meter-with-quadruple-sensors-and-transmitters/) |
| **8800 Dual** | Two sensors/transmitters; 1oo2 or 2oo2 voting to avoid spurious trips | — | [Lakeside 8800 dual](https://www.lakesidecontrols.com/products/measurement-instrumentation/flow/vortex/rosemount-8800-dual-vortex-flow-meter/) |

### 5.4 Ultrasonic

- Emerson's custody-transfer gas and liquid ultrasonic meters come from the **Daniel** lineage (e.g. Daniel/Rosemount 3410-series gas USM, 3818 liquid USM) [general knowledge — verify current model names]. The research did not return any data on a "Rosemount 3418"; do not quote one.
- Typical expectation for multipath custody gas USMs: AGA Report No. 9 / ISO 17089 compliance, flow-calibrated [general knowledge — verify].

### 5.5 Selection notes — flow (Rosemount)

- **DP vs magmeter vs vortex.** DP (orifice/Annubar) suits any fluid incl. high-T/P, with well-understood uncertainty (ISO 5167), but limited turndown (~10:1 with single DP) and needs straight run; magmeter needs conductive liquid, offers ±0.15–0.25 % over 13:1–40:1 and no pressure drop ([PlantAutomation 8705](https://plantautomation-technology.com/products/emerson-automation-solutions/rosemount-8705-flanged-magnetic-flow-meter-sensors)); vortex suits clean gas/steam/liquid with ±0.65 % liquid / ±1 % gas and no impulse lines ([8800 Quad flyer](https://d1-live.emerson.com/documents/automation/flyer-rosemounttm-8800-quad-vortex-flow-meter-en-7073954.pdf)). Hydrocarbon liquids are non-conductive, so magmeters are generally **not** applicable in hydrocarbon service [general engineering knowledge].
- **Steam.** Vortex with MultiVariable (MTA/MCA) gives integral temperature-compensated mass flow in saturated steam (±2 %); for superheated steam use 3051SMV + DP primary or external P/T compensation [general knowledge — verify].
- **Redundancy without extra tapping.** 8800 Dual/Quad give 2oo2/2oo3 in one body for SIS ([control.com](https://control.com/news/emerson-releases-brand-new-flow-meter-with-quadruple-sensors-and-transmitters/)). Common-cause failure of the shared body/shedder must be addressed in the SIL calculation [engineering opinion].
- **Annubar vs orifice.** Annubar has lower permanent pressure loss and can be hot-tapped; uncalibrated accuracy ±0.75 % (485) ([Emerson flow test data book](https://emerson.com/documents/automation/manual-rosemount-annubar-primary-flow-element-flow-test-data-book-en-74372.pdf)).

---

## 6. Emerson — Micro Motion Coriolis

### 6.1 Sensor families

| Family | Key specs | Notes | Source |
|---|---|---|---|
| **ELITE (CMF, CMFS, CMFHC)** | Liquid mass/volume: **±0.05 %** of rate (premium option) / **±0.10 %** (standard); gas mass: **±0.25 %** of rate (standard models; current data sheet). Stated accuracy includes repeatability, linearity, hysteresis, orientation. CMFHC (high capacity, up to 10–12 in): older (2012) data sheet lists gas ±0.35 % and zero stability 2.5 / 5.0 / 7.5 lb/min (68/136/204 kg/h) for CMFHC2/3/4. Low-flow rule: when flow < zero stability / 0.0035 (gas), accuracy = ±(zero stability / flow × 100) % | All CMF-designated meters are ELITE family. Super-duplex high-pressure CMFHC variants exist | [Micro Motion ELITE PDS](https://s1-live.emerson.com/documents/automation/product-data-sheet-micro-motion-elite-coriolis-flow-density-meters-en-66748.pdf); [Instrumart ELITE datasheet](https://core.instrumart.com/assets/ELITE-datasheet.pdf); [Caltrol CMFHC3Y](https://www.caltrol.com/products/measurement-instrumentation/hygienic-measurement/life-sciences/life-sciences-flow/micro-motion-elite-cmfhc3y-coriolis-meter-8-10-inch-dn200-dn250-super-duplex-steel-high-pressur/) |
| **F-Series** | Compact, drainable. Older (2019) data: ±0.10 % liquid, ±0.50 % gas; 2021 overview: gas ±0.35 %; newer data sheet: liquid ±0.05 % | Mid-tier general-purpose | [Micro Motion technical overview](https://emerson.com/documents/automation/product-data-sheet-micro-motion-technical-overview-specification-summary-en-66168.pdf); [Instrumart F-Series datasheet](https://core.instrumart.com/assets/MicroMotion-F-Series-datasheet.pdf) |
| **H-Series** | Hygienic, compact, drainable. Jan 2023 PDS: liquid mass up to ±0.05 %, density ±0.5 kg/m³; gas ±0.35 % (H050–H400), ±0.5 % (H025). 2010 PDS: liquid ±0.10 %, gas ±0.50 % | Food/pharma, also chemical injection | [Micro Motion H-Series PDS](https://emerson.com/documents/automation/product-data-sheet-micro-motion-h-series-hygienic-coriolis-flow-density-meters-en-65044.pdf); [bioprocessonline H-Series 2010](https://www.bioprocessonline.com/doc/h-series-coriolis-flow-and-density-meters-0001) |
| R-, T-, LF-Series, CNG050 | Other families (basic, straight-tube, low flow, CNG dispensing) | Listed as 5700-compatible (R, T) | [Micro Motion 5700 catalog](https://d1-auth.emerson.com/en-us/catalog/micro-motion-sku-5700) |

### 6.2 Transmitters

| Model | Key features | SIL | Source |
|---|---|---|---|
| **5700** | Field-mount, integral or remote (4-wire or 9-wire) to ELITE/F/H/R/T sensors; configurable I/O; **Smart Meter Verification (SMV) Professional**: coating detection, installation verification, optimal flow range, two-phase detection | IEC 61508: SC 3; Type B; **SIL 2 @ HFT=0, SIL 3 @ HFT=1**. SMV is the only add-on compatible with SIL licence | [5700 safety manual](https://d1-live.emerson.com/documents/automation/safety-manual-coriolis-flow-meter-micro-motion-5700-transmitters-en-66796.pdf); [Instrumart 5700 datasheet](https://core.instrumart.com/assets/micro-motion-5700-datasheet.pdf) |
| **4200** | **2-wire loop-powered** Coriolis transmitter; up to two I/O channels; SMV available | SIL 2 capable single, SIL 3 multiple (marketing — safety manual not reviewed) | [Emerson 4200 learn-about](https://s1-auth.emerson.com/en-gb/automation/measurement-instrumentation/flow-measurement/4200-learn-about); [SMV flyer](https://emerson.com/documents/automation/flyer-smart-meter-verification-capabilities-en-7234888.pdf) |
| 1700 / 2700 | Legacy/current field transmitters | — | [Emerson 1700/2700 catalog](https://www.emerson.com/en-us/catalog/micro-motion-1700-2700-transmitter) |

### 6.3 Selection notes — Coriolis vs alternatives

- **Choose Coriolis when** direct mass flow and density are needed, fluid properties vary, accuracy requirement ≤0.1 % liquid (custody, blending, chemical injection, LPG/NGL, condensate), no straight-run is available [general engineering opinion]; ELITE premium ±0.05 % liquid ([ELITE PDS](https://s1-live.emerson.com/documents/automation/product-data-sheet-micro-motion-elite-coriolis-flow-density-meters-en-66748.pdf)).
- **Choose magmeter instead** for large conductive water/slurry lines where Coriolis is expensive/heavy and ±0.25 % is enough ([8705 specs](https://plantautomation-technology.com/products/emerson-automation-solutions/rosemount-8705-flanged-magnetic-flow-meter-sensors)).
- **Gas service.** Coriolis gas accuracy (±0.25–0.35 %) is limited at low flow by zero stability — check the low-flow formula and pressure drop at max flow ([ELITE PDS](https://s1-live.emerson.com/documents/automation/product-data-sheet-micro-motion-elite-coriolis-flow-density-meters-en-66748.pdf)). For large-bore gas custody, multipath ultrasonic is usually preferred [general engineering opinion].
- **2-wire vs 4-wire.** 4200 fits 2-wire loops and SIS where field power is not available; 5700 for more I/O and SMV Professional ([5700 safety manual](https://d1-live.emerson.com/documents/automation/safety-manual-coriolis-flow-meter-micro-motion-5700-transmitters-en-66796.pdf)).
- **Revision caution.** H- and F-Series accuracy changed between 2010/2019 and 2021–2023 data sheets; quote revision.

---

## 7. Emerson — Rosemount analytical

| Model | Function | Key facts | Source |
|---|---|---|---|
| **700XA** process/natural-gas GC | Gas chromatograph (formerly Daniel) | Natural-gas custody transfer; C9+ analysis with hydrocarbon dew point and cricondentherm calculation; C6+ with H₂S; up to six 6-port or 10-port valves (max four 10-port). Analysis time, repeatability: **not found** — see PDS MS-00813 (Rev AA, Oct 2022) | [Applied Control 700XA](https://www.appliedcontrol.com/products/measurement-instrumentation/gas-analysis/process-gas-chromatographs/rosemount-700xa-process-gas-chromatograph/); [Emerson 700XA PDS](https://s1-auth.emerson.com/documents/automation/product-data-sheet-700xa-process-gas-chromatograph-en-70652.pdf); [Emerson 700XA brochure](https://s1-live.emerson.com/documents/automation/brochure-rosemount-700xa-gas-chromatograph-en-70650.pdf) |
| **370XA / 770XA** | Natural-gas GCs | 370XA designed for C6+ BTU/CV analysis; some web pages labelled 770XA contain 700XA text — check model | [DirectIndustry – GC solutions for natural gas](https://pdf.directindustry.com/pdf/emerson-automation-solutions-rosemount/gas-chromatograph-solutions-natural-gas-transmission-applications/36718-601456.html); [Caltrol 770XA](https://www.caltrol.com/products/measurement-instrumentation/gas-analysis/natural-gas-chromatographs/rosemount-770xa-natural-gas-chromatograph) |
| **OCX8800** | In-situ zirconia O₂ + combustibles transmitter | O₂ range 0–1 % to 0–40 %; uses same ZrO₂ cell as Oxymitter; field-repairable | [Instrumart OCX8800 datasheet](https://core.instrumart.com/assets/OCX8800-Datasheet.pdf); [Caltrol OCX8800](https://caltrol.com/products/measurement-instrumentation/gas-analysis/combustion-analyzers/rosemount-ocx8800-oxygen-and-combustibles-transmitter) |
| **Oxymitter** (e.g. 6888) | In-situ zirconia O₂ probe for fired heaters/boilers | [general knowledge — verify model/specs] | — |
| **1066** | 2-wire liquid analytical transmitter: pH/ORP, conductivity, chlorine, DO, ozone; SMART pH sensor calibration-data upload; manual 00809-0100-3166 Rev AF (Mar 2024) | [Emerson 1066 manual](https://www.emerson.com/documents/automation/manual-rosemount-1066-smart-enabled-2-wire-transmitter-en-71432.pdf); [Emerson 1066 news](https://www.emerson.com/en-ca/news/automation/1202-rosemountanalytical1066) |
| **1056** | 4-wire, single or dual sensor input, any combination of measurements | [processonline 1066/1056](https://www.processonline.com.au/content/instrumentation/product/rosemount-analytical-1-66-ph-orp-transmitters-262108826) |

Selection notes: GC selection is application-engineered (columns, valves, cycle time); the chatbot should request the stream composition and required components rather than recommending a model from a datasheet. In-situ zirconia (OCX8800/Oxymitter) is standard for combustion control; extractive or TDLAS is used where in-situ access or interference is a problem [general engineering opinion].

---

## 8. Emerson — Flame and gas detection

| Model | Function | Key specs | SIL | Source |
|---|---|---|---|---|
| **975MR** | Multi-spectrum IR flame detector (4 IR sensors) for hydrocarbon fires | Max range 90 m (300 ft) | Current page: IEC 61508 **SIL 3 (TÜV)**; 2016 launch release: **SIL 2** — conflict, check certificate | [Emerson 975MR](https://s1-auth.emerson.com/en-us/catalog/rosemount-sku-975mr-multi-spectrum-infrared-flame-detector); [Hydrocarbon Engineering 2016](https://www.hydrocarbonengineering.com/product-news/19072016/Emerson-develops-new-flame-detectors-3731/amp/) |
| 975 family (UV/IR, ultra-fast UV/IR, **975HR** hydrogen) | Other flame technologies | — | — | [Emerson flame & gas brochure](https://s1-live.emerson.com/documents/automation/brochure-rosemount-flame-gas-safety-solutions-en-5560820.pdf) |
| **935** | IR open-path combustible gas detector | Up to **200 m (660 ft)** | Not confirmed | [Emerson flame & gas catalog](https://www.emerson.com/en-us/catalog/flame-gas-detection) |
| **928** | Wireless toxic gas monitor (WirelessHART) | Battery powered, no field wiring | Not SIL-rated per sources found | [Emerson flame & gas catalog](https://www.emerson.com/en-us/catalog/flame-gas-detection) |
| Point IR / catalytic / toxic gas detectors and transmitters | — | Model names not confirmed in research [general knowledge — verify] | — | — |

Selection note: Emerson's F&G line came largely from acquisitions (General Monitors / Net Safety lineage) [general knowledge — verify]. Honeywell's F&G portfolio (§21) is broader in installed base on large LNG projects [engineering opinion — verify per client AVL].

---

## 9. Emerson — Wireless (WirelessHART)

| Item | Key facts | Source |
|---|---|---|
| **1410S** gateway + **781S** smart antenna | Up to **200 WirelessHART** devices, or 200 WirelessHART + **99 ISA100** devices (flyer; retailer says 100) — i.e. 1410S can also host ISA100 devices | [Emerson 1410S flyer](https://s1-live.emerson.com/documents/automation/flyer-emerson-1410s-wireless-gateway-en-7118422.pdf); [Emerson 1410S PDS](https://s1-live.emerson.com/documents/automation/product-data-sheet-emerson-wireless-1410s-gateway-781s-smart-antenna-en-6593360.pdf) |
| **702** | Wireless discrete transmitter (dry contacts, leak detection) | Battery 7–15 years (SmartPower), storage <30 °C for max life | [Rosemount wireless catalog (acomee)](https://www.acomee.com.mx/catalogos/catalogosr/ROSEMOUNT%20WIRELESS.pdf); [702 datasheet](https://core.instrumart.com/assets/702-Datasheet.pdf) |
| **648** | Wireless temperature (also X-well) | Battery life not confirmed | [Emerson wireless temperature](https://www.emerson.com/en-us/catalog/wireless-temperature?fetchFacets=true) |
| 3051S/2051 wireless, 3308, 928, 248 wireless, 708 acoustic, 775 THUM adapter | Wireless versions of wired families; THUM retrofits WirelessHART to wired HART device | [general knowledge — verify] | — |

Selection notes: WirelessHART (IEC 62591) suits monitoring, non-critical control with slow loops, and remote pads. It is not normally used for SIS final elements or fast control [general engineering opinion]. Practical design rule commonly quoted: at least 5 devices in range of the gateway and each device with ≥3 neighbours [general knowledge — verify against Emerson IEC 62591 best-practice guide].

---

## 10. Emerson — Fisher control valves, trims, actuators, positioners

### 10.1 Sliding-stem (globe) valves

| Model | Sizes / ratings | Shutoff | Typical use | Source |
|---|---|---|---|---|
| **GX** | NPS ½–4 (DN15–100) in older material; NPS ½–6 (DN15–150) in 2010 brochure and current distributor list; **CL150, CL300; PN10–40**. CL600 not found | Class IV, V, VI (VI per Yodify) | Compact general-service globe; EN/ASME; integrated GX actuator | [Fisher GX bulletin supplement](https://s1-live.emerson.com/documents/automation/product-bulletin-fisher-gx-bulletin-supplement-en-135200.pdf); [bioprocessonline GX brochure](https://www.bioprocessonline.com/doc/fisher-gx-control-valve-0002); [Spartan GX](https://spartancontrols.com/products/valves-actuation/control-valves/three-way-valves/fisher-gx-control-valve-and-actuator-system/) |
| **easy-e ET** | NPS 1–8 (DN25–200); CL150/300/600; PN10–100 | Class IV std; Class V optional (metal seats) | Balanced, cage-guided, tight shutoff | [Fisher sliding-stem selection guide](https://d1-live.emerson.com/documents/automation/product-bulletin-fisher-sliding-stem-valve-selection-guide-en-126266.pdf) |
| **easy-e ED** | Large ED/EWD bulletins cover NPS 12–30 | ED/EWD: Class IV std, Class V optional; ET/EWT: Class V standard (large-valve bulletin) | Balanced general service; high capacity | [Fisher large ED/ET bulletin](https://d1-live.emerson.com/documents/automation/product-bulletin-fisher-large-ed-ewd-et-ewt-valves-nps-12-through-30-en-122576.pdf) |
| **easy-e EZ** | Selection guide row (garbled) shows NPS 1–20 range and CL125–600 — unconfirmed | Class IV std; V/VI optional | Unbalanced, general service | [Fisher sliding-stem selection guide](https://d1-live.emerson.com/documents/automation/product-bulletin-fisher-sliding-stem-valve-selection-guide-en-126266.pdf) |
| **EH, HP, EHD/EHT** | High-pressure (CL900–2500) globe [general knowledge — verify] | — | HP gas, compressor recycle (with WhisperFlo), letdown | — |

### 10.2 Rotary valves

| Model | Key facts | Source |
|---|---|---|
| **Vee-Ball V150 / V300** | Segmented V-notch ball, modified equal-% characteristic; slurries, liquids, gas, steam. Sizes differ by bulletin edition (2013: V150 NPS 1–24×20, V300 NPS 1–20; 2022: DN25–300) | [Fisher rotary selection guide](https://d1-auth.emerson.com/documents/automation/product-bulletin-fisher-rotary-valve-selection-guide-en-135280.pdf); [Fisher V150 data sheet](https://www.heatingandprocess.com/wp-content/uploads/2016/07/Fisher-Vee-Ball-V150-Segmented-Ball-Valve-Rotary-Valves-Data-Sheet.pdf) |
| **Control-Disk** | Butterfly with contoured disk for extended throttling range; rangeability value not found | [Fisher rotary selection guide](https://d1-auth.emerson.com/documents/automation/product-bulletin-fisher-rotary-valve-selection-guide-en-135280.pdf) |
| **8580** | High-performance butterfly: rangeability **100:1**; Class VI shutoff option; −129 to 454 °C | [Fisher rotary selection guide](https://d1-auth.emerson.com/documents/automation/product-bulletin-fisher-rotary-valve-selection-guide-en-135280.pdf) |
| **A31D** | **Correction:** A31D is a POSI-SEAL (pipeline/high-performance) valve in the A11/A31A/A31C/A31D/A81 group per selection guide, for on/off service −196 to 816 °C; often described as triple-offset — confirm valve type in current bulletin | [Fisher rotary selection guide](https://d1-auth.emerson.com/documents/automation/product-bulletin-fisher-rotary-valve-selection-guide-en-135280.pdf) |
| V250/V260/V500/8510/8532 | Other rotary (full-bore ball, eccentric plug, butterfly) | [manualmachine Fisher rotary data](https://manualmachine.com/emerson/fisher8510/1949424-data-sheet) |

### 10.3 Severe-service trims

| Trim | Purpose | Facts | Source |
|---|---|---|---|
| **Cavitrol III** | Anti-cavitation (liquid), 1-stage and 3-stage versions | Stage ΔP limits not found | [Emerson Exchange 2025 presentation](https://emersonexchange365.com/conferences/01---emerson-exchange-2025---san-antonio/m/presentation-library/7164/download) |
| **NotchFlo DST** | Multi-stage anti-cavitation for dirty service (erosive solids) | Stages: CL600 3-stage, CL900/1500 4-stage, CL1500/2500 6-stage (Oct 2023 bulletin); liquid ΔP up to 6000+ psid (presentation) | [Fisher NotchFlo DST bulletin](https://d1-live.emerson.com/documents/automation/product-bulletin-fisher-notchflo-dst-control-valve-en-123650.pdf) |
| **Whisper Trim III** | Aerodynamic noise attenuation | Up to 30 dBA vs standard trim | [Emerson Whisper Trim III](https://www.emerson.com/en-us/catalog/fisher-whisper-trim-iii) |
| **WhisperFlo** | High-ΔP gas/vapour noise attenuation | Up to 40 dBA (50 dBA special); another Emerson doc: 30–40 dBA | [Caltrol WhisperFlo](https://caltrol.com/products/valves-actuators-regulators/control-valves/engineered-products/fisher-whisperflo-aerodynamic-noise-attenuation-trim/); [Emerson WhisperFlo](https://www.emerson.com/en-us/catalog/fisher-whisperflo) |

### 10.4 Actuators

| Model | Type | Facts | Source |
|---|---|---|---|
| **667** | Spring-and-diaphragm sliding-stem actuator (spring extends stem on air failure; 657 is the counterpart with opposite action) | Sizes/thrust and fail action per valve body: [general knowledge — verify] | — |
| **585C** | Spring-return or double-acting piston actuator for high thrust | [general knowledge — verify] | — |
| GX actuator | Integrated multi-spring diaphragm actuator for GX | [Spartan GX](https://spartancontrols.com/products/valves-actuation/control-valves/three-way-valves/fisher-gx-control-valve-and-actuator-system/) | — |
| 2052 / 1061 | Rotary diaphragm / rotary piston actuators [general knowledge — verify] | — | — |

### 10.5 FIELDVUE digital valve controllers

| Model | Facts | Source |
|---|---|---|
| **DVC6200** | Linkage-less, non-contact magnetic position feedback; HART (incl. HART 7), FF (DVC6200f), Profibus (DVC6200p); **DVC6200 SIS** for ESD valves with partial-stroke test (PST); SIL 3 capable | [general knowledge — verify all; search budget exhausted before confirmation] |
| **DVC7K** | Launched **10 Oct 2023**; embedded edge computing and prognostics ("Advice at the Device"), Bluetooth built in; each alert includes recommended actions; specifiable for new valves and retrofit; separate lower-cost version for critical on/off valves (diagnostics + PST) | [Emerson news – DVC7K](https://www.emerson.com/en/corporate/news/2023/10-fisher-fieldvue-dvc7k-digital-valve-controller); [Valve Magazine](https://valvemagazine.com/products/new-valve-controller-from-emerson-offers-embedded-edge-computing/) |
| DVC2000, DVC6000 (legacy, linkage-based) | [general knowledge — verify] | — |
| FIELDVUE diagnostics | ValveLink software (signature, step response, PST) integrated in AMS Device Manager [general knowledge — verify] | — |

### 10.6 Selection notes — control valves

- **Globe vs rotary.** Globe (ET/ED/GX) for best throttling and severe-service trim availability; Vee-Ball for slurry/fibrous or high-capacity, and 8580 high-performance butterfly where 100:1 rangeability and large size are needed ([Fisher rotary selection guide](https://d1-auth.emerson.com/documents/automation/product-bulletin-fisher-rotary-valve-selection-guide-en-135280.pdf)).
- **Cavitation.** Clean liquid with cavitation → Cavitrol III; dirty/erosive → NotchFlo DST ([NotchFlo DST bulletin](https://d1-live.emerson.com/documents/automation/product-bulletin-fisher-notchflo-dst-control-valve-en-123650.pdf)).
- **Noise.** Gas with predicted noise > project limit (often 85 dBA at 1 m) → Whisper Trim III (~30 dBA) or WhisperFlo (~40 dBA) ([Emerson Whisper Trim III](https://www.emerson.com/en-us/catalog/fisher-whisper-trim-iii); [Caltrol WhisperFlo](https://caltrol.com/products/valves-actuators-regulators/control-valves/engineered-products/fisher-whisperflo-aerodynamic-noise-attenuation-trim/)).
- **GX limits.** GX is a compact general-service valve; CL600 rating was not found — for CL600+ use easy-e ET/ED or HP series ([Fisher GX supplement](https://s1-live.emerson.com/documents/automation/product-bulletin-fisher-gx-bulletin-supplement-en-135200.pdf)).
- **Shutoff class** refers to ANSI/FCI 70-2. Class V/VI requires seat/actuator thrust sizing — confirm in Fisher sizing (Fisher Specification Manager) [general knowledge — verify].

---

## 11. Emerson — Bettis / EIM actuators

> Search budget ran out before this section could be researched. All entries are **[general knowledge — verify]**.

| Model | Type | Typical facts to verify | Typical use |
|---|---|---|---|
| **Bettis G-series** | Pneumatic / hydraulic scotch-yoke, spring-return or double-acting | Very high torque range (to several hundred thousand N·m); symmetric or canted yoke | ESD/XV on large ball valves, pipeline |
| **Bettis CBA / RPC / T-series** | Scotch-yoke / rack-and-pinion | — | On/off quarter-turn |
| **Bettis XTE3000** | Intelligent electric actuator (non-intrusive set-up) | SIL rating, protocols (HART, FF, Modbus, Profibus) — verify | MOVs |
| **Bettis TEC2000 (EIM)** | Electric multi-turn/quarter-turn actuator | — | MOVs, tank farm |

Selection note: for ESD valves, check the actuator's SIL certificate, the solenoid/quick-exhaust/ PST arrangement and stroke-time test, and design torque with safety factor per client specification [general engineering practice].

---

## 12. Emerson — Crosby / Anderson Greenwood pressure relief

> Not researched (search budget). All entries **[general knowledge — verify]**.

| Model | Type | Notes |
|---|---|---|
| **Crosby JOS-E / JBS-E** (J-series) | Conventional (JOS-E) and balanced-bellows (JBS-E) spring-loaded PRV, API 526 dimensions, orifices D–T | Process gas/liquid; ASME VIII UV stamp |
| **Anderson Greenwood Series 200 / 400 / 800** | Pilot-operated relief valves (POPRV); 200 piston, 400/800 various pilot types (modulating/pop) | High set pressure close to operating pressure, back-pressure tolerant; not for dirty/polymerising service without filter/purge |
| **Anderson Greenwood 9000 / 90 series**, Varec 2000 tank vents | Low-pressure tank protection [verify] | Storage tanks per API 2000 |

Selection note: conventional spring PRVs tolerate ~10 % built-up back-pressure; balanced bellows allow higher superimposed back-pressure; pilot-operated allow operation closer to set pressure (~95 %+) [general engineering knowledge per API 520 — verify].

---

## 13. Emerson — DeltaV, DeltaV SIS, Ovation, AMS, Plantweb

> Not researched (search budget). Entries **[general knowledge — verify]**.

| Product | Key facts to verify |
|---|---|
| **DeltaV DCS** | M-series (legacy) and **S-series** controllers/I/O; **PK controller** (standalone/skid capable); **CHARMs** (single-channel characterisation modules) on **CIOC** (CHARM I/O Card, up to 96 CHARMs per CIOC) — **Electronic Marshalling**: any channel type to any terminal, late binding of I/O, reduces marshalling cabinets; Wireless I/O Card (WIOC); DeltaV Live HMI; current major versions DeltaV v14/v15 LTS |
| **DeltaV SIS** | **SLS 1508** logic solver (one SIS module per logic solver, redundant pairs), **CHARM SLS / SZ controller** with Electronic Marshalling for SIS; **TÜV certified to IEC 61508 SIL 3**; integrated-but-separate with DeltaV DCS |
| **Ovation** | Emerson DCS for power generation and water/wastewater (from Westinghouse lineage) |
| **AMS Device Manager** | HART/FF/Profibus/WirelessHART device configuration, diagnostics, calibration records; integrates ValveLink for FIELDVUE |
| **Plantweb** | Emerson digital ecosystem: Plantweb Insight apps, Plantweb Optics; "Plantweb" originally FOUNDATION fieldbus architecture brand |
| **Emerson Electronic Marshalling vs Honeywell Universal I/O** | Both remove fixed I/O-type assignment; DeltaV does it per channel via CHARM, Honeywell via software-configured universal channel (see §19) |

---

## 14. Emerson — cross-cutting field-device features

- **HART revision.** Rosemount 644 head/field mount is selectable HART Rev 5 or 7 ([Emerson 644 PDS](https://d1-live.emerson.com/documents/automation/product-data-sheet-rosemount-644-temperature-transmitter-en-73332.pdf)). Most current Rosemount transmitters ship HART 7 with HART 5 selectable [general knowledge — verify per model].
- **NAMUR NE 43** saturation/alarm levels (≤3.6 mA / ≥21 mA) are configurable on Rosemount 4–20 mA transmitters [general knowledge — verify]; **NE 107** status categories (Failure, Function check, Out of specification, Maintenance required) supported via HART 7 device status and in AMS Device Manager [general knowledge — verify].
- **SIL ordering.** Option code **QT** = safety certified to IEC 61508 with certificate of FMEDA data (shown for 644, [Emerson 644 PDS](https://d1-live.emerson.com/documents/automation/product-data-sheet-rosemount-644-temperature-transmitter-en-73332.pdf)); assume the same pattern for 3051/3051S/2051 but verify.
- **Recurring SIL pattern** in Emerson certificates found: SIL 2 @ HFT=0, SIL 3 @ HFT=1, SC 3 — 644 ([exida](https://emerson.com/documents/automation/safety-certificate-rosemount-644-software-rev-1-1-x-en-5260914.pdf)), 2140:SIS ([safety manual](https://emerson.com/documents/automation/safety-manual-rosemount-2140-sis-level-detector-vibrating-fork-en-us-187108.pdf)), 8732EM ([FMEDA](https://d1-live.emerson.com/documents/automation/certificate-of-compliance-fmeda-report-rosemount-magnetic-flow-meter-model-8732em-en-79416.pdf)), 8800D ([FMEDA](https://s1-live.emerson.com/documents/automation/functional-safety-certificate-fmeda-report-rosemount-8800d-vortex-flow-meter-en-1624366.pdf)), 5700 ([safety manual](https://d1-live.emerson.com/documents/automation/safety-manual-coriolis-flow-meter-micro-motion-5700-transmitters-en-66796.pdf)), 5408 ([certificate](https://www.emerson.com/documents/automation/certificate-rosemount-5408-5408-sis-level-transmitters-en-202464.pdf)).
- **Hazardous-area approvals.** Rosemount transmitters are generally available with ATEX, IECEx, FM, CSA, plus regional (EAC, INMETRO, KCs, CCC, NEPSI) approvals as order options, Ex d and Ex ia; ambient −40 to 85 °C typical for electronics, LCD limited at low temperature [general knowledge — verify per PDS].
- **Materials.** Standard wetted 316L SST; options Alloy C-276, Alloy 400, tantalum, gold-plated diaphragms for hydrogen permeation; NACE MR0175/ISO 15156 compliance options [general knowledge — verify per PDS].

---

## 15. Honeywell — corporate context

> **The Honeywell section was not web-researched** (search budget exhausted; process.honeywell.com unreachable for fetch). Everything below is **[general knowledge — verify]** unless a link is shown. Use it to orient the engineer, not as a spec basis.

- Honeywell's process business is **Honeywell Process Solutions (HPS)**, within the **Industrial Automation** segment. Honeywell announced a plan to separate into three public companies (Automation, Aerospace, Advanced Materials), targeted for completion in the second half of 2026; check the current corporate status. [general knowledge — verify]
- **UOP** (process licensing, catalysts, adsorbents) is a Honeywell business; UOP-licensed units often come with Honeywell control/APC preferences in the licensor package. [general knowledge — verify]
- **Elster** (gas metering, Enraf tank gauging via Honeywell Enraf, Q.Sonic ultrasonic meters) joined Honeywell via the 2016 Elster acquisition; **Enraf** has been Honeywell since ~2010. [general knowledge — verify]
- Many Honeywell flow meters have historically been OEM products (Krohne for VersaFlow; Azbil/Yamatake heritage for MagneW). [general knowledge — verify]

---

## 16. Honeywell — SmartLine field instruments

All **[general knowledge — verify]**. SmartLine is Honeywell's transmitter platform with common display, modular electronics, HART/FF (and DE for legacy TDC/TPS), and Experion integration ("SmartLine + Experion" device health/maintenance-mode features).

| Model | Measures | Indicative specs to verify | SIL / approvals to verify | Typical use |
|---|---|---|---|---|
| **ST700** | P, DP, GP, AP | Value tier; reference accuracy ~±0.065 % (standard) / ~±0.05 % option; turndown ~100:1 | IEC 61508 SIL 2/3 option; ATEX/IECEx/FM/CSA | General service |
| **ST800** | P, DP, GP, AP, remote seal | Premium tier; ~±0.0375 % accuracy (premium config), turndown up to ~400:1 claimed; 10-year stability | SIL 2/3 (IEC 61508) | Critical control, SIS, flow |
| **ST850** | P, DP | Newest top tier (higher accuracy/stability) — confirm launch date and specs | SIL 2/3 | Critical/premium |
| **STT700 / STT850** | Temperature transmitters (head/field) | Dual input on 850; HART 7 / FF | SIL 2/3 (STT850) | Temperature |
| **SLG700** (SLG720/SLG726) | Guided wave radar level/interface | ~±3 mm or ±0.03 % of measured distance; max probe length — verify | SIL 2/3 | Separators, storage |
| **SmartLine remote seals** | Diaphragm seals for ST700/800 | — | — | DP level |
| Legacy **ST3000 / STT3000** | Predecessors to SmartLine | Discontinued/replaced by ST700/800 | — | Brownfield |

Selection notes (opinion — verify): SmartLine's main differentiators are Experion integration (device status and "maintenance mode" indication in the DCS), modular field-replaceable electronics/display, and the DE protocol for TPS/TDC brownfield. Emerson 3051S Ultra and Honeywell ST800 are the usual head-to-head pair in bid evaluations; compare **total probable error** at project conditions, not headline accuracy.

---

## 17. Honeywell — Flow

All **[general knowledge — verify]**.

| Product | Notes to verify |
|---|---|
| **VersaFlow** (Mag, Vortex, Coriolis, Ultrasonic) | Sold by Honeywell under a Krohne OEM partnership (VersaFlow Mag ≈ Krohne OPTIFLUX; VersaFlow Coriolis ≈ Krohne OPTIMASS). **Verify whether still offered** — reported as reduced/discontinued in some regions; spare-part support goes through Krohne designs. |
| **MagneW** (MagneW 3000 PLUS+) | Electromagnetic flowmeter of Yamatake/Azbil origin, historically sold by Honeywell in Asia; check availability. |
| **Elster Q.Sonic** (Q.Sonic plus / max) | Multipath gas ultrasonic custody meters (AGA 9 / OIML R137) from Elster-Instromet; also Elster turbine (TRZ) and rotary meters. |
| **SmartLine flow** | ST800 DP + primary elements, multivariable SMV800 (DP + SP + T, compensated flow) |

Selection note: unlike Emerson (Micro Motion, Rosemount 8700/8800 built in-house), Honeywell's non-DP flow portfolio has historically relied on partners; on EPC AVLs the flow package is often bought from Emerson, Endress+Hauser, Krohne or Yokogawa even on a Honeywell-DCS project [engineering opinion — verify].

---

## 18. Honeywell — Enraf tank gauging

All **[general knowledge — verify]**.

| Model | Type | Notes to verify |
|---|---|---|
| **990 SmartRadar FlexLine** | Radar tank gauge (planar/horn/stilling-well antennas) | Custody accuracy ±0.5 mm class (OIML R85, API MPMS 3.1B); SIL 2/3 options |
| **973 SmartRadar LTi** | Radar for LNG/LPG with in-tank verification | LNG storage; cryogenic |
| **854 ATG / 854 XTG servo gauge** | Servo (displacer) level gauge: level, interface, density profiling | Custody, refinery tanks, LNG (density profiles for rollover) |
| **Entis Pro** (Entis+, Entis XL) | Tank inventory management software | Volume/mass calcs per API MPMS 11.1/12 |
| **CIU 888 / CIU Prime** | Communication interface unit (concentrator) | Field bus to host |
| **VITO** temperature/water-bottom probes; **877 FDI** field display | Multi-spot temperature | Average product temperature |
| **Tank-side monitor** | FlexConn modules | — |

Selection notes (opinion — verify): Enraf and Rosemount TankRadar (5900S) dominate refinery/terminal custody tank gauging; Enraf servo gauges (854) remain the reference for LNG tanks needing density profiling for rollover detection, while radar is preferred for maintenance-free bulk storage.

---

## 19. Honeywell — Experion PKS, Experion LX, ControlEdge

All **[general knowledge — verify]**.

| Product | Key facts to verify |
|---|---|
| **Experion PKS** | Flagship DCS. Releases R4xx/R5xx (R520/R530 current at time of writing — verify). Fault-Tolerant Ethernet (FTE) control network. Supports HART, FF (FIM), Profibus, ISA100/OneWireless, DE (legacy). |
| **C300** controller | Series C form factor (vertical, cooling-optimised IOTA); redundant; Control Execution Environment (CEE). **C300 PCNT05** = newer-generation C300 hardware (replacing PCNT02) — verify release and differences. |
| **Series C I/O** | AI/AO/DI/DO, HART-enabled modules; redundant; IOTAs with integrated marshalling |
| **Universal I/O (UIO / UIO-2)** | Software-configurable channels (AI/AO/DI/DO per channel) — Honeywell's answer to late I/O binding; **Universal Marshalling** cabinets; **Universal Safety I/O** for Safety Manager SC |
| **Experion PKS HIVE** | Highly Integrated Virtual Environment: IT/IO/Control HIVE — decouples controllers from I/O so any controller can use any I/O; virtualization of servers |
| **LEAP** | Lean Execution of Automation Projects: Universal I/O + virtualization + cloud engineering to decouple hardware from design |
| **Experion LX** | Mid-market DCS (scaled-down Experion with C300-type controller), common in chemical/smaller plants |
| **ControlEdge PLC** (ControlEdge 900 / HC900 heritage) and **ControlEdge RTU** (RTU2020) | PLC and RTU tightly integrated with Experion; RTU for wellheads/pipelines (IEC 61131-3, DNP3, Modbus) |
| **LCN / TPS / TDC 2000/3000** | Legacy Honeywell systems (TDC 2000 1975; TDC 3000 / LCN 1980s; TPS 1990s). Migration paths: **EHPM** (Enhanced HPM on FTE), **ELCN** (Enhanced LCN — virtualised LCN nodes on Ethernet), Experion TPS (ETPS) |

Selection notes (opinion — verify): Honeywell Experion and Emerson DeltaV are the most common DCS choices on large O&G/LNG EPCs, alongside Yokogawa CENTUM VP and ABB 800xA. For brownfield TDC/TPS sites, Honeywell's ELCN/EHPM migration path usually favours staying on Experion. Both vendors offer electronically/universally configurable I/O (DeltaV CHARMs vs Honeywell UIO) reducing marshalling and late-change cost.

---

## 20. Honeywell — Safety Manager / Safety Manager SC

All **[general knowledge — verify]**.

| Product | Facts to verify |
|---|---|
| **Safety Manager** (QMR architecture, from FSC heritage) | TÜV certified IEC 61508 **SIL 3**; Quadruple Modular Redundant (2oo4D) processing; used for ESD/F&G/BMS; IEC 61511 |
| **Safety Manager SC** | Series C form factor, integrated with Experion; **Universal Safety I/O** (configurable per channel), Universal Safety Cabinet/Universal Safety Logic Cabinet; SIL 3 |
| **FSC** | Legacy Fail Safe Controller (predecessor) |
| **Safety Historian / SafeView** | Event/SOE tools |

F&G: Safety Manager is often configured as an EN 54 / NFPA 72-compliant F&G controller [verify certifications per project].

---

## 21. Honeywell — Fire & Gas detection

All **[general knowledge — verify]**. Brands: Honeywell Analytics (Sieger/Searchline heritage), Honeywell Fire Sentry (flame).

| Model | Function | Notes to verify |
|---|---|---|
| **Searchpoint Optima Plus** | Point IR hydrocarbon gas detector (0–100 % LEL) | SIL 2 (IEC 61508); ATEX/IECEx; heated optics; widely specified on offshore/LNG |
| **Searchline Excel / Excel Plus / Excel Edge** | Open-path IR hydrocarbon detector (LEL·m), ranges up to ~200 m | SIL 2; Excel Edge is the newer generation |
| **XNX Universal Transmitter** | Transmitter for catalytic, IR (Optima/Excel) and electrochemical toxic sensors; HART, Modbus, FF options | SIL 2 |
| **Sensepoint XCD / Sensepoint XRL** | Gas detectors (flammable, toxic, O₂) with display | SIL rating — verify |
| **FS24X** (Fire Sentry) | Multi-spectrum IR (WideBand IR) flame detector | SIL rating — verify; FS20X predecessor |
| **Midas / Vertex** | Extractive toxic monitors (semiconductor) | Not typical O&G |
| **ACM150, Searchzone Sonik** | Acoustic gas-leak detection — verify product status | |

Selection note: point IR (Searchpoint Optima Plus / Emerson point IR) + open path (Searchline Excel / Rosemount 935) + flame (FS24X / Rosemount 975MR) is the standard O&G mix; mapping (FGS mapping/coverage per ISA TR84.00.07) drives quantity [general engineering practice].

---

## 22. Honeywell — OneWireless, FDM, Uniformance, valve positioner, UOP

All **[general knowledge — verify]**.

| Product | Facts to verify |
|---|---|
| **OneWireless** | Industrial wireless network based on **ISA100.11a (IEC 62734)**; Wireless Device Manager (WDM); Field Device Access Points (FDAP); multi-protocol (later releases also support WirelessHART devices — verify); ISA100 transmitters XYR 6000 (legacy) and SmartLine wireless |
| **FDM (Field Device Manager)** | Honeywell's asset-management tool (HART/FF/Profibus/ISA100), equivalent to Emerson AMS Device Manager |
| **Uniformance PHD** | Process historian; **Uniformance Insight / Asset Sentinel** analytics |
| **Honeywell Smart Valve Positioner** (SVP; HART/FF; e.g. "SmartLine SVP") | Digital valve positioner with diagnostics — confirm current model name; Honeywell does not own a major control-valve brand comparable to Fisher, so positioners mostly go on third-party valves |
| **Honeywell Forge / Experion Operations Assistant** | Enterprise analytics/AI |
| **UOP** | Process licensor; UOP "Callidus" burners/flares; UOP package units often specify instrumentation in licensor's standard specs |

---

## 23. Emerson vs Honeywell — quick comparison

| Category | Emerson | Honeywell | Comment |
|---|---|---|---|
| Pressure | Rosemount 3051S / 3051 / 2051 (sourced specs above) | SmartLine ST850 / ST800 / ST700 (verify) | Compare total probable error and stability at project conditions |
| Temperature | 3144P, 644 (SIL 2 @ HFT0) | STT850, STT700 | — |
| Level | 5408 (26 GHz FMCW), 5300 GWR, 2140 fork | SLG700 GWR | Honeywell non-contacting process radar: verify offering |
| Tank gauging | 5900S (±0.5 mm, SIL 3 2-in-1), 2410 | Enraf 990 SmartRadar, 854 servo, Entis Pro | Both widely approved for custody (OIML R85) |
| Coriolis / mag / vortex | In-house (Micro Motion, 8700, 8800) | Partner/OEM (VersaFlow/Krohne; MagneW) — verify current | Emerson broader in-house flow portfolio [opinion] |
| Control valves | Fisher (full range + severe service) | No comparable in-house valve brand | — |
| DCS | DeltaV (CHARMs electronic marshalling) | Experion PKS (UIO, HIVE, LEAP) | — |
| SIS | DeltaV SIS (SLS 1508/CHARM SLS, SIL 3) | Safety Manager / SC (QMR, SIL 3) | — |
| Wireless | WirelessHART (1410S also hosts ISA100) | ISA100 OneWireless | Protocol choice drives device choice |
| Asset mgmt | AMS Device Manager, ValveLink | FDM | — |
| F&G | Rosemount 975/935/928 | Searchpoint Optima Plus, Searchline Excel, XNX, FS24X | — |

---

## Gaps

1. **Honeywell section unverified.** Web-search budget (shared across agents) ran out before any Honeywell query, and process.honeywell.com / emerson.com could not be fetched (DNS blocked in the research environment). Every Honeywell spec (ST700/800/850 accuracy and turndown, STT, SLG700, SIL certificates, Enraf 990/854 accuracy, Safety Manager SC, Searchpoint/Searchline/XNX/FS24X SIL, OneWireless WirelessHART support, C300 PCNT05, VersaFlow status) needs sourcing. Priority: SmartLine PDSs and exida/TÜV certificates; VersaFlow availability; Enraf 990/854 custody accuracy.
2. **Emerson sections not researched:** Fisher DVC6200 (linkage-less, SIS/PST, HART 7, SIL), 667/585C actuator sizes, Bettis G-series/XTE3000/TEC2000, Crosby JOS-E/Anderson Greenwood 200/400/800, DeltaV/DeltaV SIS/CHARMs/SLS 1508, Ovation, AMS, Plantweb, 305/306/304 manifolds, Rosemount thermowells (PTC 19.3 TW), Emerson ultrasonic meters. All marked [general knowledge — verify].
3. **Missing numbers even where researched:** 2051 current turndown (2024 PDS); 3051S/3051 ambient and static-pressure effects; 3144P/644 digital accuracy tables; 5300 max process T/P and SIL certificate; 2140 response time; 700XA cycle time/repeatability; 975MR SIL (SIL 2 vs SIL 3 conflict); 8732EM-specific accuracy; 405 straight-run; Cavitrol III stage ΔP; Control-Disk rangeability; GX size range (NPS 4 vs 6) and CL600 availability; Micro Motion 4200 safety manual; 648 battery life; A31D valve type (POSI-SEAL vs high-performance butterfly — confirm).
4. **Conflicting sources flagged:** 2051 accuracy/turndown; 3051SMV mass-flow accuracy (0.04 % vs 0.65 %); H-/F-Series gas accuracy by revision; 1195 turndown (14:1 vs 8:1); 975 SIL; WhisperFlo dBA (30–50); 1410S ISA100 count (99 vs 100).
5. **Hazardous-area certificate numbers, NE 43/NE 107 configuration details, HART revision per model, NACE/material options** were not confirmed for any model.
