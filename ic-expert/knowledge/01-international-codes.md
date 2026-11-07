# 01 — International Codes & Standards for Instrumentation and Control (I&C)

> **How to use this file**
> 1. This is reference material for an I&C expert assistant on oil & gas / LNG / petrochemical EPC projects (e.g. Saudi Aramco, QatarEnergy). Client specs (SAES/SAMSS, QatarEnergy/QP standards) normally *invoke and modify* the standards below. The project spec governs where it is stricter or different.
> 2. Every number has a source link next to it. Items tagged **[general knowledge — verify]** come from engineering practice and could not be confirmed by web search in this research pass. Check them against the purchased standard before quoting them in a deliverable.
> 3. Edition years were checked against standards-store listings where possible. Standards are revised often, so always confirm the edition named in the project's "codes and standards" list. The *project-contractual* edition is the one that applies, even if a newer one exists.
> 4. Most sources are secondary (vendor white papers, standards-store abstracts, trade press), because the standards themselves are paywalled. Where sources disagreed, both values are given.
> 5. Answer pattern for the chatbot: state the requirement, then the number, then the source. Add the "pitfall" bullet when relevant, and point the user to the [Gaps](#gaps) section for anything unconfirmed.

## Table of contents

1. [ISA-5.1 — Instrumentation & control symbols and identification](#isa-51--instrumentation--control-symbols-and-identification)
2. [ISA-5.2 / 5.3 / 5.4 / 5.5 and ISA-20 datasheets](#isa-52--53--54--55-and-isa-20-datasheets)
3. [IEC 61508 — Functional safety (generic)](#iec-61508--functional-safety-generic)
4. [IEC 61511 / ISA-84 — SIS for the process industry](#iec-61511--isa-84--sis-for-the-process-industry)
5. [IEC 60079 series — Explosive atmospheres](#iec-60079-series--explosive-atmospheres)
6. [Intrinsic safety entity / FISCO checks](#intrinsic-safety-entity--fisco-checks)
7. [ATEX and IECEx certification](#atex-and-iecex-certification)
8. [NEC Articles 500/505 and API RP 500/505 (area classification)](#nec-articles-500505-and-api-rp-500505-area-classification)
9. [IEC 60529 IP codes and NEMA 250](#iec-60529-ip-codes-and-nema-250)
10. [API RP 551 — Process measurement](#api-rp-551--process-measurement)
11. [API RP 552 — Signal processing, transmission and installation](#api-rp-552--signal-processing-transmission-and-installation)
12. [API RP 553 — Refinery valves and accessories for control and SIS](#api-rp-553--refinery-valves-and-accessories-for-control-and-sis)
13. [API RP 554 — Process control systems](#api-rp-554--process-control-systems)
14. [API RP 555 — Process analyzers](#api-rp-555--process-analyzers)
15. [API RP 556 — Fired heater instrumentation](#api-rp-556--fired-heater-instrumentation)
16. [API 670 — Machinery protection systems](#api-670--machinery-protection-systems)
17. [API 2350 — Tank overfill protection](#api-2350--tank-overfill-protection)
18. [API 520 / 521 / 526 / 527 — Pressure relief](#api-520--521--526--527--pressure-relief)
19. [API 598 / 6D / 600 / 608 / 609 — Valves](#api-598--6d--600--608--609--valves)
20. [IEC 60534 / ISA-75 — Control valves (sizing, noise, leakage, face-to-face)](#iec-60534--isa-75--control-valves-sizing-noise-leakage-face-to-face)
21. [ANSI/FCI 70-2 — Control valve seat leakage](#ansifci-70-2--control-valve-seat-leakage)
22. [ASME PTC 19.3 TW-2016 — Thermowells](#asme-ptc-193-tw-2016--thermowells)
23. [ASME B16.5 / B16.47 / B16.34 / B16.10 / B31.3](#asme-b165--b1647--b1634--b1610--b313)
24. [ISO 5167 — Differential pressure flow measurement](#iso-5167--differential-pressure-flow-measurement)
25. [AGA 3 / 7 / 8 / 9 and API MPMS — Custody transfer](#aga-3--7--8--9-and-api-mpms--custody-transfer)
26. [IEC 61131-3 — PLC programming languages](#iec-61131-3--plc-programming-languages)
27. [Fieldbus and digital protocols: IEC 61158 / FOUNDATION Fieldbus, PROFIBUS, Modbus](#fieldbus-and-digital-protocols-iec-61158--foundation-fieldbus-profibus-modbus)
28. [HART and WirelessHART (IEC 62591)](#hart-and-wirelesshart-iec-62591)
29. [IEC 62443 — OT cybersecurity](#iec-62443--ot-cybersecurity)
30. [NAMUR NE 43, NE 107, NE 95 (and related)](#namur-ne-43-ne-107-ne-95-and-related)
31. [IEC 60751 (RTD) and IEC 60584 (thermocouples)](#iec-60751-rtd-and-iec-60584-thermocouples)
32. [EN 837 — Pressure gauges](#en-837--pressure-gauges)
33. [Cables: IEC 60331 / 60332 / BS EN 50288-7 and related](#cables-iec-60331--60332--bs-en-50288-7-and-related)
34. [Earthing / grounding: IEC 60364 and intrinsically safe earth](#earthing--grounding-iec-60364-and-intrinsically-safe-earth)
35. [NFPA 70 and NFPA 72](#nfpa-70-and-nfpa-72)
36. [NACE MR0175 / ISO 15156 — Sour service materials](#nace-mr0175--iso-15156--sour-service-materials)
37. [IEC 61326 — EMC for measurement and control equipment](#iec-61326--emc-for-measurement-and-control-equipment)
38. [IEC 62682 / ISA-18.2 — Alarm management](#iec-62682--isa-182--alarm-management)
39. [ISA-101 — HMI](#isa-101--hmi)
40. [IEC 61850 — Substation communication (I&C interface)](#iec-61850--substation-communication-ic-interface)
41. [Gaps](#gaps)

---

## ISA-5.1 — Instrumentation & control symbols and identification

- **Scope**
  - Defines the instrument identification (tagging) system and graphic symbols for P&IDs, loop diagrams and other I&C documents. The 2024 edition was retitled *Instrumentation and Control Symbols and Identification* to stress that control symbols are covered ([ISA press release](https://www.isa.org/news-press-releases/2024/october/widely-used-engineering-symbols-and-drawings-stand); [ISA product page](https://www.isa.org/products/ansi-isa-5-1-2024-instrumentation-and-control-symb)).
- **Edition status**
  - **ANSI/ISA-5.1-2024** is the current edition. It improves readability, adds new symbols, and moves the 2022 edition's non-mandatory annexes into separate technical reports: **ISA-TR5.1.02** (identification guidelines) and **ISA-TR5.1.03** (graphic symbol guidelines) ([ANSI blog](https://blog.ansi.org/ansi/ansi-isa-5-1-2024-instrumentation-symbols/); [control.com](https://control.com/news/update-to-the-isa-5.1-standard-for-engineering-symbols-and-drawings/)).
  - Earlier editions still often named in older client specs: ISA-5.1-2009 and ISA-5.1-2022 ([ANSI blog](https://blog.ansi.org/ansi/ansi-isa-5-1-2024-instrumentation-symbols/)).
- **Key requirements & numbers (how the tag is built)** **[general knowledge — verify]**
  - Tag = loop identifier + functional identification letters. The **first letter** is the measured or initiating variable: A analysis, F flow, L level, P pressure, T temperature, S speed, V vibration, W weight, Z position. An optional **modifier** follows it, e.g. D differential (PDT), F ratio, Q totalize (FQ).
  - **Succeeding letters** are functions: I indicate, R record, C control, T transmit, E primary element, V valve, Y relay/compute/convert (e.g. I/P converter "FY"), S switch, A alarm, with H/L/HH/LL as alarm/switch modifiers. Examples: PT (pressure transmitter), FCV (flow control valve), LAHH (level alarm high-high), TE/TW (element/thermowell).
  - Location symbols: a plain circle is field mounted. A circle with a solid line is primary location (control room panel). A circle with a dashed line is behind panel or inaccessible. A square with a circle inside is a shared display/control (DCS). A hexagon is computer function. A diamond inside a square is PLC/logic. Signal lines: dashed = electric, solid with "//" = pneumatic, solid with "o" = software/data link.
  - The 2009 edition absorbed the former ISA-5.3 DCS/shared display symbols.
- **Project pitfalls / checks**
  - Middle East clients usually have their *own* tagging standard that overlays ISA-5.1. Saudi Aramco uses plant/unit prefixes, and QatarEnergy uses project-specific tag formats. Check the project "Instrument Numbering Procedure" before tagging.
  - SIS devices: many projects use a distinct symbol or tag prefix for SIS initiators and final elements (e.g. "Z" second letter, or separate loop number ranges). Make sure P&ID, instrument index and SRS all use the same tags.
  - Confirm which ISA-5.1 edition the P&ID legend sheets follow. Mixing 2009 and 2024 symbol conventions across sheets is a common audit finding.
- **Sources**: [ISA press release 2024](https://www.isa.org/news-press-releases/2024/october/widely-used-engineering-symbols-and-drawings-stand) · [ANSI blog](https://blog.ansi.org/ansi/ansi-isa-5-1-2024-instrumentation-symbols/) · [control.com](https://control.com/news/update-to-the-isa-5.1-standard-for-engineering-symbols-and-drawings/) · [ISA store](https://www.isa.org/products/ansi-isa-5-1-2024-instrumentation-and-control-symb)

## ISA-5.2 / 5.3 / 5.4 / 5.5 and ISA-20 datasheets

- **Scope** **[general knowledge — verify]** (no edition was confirmed by search for these)
  - **ISA-5.2** — Binary logic diagrams for process operations (AND/OR/NOT, timing elements). Used for cause & effect and interlock logic diagrams.
  - **ISA-5.3** — Graphic symbols for distributed control/shared display instrumentation. Withdrawn as its content was folded into ISA-5.1 (2009).
  - **ISA-5.4** — Instrument loop diagrams. Defines minimum content: tags, terminal/junction box numbers, cable/pair numbers, I/O addresses, power sources, and the instrument and calibration range.
  - **ISA-5.5** — Graphic symbols for process displays (1985). In practice it has largely been overtaken by ISA-101 HMI philosophy.
  - **ISA-20** — Specification forms (datasheets) for process measurement and control instruments. The original ISA-S20 (1981) forms were replaced by **ISA-TR20.00.01** technical report forms. These are the basis of most vendor and EPC datasheet templates (and of IEC 62683 / IEC 61987 data structures for electronic exchange).
- **Key requirements & numbers**
  - Loop diagrams per ISA-5.4 are typically produced one per loop, with every termination numbered **[general knowledge — verify]**.
- **Project pitfalls / checks**
  - Aramco and QatarEnergy projects mostly mandate *client* datasheet templates (e.g. Aramco ISS — Instrument Specification Sheets) rather than raw ISA-20 forms **[general knowledge — verify]**. Do not hand vendors ISA-20 blank forms unless the spec allows it.
  - Loop diagrams for SIS loops must show the safety logic solver I/O and any IS barriers/isolators, with entity parameters on the drawing or in the IS calculation.
- **Sources**: no web confirmation obtained. See [Gaps](#gaps).

## IEC 61508 — Functional safety (generic)

- **Scope**
  - The umbrella functional-safety standard for E/E/PE safety-related systems. In process plants it mainly governs **device manufacturers** (SIL-capable transmitters, valves, logic solvers). End users and EPCs apply IEC 61511.
- **Edition status**
  - Current normative parts are edition 2 (2010). **Edition 3** is in preparation. IEC TR 61508-3-3:2025 (object-oriented software) was published July 2025 ([Genorma](https://genorma.com/en/standards/iec-tr-61508-3-3-2025-ed1)). Part 4 ED3 was shown at FDIS stage in 2026 ([Genorma](https://genorma.com/en/standards/iec-61508-4-ed3/amp)). A November 2025 industry blog expected the main ED3 parts in about 2027 ([Gofore](https://gofore.com/?p=226169)). Confirm the status before citing ED3.
- **Key requirements & numbers**
  - The SIL bands (PFDavg for low demand) are the same as in IEC 61511. See the next section.
  - **Route 1H vs Route 2H** for architectural constraints. Route 2H gives a minimum HFT table. Route 1H uses Safe Failure Fraction (SFF). For example, a Type B element with HFT 0 needs SFF ≥ 90% to claim SIL 2 ([PTQ Q2 2024](https://ptqmagazines.digitalrefining.com/view/747650962/88/)).
  - Device certificates (e.g. exida, TÜV) state systematic capability (SC 1–3), λDU/λSD failure rates, SFF, and Type A/B classification **[general knowledge — verify]**.
- **Project pitfalls / checks**
  - A "SIL 3 certified" device does not make a loop SIL 3. The whole SIF must meet PFDavg, HFT and systematic capability.
  - Check that the certificate covers the *exact* model and options (e.g. HART version, diagnostics enabled, NE 43 alarm configuration), and read the safety manual restrictions.
- **Sources**: [Genorma TR 61508-3-3](https://genorma.com/en/standards/iec-tr-61508-3-3-2025-ed1) · [Genorma 61508-4 ED3](https://genorma.com/en/standards/iec-61508-4-ed3/amp) · [Gofore blog](https://gofore.com/?p=226169) · [PTQ](https://ptqmagazines.digitalrefining.com/view/747650962/88/)

## IEC 61511 / ISA-84 — SIS for the process industry

- **Scope**
  - Covers the safety lifecycle for Safety Instrumented Systems in the process sector: hazard and risk assessment, SIL determination (LOPA, risk graph), the Safety Requirements Specification (SRS), design, FAT/SAT, validation, operation, proof testing, management of change and decommissioning.
- **Edition status**
  - **IEC 61511-1:2016 + AMD1:2017** (consolidated "Edition 2.1", 2017-08) is current ([iTeh catalog](https://standards.iteh.ai/catalog/standards/iec/361c0fa3-af20-46c6-aa33-02db10e53012/iec-61511-1-2016); [VDE preview](https://www.vde-verlag.de/iec-normen/preview-pdf/info_iec61511-1{ed2.0}b.pdf)). No published edition 3 was confirmed in this research.
  - **US equivalent:** ANSI/ISA-84.00.01-2004 adopted IEC 61511 (2003) with one added "grandfather clause" for existing SIS ([Chemical Processing](https://www.chemicalprocessing.com/articles/2005/521)). ISA then adopted IEC 61511 Ed. 2 as **ANSI/ISA-61511-2018** to replace ISA-84.00.01-2004 ([Control Global](https://www.controlglobal.com/articles/2018/is-your-sis-getting-the-job-done); [ISA blog](https://blog.isa.org/understanding-isa-84-functional-safety-process-industries-manufacturing)). Under the newer edition, grandfathered systems need a formal assessment that they are still adequate ([Control Global](https://www.controlglobal.com/articles/2018/is-your-sis-getting-the-job-done)).
- **Key requirements & numbers**
  - **SIL bands, low-demand mode** (PFDavg / risk reduction factor RRF = 1/PFDavg) ([Yokogawa](https://yokogawa.com/eu/library/resources/white-papers/effects-on-pfdavg); [open-exam-prep](https://open-exam-prep.com/study-guides/pe-control-systems/sis-design-sil/sil-calculations)):

    | SIL | PFDavg | RRF |
    |---|---|---|
    | 1 | ≥10⁻² to <10⁻¹ | >10 to ≤100 |
    | 2 | ≥10⁻³ to <10⁻² | >100 to ≤1,000 |
    | 3 | ≥10⁻⁴ to <10⁻³ | >1,000 to ≤10,000 |
    | 4 | ≥10⁻⁵ to <10⁻⁴ | >10,000 to ≤100,000 |

  - High-demand/continuous mode uses PFH (dangerous failures per hour). The bands are SIL 1 ≥10⁻⁶ to <10⁻⁵, SIL 2 ≥10⁻⁷ to <10⁻⁶, SIL 3 ≥10⁻⁸ to <10⁻⁷, SIL 4 ≥10⁻⁹ to <10⁻⁸ **[general knowledge — verify]**.
  - **Minimum hardware fault tolerance (IEC 61511-1:2016, aligned with IEC 61508 Route 2H):** SIL 1 → HFT 0. SIL 2 low demand → HFT 0. SIL 2 high/continuous demand → HFT 1. SIL 3 → HFT 1. SIL 4 → HFT 2 ([PR electronics SIL poster](https://www.prelectronics.com/media/vzfoubbd/sil-poster-a1-2307.pdf); [PTQ](https://ptqmagazines.digitalrefining.com/view/747650962/88/)). The secondary sources also describe conditions under which HFT may be reduced or must be increased. Check these clauses in the standard ([instrumentationtools](https://instrumentationtools.com/sis-hardware-fault-tolerance/amp/)).
  - **SRS:** IEC 61511-1:2016 lists about 28 SRS content items. These include, per SIF, the safe state, the process safety time, the trip setpoints, the response time, the **proof-test interval** and the proof-test implementation requirements ([PetroSolutions](https://thepetrosolutions.com/safety-requirements-specification-srs-61511/)). The SRS should reference the proof-test procedure, or the justification for the proof-test coverage assumed in the SIL verification ([PetroSolutions](https://thepetrosolutions.com/?p=4743)).
  - **PFDavg simplified (1oo1)** ≈ λDU × TI / 2, where TI is the proof-test interval. Imperfect proof testing (proof-test coverage < 100%) and mission time raise PFDavg over life ([Yokogawa white paper](https://yokogawa.com/eu/library/resources/white-papers/effects-on-pfdavg)). The formula itself is **[general knowledge — verify]**.
  - A SIF specified with an RRF must meet that RRF, not just the SIL band ([Scribd "Three Barriers"](https://www.scribd.com/document/716264366/Three-Barriers)).
- **Project pitfalls / checks**
  - PFDavg alone does not set the SIL. Architectural constraints (HFT) and systematic capability must also be met ([Yokogawa](https://yokogawa.com/eu/library/resources/white-papers/effects-on-pfdavg)).
  - The proof-test interval assumed in the SIL verification must match the plant turnaround cycle. Middle East LNG trains often run 4–6 years between turnarounds **[general knowledge — verify]**. If online testing is not possible, the design may need redundancy or partial-stroke testing.
  - Separation of BPCS and SIS: a BPCS failure must not be an initiating cause that the same BPCS is then credited as a protection layer for. This is a typical LOPA error.
  - NE 43 alarm currents: SIS input cards must be configured to treat ≤3.6 mA and ≥21 mA as fault (see NE 43). The transmitter's failure direction must be set consistently with the SRS (fail-high vs fail-low trips).
  - Bypasses/overrides, MOS (maintenance override switches) and their alarming must be in the SRS.
- **Sources**: [iTeh 61511-1:2016](https://standards.iteh.ai/catalog/standards/iec/361c0fa3-af20-46c6-aa33-02db10e53012/iec-61511-1-2016) · [Yokogawa](https://yokogawa.com/eu/library/resources/white-papers/effects-on-pfdavg) · [PR SIL poster](https://www.prelectronics.com/media/vzfoubbd/sil-poster-a1-2307.pdf) · [PetroSolutions SRS](https://thepetrosolutions.com/safety-requirements-specification-srs-61511/) · [Control Global](https://www.controlglobal.com/articles/2018/is-your-sis-getting-the-job-done)

## IEC 60079 series — Explosive atmospheres

- **Scope**
  - The IEC 60079 series covers explosion-protected equipment (Part 0 general requirements plus one part per protection type), area classification (Part 10-1 gas, 10-2 dust), installation design (Part 14), inspection & maintenance (Part 17) and repair (Part 19).
- **Key requirements & numbers**
  - **Zones** (IEC 60079-10-1) **[general knowledge — verify exact wording]**: Zone 0 is where an explosive gas atmosphere is present continuously or for long periods. Zone 1 is where it is likely in normal operation. Zone 2 is where it is not likely in normal operation and, if it occurs, lasts only a short time. Dust: Zones 20/21/22.
  - IEC 60079-10-1:2020 (Ed. 3) replaced the 2015 edition ([IEC webstore](https://webstore.iec.ch/publication/63327); [VDE preview](https://www.vde-verlag.de/iec-normen/preview-pdf/info_iec60079-10-1{ed3.0}b.pdf)). Zone type and extent are derived from **grade of release** (continuous/primary/secondary) and **ventilation** (degree and availability) ([iTeh 2025 draft](https://standards.iteh.ai/catalog/standards/sist/7771650a-dc78-4417-b989-aa75abdf990f/osist-pren-iec-60079-10-1-2025)). A revision draft circulated in 2025 ([iTeh](https://standards.iteh.ai/catalog/standards/sist/7771650a-dc78-4417-b989-aa75abdf990f/osist-pren-iec-60079-10-1-2025)).
  - **EPL ↔ zone:** Ga → Zone 0, Gb → Zone 1, Gc → Zone 2. Dust: Da/Db/Dc → Zones 20/21/22 ([Phoenix Contact](https://www.phoenixcontact.com/en-gb/certifications-and-approvals/explosion-protection); [ABB](https://new.abb.com/drives/segments/motors-and-drives-in-potentially-explosive-atmospheres/groups-zones-categories-and-devices)).
  - **Gas groups:** IIA (propane), IIB (ethylene), IIC (hydrogen, acetylene). IIC equipment is suitable for IIB and IIA ([R. STAHL](https://r-stahl.com/en/in/services-and-seminars/explosion-protection-knowledge/technical-principles/); [HPC Ex marking guide](https://hpcimedia.com/images/ex-marking-guide.pdf)). Group I is mining, Group III is dust (IIIA/IIIB/IIIC).
  - **Temperature classes** (maximum surface temperature): T1 450 °C, T2 300 °C, T3 200 °C, T4 135 °C, T5 100 °C, T6 85 °C. Equipment must stay below the gas autoignition temperature. A T6 device may be used for any T-class requirement ([Phoenix Contact](https://www.phoenixcontact.com/en-gb/certifications-and-approvals/explosion-protection)).
  - **Types of protection and their parts:**

    | Code | Concept | Part | Typical EPL |
    |---|---|---|---|
    | Ex d (da/db/dc) | Flameproof enclosure | 60079-1 | Gb |
    | Ex e (eb/ec) | Increased safety | 60079-7 | Gb / Gc |
    | Ex i (ia/ib/ic) | Intrinsic safety | 60079-11 | Ga / Gb / Gc |
    | Ex p (pxb/pyb/pzc) | Pressurized enclosure | 60079-2 (rooms: 60079-13) | Gb / Gc |
    | Ex m (ma/mb/mc) | Encapsulation | 60079-18 | Ga / Gb / Gc |
    | Ex n (nA/nC/nR …) | Type "n" | 60079-15 | Gc |
    | Ex o / q | Liquid / powder filling | 60079-6 / 60079-5 | Gb |

    Part mapping per [ABB main Ex standards](https://new.abb.com/drives/segments/motors-and-drives-in-potentially-explosive-atmospheres/main-ex-standards), [Beckhoff catalogue](https://download.beckhoff.com/download/document/Catalog/Beckhoff_Explosion_protection_e.pdf) and [BSI 60079-13 listing](https://knowledge.bsigroup.com/products/explosive-atmospheres-equipment-protection-by-pressurized-room-p-and-artificially-ventilated-room-v). The EPL column is **[general knowledge — verify]**.
  - **Ex nA → Ex ec:** The Ex nA requirements of EN 60079-15:2010 were superseded by **Ex ec** in EN 60079-7:2015 ([BSI preview](https://webstore.ansi.org/preview-pages/BSI/preview_30469238.pdf)). Other "n" subtypes moved too: nC → dc, nL → ic, nR stays in 60079-15, nZ → pz ([SGS Baseefa harmonisation table](https://www.sgs.co.uk/-/media/local/uk/documents/brochures/bas-ps-010-sgs-baseefa-harmonisation-status-20-03.pdf?la=en-gb); [Heating & Process](https://www.heatingandprocess.com/?p=26117)). Current editions: IEC 60079-7:2015+AMD1:2017 ([standards.ie](https://shop.standards.ie/en-ie/standards/iec-60079-7-2015-amd1-2017-csv-563953_saig_iec_iec_2731838)) and IEC 60079-15:2017 ([Standards Australia store](https://store.standards.org.au/product/iec-60079-15-2017)).
  - **Marking example:** "Ex ic IIC T4 Gc" = protection type, gas group, T-class, EPL ([HPC Ex marking guide](https://hpcimedia.com/images/ex-marking-guide.pdf)).
- **Project pitfalls / checks**
  - Gulf ambient: equipment is certified for −20 °C to +40 °C by default. Middle East sites often specify +50 °C to +55 °C (and higher in sun or inside enclosures), so a certificate with an **extended Ta range** is needed **[general knowledge — verify]**.
  - The "X" suffix on a certificate means special conditions of use. These must be read and implemented, e.g. impact protection or cable gland types ([Wolf Safety poster](https://www.wolfsafety.com/downloads/468/Wolf%20ATEX%20Explained%20A1%20Poster-April_2024_V10.pdf)).
  - Hydrogen-rich units (hydrotreaters, H₂ plants, refinery fuel gas) need IIC. LNG/NG is normally IIA. Ethylene units need IIB. Do not default everything to IIB T3 without checking the process fluid list in the area classification.
  - Ex d enclosures: flamepath gaps must not be painted or gasketed unless the certificate allows it. Only Ex d certified glands and stoppers may be used (barrier glands where IEC 60079-14 requires them).
  - Old datasheets requesting "Ex nA" must be updated to "Ex ec" for new purchases.
- **Sources**: [R. STAHL](https://r-stahl.com/en/in/services-and-seminars/explosion-protection-knowledge/technical-principles/) · [Phoenix Contact](https://www.phoenixcontact.com/en-gb/certifications-and-approvals/explosion-protection) · [IEC webstore 60079-10-1](https://webstore.iec.ch/publication/63327) · [ABB standards](https://new.abb.com/drives/segments/motors-and-drives-in-potentially-explosive-atmospheres/main-ex-standards) · [BSI preview](https://webstore.ansi.org/preview-pages/BSI/preview_30469238.pdf) · [SGS harmonisation](https://www.sgs.co.uk/-/media/local/uk/documents/brochures/bas-ps-010-sgs-baseefa-harmonisation-status-20-03.pdf?la=en-gb)

## Intrinsic safety entity / FISCO checks

- **Scope**
  - Loop-level verification that an intrinsically safe (IS) field device connected to associated apparatus (barrier or isolator) through a cable stays within the certified parameters (IEC 60079-11 apparatus; IEC 60079-14 installation; IEC 60079-25 IS systems) **[standard numbers: general knowledge — verify]**.
- **Key requirements & numbers**
  - Parameters: associated apparatus outputs **Uo, Io, Po, Co, Lo**. Field device inputs **Ui, Ii, Pi, Ci, Li** ([automationforum](https://automationforum.co/intrinsic-safe-calculation-for-instrumentation-design-engineers/)).
  - Checks: **Ui ≥ Uo, Ii ≥ Io, Pi ≥ Po, Ci + Ccable ≤ Co, Li + Lcable ≤ Lo**. Cable C or L = per-length value × length ([automationforum](https://automationforum.co/intrinsic-safe-calculation-for-instrumentation-design-engineers/); [Macromatic](https://macromatic.com/support/knowledge-base-articles/understanding-entity-parameters)).
  - The barrier control drawing may require Co/Lo to be reduced when Ci or Li are significant (about 1% of Co/Lo) ([automationforum](https://automationforum.co/intrinsic-safe-calculation-for-instrumentation-design-engineers/)). Inductance can be the limiting factor even when capacitance passes. The L/R ratio method is an alternative to the Lo check **[general knowledge — verify]**.
  - FOUNDATION Fieldbus / PROFIBUS PA IS segments use FISCO parameters instead of the entity method ([automationforum](https://automationforum.co/intrinsic-safe-calculation-for-instrumentation-design-engineers/)).
- **Project pitfalls / checks**
  - Use the cable datasheet C and L values (e.g. pF/m, µH/m), not "typical" ones. Long runs to tank farms or jetties often fail Co.
  - IS cables and terminals must be identifiable (light blue is customary) and segregated from non-IS wiring **[general knowledge — verify]**.
  - Simple apparatus (RTDs, thermocouples, switches) need no certificate but must still be included in the loop check, with the T-class assessed.
- **Sources**: [automationforum](https://automationforum.co/intrinsic-safe-calculation-for-instrumentation-design-engineers/) · [Macromatic](https://macromatic.com/support/knowledge-base-articles/understanding-entity-parameters) · [Pepperl+Fuchs blog](https://blog.pepperl-fuchs.com/en/?p=13865)

## ATEX and IECEx certification

- **Scope**
  - **ATEX** (Directive 2014/34/EU for equipment) is EU *law*. Notified bodies issue EU-Type Examination Certificates, and the manufacturer issues the EU Declaration of Conformity ([ATEX flyer](https://www.scribd.com/document/453968076/atex-flyer-en)).
  - **IECEx** is a voluntary, standards-based international scheme. An ExCB issues the Certificate of Conformity after test reports (ExTR) and a quality audit (QAR) ([HSE Blog](https://www.hseblog.com/atex-vs-iecex/); [PR electronics](https://www.prelectronics.com/sa/support/pr-knowledge-library/tips-and-tricks/atex-vs-iecex-differences-explained/)).
- **Key requirements & numbers**
  - Category ↔ EPL ↔ zone: **1G = Ga = Zone 0, 2G = Gb = Zone 1, 3G = Gc = Zone 2**. Dust: 1D/2D/3D = Da/Db/Dc ([DNV](https://www.dnv.com.mx/services/industrial-product-assurance/welding/atex-product-certification-5985/)).
  - Certificate numbering: ATEX numbers contain the year and "ATEX" (e.g. "Baseefa07ATEX0091X"), IECEx numbers start with "IECEx" and the ExCB code. "X" = special conditions of use. "U" = Ex component (not usable alone) ([Wolf Safety](https://www.wolfsafety.com/downloads/468/Wolf%20ATEX%20Explained%20A1%20Poster-April_2024_V10.pdf)).
- **Project pitfalls / checks**
  - Saudi Arabia and Qatar generally accept IECEx (often together with ATEX). Some projects also require local conformity: Saudi SASO/SABER marking, or a Qatar-specific approval **[general knowledge — verify]**. Check the project spec.
  - "U" component certificates (e.g. empty enclosures, terminals) do not certify an assembled junction box. The assembly needs its own certificate.
  - North American (UL/CSA/FM Class/Division) approvals do not substitute for IECEx/ATEX unless the spec says so.
- **Sources**: [DNV](https://www.dnv.com.mx/services/industrial-product-assurance/welding/atex-product-certification-5985/) · [PR electronics](https://www.prelectronics.com/sa/support/pr-knowledge-library/tips-and-tricks/atex-vs-iecex-differences-explained/) · [HSE Blog](https://www.hseblog.com/atex-vs-iecex/) · [Wolf Safety](https://www.wolfsafety.com/downloads/468/Wolf%20ATEX%20Explained%20A1%20Poster-April_2024_V10.pdf)

## NEC Articles 500/505 and API RP 500/505 (area classification)

- **Scope**
  - **NFPA 70 (NEC) Article 500** sets out the Class/Division system. **Article 505** sets out the Class I Zone system for gases ([ECM](https://www.ecmweb.com/nec/article-505-zone-locations)).
  - **API RP 500** gives Division-based area classification recommendations for petroleum facilities. **API RP 505** gives the Zone-based equivalent ([forumautomation](https://forumautomation.com/t/what-is-the-difference-between-api-500-and-505/13992); [GlobalSpec RP 505](https://standards.globalspec.com/std/13052108/api-rp-505)).
- **Edition status**
  - API RP 500 4th edition, June 2023 ([GlobalSpec RP 500](https://standards.globalspec.com/std/14608086/rp-500); [API announcement](https://www.api.org/products-and-services/standards/important-standards-announcements/rp500article)).
  - API RP 505: the 2nd edition (August 2018) is now listed as historical, and a 2025 edition is referenced ([technormen](https://www.technormen.de/norm/apirp-505-ed-2-1.8.2018.html); [GlobalSpec](https://standards.globalspec.com/std/13052108/api-rp-505)). Not fully confirmed — verify.
- **Key requirements & numbers**
  - Division 1 ≈ Zone 0 + Zone 1. Division 2 ≈ Zone 2. They are approximately but not exactly equivalent ([IAEI magazine](https://iaeimagazine.org/features/comparison-of-division-and-zone-systems/); [ECmag](https://www.ecmag.com/magazine/articles/article-detail/codes-standards-tradition-meets-alternative-how-determine-and-classify-hazardous-locations)).
  - Gas groups (Division system): A (acetylene), B (hydrogen), C (ethylene), D (propane). Zone system equivalents: IIC ≈ A+B, IIB ≈ C, IIA ≈ D **[general knowledge — verify]**. Example: a propane room = Class I, Div 2, Group D, or Zone 2, Group IIA ([ECM](https://www.ecmweb.com/nec/article-505-zone-locations)).
  - Equipment listed for Class I Zone 0/1/2 may be used in Class I Division 2 for the same gas and a suitable T-class (per a summary of NEC 501) ([ECM](https://www.ecmweb.com/nec/hazardous-locations-and-nec)).
  - Zone and Division boundaries: the sources conflict on whether a Zone 2 area may *abut* a Division 2 area (overlapping is not allowed). Check NEC 505.7 in the edition in force ([ECM](https://www.ecmweb.com/nec/article-505-zone-locations); [IAEI](https://iaeimagazine.org/features/comparison-of-division-and-zone-systems/)).
- **Project pitfalls / checks**
  - Middle East projects almost always use the **IEC Zone system** (IEC 60079-10-1, often with the Energy Institute EI 15 model code or API RP 505 for extents) **[general knowledge — verify]**. Aramco's SAES-B-068 governs Aramco area classification **[general knowledge — verify]**.
  - Do not mix NEC Division-marked equipment into a Zone-classified plant unless it is dual-marked and the spec allows it.
- **Sources**: [API RP 500 announcement](https://www.api.org/products-and-services/standards/important-standards-announcements/rp500article) · [GlobalSpec RP 505](https://standards.globalspec.com/std/13052108/api-rp-505) · [IAEI](https://iaeimagazine.org/features/comparison-of-division-and-zone-systems/) · [ECM Art. 505](https://www.ecmweb.com/nec/article-505-zone-locations) · [Engineering Toolbox](https://www.engineeringtoolbox.com/hazardous-areas-classification-d_345.html)

## IEC 60529 IP codes and NEMA 250

- **Scope**
  - **IEC 60529** gives the degree of protection by enclosures (IP code): first digit for solids and dust, second digit for water. **NEMA 250** gives US enclosure types, which also test corrosion, icing and gasket ageing ([Siemens IP vs NEMA](https://assets.new.siemens.com/siemens/assets/api/uuid:7f2844f1-502a-4c23-b123-117894c39a8c/ip-vs-nema-whitepaper-icp-us.pdf)).
- **Key requirements & numbers**
  - First digit **6 = dust-tight**. Second digit **6 = powerful water jets**, tested with a 12.5 mm nozzle at 100 L/min for 3 min from any direction ([indexenclosures](https://indexenclosures.com/resources/ip-ratings-guide/); [DSMT chart](https://dsmt.com/resources/ip-rating-chart/)).
  - **7 = temporary immersion up to 1 m**. The standard test is 30 min at 1 m depth **[general knowledge — verify]**. One vendor table describes the time as "specified by manufacturer" ([DSMT](https://dsmt.com/resources/ip-rating-chart/)).
  - **8 = continuous immersion** beyond 1 m, with depth and duration declared by the manufacturer ([indexenclosures](https://indexenclosures.com/resources/ip-ratings-guide/)).
  - Ratings are **not cumulative between jets and immersion**. An IP67 device has not necessarily passed IP66 jets, so specify **IP66/IP67** (dual marking) where both apply ([indexenclosures](https://indexenclosures.com/resources/ip-ratings-guide/)).
  - Approximate NEMA ↔ IP: NEMA 4/4X ≈ IP66, NEMA 6 ≈ IP67, NEMA 6P ≈ IP68, NEMA 12/13 ≈ IP54 (some sources say IP52 for 12). The comparison only works one way: a NEMA type can be said to meet an IP code, but not the reverse ([Gore chart](https://www.gore.com/node/4221); [control.com](https://control.com/technical-articles/understanding-different-ip-enclosure-ratings/)). **NEMA 7 and 9** are hazardous-location enclosures with no IP equivalent ([c3controls](https://www.c3controls.com/white-paper/nema-ratings-and-environmental-protection-choosing-the-right-enclosure)). The "X" in 4X means corrosion resistance.
- **Project pitfalls / checks**
  - Gulf coastal, offshore and desert sites typically require a minimum of IP65/IP66 for field instruments and junction boxes, with IP66/IP67 dual rating common for transmitters **[general knowledge — verify against the client spec]**.
  - Sand/dust storms and deluge-system testing: specify IP66 (jets), not just IP67.
  - The IP rating is only valid with the correct cable glands/plugs installed. Unused entries must use certified stopping plugs.
- **Sources**: [indexenclosures](https://indexenclosures.com/resources/ip-ratings-guide/) · [DSMT](https://dsmt.com/resources/ip-rating-chart/) · [Gore](https://www.gore.com/node/4221) · [control.com](https://control.com/technical-articles/understanding-different-ip-enclosure-ratings/) · [Siemens](https://assets.new.siemens.com/siemens/assets/api/uuid:7f2844f1-502a-4c23-b123-117894c39a8c/ip-vs-nema-whitepaper-icp-us.pdf) · [c3controls](https://www.c3controls.com/white-paper/nema-ratings-and-environmental-protection-choosing-the-right-enclosure)

## API RP 551 — Process measurement

- **Scope**
  - Covers selection, design, installation, commissioning and operation of process measurement instruments (flow, level, pressure, temperature, seals/purges) ([SAI Global](https://infostore.saiglobal.com/en-au/standards/api-551-2016-96993_saig_api_api_203195/); [GlobalSpec](https://standards.globalspec.com/std/9988220/api-rp-551)).
- **Edition status**
  - 2nd edition, February 2016, reaffirmed 2024 ("R2024") ([technormen](https://www.technormen.de/norm/apirp-551_r2024-1.2.2016.html)). One reseller lists it as superseded in 2024 — verify ([SAI Global](https://infostore.saiglobal.com/en-au/standards/api-551-2016-96993_saig_api_api_203195/)). The 1st edition (1993) was derived from API RP 550 Part I ([GlobalSpec](https://standards.globalspec.com/std/207907/api-rp-551)).
- **Key requirements & numbers**
  - Practical guidance on impulse lines, slope, root valves, manifolds, seals, purges, and installation of DP flow, level and temperature elements **[general knowledge — verify]**. One secondary article cites API 551 for a transmitter short-circuit output above 22 mA, but this was not confirmed ([electricalvolt](https://www.electricalvolt.com/what-is-namur-ne-43)).
- **Project pitfalls / checks**
  - API 551 is a recommended practice. Client hook-up standards (e.g. Aramco standard drawings) take precedence for hook-up details **[general knowledge — verify]**.
- **Sources**: [SAI Global](https://infostore.saiglobal.com/en-au/standards/api-551-2016-96993_saig_api_api_203195/) · [technormen](https://www.technormen.de/norm/apirp-551_r2024-1.2.2016.html) · [GlobalSpec](https://standards.globalspec.com/std/9988220/api-rp-551)

## API RP 552 — Signal processing, transmission and installation

- **Scope / edition**
  - The old **API RP 552 "Transmission Systems" (1994, R2022)** has been replaced by the **2nd edition, 2025**, retitled *Signal Processing, Transmission, and Installation* ([standards.ie 2025](https://shop.standards.ie/en-ie/standards/api-rp-552-2025-96994_saig_api_api_3521664); [standards.ie 1994](https://shop.standards.ie/en-ie/standards/api-rp-552-1994-r2022--96994_saig_api_api_3201689); [BSI](https://knowledge.bsigroup.com/products/signal-processing-transmission-and-installation)).
- **Key requirements & numbers**
  - Covers analog (4–20 mA) and digital transmission, cable types, shielding, segregation and grounding of signal circuits **[content of 2025 edition not confirmed — verify]**.
- **Project pitfalls / checks**
  - Projects whose specs still cite the 1994 edition should get a deviation or clarification about which edition applies.
- **Sources**: [standards.ie](https://shop.standards.ie/en-ie/standards/api-rp-552-2025-96994_saig_api_api_3521664) · [BSI](https://knowledge.bsigroup.com/products/signal-processing-transmission-and-installation)

## API RP 553 — Refinery valves and accessories for control and SIS

- **Scope**
  - Covers control valves, on/off and SIS valves, and their accessories: actuators, positioners, solenoids, limit switches, volume boosters ([Skybear](https://www.skybearstandards.com/documents/api-rp-553-refinery-valves-and-accessories-for-control-and-safety-instrumented-systems/)).
- **Edition status**
  - The 2nd edition (October 2012) is listed as replaced. A **3rd edition** is listed as most recent, but its year was not confirmed ([Accuris](https://store.accuristech.com/cii/subgroups/16827)).
- **Key requirements & numbers**
  - Typical content: actuator sizing margins, fail-safe action, positioner selection, SIS valve requirements such as tight shut-off and partial-stroke testing, and solenoid valve selection **[general knowledge — verify]**.
- **Project pitfalls / checks**
  - Check actuator sizing at **minimum** air supply pressure. Check that SIS valve stroke times (open/close) are validated against the process safety time in the SRS.
- **Sources**: [Skybear](https://www.skybearstandards.com/documents/api-rp-553-refinery-valves-and-accessories-for-control-and-safety-instrumented-systems/) · [Accuris](https://store.accuristech.com/cii/subgroups/16827)

## API RP 554 — Process control systems

- **Scope / editions**
  - **Part 1** — Functions and functional specification development, 3rd ed., May 2021 ([mystandards](https://www.mystandards.biz/standard/apirp-554-1-ed-3-1.5.2021.html)).
  - **Part 2** — Process control system design, 2nd ed., August 2023 ([mystandards](https://www.mystandards.biz/standard/apirp-554-2-ed-2-1.8.2023.html)).
  - **Part 3** — Project execution and process control system ownership, 2nd ed., January 2021 ([mystandards](https://www.mystandards.biz/standard/apirp-554-3-ed-2-1.1.2021.html)).
- **Key requirements & numbers**
  - Covers DCS/PLC functional specs, redundancy, I/O, alarm and HMI considerations, network design, FAT/SAT and lifecycle ownership **[detail general knowledge — verify]**.
- **Project pitfalls / checks**
  - Use Part 3 to frame the control system vendor's (MAC/MICC) scope split, FAT/SAT and obsolescence-management obligations.
- **Sources**: [Part 1](https://www.mystandards.biz/standard/apirp-554-1-ed-3-1.5.2021.html) · [Part 2](https://www.mystandards.biz/standard/apirp-554-2-ed-2-1.8.2023.html) · [Part 3](https://www.mystandards.biz/standard/apirp-554-3-ed-2-1.1.2021.html)

## API RP 555 — Process analyzers

- **Scope**
  - Covers process analyzer systems that measure chemical composition or physical/chemical properties: selection, sample systems, pre-packaged vs field-built systems, installation, maintenance and safety ([standards.ie](https://shop.standards.ie/en-ie/standards/api-555-2013-96997_saig_api_api_203208); [BSI](https://knowledge.bsigroup.com/products/process-analyzers)).
- **Edition status**
  - 3rd edition, 2013. One store lists it as replaced, another as current — verify ([standard.no](https://online.standard.no/en/api-rp-555)).
- **Key requirements & numbers**
  - Sample transport lag time targets (often ≤ 60 s total lag), fast-loop design, analyzer shelter ventilation/purge and gas detection **[general knowledge — verify; shelter content not confirmed in API 555]**.
- **Project pitfalls / checks**
  - Analyzer shelters in Zone 2 areas normally rely on Ex p / ventilation with gas detection interlocks. Coordinate the area classification of the shelter interior with the safety department **[general knowledge — verify]**.
- **Sources**: [standards.ie](https://shop.standards.ie/en-ie/standards/api-555-2013-96997_saig_api_api_203208) · [standard.no](https://online.standard.no/en/api-rp-555) · [BSI](https://knowledge.bsigroup.com/products/process-analyzers)

## API RP 556 — Fired heater instrumentation

- **Scope**
  - Instrumentation, control and protective systems (alarms, shutdown, burner management, automatic start-up/shutdown) for **gas-fired** heaters and related steam generators in petroleum, petrochemical and chemical plants. It **excludes** oil-fired and combination-fired heaters, pyrolysis furnaces, and water-tube boilers (covered by NFPA 85) ([DIN Media](https://www.dinmedia.de/en/technical-rule/api-rp-556/142709619)).
- **Edition status**
  - 2nd edition, April 2011, reaffirmed 2024 ([mystandards](https://www.mystandards.biz/standard/apirp-556_r2024-1.4.2011.html)). One distributor states it has been partially replaced by a new part (API RP 556-5, 2026) — verify ([standard.no](https://online.standard.no/en/api-rp-556-3)).
- **Key requirements & numbers**
  - Typical protective functions: low fuel gas pressure, high fuel gas pressure, flame failure, low combustion air flow/draft, high arch pressure, low pass flow, and purge-permissive logic **[general knowledge — verify]**.
- **Project pitfalls / checks**
  - Fired heater SIFs (BMS) are usually SIL-rated under IEC 61511. Check flame scanner certification and the burner management logic against both API 556 and the SRS.
- **Sources**: [DIN Media](https://www.dinmedia.de/en/technical-rule/api-rp-556/142709619) · [mystandards](https://www.mystandards.biz/standard/apirp-556_r2024-1.4.2011.html) · [AFPM paper](https://www2.afpm.org/forms/store/ProductFormPublic/pd-12-10-the-new-api-rp-556-best-practices-for-instrumentation-control-and-protective-systems-for-gas-fired-heaters)

## API 670 — Machinery protection systems

- **Scope**
  - Minimum requirements for radial shaft vibration, casing vibration, shaft axial position, speed, piston-rod drop, phase reference, **overspeed** and **surge detection** systems on critical rotating machinery ([fabrico](https://www.fabrico.io/blog/api-670-machinery-protection/)).
- **Edition status**
  - 5th edition, November 2014, listed as current ([GlobalSpec](https://standards.globalspec.com/std/9881344/api-std-670)). Check whether a 6th edition has since been issued.
- **Key requirements & numbers**
  - Default transducer sensitivity for radial vibration and axial position: **7.87 mV/µm (200 mV/mil)** ([vibsens](https://vibsens.com/index.php/knowledge-base/api670-compliance)). Proximity probe tip sizes of 5 mm or 8 mm ([ASEE paper](https://peer.asee.org/uniprobe-universal-inductive-proximity-probe-design-and-testing.pdf)).
  - Axial position comes from the probe's average DC gap voltage. **Two probes** are recommended so that voting protection can be used for automatic shutdown ([ASEE paper](https://peer.asee.org/uniprobe-universal-inductive-proximity-probe-design-and-testing.pdf)).
  - Probe calibration should be verified on a target with the same electrical properties as the shaft material ([vibsens](https://vibsens.com/index.php/knowledge-base/api670-compliance)).
  - Typical probe system length: 5 m or 9 m (probe + extension cable). Two radial probes per bearing at 90° (X–Y) **[general knowledge — verify]**.
- **Project pitfalls / checks**
  - Probe system lengths must match the proximitor's calibrated length. Field cutting of extension cables breaks calibration.
  - Overspeed trip systems are often SIL-rated. Make sure the overspeed module has the appropriate certification and response time.
- **Sources**: [GlobalSpec](https://standards.globalspec.com/std/9881344/api-std-670) · [vibsens](https://vibsens.com/index.php/knowledge-base/api670-compliance) · [ASEE](https://peer.asee.org/uniprobe-universal-inductive-proximity-probe-design-and-testing.pdf) · [fabrico](https://www.fabrico.io/blog/api-670-machinery-protection/)

## API 2350 — Tank overfill protection

- **Scope**
  - Overfill protection for petroleum storage tanks (atmospheric aboveground). It covers the management system, levels of concern (LOC), response times, and tank categories ([API announcement](https://www.api.org/products-and-services/standards/important-standards-announcements/standard-2350)).
- **Edition status**
  - **5th edition, September 2020** ([Hydrocarbon Engineering](https://www.hydrocarbonengineering.com/tanks-terminals/18092020/api-publishes-fifth-edition-of-api-2350)).
- **Key requirements & numbers**
  - Added **Category 0** (manual hand-gauging only) ([Emerson article](https://emerson.com/documents/automation/article-api-2350-reducing-risk-of-overfills-en-8330454.pdf)).
  - Category 1: manual/local reading. Category 2: ATG with alarms. Category 3: ATG plus an **independent** high-high level sensor/alarm. An **Automated Overfill Prevention System (AOPS)** is an add-on to Category 2 or 3, never used alone ([inspenet](https://inspenet.com/en/articles/api-2350-for-tanks-overfill-prevention/); [Emerson](https://www.emersonautomationexperts.com/2021/measurement-instrumentation/tank-gauging/understanding-api-2350-storage-tank-overfill-prevention/)).
  - Default minimum response times when not calculated: **Cat 0: 60 min, Cat 1: 45 min, Cat 2: 30 min, Cat 3: 15 min** ([inspenet](https://inspenet.com/en/articles/api-2350-for-tanks-overfill-prevention/)). This is a secondary source — verify.
  - LOCs (critical high, high-high, maximum working level) must be reviewed periodically ([Emerson](https://emerson.com/documents/automation/article-api-2350-reducing-risk-of-overfills-en-8330454.pdf)).
- **Project pitfalls / checks**
  - The independent HH sensor must not share the ATG's transmitter, power or I/O.
  - An AOPS is normally treated as a SIF under IEC 61511.
  - LNG full-containment tanks are outside API 2350's atmospheric-tank focus. LNG tanks follow EN 14620 / API 625 plus project SIS **[general knowledge — verify]**.
- **Sources**: [API](https://www.api.org/products-and-services/standards/important-standards-announcements/standard-2350) · [Hydrocarbon Engineering](https://www.hydrocarbonengineering.com/tanks-terminals/18092020/api-publishes-fifth-edition-of-api-2350) · [inspenet](https://inspenet.com/en/articles/api-2350-for-tanks-overfill-prevention/) · [Emerson](https://emerson.com/documents/automation/article-api-2350-reducing-risk-of-overfills-en-8330454.pdf)

## API 520 / 521 / 526 / 527 — Pressure relief

### API 520 (Parts I & II) — Sizing, selection and installation of PRDs
- **Key requirements & numbers**
  - **Inlet pressure loss** for conventional PRVs should be **< 3% of set pressure** (Part II). Exceeding it is allowed only with an engineering analysis ([processengr](https://processengr.com/?p=4225); [projectmaterials](https://blog.projectmaterials.com/quick-answers/pipes/how-to-size-relief-valve-api-520/)).
  - **Built-up back pressure** for a conventional spring valve is generally limited to the allowable overpressure (e.g. **10%** for a non-fire case). Variable superimposed back pressure calls for a **balanced bellows** or pilot valve ([Eng-Tips, citing API 520 Pt I §5.3, Oct 2020](https://www.eng-tips.com/viewthread.cfm?qid=497454)). Balanced bellows valves need a Kb back-pressure correction ([projectmaterials](https://blog.projectmaterials.com/quick-answers/pipes/how-to-size-relief-valve-api-520/)).
  - Allowable accumulation (from ASME Section VIII practice): 10% single valve, 16% multiple valves, 21% fire case **[general knowledge — verify]**.
- **Pitfall**: Instrument engineers often own PSV datasheets. Check that the back-pressure type (conventional/bellows/pilot) matches the flare network back pressure from the API 521 study.

### API 521 — Pressure-relieving and depressuring systems
- **Edition**: 7th edition, 2020, with Errata 1 in 2022 ([Hydrocarbon Engineering](https://www.hydrocarbonengineering.com/petrochemicals/08062020/api-publishes-7th-edition-of-api-standard-521/); [standards.ie](https://shop.standards.ie/en-ie/standards/api-std-521-2020-err-1-2022-96973_saig_api_api_3201718)).
- **Key requirements & numbers**
  - The classic fire-depressuring guideline is to reach **690 kPa(g) (100 psig) or 50% of design pressure, whichever is lower, within about 15 min**. It applies to carbon-steel vessels ≥ 25 mm (1 in) wall. Thinner walls may need faster depressuring ([API 521 committee Q&A](https://www.scribd.com/doc/273974550/API-521-Technical-Committee-Q-A)).
  - The 7th edition emphasizes evaluating vessel wall stress during fire exposure (analytical method, Annex A) instead of relying only on the fixed time/pressure target ([Hydrocarbon Processing Feb 2024](https://read.nxtbook.com/gulf_energy_information/hydrocarbon_processing/february_2024/environment_and_safety_rodrig.html)).
- **Pitfall**: Blowdown valve (BDV) stroke time and fail-open action, plus the restriction orifice sizing, must be consistent with the depressuring study.

### API 526 — Flanged steel pressure-relief valves
- **Edition**: API STD 526, 7th edition (2017) with Errata 1 (2018) ([SAI Global](https://infostore.saiglobal.com/en-us/standards/api-std-526-2017-errata-1-2018-96976_saig_api_api_2677153/)).
- **Key requirements & numbers**
  - Standard orifice letters **D, E, F, G, H, J, K, L, M, N, P, Q, R, T** (no I or O). D = **0.110 in²**, T = **26.0 in²** ([Neutrium](https://neutrium.net/articles/equipment/relief-valve-orifice-area-to-api-rp-526/)). Select the next letter whose effective area ≥ the calculated required area ([fluidflow](https://knowledge.fluidflowinfo.com/en/articles/15935449-pressure-safety-valve-sizing-and-selection-the-8-step-workflow)).
  - Effective areas (in²): D 0.110, E 0.196, F 0.307, G 0.503, H 0.785, J 1.287, K 1.838, L 2.853, M 3.60, N 4.34, P 6.38, Q 11.05, R 16.0, T 26.0 **[intermediate values general knowledge — verify]**.
- **Pitfall**: API 526 *effective* areas are for sizing with API 520 coefficients only. For ASME-certified capacity, use the manufacturer's *actual* area and certified coefficient.

### API 527 — Seat tightness of PRVs
- **Edition**: API STD 527, 5th edition 2020, reaffirmed 2025 ([standards.ie](https://shop.standards.ie/en-ie/standards/api-std-527-2020-r2025--96977_saig_api_api_3652878)).
- **Key requirements & numbers**
  - Leakage is measured with the inlet held at **90% of set pressure** (or of CDTP) for at least 1 min. For metal seats with set ≤ 50 psig, the test is at 5 psig below set ([Farris manual](https://manualedistruzioni.it/farris-engineering/control-unit/1800-series/user-manual/19xhl)). Bubbles are counted from a **5/16 in OD × 0.049 in wall tube submerged ½ in** in water ([open-exam-prep](https://open-exam-prep.com/study-guides/api-510/pressure-relieving-devices-api-576/prd-causes-of-failure-and-overhaul)).
  - **Soft-seated valves: zero bubbles** for 1 min. Metal-seated limits depend on set pressure and orifice size (≤ F/0.307 in² vs larger), per Table 6 ([Farris manual](https://manualedistruzioni.it/farris-engineering/control-unit/1800-series/user-manual/19xhl)). Typical metal-seat values (40 bubbles/min ≤ 1000 psig for small orifices, 20 for larger) are **[general knowledge — verify]**.
- **Sources (all PSV standards)**: [Neutrium](https://neutrium.net/articles/equipment/relief-valve-orifice-area-to-api-rp-526/) · [processengr](https://processengr.com/?p=4225) · [Eng-Tips](https://www.eng-tips.com/viewthread.cfm?qid=497454) · [Hydrocarbon Engineering](https://www.hydrocarbonengineering.com/petrochemicals/08062020/api-publishes-7th-edition-of-api-standard-521/) · [Farris](https://manualedistruzioni.it/farris-engineering/control-unit/1800-series/user-manual/19xhl)

## API 598 / 6D / 600 / 608 / 609 — Valves

- **API 598 — Valve inspection and testing**
  - Shell test at **1.5 × CWP** (cold working pressure at 38 °C). High-pressure closure (seat) test at **1.1 × CWP**. There is also a low-pressure air/gas closure test, a backseat test and double block-and-bleed tests ([projectmaterials](https://blog.projectmaterials.com/quick-answers/valves/what-is-api-598/)). Durations depend on size.
  - Editions: 10th (2016). A 2023 edition is listed ([cncontrolvalve](https://cncontrolvalve.com/api-standard-598-valve-inspection-and-testing-2023-11-edition)).
- **API 6D — Pipeline and piping valves**
  - **25th edition, November 2021**, with Errata 1 (Dec 2021), Addendum 1 (April 2023) and Addendum 2 (Sept 2024). Addendum 2 removed references to QSL-1 in the nameplate marking table ([API Errata 1](https://API.org/-/media/Files/Certification/Monogram-APIQR/0_API-Monogram-APIQR/Advisories-Updates/Addenda-Errata/API_Specification_6D_25th_Edition_Errata_1_20211227.pdf); [Addendum 1](https://API.org/-/media/Files/Certification/Monogram-APIQR/0_API-Monogram-APIQR/Advisories-Updates/Addenda-Errata/API_6D_25th_Edition_Addendum_1_April_2023.pdf); [Addendum 2](https://www.api.org/-/media/files/certification/monogram-apiqr/0_api-monogram-apiqr/advisories-updates/addenda-errata/api_specification_6d_25th_edition_addendum_2_20240910.pdf)).
- **API 600 — Steel gate valves** (bolted bonnet). The 13th edition (2015) extended sizes to NPS 48 ([Valve Magazine](https://valvemagazine.com/articles/an-update-on-u-s-valve-related-standards/)). A later edition may exist — verify.
- **API 608 — Metal ball valves** (flanged, butt-weld, socket-weld, threaded; full, single-reduced and double-reduced bore). 6th edition, January 2020 ([Accuris](https://store.accuristech.com/api/products/preview/2098132); [GlobalSpec](https://standards.globalspec.com/std/14207783/api-std-608)).
- **API 609 — Butterfly valves** (double-flanged, lug, wafer) ([Engineering Toolbox](https://engineeringtoolbox.com/api-valve-standards-d_378.html)). **Category A** = concentric (typically Class 150, 2–48 in) ([Scribd valve table](https://www.scribd.com/document/457360248/Valve-Spec-Table)). **Category B** = offset/high-performance (double/triple offset), rated to ASME B16.34 classes **[general knowledge — verify]**. Current edition not confirmed.
- **Project pitfalls / checks**
  - On/off SIS and ESD valves bought to API 6D/608 often need **fire-safe certification (API 607 / ISO 10497)** and specified seat leakage. Check the valve datasheet calls up both the body standard and the test standard.
  - Tight-shutoff ESD valves: specify the test standard explicitly. API 598 metal-seat allowance ≠ zero leakage ≠ FCI 70-2 Class V/VI.
- **Sources**: [projectmaterials API 598](https://blog.projectmaterials.com/quick-answers/valves/what-is-api-598/) · [API 6D addenda](https://www.api.org/-/media/files/certification/monogram-apiqr/0_api-monogram-apiqr/advisories-updates/addenda-errata/api_specification_6d_25th_edition_addendum_2_20240910.pdf) · [Valve Magazine](https://valvemagazine.com/articles/an-update-on-u-s-valve-related-standards/) · [Accuris API 608](https://store.accuristech.com/api/products/preview/2098132)

## IEC 60534 / ISA-75 — Control valves (sizing, noise, leakage, face-to-face)

- **Scope**
  - IEC 60534 is a multi-part control valve series. **60534-2-1** is sizing equations for incompressible and compressible flow. **60534-8-3** is aerodynamic noise prediction. **60534-8-4** is hydrodynamic noise. **60534-4** is inspection and routine testing, including leakage **[8-4 and 4 general knowledge — verify]**. ISA-75.01.01 is the US sizing equivalent ([fluids docs](https://fluids.readthedocs.io/fluids.control_valve.html)).
- **Edition status**
  - IEC 60534-2-1:2011 (Ed. 2) ([standards.ie](https://shop.standards.ie/en-ie/standards/iec-60534-2-1-2011-564746_saig_iec_iec_1288444)). IEC 60534-8-3:2010 ([Neles manual](https://www.neles.com/flow-control-manual/gas-and-steam-flow/)). Check for newer editions.
  - **ANSI/ISA-75.08.01-2016 (R2025)** sets face-to-face dimensions for integral-flanged globe-style control valves, Classes 125–600, 15–400 mm (½–16 in) ([ISA](https://www.isa.org/products/ansi-isa-75-08-01-2016-r2025-face-to-face-dimensio); [ANSI](https://webstore.ansi.org/standards/isa/ansiisa7508012016r2025)). Other ISA-75.08.xx parts cover other end types and classes **[general knowledge — verify]**.
- **Key requirements & numbers**
  - **Kv = Cv / 1.156 (≈ 0.865 Cv)**. Kv is in m³/h of water at 1 bar ΔP. Cv is in US gpm at 1 psi ΔP ([valve sizing calculator](https://boq-eta.vercel.app/control-valve-sizing)). This is a non-authoritative source but the standard conversion.
  - Liquid choked flow is governed by **FL** (liquid pressure-recovery factor) and FF. Gas choking is governed by **xT** (pressure differential ratio factor). The `fluids` library implements IEC 60534 choked checks with defaults FL = 0.9, xT = 0.7 ([fluids docs](https://fluids.readthedocs.io/fluids.control_valve.html)).
  - Noise: many specs limit valve noise to **85 dB(A) at 1 m** downstream and 1 m from the pipe wall. This is a specification/occupational limit, *not* a value set by IEC 60534-8-3, which only provides the prediction method **[general knowledge — verify]**.
  - Typical sizing rule: valve travel at normal flow 60–80% open. Rangeability check at minimum flow ≥ ~10% open **[general knowledge — verify]**.
- **Project pitfalls / checks**
  - Flashing/cavitation service (e.g. LNG letdown, amine, produced water) needs special trims and hardened materials. Check FL/xT with the *installed* fitting factor Fp when reducers are used.
  - Face-to-face dimensions must match the piping layout. Ask vendors to confirm ISA-75.08.01 compliance on the datasheet.
- **Sources**: [fluids docs](https://fluids.readthedocs.io/fluids.control_valve.html) · [standards.ie IEC 60534-2-1](https://shop.standards.ie/en-ie/standards/iec-60534-2-1-2011-564746_saig_iec_iec_1288444) · [Neles](https://www.neles.com/flow-control-manual/gas-and-steam-flow/) · [ISA 75.08.01](https://www.isa.org/products/ansi-isa-75-08-01-2016-r2025-face-to-face-dimensio)

## ANSI/FCI 70-2 — Control valve seat leakage

- **Scope**
  - Defines seat leakage classes and test procedures for control valves. Equivalent concepts appear in IEC 60534-4. Editions 2006 and 2013 appear in sources ([Scribd FCI 70-2](https://www.scribd.com/document/418277281/ANSI-FCI-70-2-pdf); [controlandinstrumentation](https://controlandinstrumentation.com/resources/valve-leakage.html)).
- **Key requirements & numbers**

  | Class | Allowable leakage | Test medium / note |
  |---|---|---|
  | I | No test (by agreement) | — |
  | II | 0.5% of rated capacity | Air or water, Type A test |
  | III | 0.1% of rated capacity | Air or water |
  | IV | 0.01% of rated capacity | Air or water |
  | V | 5 × 10⁻⁴ ml/min water per inch of seat diameter per psi ΔP | Water at max service ΔP |
  | VI | Bubbles/min by port size, e.g. 1 in: 1 bubble (0.15 ml/min); 2 in: 3 (0.45); 4 in: 11 (1.70); 6 in: 27 (4.00) | Air/N₂, typically soft seat |

  Values from [Scribd FCI 70-2](https://www.scribd.com/document/418277281/ANSI-FCI-70-2-pdf), [SVF leakage classes](https://svf.net/wp-content/uploads/2021/10/ANSI-Leakage-Classes.pdf), [controlandinstrumentation](https://controlandinstrumentation.com/resources/valve-leakage.html) and [Wermac](https://wermac.org/valves/valve_leakage.html).
- **Project pitfalls / checks**
  - Class IV is typical metal-seat globe. Class V needs a high seat load or special seat design. Class VI is soft seat. Severe-service, high-temperature or erosive valves rarely keep Class VI in service.
  - Do not mix FCI 70-2 classes with API 598 or ISO 5208 isolation-valve leakage rates. They are different tests ([valvesonline comparison](https://www.valvesonline.com.au/blog/comparison-of-internationally-accepted-valve-leaka/)).
- **Sources**: as linked above.

## ASME PTC 19.3 TW-2016 — Thermowells

- **Scope**
  - Mechanical design of tapered, straight and stepped thermowells: wake-frequency (vortex shedding) resonance, steady and dynamic stress, pressure rating. It replaces PTC 19.3 TW-2010 and the 1974 Murdock-based method ([Scribd thermowell calc](https://www.scribd.com/document/442042576/Thermowell-calculation-pdf); [WIKA white paper](https://www.wika.com/media/Others/EN-US/wp017_thermowell_wakefrequency_en_us.pdf)).
- **Key requirements & numbers**
  - **Transverse resonance:** frequency ratio r = fs/fn,c must be **≤ 0.8** (the typical limit shown in calculations) ([WIKA datasheet](https://cn.shop.wika.com/upload/DS_IN0015_en_co_1353.pdf); [design calculator](https://designcalculators.netlify.app/thermowellwakefreq)).
  - **In-line resonance** (at about 2× the shedding frequency): generally keep **r < 0.4**. Passing through the in-line resonance band is allowed only if the **Scruton number Nsc > 2.5** (high damping, typically low-density gas) and the dynamic stress check is met ([design calculator](https://designcalculators.netlify.app/thermowellwakefreq); [Scribd](https://www.scribd.com/document/442042576/Thermowell-calculation-pdf)). The sources differ on the exact conditions (e.g. Re limits), so verify against the standard.
  - The in-line condition can govern at high velocity, with amplitude depending on the Scruton number ([Wikipedia: Thermowell](https://en.wikipedia.org/wiki/Thermowell)).
- **Project pitfalls / checks**
  - Calculations must use maximum flow velocity (including upset/startup), the actual nozzle standoff length (shielded length), and the support/installation compliance. Emerson and WIKA notes describe nozzle effects ([Emerson Exchange](https://emersonexchange365.com/products/measurement-instrumentation/f/level-pressure-temperature-tank-gauging/10755/thermowell-design-asme-ptc-19-3-tw)).
  - A failing calculation is usually fixed by shortening the immersion length, using a stepped or larger-root design, or (last resort) adding a velocity collar. Collars need tight bore fit and are discouraged by many clients.
- **Sources**: [WIKA white paper](https://www.wika.com/media/Others/EN-US/wp017_thermowell_wakefrequency_en_us.pdf) · [design calculator](https://designcalculators.netlify.app/thermowellwakefreq) · [Scribd](https://www.scribd.com/document/442042576/Thermowell-calculation-pdf) · [Wikipedia](https://en.wikipedia.org/wiki/Thermowell)

## ASME B16.5 / B16.47 / B16.34 / B16.10 / B31.3

- **ASME B16.5-2020** — Pipe flanges and flanged fittings, **NPS ½ to 24**. Classes 150, 300, 400, 600, 900, 1500, and 2500 (NPS ½–12 only for Class 2500) ([ASME scope PDF](https://asme.org/getmedia/5cc627a0-d379-4186-89b4-4f552381a98f/b16-5_pipe-flanges-and-flanged-fittings-2020.pdf); [BSI](https://knowledge.bsigroup.com/products/pipe-flanges-and-flanged-fittings-nps-1-2-through-nps-24-metric-inch-standard)). Some listings show 2020 as superseded — confirm the current edition.
- **ASME B16.47-2020** — Large-diameter steel flanges **NPS 26–60** (Series A and B) ([ANSI](https://webstore.ansi.org/standards/asme/asmeb16472020); [projectmaterials](https://blog.projectmaterials.com/quick-answers/epc/asme-b16-5-vs-b16-47/)).
- **ASME B16.34 (2020 cited)** — Valves (flanged, threaded, welding end). Classes 150, 300, 600, 900, 1500, 2500, 4500, in Standard Class and Special Class ([projectmaterials](https://blog.projectmaterials.com/quick-answers/valves/what-is-asme-b16-34/)). Group 1.1 (e.g. WCB) at −29 to 38 °C: **Class 150 ≈ 285 psig (19.6 bar), 300 ≈ 740 psig, 600 ≈ 1,480 psig (102.1 bar), 900 ≈ 2,220 psig, 1500 ≈ 3,705 psig** ([valve-world](https://valve-world.net/pressure-class-in-valves-and-flanges/); [Emerson ratings](https://www.emerson.com/is/content/emerson/en/final-control/isolation-valves/bu-content/documents/ISV-BLT-Pressure-Temperature-Ratings-ASME-16.34-VCBUL-04493-EN.pdf)).
- **ASME B16.10** — Face-to-face and end-to-end dimensions of (isolation) valves. Edition not confirmed **[general knowledge — verify]**. Control valves use ISA-75.08 instead.
- **ASME B31.3** — Process piping. It governs instrument piping/tubing, hook-ups up to the first block valve, and thermowell/branch connections. It is issued in even-numbered years (2022, 2024) **[general knowledge — verify]**.
- **Project pitfalls / checks**
  - Instrument flange ratings (e.g. DP transmitters with remote seals, flanged level instruments) must match the *piping class* rating at design temperature. Do not use the 38 °C rating.
  - Thermowell flange facing (RF/RTJ) and material must follow the piping class.
- **Sources**: [ASME B16.5 scope](https://asme.org/getmedia/5cc627a0-d379-4186-89b4-4f552381a98f/b16-5_pipe-flanges-and-flanged-fittings-2020.pdf) · [ANSI B16.47](https://webstore.ansi.org/standards/asme/asmeb16472020) · [projectmaterials B16.34](https://blog.projectmaterials.com/quick-answers/valves/what-is-asme-b16-34/) · [valve-world](https://valve-world.net/pressure-class-in-valves-and-flanges/)

## ISO 5167 — Differential pressure flow measurement

- **Scope**
  - **ISO 5167-1** (general principles), **-2** (orifice plates), **-3** (nozzles and Venturi nozzles), **-4** (Venturi tubes), **-5** (cone meters), **-6** (wedge meters). Part 2 is at the 2022 edition ([AFNOR](https://www.boutique.afnor.org/en-gb/standard/iso-516722022/measurement-of-fluid-flow-by-means-of-pressure-differential-devices-inserte/xs139600/326524); [EVS](https://www.evs.ee/en/evs-en-iso-5167-2-2022)). Parts 5 and 6 are **[general knowledge — verify]**.
- **Key requirements & numbers**
  - ISO 5167-2:2022 **does not cover** orifice plates in pipes **< 50 mm or > 1000 mm**, or at pipe **Re < 5000** ([EVS](https://www.evs.ee/en/evs-en-iso-5167-2-2022)). Tappings covered: corner, flange, and D and D/2. Vena contracta and pipe taps are not covered ([EVS](https://www.evs.ee/en/evs-en-iso-5167-2-2022)).
  - **Beta ratio:** the sources conflict (0.1–0.75 per the standard's limits of use vs a design practice of 0.2–0.7) ([automationforum](https://automationforum.co/orifice-sizing-guidelines-rules-associated-with-selection/); [projectmaterials](https://blog.projectmaterials.com/quick-answers/pipes/how-to-size-orifice-plate/)). Many EPC specs target **β 0.3–0.7** for good accuracy **[general knowledge — verify]**.
  - Straight-length requirements depend on beta and the upstream fitting (tables in Part 2). A flow conditioner can reduce them.
- **Project pitfalls / checks**
  - Check the minimum flow Re and DP. Rangeability of one DP transmitter is about 3:1–4:1 in flow, because flow varies with the square root of DP **[general knowledge — verify]**.
  - Custody transfer of gas by orifice in the US uses AGA 3 / API MPMS 14.3, not ISO 5167. Check which standard the client's metering spec invokes.
- **Sources**: [EVS](https://www.evs.ee/en/evs-en-iso-5167-2-2022) · [AFNOR](https://www.boutique.afnor.org/en-gb/standard/iso-516722022/measurement-of-fluid-flow-by-means-of-pressure-differential-devices-inserte/xs139600/326524) · [automationforum](https://automationforum.co/orifice-sizing-guidelines-rules-associated-with-selection/) · [projectmaterials](https://blog.projectmaterials.com/quick-answers/pipes/how-to-size-orifice-plate/)

## AGA 3 / 7 / 8 / 9 and API MPMS — Custody transfer

- **AGA Report No. 3** — Orifice metering of natural gas. It is also published as API MPMS Ch. 14.3 **[general knowledge — verify]** ([AGA store](https://store.accuristech.com/aga/pages/home)). The current edition year was not confirmed.
- **AGA Report No. 7** — Turbine meters for gas. Edition not confirmed **[general knowledge — verify]**.
- **AGA Report No. 8** — Compressibility/thermodynamic properties of natural gas. **Part 1 (3rd ed., 2017)** keeps the DETAIL and GROSS equations of the 1994 edition. **Part 2 (1st ed., 2017)** is based on **GERG-2008** ([NIST](https://www.nist.gov/node/560346); [NIST](https://www.nist.gov/node/554331)).
- **AGA Report No. 9** — Multipath ultrasonic gas meters. **3rd edition, July 2017**, replacing the 2nd edition (April 2007) ([ASGMT paper](https://asgmt.com/paper/an-overview-and-update-of-aga-9-3)).
- **API MPMS** (Manual of Petroleum Measurement Standards) — Ch. 4 proving systems (displacement, small-volume, tank and master-meter provers). Ch. 5 metering (displacement, turbine, Coriolis, ultrasonic). Ch. 21 electronic metering systems (21.1 gas, 21.2 liquid) ([MPMS list](https://www.scribd.com/document/442416166/kupdf-net-api-mpms-list)). **Ch. 12** = calculation of petroleum quantities and **Ch. 14.3** = orifice metering of natural gas are **[general knowledge — verify]**.
- **Project pitfalls / checks**
  - Middle East custody metering usually also needs OIML R117 (liquids) / R137 (gas) or national metrology approval, and a third-party witness. Check the client's metering spec **[general knowledge — verify]**.
  - Flow computers must implement the AGA 8 version (DETAIL vs GERG-2008) that the sales contract names.
- **Sources**: [ASGMT AGA 9](https://asgmt.com/paper/an-overview-and-update-of-aga-9-3) · [NIST AGA 8](https://www.nist.gov/node/560346) · [NIST](https://www.nist.gov/node/554331) · [MPMS list](https://www.scribd.com/document/442416166/kupdf-net-api-mpms-list)

## IEC 61131-3 — PLC programming languages

- **Scope / edition**
  - **IEC 61131-3:2025, edition 4.0**, published 22 May 2025 ([IEC webstore](https://webstore.iec.ch/en/publication/68533)). Annex B lists features added, removed or deprecated compared with the 2013 edition ([IEC webstore](https://webstore.iec.ch/en/publication/68533)).
- **Key requirements & numbers**
  - Languages: **Structured Text (ST), Ladder Diagram (LD), Function Block Diagram (FBD)**, plus **Sequential Function Chart (SFC)** elements for structuring. **Instruction List (IL)** was deprecated in Ed. 3 (2013) and removed in Ed. 4 (2025) ([open-exam-prep](https://open-exam-prep.com/study-guides/isa-cap/development-software-logic-programming/iec61131-programming-languages); [Wikipedia mirror](https://wiki.krisyotam.com/content/wikipedia_en_all_nopic_2026-03/IEC-61131-3)). Ed. 4 adds UTF-8 strings ([open-exam-prep](https://open-exam-prep.com/study-guides/isa-cap/development-software-logic-programming/iec61131-programming-languages)).
- **Project pitfalls / checks**
  - SIS application programs should use limited-variability languages (FBD/LD) per IEC 61511 practice **[general knowledge — verify]**. Avoid IL in new code.
- **Sources**: [IEC webstore](https://webstore.iec.ch/en/publication/68533) · [open-exam-prep](https://open-exam-prep.com/study-guides/isa-cap/development-software-logic-programming/iec61131-programming-languages)

## Fieldbus and digital protocols: IEC 61158 / FOUNDATION Fieldbus, PROFIBUS, Modbus

- **FOUNDATION Fieldbus H1** (IEC 61158-2 physical layer)
  - **31.25 kbit/s**, Manchester-coded, twisted pair. The same physical layer as PROFIBUS PA ([Wikipedia FF H1](https://en.wikipedia.org/wiki/Foundation_Fieldbus_H1); [Siemens](https://mall.industry.siemens.com/mall/en/WW/Catalog/Products/10573184)).
  - Max **1900 m** total trunk + spurs per segment. Up to 4 repeaters extend this to 9500 m ([Wikipedia FF H1](https://en.wikipedia.org/wiki/Foundation_Fieldbus_H1)).
  - Up to **32 devices** per segment in theory. Typically **8–12** in practice ([Siemens](https://mall.industry.siemens.com/mall/en/WW/Catalog/Products/10573184)). Realistically up to about 16 on IS segments ([Phoenix Contact](https://assets.phoenixcontact.com/file/6135ba71-1c3d-4cf3-a479-bc698960161b/media/original)).
  - Spurs up to **120 m** ([Siemens](https://mall.industry.siemens.com/mall/en/WW/Catalog/Products/10573184)). FISCO total cable length depends on gas group (about 1 km for IIC, 1.9 km for IIB/IIA per a Wikipedia summary) ([Wikipedia FF H1](https://en.wikipedia.org/wiki/Foundation_Fieldbus_H1)).
  - **Pitfall**: many Aramco/QatarEnergy projects limit devices per segment (e.g. ≤ 12–16) and forbid putting redundant control loops or SIS functions on one segment. Check the client fieldbus design spec **[general knowledge — verify]**.
- **PROFIBUS** **[general knowledge — verify]**
  - PROFIBUS DP uses RS-485 at up to 12 Mbit/s (length falls as speed rises). PROFIBUS PA uses IEC 61158-2 MBP at 31.25 kbit/s and is often coupled to DP. Common for MCC/electrical and packaged units.
- **Modbus** **[general knowledge — verify]**
  - Modbus RTU (serial RS-485/RS-232) and Modbus TCP (TCP port 502). Master/slave (client/server) polling. Typical for package PLC ↔ DCS interfaces, often with redundant links. No built-in security, so place it in an IEC 62443 zone with conduit protection.
- **Sources**: [Wikipedia FF H1](https://en.wikipedia.org/wiki/Foundation_Fieldbus_H1) · [Siemens](https://mall.industry.siemens.com/mall/en/WW/Catalog/Products/10573184) · [Phoenix Contact](https://assets.phoenixcontact.com/file/6135ba71-1c3d-4cf3-a479-bc698960161b/media/original) · [Fluke](https://fluke.com/en-in/learn/blog/oscilloscopes/foundation-fieldbus-system-and-diagnostic-basics)

## HART and WirelessHART (IEC 62591)

- **Wired HART**
  - Bell 202 **FSK** superimposed on 4–20 mA ([Phoenix Contact](https://assets.phoenixcontact.com/file/827bc9d6-1e7b-4a5d-8746-386b9233b3e3/media/original)). **1200 bit/s**. Logic 1 = **1200 Hz**, logic 0 = **2200 Hz** ([HART intro document](https://kolegite.com/EE_library/books_and_lectures/%D0%A6%D0%B8%D1%84%D1%80%D0%BE%D0%B2%D0%B0%20%D1%81%D1%85%D0%B5%D0%BC%D0%BE%D1%82%D0%B5%D1%85%D0%BD%D0%B8%D0%BA%D0%B0/%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D1%84%D0%B5%D0%B9%D1%81%D0%B8/HART.pdf)).
  - Loop resistance **230–1100 Ω** must be present for communication ([HART intro document](https://kolegite.com/EE_library/books_and_lectures/%D0%A6%D0%B8%D1%84%D1%80%D0%BE%D0%B2%D0%B0%20%D1%81%D1%85%D0%B5%D0%BC%D0%BE%D1%82%D0%B5%D1%85%D0%BD%D0%B8%D0%BA%D0%B0/%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D1%84%D0%B5%D0%B9%D1%81%D0%B8/HART.pdf)). **250 Ω** is the common practical value ([Siemens application note](https://cache.industry.siemens.com/dl/files/810/109783810/att_1038663/v1/AG012712.pdf); [open-exam-prep](https://open-exam-prep.com/study-guides/isa-ccst-i/signal-transmission-fieldbus/hart-smart-transmitters)).
- **WirelessHART (IEC 62591)**
  - IEEE 802.15.4 radio in the **2.4 GHz** band. Time-synchronized, self-organizing, self-healing **mesh**. Frequency hopping with channel blacklisting. About 10 dBm nominal transmit power. Field devices act as routers ([Wikipedia WirelessHART](https://en.wikipedia.org/wiki/WirelessHART); [control.com](https://control.com/textbook/wireless-instrumentation/wirelesshart/)). Latest IEC edition cited as IEC 62591:2016 ([Wikipedia](https://en.wikipedia.org/wiki/WirelessHART)).
- **Project pitfalls / checks**
  - SIS input cards with HART pass-through: make sure HART write commands cannot change SIS transmitter configuration (write-protect jumper/lock).
  - Wireless is normally limited to monitoring and non-critical uses, not SIS or fast control loops, on Middle East projects **[general knowledge — verify]**. Check spectrum licensing (CITC Saudi / CRA Qatar) **[general knowledge — verify]**.
- **Sources**: as linked above.

## IEC 62443 — OT cybersecurity

*No web confirmation was obtained for this section (search budget exhausted). Everything below is **[general knowledge — verify]**.*

- **Scope**: A series for Industrial Automation and Control Systems (IACS) security, covering asset owners, system integrators and product suppliers.
- **Key parts**: 1-1 (concepts/models), 2-1 (asset owner security program), 2-3 (patch management), 2-4 (service provider requirements), 3-2 (security risk assessment and **zones & conduits**), 3-3 (system security requirements and security levels), 4-1 (secure product development lifecycle), 4-2 (component technical requirements).
- **Key requirements & numbers**
  - **Seven foundational requirements (FR)**: identification & authentication control, use control, system integrity, data confidentiality, restricted data flow, timely response to events, resource availability.
  - **Security levels (SL)**: SL 1 protects against casual or coincidental violation. SL 2 protects against intentional violation by simple means with low resources. SL 3 protects against sophisticated means with moderate resources and IACS-specific skills. SL 4 protects against sophisticated means with extended resources. Each zone gets a target SL (SL-T), which is compared with the achieved (SL-A) and capability (SL-C) levels.
- **Project pitfalls / checks**
  - Saudi Aramco requires compliance with its own cybersecurity standards, e.g. SACS-002 for third parties **[general knowledge — verify]**. Saudi NCA OTCC controls also apply in KSA **[general knowledge — verify]**. QatarEnergy has its own requirements. The IEC 62443 SL-T per zone should be agreed early in the project.
  - The SIS should be in its own zone. Engineering workstation access to the SIS needs explicit conduit controls.
- **Sources**: none confirmed in this research pass. See [Gaps](#gaps).

## NAMUR NE 43, NE 107, NE 95 (and related)

### NE 43 — Standardization of the signal level for failure information of digital transmitters
- **Key requirements & numbers**
  - **Measurement information: 3.8 mA to 20.5 mA**. The 3.8–4 mA and 20–20.5 mA bands show saturation (out of range but measuring) ([Beckhoff](https://infosys.beckhoff.com/content/1033/el3182/4004665227.html); [Jumo manual](https://www.manualslib.com/manual/1436749/Jumo-Mtron-T.html?page=35)).
  - **Failure information: ≤ 3.6 mA (downscale) or ≥ 21.0 mA (upscale)** ([Beckhoff](https://infosys.beckhoff.com/content/1033/el3182/4004665227.html)).
  - The 3.6–3.8 mA and 20.5–21 mA bands are undefined and can be used for diagnostic indication ([Analog Devices](https://ez.analog.com/ez-blogs/b/engineerzone-spotlight/posts/functional-safety-of-4-20ma-networks)).
- **Project pitfalls / checks**
  - Some vendors' "high alarm" default is ≥ 21.75 mA or ~22.5 mA (vendor-specific). Configure DCS/SIS input fault thresholds to match ([industrialmonitordirect](https://industrialmonitordirect.com/blogs/knowledgebase/4-20ma-signal-below-4ma-namur-ne43-standards-fail-safe-levels)).
  - Transmitter burnout direction (high or low) must be chosen per SIF so that a transmitter failure drives the loop toward the trip, or at least raises a diagnostic alarm with a defined action in the SRS.

### NE 107 — Self-monitoring and diagnosis of field devices **[general knowledge — verify]**
- Four standard status signals: **F (Failure)**, **C (Function check)**, **S (Out of specification)**, **M (Maintenance required)**, each with a standard colour/symbol. Device-specific diagnostics are mapped to these categories so that the operator sees a uniform view. They are used in FF, PROFIBUS PA and HART 7 asset management.

### NE 95 **[general knowledge — verify]**
- NE 95 is generally understood as "Basic principles of homologation" (NAMUR's approach to qualifying and approving devices for use in member companies' plants). The exact title and content could not be confirmed. Other NAMUR recommendations often cited in specs: **NE 21** (EMC requirements for process control equipment) and **NE 53** (software/firmware revision handling of field devices) **[general knowledge — verify]**.
- **Sources**: [Beckhoff NAMUR](https://infosys.beckhoff.com/content/1033/el3182/4004665227.html) · [Jumo](https://www.manualslib.com/manual/1436749/Jumo-Mtron-T.html?page=35) · [Analog Devices](https://ez.analog.com/ez-blogs/b/engineerzone-spotlight/posts/functional-safety-of-4-20ma-networks) · [electricalvolt](https://www.electricalvolt.com/what-is-namur-ne-43)

## IEC 60751 (RTD) and IEC 60584 (thermocouples)

*No web confirmation was obtained. All values are **[general knowledge — verify]**.*

- **IEC 60751 — Industrial platinum resistance thermometers**
  - Pt100: R₀ = 100 Ω at 0 °C, α = 0.00385 /°C (Callendar–Van Dusen coefficients). The current edition is believed to be 2022 (Ed. 3) — verify.
  - Tolerance classes (wire-wound / film ranges differ):
    - Class AA: ±(0.10 + 0.0017|t|) °C
    - Class A: ±(0.15 + 0.002|t|) °C
    - Class B: ±(0.30 + 0.005|t|) °C
    - Class C: ±(0.60 + 0.010|t|) °C
  - **Pitfalls**: use 3-wire minimum, 4-wire for high accuracy or long runs (custody, reactor beds). The class is valid only within its stated temperature range (e.g. class A is not valid up to 600 °C for thin-film elements). Duplex elements are often specified for critical services.
- **IEC 60584 — Thermocouples**
  - 60584-1: EMF tables and tolerances. 60584-3: extension and compensating cables (tolerances and colour codes).
  - Type K tolerance: Class 1 ±1.5 °C or ±0.004|t| (−40 to 1000 °C). Class 2 ±2.5 °C or ±0.0075|t| (−40 to 1200 °C), whichever is greater.
  - IEC 60584-3 colour code: the positive conductor and sheath have the type colour and the negative is white. K = green, J = black, T = brown, N = pink, E = violet, R/S = orange. Never mix ANSI MC96.1 colours (K yellow/red) with IEC on one project.
  - **Pitfalls**: use type K for general high temperature and type N for better stability above ~1000 °C. Use mineral-insulated (MI) cable in fired heaters and reactors. Choose grounded vs ungrounded junction to match the input card isolation.

## EN 837 — Pressure gauges

*No web confirmation was obtained. All values are **[general knowledge — verify]**.*

- **Scope**: EN 837-1 Bourdon tube gauges, EN 837-2 selection and installation recommendations, EN 837-3 diaphragm and capsule gauges.
- **Key numbers**: nominal sizes (NS) 40, 50, 63, 80, 100, 160, 250 mm. Accuracy classes 0.1, 0.25, 0.6, 1.0, 1.6, 2.5, 4.0 (% of span). For safety-pattern gauges, the "S3" design has a solid baffle wall and blow-out back.
- **Pitfalls**: select the range so normal operating pressure is in the middle third of the scale (about 25–75% of full scale for steady pressure). Use pulsation dampers or liquid filling on pumps and compressors. Use diaphragm seals for corrosive, viscous or sour service. Many client specs require NS 100 or 150 mm, class 1.0 and S3 safety pattern.

## Cables: IEC 60331 / 60332 / BS EN 50288-7 and related

*No web confirmation was obtained. All items are **[general knowledge — verify]**.*

- **IEC 60331** — Fire resistance / **circuit integrity** under fire. IEC 60331-21 (cables up to 0.6/1 kV) applies a flame at ≥ 750 °C for typically 90 min, and the circuit must keep working. Cables > 20 mm diameter are tested to 60331-1 (830 °C, with mechanical shock). Used for ESD/SIS, F&G, PA/GA, emergency lighting and fire-safe valve actuators that must work during a fire.
- **IEC 60332** — Flame propagation (fire retardant). **60332-1** (single vertical wire/cable). **60332-3** (bunched cables, categories A/B/C/D by non-metallic volume per metre). Most Middle East specs require 60332-3 Cat A or C for instrument cable.
- **Related**: IEC 61034 (smoke density), IEC 60754-1/-2 (halogen acid gas / corrosivity) for LSZH cables in buildings and enclosed modules.
- **BS EN 50288-7** — Multi-element metallic cables for analogue and digital communication and control, sectional specification for **instrumentation and control cables**. It replaced the old BS 5308 for many projects. Typical construction: Cu stranded conductors 0.5–1.5 mm², pairs/triads with individual and overall screens (Al/PET with drain wire), PVC/XLPE insulation, armour (SWA/GSWB) for direct burial or tray, and lead sheath or extra protection where hydrocarbon contamination is possible.
- **Pitfalls**: specify cable capacitance and inductance (pF/m, µH/m) on datasheets for IS loop calculations. Fieldbus cable must be Type A (100 Ω, 31.25 kHz). Lead sheath is often required in process areas with hydrocarbon soaking risk (e.g. Aramco) — check the project spec.

## Earthing / grounding: IEC 60364 and intrinsically safe earth

*No web confirmation was obtained. All items are **[general knowledge — verify]**.*

- **IEC 60364** — Low-voltage electrical installations (earthing systems TN/TT/IT, protective earthing, equipotential bonding). I&C ties into it through the plant earth grid.
- **Instrument earthing practice**: separate **instrument clean earth** (signal reference/screens) and **IS earth** bars in marshalling and system cabinets, connected to the plant earth grid at a single point. Cable screens are earthed at **one end only** (usually the control room/system end) to avoid ground loops.
- **IS earth (IEC 60079-14)**: shunt-diode (Zener) barriers need a dedicated, insulated IS earth conductor. The commonly cited resistance from barrier bar to the main earth point is **≤ 1 Ω**, with redundant conductors of ≥ 4 mm² Cu each. Galvanically isolated barriers generally do not need an IS earth.
- **Pitfalls**: never bond screens at both ends unless the system is designed for it (e.g. some fieldbus capacitive earthing schemes). Check junction box screen continuity and insulation of screen drains.

## NFPA 70 and NFPA 72

*No web confirmation was obtained. All items are **[general knowledge — verify]**.*

- **NFPA 70 (NEC)** — US National Electrical Code, on a 3-year cycle (2020, 2023, 2026). Relevant for Class/Division (Art. 500–504), Zones (505), and IS installation (Art. 504). On Middle East projects it is usually *not* the governing code (IEC 60079-14 governs) unless the client specifies US practice. Some Aramco electrical standards reference NEC **[verify]**.
- **NFPA 72** — National Fire Alarm and Signaling Code (2022 edition believed current). It covers fire alarm control panels, detector spacing, notification appliances and survivability. It is often referenced in Aramco fire & gas and building fire alarm specs, while IEC 60079-29 / EN 54 cover gas detection and building detection respectively.
- **Pitfalls**: F&G systems for process areas are typically designed to performance-based mapping (ISA-TR84.00.07) rather than NFPA 72 prescriptive spacing. Confirm which applies.

## NACE MR0175 / ISO 15156 — Sour service materials

*No web confirmation was obtained. All items are **[general knowledge — verify]**.*

- **Scope**: Materials for use in H₂S-containing environments in oil and gas *production* (Part 1 general principles, Part 2 carbon and low-alloy steels and cast irons, Part 3 CRAs and other alloys). Refinery sour service is usually NACE MR0103 / ISO 17945.
- **Key numbers**: sour service applies when the H₂S partial pressure ≥ **0.3 kPa (0.05 psia)** in the gas phase. Carbon steel hardness limit **22 HRC (≈ 250 HV)**. CRA limits depend on environment (temperature, pH₂S, chloride, pH, elemental sulfur).
- **I&C relevance**: wetted parts of transmitters (diaphragms, flanges, bolting), control valve trims and bodies, tubing (316L limits), compression fittings, thermowells, PSV springs and bolting.
- **Pitfalls**: a vendor statement of "NACE compliant" is not enough. Require material certificates (EN 10204 3.1) and the specific Part/Table/environmental limit used. Bolting exposed to the atmosphere vs buried/insulated has different requirements.

## IEC 61326 — EMC for measurement and control equipment

*No web confirmation was obtained. All items are **[general knowledge — verify]**.*

- **Scope**: EMC immunity and emission requirements for electrical equipment for measurement, control and laboratory use. **61326-1** is general. **61326-2-3** is transducers with integrated or remote signal conditioning (transmitters). **61326-3-1/-3-2** are immunity for safety-related functions (functional safety EMC).
- **Pitfalls**: SIL-rated transmitters should demonstrate 61326-3-x immunity. Specify walkie-talkie (radio) immunity in control rooms and field. NAMUR NE 21 is often cited as a stricter EMC recommendation.

## IEC 62682 / ISA-18.2 — Alarm management

*No web confirmation was obtained. All items are **[general knowledge — verify]**.*

- **Scope**: Alarm management lifecycle: philosophy, identification, rationalization, detailed design, implementation, operation, maintenance, monitoring and assessment, MOC and audit. IEC 62682 is the international adoption of ANSI/ISA-18.2. ISA-18.2 was revised in 2016. IEC 62682 Ed. 2 was published around 2022 — verify.
- **Key numbers (performance benchmarks, from ISA-18.2/EEMUA 191)**: average alarm rate ~**1 per 10 min** (≈ 6/hour, ≈ 150/day) per operator is "very likely acceptable". ~2 per 10 min (≈ 12/hour, ≈ 300/day) is "maximum manageable". An **alarm flood** is > 10 alarms in 10 min. Priority distribution target ~**80% low / 15% medium / 5% high**. Stale alarms, chattering alarms and suppressed alarms must be tracked.
- **Pitfalls**: every alarm needs a documented operator action and consequence (master alarm database). Do not configure an alarm on every DCS tag by default. SIS pre-trip alarms must be rationalized consistently with the SRS.

## ISA-101 — HMI

*No web confirmation was obtained. All items are **[general knowledge — verify]**.*

- **Scope**: ANSI/ISA-101.01-2015, HMIs for process automation systems. It covers the HMI philosophy, style guide, display hierarchy, and lifecycle.
- **Key concepts**: display hierarchy **Level 1** (overview/area), **Level 2** (unit control), **Level 3** (detail/equipment), **Level 4** (diagnostic/support). "High-performance HMI" practice: grey backgrounds, colour reserved for abnormal conditions and alarms, analog indicators with normal-range bands.
- **Pitfalls**: the HMI style guide must be agreed with the client before graphics development starts. Aramco and QatarEnergy often have their own colour and symbol standards.

## IEC 61850 — Substation communication (I&C interface)

*No web confirmation was obtained. All items are **[general knowledge — verify]**.*

- **Scope**: Communication networks and systems for power utility automation (substations). In oil & gas it is relevant for the **Electrical Control and Monitoring System (ECMS/ENMC)** and its interface to the DCS: IEDs (protection relays) use MMS for client/server data and **GOOSE** for fast peer-to-peer trips/interlocks. Network redundancy uses PRP/HSR (IEC 62439-3).
- **Pitfalls**: the DCS ↔ ECMS interface (often via IEC 61850 gateway, or Modbus TCP / OPC) must be specified for data points, time sync (IEEE 1588 PTP or SNTP) and cybersecurity zoning. Load-shedding signals are often hardwired in addition for reliability.

---

## Gaps

What could not be confirmed in this research pass. The web search budget was exhausted partway through, and direct page fetching (e.g. Wikipedia) was blocked by the session network:

1. **IEC 62443** — parts, security level definitions and foundational requirements are general knowledge only. No source URL was obtained.
2. **NAMUR NE 107 and NE 95** — the NE 107 status categories (F/C/S/M) are general knowledge. The title and scope of **NE 95** are uncertain. NE 21 and NE 53 are not confirmed.
3. **IEC 60751 / IEC 60584 / EN 837** — tolerance formulas, temperature ranges, colour codes, accuracy classes and current edition years were not web-verified.
4. **Cable standards (IEC 60331, 60332, 61034, 60754, BS EN 50288-7)**, **IEC 60364 / IS earth ≤ 1 Ω**, **NFPA 70/72 editions**, **NACE MR0175/ISO 15156 thresholds (0.3 kPa, 22 HRC)**, **IEC 61326**, **ISA-18.2/IEC 62682 benchmark rates**, **ISA-101**, **IEC 61850** — all general knowledge, no source URLs.
5. **ISA-5.2/5.4/5.5 and ISA-20/TR20.00.01** — editions and content not confirmed.
6. **Edition currency uncertainties**: API RP 505 (2018 vs 2025), API RP 553 3rd edition year, API RP 555 status, API 556 partial replacement by RP 556-5 (2026), API 670 (still 5th ed. 2014?), API 609 current edition, API 600 after 13th ed., API 598 2023 edition, ASME B16.5/B16.34/B16.10/B31.3 current editions, IEC 60534-2-1 and 8-3 newer editions, IEC 61511 edition 3 status, AGA 3 and AGA 7 editions.
7. **Numerical items that need the standard text**: API 527 Table 6 metal-seat bubble limits; ISO 5167-2 beta-ratio limits (sources disagree: 0.1–0.75 vs 0.2–0.75); PTC 19.3 TW in-line resonance conditions (Scruton number / Reynolds number limits); intermediate API 526 orifice areas (E–R); SIL PFH bands for high demand; IP67 30-minute test duration; EPL by protection-type mapping table; API 2350 default response times (secondary source only); NEC 505.7 Zone/Division boundary rule (sources conflict).
8. **Client-specific overlays** (Saudi Aramco SAES/SAMSS, QatarEnergy standards, SASO/SABER, NCA OTCC) are mentioned only as pointers. They were not researched and must be checked in the client's document set.
