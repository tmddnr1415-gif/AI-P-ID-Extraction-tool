# Saudi Aramco Instrumentation & Control (I&C) Standards and Practice

> Knowledge-base file 02 · Topic: Saudi Aramco I&C engineering standards (SAES-J, SAES-Z, 34-SAMSS, 23-SAMSS, SAEP, SAIC) and typical project practice on oil & gas EPC work.
> Compiled: November 2026. Research method: public web search only (no access to Aramco's controlled standards library).

---

## 0. How to use this file / confidentiality note

**What this file is.** A map of the Saudi Aramco I&C document system. For each document it gives the number, title, scope and the requirements that are described in public sources. Use it to:

- identify which Aramco document governs a question (for example, "which spec covers outdoor instrument cabinets?" The answer is 34-SAMSS-821);
- explain how the documents relate to each other (SAES vs SAMSS vs SAEP vs SAIC vs 9COM);
- flag typical review comments and pitfalls;
- tell the engineer which items need checking against the project's controlled copy.

**What this file is NOT.** It is not a substitute for the controlled documents. Saudi Aramco Engineering Standards (SAES), Materials System Specifications (SAMSS), Engineering Procedures (SAEP), Standard Drawings, Instrument Specification Sheets (ISS) and Inspection Checklists (SAIC) are proprietary. Aramco releases them to contractors and vendors under contract. The copies that circulate on document-sharing sites (Scribd, pdfcoffee and similar) are unofficial, often out of date, and must never be used as the project basis. **This file paraphrases. It does not reproduce clause text.** Revision dates quoted here come from whichever copy surfaced publicly and are usually superseded.

**Confidence tags used throughout:**

| Tag | Meaning |
|---|---|
| **[confirmed]** | Number and title (and the described content) appear consistently in two or more independent public sources, or in an official aramco.com / vendor approval document. |
| **[secondary source]** | Found only in second-hand material: Scribd/pdfcoffee listings or snippets, forums, blogs, training modules, cross-references inside other unofficial copies. Probably correct, but check it. |
| **[general knowledge — verify]** | From the compiler's background knowledge of Aramco practice and **not** confirmed during this research. Treat it as a hypothesis. |
| **[unverified]** | Document number or title that the brief asked about but that no source confirmed. The number may not exist or may cover something else. |

**Chatbot rule of thumb:** when you answer from this file, always name the document number, say that the user must check the current revision in the project's Aramco document set (or with the Aramco PMT / Consulting Services Department), and pass on the confidence tag. Never invent clause numbers. Clause numbers cited below are only those that appeared in public excerpts.

**Research limitation:** WebFetch was blocked for most hosts, including scribd.com mirrors, pdfcoffee.com and ask.instrumentationtools.com. All findings therefore come from search-engine snippets and summaries. The shared web-search budget ran out before the per-measurement standards (J-100/200/300/400) could be researched in depth. See Section 8, "Gaps".

**Update (second research pass, November 2026):** a follow-up pass (about 37 searches) added clause-level items for SAES-J-100, J-200, J-300 and J-400, FF segment-length limits from SABP-J-900, the titles of SAES-J-602, SAES-J-905 and 34-SAMSS-911, the SAEP-302 waiver and SAEP-303 review procedures, and several standard drawing numbers. WebFetch still failed for scribd.com, pdfcoffee.com, aramco.com and the pages.dev mirror (DNS failure), so these items also come from search-result snippets of unofficial copies and are tagged **[secondary source]** unless stated otherwise. Items added in this pass are marked *(2nd pass)*.

---

## Table of contents

1. [Document system overview](#1-document-system-overview)
2. [Index table of I&C documents](#2-index-table-of-ic-documents)
3. [Per-topic requirements](#3-per-topic-requirements)
   - 3.1 Instruments general / basic design criteria
   - 3.2 Symbols, identification, drawings and forms
   - 3.3 Flow measurement
   - 3.4 Pressure
   - 3.5 Level
   - 3.6 Temperature
   - 3.7 Analyzers and gas detection
   - 3.8 Control valves
   - 3.9 ESD / ZV / emergency isolation and SIS
   - 3.10 Pressure relief devices (PSV/PZV) and surge relief
   - 3.11 Valve actuators: MOV, pneumatic, hydraulic
   - 3.12 Panels, cabinets, packaged units and control buildings
   - 3.13 Power, wiring and grounding for instrumentation
   - 3.14 Intrinsic safety and hazardous-area practice
   - 3.15 FOUNDATION fieldbus
   - 3.16 DCS / PCS / SCADA / networks
   - 3.17 Cybersecurity
4. [Vendor approval: 9COM, RVL and plant approval](#4-vendor-approval-9com-rvl-and-plant-approval)
5. [iKTVA and localization](#5-iktva-and-localization)
6. [Project execution, design review and inspection](#6-project-execution-design-review-and-inspection)
7. [Typical Aramco review comments / pitfalls](#7-typical-aramco-review-comments--pitfalls)
8. [Gaps and open items](#8-gaps-and-open-items)
9. [Source list](#9-source-list)

---

## 1. Document system overview

### 1.1 Document families

| Family | What it is | I&C relevance |
|---|---|---|
| **SAES-x-nnn** (Saudi Aramco Engineering Standard) | Mandatory design and installation requirements, grouped by letter. **J = Instrumentation**, **Z = Process control / automation**, B = loss prevention / safety, P = electrical, T = telecom, A = general/drawings, K = mechanical/HVAC, L = piping. | SAES-J-xxx and SAES-Z-xxx are the core I&C set. SAES-B-058 (ESD/isolation/depressuring), SAES-B-068 (electrical area classification), SAES-P-103 (batteries/UPS) and SAES-P-111 (grounding) are frequent cross-references. [confirmed: J-001 index and cross-references, see §2] |
| **nn-SAMSS-nnn** (Materials System Specification) | Purchase specifications for equipment. The number prefix matches the SAMS materials class. **34 = instrumentation** (valves classified under "SAMS Class 34" include control, safety-relief, surge-relief and solenoid valves). **23 = process automation systems** (DCS, SCADA). | Bound into purchase orders and vendor requisitions. 04-SAMSS-035 (general valves) explicitly excludes valves classified under SAMS Class 34. [secondary source] ([scribd 04-SAMSS-035](https://es.scribd.com/document/382959447/04-SAMSS-035-ARAMCO-General-Reuirement-for-Valves-pdf)) |
| **SAEP-nnn** (Saudi Aramco Engineering Procedure) | Procedures for project execution, reviews, waivers, vendor evaluation, relief-valve programmes and similar. | SAEP-1400 (instrumentation vendor technical evaluation tied to 9COMs), SAEP-15 (process automation Restricted Vendor Lists), SAEP-318 (relief valve programme), SAEP-99 (network security). [secondary source] |
| **SABP-x-nnn** (Saudi Aramco Best Practice) | Non-mandatory guidance. | SABP-J-900 (FF/hazardous-area practice), SABP-Z-002, SABP-Z-019, SABP-Z-057 (network security) and others. [secondary source] |
| **SAIC-x-nnnn / SATIP** (Inspection Checklists / Typical Inspection Plans) | Field and QC checklists that cite the SAES/SAMSS clauses they verify. | SAIC-J-6xxx series for instrumentation, for example SAIC-J-6022 (packaged units), SAIC-J-6904 (IS systems) and SAIC-J-6806 (ESD and power supply). [secondary source] |
| **ISS / Form 8020-nnn-ENG** (Instrument Specification Sheets) | Aramco standard data-sheet forms, numbered after the matching SAMSS. | For example, ISS 8020-611-ENG for conventional and balanced PRVs, matching 34-SAMSS-611. [secondary source] ([scribd SAEP-318](https://www.scribd.com/document/473260773/SAEP-318-pdf)) |
| **Standard Drawings (AA-/AB-/AC-/AD- numbers) and Library Drawings (DB-…)** | Standard installation details. | Hook-ups and installation details are listed in the SAES-J-001 index. Instrument-related standard drawings seen cited *(2nd pass)*: **AC-036413 / AB-036414** (orifice flange tap connections, cited by SAES-J-100 2009), **AB-036019** "Thermowell – Assembly and Detail" (cited by SAES-J-100 2020), **AB-036521** (valve bracing, cited by an SAIC inspection checklist; which SAIC was not identified). Library drawings: **DB-950046** "Instrument Piping Detail for Liquid Level Gauge Glasses" and **DB-950047** (pneumatic level instruments), both cited by SAES-J-100. SAES-J-200 refers to "Saudi Aramco Library Drawings" for typical pressure installations without naming them in the snippet. The 036xxx series therefore holds at least some instrument details, but the meaning of the AA/AB/AC/AD prefix (probably sheet size) was not confirmed. [secondary source] ([scribd J-100](https://www.scribd.com/document/494872706/SAES-J-100), [pdfcoffee J-100](https://pdfcoffee.com/saes-j-100-pdf-free.html), [scribd SAIC-J-6022](https://www.scribd.com/document/444577400/SAIC-J-6022-Rev-0), [scribd J-200](https://www.scribd.com/document/439171375/SAES-J-200-Pressure)) |
| **GI (General Instructions)** | Corporate procedures, for example GI 2.102 on pressure testing safely and GI 1603.000 on importing communications equipment. | Indirect relevance to I&C. [secondary source] |
| **SACS-002** | Saudi Aramco Third Party Cybersecurity Standard, published by Aramco for suppliers and contractors. | Cyber requirements on contractors and vendors. [confirmed: hosted on aramco.com] ([SACS-002](https://SaudiAramco.com/-/media/downloads/working-with-us/ccc/sacs-002-third-party-cybersecurity-standard.pdf)) |

### 1.2 Document responsibility and revision cycle

- Each SAES/SAMSS shows a "Document Responsibility" committee on its cover. The J-series and the 34-SAMSS instrument specifications are owned by the **Instrumentation Standards Committee**. The Z-series is owned by **Process Control** (Process Control Standards Committee). [secondary source] ([scribd 34-SAMSS-711](https://www.scribd.com/document/468687176/34-SAMSS-711-pdf), [scribd SAES-Z-002](https://www.scribd.com/doc/239724008/Saes-z-002-Locked-by-Badr))
- Every document has an Issue Date and a **Next Planned Update**, typically 3 to 5 years later. Documents are periodically "reaffirmed" with editorial changes. Example: SAES-J-001 was reaffirmed in December 2011 with editorial changes that added SAES-J-905 and 34-SAMSS-911 to the index. [secondary source] ([pdfcoffee SAES-J-001](https://pdfcoffee.com/saes-j-001-3-pdf-free.html))
- **Practical consequence:** the governing revision is the one listed in the project's contract (Schedule Q / Project Specification document list), not the latest one you can find. [general knowledge — verify]

### 1.3 SAES-J-001: the index

SAES-J-001 "Instrumentation Index" compiles the Saudi Aramco documents (SAES, SAMSS, forms and standard drawings) that govern the design and installation of instrumentation. It contains no technical requirements of its own; its job is to point to the other documents. Public copies are dated 31 Dec 2003, 24 Aug 2008, 10 Dec 2011 and 16 Feb 2013. **Use the current J-001 as the master list for "which Aramco I&C documents apply".** [confirmed] ([pdfcoffee J-001 2013](https://pdfcoffee.com/saes-j-001-3-pdf-free.html), [scribd J-001](https://www.scribd.com/document/680621562/SAES-J-001), [kishorekaruppaswamy J-001 2003 copy](https://kishorekaruppaswamy.wordpress.com/wp-content/uploads/2011/10/saudi-arabian-engineering-standardssaes-j-001.pdf))

### 1.4 Project-specific variants

Large joint-venture projects have issued project-prefixed versions of Aramco standards. Yanbu Export Refinery (YASREF), for example, issued "YERP-SAES-J-601", "YERP-SAES-J-904" and a YERP document replacing SAES-B-058. These say that all Saudi Aramco standards apply "except as noted". On JV or affiliate projects (SASREF, SATORP, YASREF, Sadara, Jazan and others), check whether the project's own variant overrides the base SAES. [secondary source] ([scribd YERP-PE-YSS-0048](https://es.scribd.com/document/178151012/100-YER-PE-YSS-0048), [scribd YERP FF spec](https://www.scribd.com/doc/142169992/192-YER-PE-I35-0011))

### 1.5 Waivers

A deviation from a mandatory SAES/SAMSS requirement needs a formal waiver. The waiver procedure is **SAEP-302** ("Instructions for Obtaining a Waiver of a Mandatory Saudi Aramco Engineering Requirement"). [secondary source — upgraded from general knowledge in the 2nd pass] ([scribd SAEP-302](https://www.scribd.com/document/683056429/SAEP-302), [scribd SAEP-302 older](https://www.scribd.com/document/83925264/SAEP-302)) Publicly visible points *(2nd pass)*:
- A **waiver** is defined as a deviation from a requirement stipulated in a **Mandatory Saudi Aramco Engineering Requirement (MSAER)**. MSAERs themselves are established and maintained under **SAEP-301**. [secondary source] ([scribd SAEP-301](https://www.scribd.com/document/607475675/SAEP-301))
- The 2005 edition says approval to deviate must be obtained **before** the non-compliance is implemented, and encourages new projects to raise waivers early, during **Project Proposal** development. It also says waivers are submitted electronically through the **SAP e-Waiver process**. [secondary source]
- A copy carrying a 2023 copyright notice adds a prohibition on attaching confidential or sensitive documents to the waiver; the document owner shown is the **Standards Management Committee**. [secondary source]
- Approval authorities and step-by-step workflow were not visible. [gap]

Contractors should not assume that a "comply with exceptions" vendor response is acceptable without a waiver or a formal Aramco disposition. [general knowledge — verify]

---

## 2. Index table of I&C documents

Legend: **C** = confirmed, **S** = secondary source, **G** = general knowledge — verify, **U** = unverified (number or title not found).

### 2.1 SAES-J (Instrumentation)

| Number | Title (as found) | Scope (paraphrased) | Conf. | Source |
|---|---|---|---|---|
| SAES-J-001 | Instrumentation Index | Compiles the Aramco documents governing instrumentation design and installation; no technical requirements of its own. Revisions seen: 2003, 2008, 2011, 2013. | C | [pdfcoffee](https://pdfcoffee.com/saes-j-001-3-pdf-free.html), [scribd](https://www.scribd.com/document/476010934/SAES-J-001) |
| SAES-J-002 | Technically Acceptable Instrument Manufacturers (older title; current status unknown) | List of technically acceptable instrument manufacturers or product lines per instrument type. A 2004 revision alert lists a **major revision dated 30 Nov 2004** (superseding 29 Feb 2004) *(2nd pass)*; no cancellation notice was found. Vendor evaluation now appears to run through SAEP-1400 and 9COM approvals (see §4). | S | [scribd ALERT-OLD](https://www.scribd.com/document/508178538/ALERT-OLD), [instrumentqcnotes blog](http://instrumentqcnotes.blogspot.com/2015/03/introduction-it-is-branch-of.html), [kishorekaruppaswamy J-002 copy](https://kishorekaruppaswamy.wordpress.com/wp-content/uploads/2011/10/saudi-arabian-engineering-standardssaes-j-002.pdf), [scribd](https://www.scribd.com/document/476010944/SAES-J-002) |
| SAES-J-003 | Instrumentation – Basic Design Criteria | General design criteria, including environmental conditions (ambient temperature table, section 8.1 in the 2013 issue). Issues seen: 31 May 2004, 13 May 2013 (previous issue 31 Dec 2012, next planned update 6 Sep 2016) *(2nd pass)*. No later issue surfaced in search. | C | [scribd](https://www.scribd.com/document/553817194/SAES-J-003), [pdfcoffee](https://pdfcoffee.com/saes-j-003-pdf-free.html) |
| SAES-J-004 | Instrumentation Symbols and Identification | Based on ISA-5.1, with an "Exceptions to ISA-5.1" section. Issues seen: 30 Jun 2002, 10 Dec 2011. | C | [scribd](https://www.scribd.com/document/668988283/SAES-J-004), [scribd INDX-SAES](https://www.scribd.com/document/527150981/INDX-SAES) |
| SAES-J-005 | Instrumentation Drawings and Forms | Required instrument drawings, documents and forms. | S | [scribd J-001 2008](https://www.scribd.com/document/680621562/SAES-J-001) |
| SAES-J-100 | "Process Flow Metering" (2009 and 2013 issues); "Process Measurement" (2020 issue, next planned update 6 Oct 2025) | Flow measurement design and selection. The 2009 issue is written as additions/exceptions to PIP PCCFL001. The October 2020 issue says instruments for ESD service must also meet SAES-J-601. References 34-SAMSS-117 (turbine meters) and 34-SAMSS-118 (PD meters). See §3.3 for clauses. | S | [scribd J-100](https://www.scribd.com/document/494872706/SAES-J-100), [pdfcoffee J-100](https://pdfcoffee.com/saes-j-100-pdf-free.html), [mirror J-100](https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-31108---Tecnicas---Riyas/RFQ-Files/SAES-J-100) |
| SAES-J-200 | Pressure | Minimum mandatory requirements for design and installation of pressure and D/P instruments, written as additions to **PIP PCCPR001**. Issues seen: 2008 (next planned update 2013), 2013 (next planned update 2018). See §3.4. | S | [scribd](https://www.scribd.com/document/494872703/Saes-j-200-Pressure), [scribd J-200 (2)](https://www.scribd.com/document/439171375/SAES-J-200-Pressure), [scribd J-200 (3)](https://www.scribd.com/document/519224007/SAES-J-200), [englogs](https://englogs.com/saudi-aramco-engineering-standard-instrumentation-system/) |
| SAES-J-300 | Level | Level instrumentation (SAES-J-400 excludes level and points to J-300). Index issue dates 2003–2005. Companion SATIP-J-300-01 covers level installations. See §3.5. | S | [scribd INDX-SAES](https://www.scribd.com/document/527150981/INDX-SAES), [scribd J-400](https://www.scribd.com/document/519224174/SAES-J-400), [scribd SAIC-J-6022](https://www.scribd.com/document/324772531/SAIC-J-6022-Rev-0-pdf), [englogs](https://englogs.com/saudi-aramco-engineering-standard-instrumentation-system/), [paktechpoint](https://paktechpoint.com/saudi-aramco-engineering-standard-for-electrical-instrumentation-and-cp/) |
| SAES-J-400 | Temperature | Temperature instrumentation. Issue seen: 28 Jun 2009 (next planned update 2013). See §3.6. | S | [scribd](https://www.scribd.com/document/519224174/SAES-J-400), [englogs](https://englogs.com/saudi-aramco-engineering-standard-instrumentation-system/) |
| SAES-J-410 | not found (searched again in 2nd pass) | — | U | — |
| SAES-J-502 | Analyzer Shelters | Analyzer shelter design. | S | [englogs](https://englogs.com/saudi-aramco-engineering-standard-instrumentation-system/) |
| SAES-J-505 | Combustible Gas and Hydrogen Sulfide in Air Detection Systems | Fixed combustible gas and H2S detection system design. | S | [englogs](https://englogs.com/saudi-aramco-engineering-standard-instrumentation-system/) |
| SAES-J-510 | not found (the brief suggested "analyzers"; not confirmed; searched again in 2nd pass) | — | U | — |
| SAES-J-600 | Pressure Relief Devices | Pressure relief devices; uses the tag "PZV" for relief valves. Issue seen: 30 Mar 2005. | C | [scribd Indx-saes Oct 2006](https://www.scribd.com/document/527150957/Indx-saes-Oct-2006), [scribd SAEP-318](https://www.scribd.com/document/473260773/SAEP-318-pdf) |
| SAES-J-601 | Emergency Shutdown and Isolation Systems | ESD and emergency isolation (ZV) instrumentation and alarms. Issue seen: 29 Jun 2005 (previous 31 Mar 2001). Still cross-referenced by SAES-J-100 (2020) and SAES-Z-001. | C | [scribd INDX-SAES](https://www.scribd.com/document/527150981/INDX-SAES), [kishorekaruppaswamy J-601 copy](https://kishorekaruppaswamy.wordpress.com/wp-content/uploads/2011/10/saudi-arabian-engineering-standards-saes-j-601.pdf) |
| SAES-J-602 | Burner Management, Combustion and Waterside Control Systems for Watertube Boilers *(2nd pass)* | Boiler BMS / combustion / drum-level controls. Index dates: issue 31 Jan 2005, previous 30 Jan 2002, next planned update 1 Feb 2008. | S | [scribd INDX-SAES](https://www.scribd.com/document/527150981/INDX-SAES) |
| SAES-J-605 | Surge Relief Protection Systems | Surge relief for pipelines and loading systems. | S | [scribd Indx-saes Oct 2006](https://www.scribd.com/document/527150957/Indx-saes-Oct-2006) |
| SAES-J-700 | Control Valves | Control valve application and installation. Minor revision Aug 2004; later issues exist. | C | [scribd ALERT-OLD](https://www.scribd.com/document/508178538/ALERT-OLD), [scribd SAIC-L-2043](https://www.scribd.com/document/457762664/SAIC-L-2043) |
| SAES-J-800 | not found (searched again in 2nd pass; J-801 Control Buildings exists) | — | U | — |
| SAES-J-801 | Control Buildings | Control building requirements, including HVAC monitoring. Issue seen: Dec 2005. | C | [scribd INDX-SAES](https://www.scribd.com/document/527150981/INDX-SAES), [scribd SAES-B-014](https://www.scribd.com/document/405891268/SAES-B-014) |
| SAES-J-902 | Electrical Systems for Instrumentation | Design criteria for installing power and wiring systems for electrical instrumentation. Issues seen: 2013, 2017, 26 Mar 2020. | C | [scribd](https://www.scribd.com/document/426879234/SAES-J-902-pdf), [mirror](https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-31108---Tecnicas---Riyas/RFQ-Files/SAES-J-902) |
| SAES-J-903 | Intrinsically Safe Systems | Design and installation of IS systems. Issue seen: 31 Jan 2005. | C | [scribd INDX-SAES](https://www.scribd.com/document/527150981/INDX-SAES), [scribd SAIC-J-6904](https://www.scribd.com/document/226927140/SAIC-J-6904-Rev-0) |
| SAES-J-904 | FOUNDATION Fieldbus (FF) Systems | Design, specification, installation, configuration, commissioning and maintenance of FF-based control systems. | C | [pdfcoffee SAES-Z-010](https://pdfcoffee.com/saes-z-010-pdf-pdf-free.html), [Control Global](https://www.controlglobal.com/network/industrial-networks/article/11321803/foundation-fieldbus-in-hazardous-areas) |
| SAES-J-905 | Instrument Asset Management Systems (IAMS) *(2nd pass)* | Minimum requirements for design, commissioning and documentation of IAMS installations; IAMS must comply with 34-SAMSS-911. Issue seen: 31 May 2011 (Instrumentation Standards Committee). | S | [pdfcoffee J-905](https://pdfcoffee.com/saes-j-905-pdf-free.html), [pdfcoffee J-001](https://pdfcoffee.com/saes-j-001-3-pdf-free.html) |

### 2.2 SAES-Z (Process control / automation)

| Number | Title (as found) | Scope (paraphrased) | Conf. | Source |
|---|---|---|---|---|
| SAES-Z-001 | Process Control Systems | PCS (DCS/PLC-based) design. Process control networks are in scope. ESD (SAES-J-601) and SCADA (SAES-Z-004) are excluded except for their interfaces to the PCS. Source copy: draft dated 22 Jul 2012. | C | [pdfcoffee Z-001](https://pdfcoffee.com/saes-z-001-pdf-pdf-free.html), [scribd SABP-Z-019](https://www.scribd.com/document/509522885/SABP-Z-019) |
| SAES-Z-002 | "Process Automation Systems" appears in the header of a 2006 copy (issue 28 May 2006, next planned update 2011); exact title unconfirmed. Possibly "Technically Acceptable Process Automation Systems". | Identifies acceptable manufacturers of process automation systems. Lists are split into **Restricted Vendor Lists** (host systems: DCS, SCADA) and **Recommended Vendor Lists** (subsystems, e.g. ESD, RTU), the latter being products evaluated by P&CSD and found technically acceptable *(2nd pass)*. | S | [scribd Z-002](https://www.scribd.com/doc/239724008/Saes-z-002-Locked-by-Badr) |
| SAES-Z-004 | Supervisory Control and Data Acquisition (SCADA) System | SCADA systems in Aramco plants and pipelines. Issue seen: 10 Nov 2013. | C | [pdfcoffee Z-004](https://pdfcoffee.com/saes-z-004-pdf-free.html) |
| SAES-Z-010 | Process Automation Networks (also cited with a "…Connectivity" variant) | Design, installation, configuration and commissioning of plant-wide Process Automation Networks (PAN) that link the PCNs and interface to the WAN. Ethernet (IEEE 802.3) based. Issues seen: 26 Oct 2005, 24 Oct 2009. | C | [scribd Z-010](https://www.scribd.com/document/415401236/SAES-Z-010-pdf), [pdfcoffee Z-010](https://pdfcoffee.com/saes-z-010-pdf-pdf-free.html) |

### 2.3 34-SAMSS (Instrumentation purchase specifications)

| Number | Title (as found) | Scope (paraphrased) | Conf. | Source |
|---|---|---|---|---|
| 34-SAMSS-001 | Multiphase Flow Meters & Wellhead Water Cut Meters *(2nd pass)* | Multiphase metering; cited with 34-SAMSS-114 in SAEP-146. Listed in Aramco's own iKTVA instrumentation deck and sourcing lists. | C (number and title on aramco.com, seen via search snippet) | [aramco iKTVA deck](https://www.aramco.com/-/media/downloads/iktva/instrumentation.pdf), [scribd SAEP-146](https://www.scribd.com/document/473260753/SAEP-146-pdf) |
| 34-SAMSS-010 | Title not seen *(2nd pass)* | Aramco sourcing lists tie this number to glass level gauges and to ultrasonic and vortex flowmeters; the iKTVA deck lists it with IOGP S-718 as an applicable standard. Probably a general process-instrument purchase specification. | S (number on aramco.com lists; title unknown) | [aramco iKTVA deck](https://www.aramco.com/-/media/downloads/iktva/instrumentation.pdf), [Aramco India sourcing list Jan 2024](https://india.aramco.com/-/media/aramcoindia/sourcing-list/sourcing-list-jan-2024.pdf), [Aramco India sourcing list Sep 2025](https://india.aramco.com/-/media/aramcoindia/sourcing-list/30-sept_2025-sourcing-list-aa-india.pdf), [AOC materials sourcing list](https://europe.aramco.com/-/media/aramcoaoc/pdf/aramco-materials-sourcing-list.pdf) |
| 34-SAMSS-112 | not found (searched again in 2nd pass) | — | U | — |
| 34-SAMSS-113 | not found (searched again in 2nd pass) | — | U | — |
| 34-SAMSS-114 | Ultrasonic Flow Meter for Gas Custody Measurement | Gas custody USM. Issue seen: 17 Sep 2007. | S | [pdfcoffee 34-SAMSS-114](https://pdfcoffee.com/34-samss-114-pdf-free.html) |
| 34-SAMSS-117 | Turbine meters (exact title not seen) | Cited by SAES-J-100 for turbine meters. | S | [scribd J-100](https://www.scribd.com/document/494872706/SAES-J-100) |
| 34-SAMSS-118 | Positive displacement meters (exact title not seen) | Cited by SAES-J-100 for PD meters. | S | [scribd J-100](https://www.scribd.com/document/494872706/SAES-J-100) |
| 34-SAMSS-514 | Stationary combustible gas and H2S detection / monitoring systems | Purchase specification for fixed gas detectors. Issue seen: 26 Dec 2013. | S | [scribd 34-SAMSS-514](https://www.scribd.com/document/517672324/34-SAMSS-514), [scribd Dec 2013](https://www.scribd.com/document/329480655/34-SAMSS-514-Dec-26-2013) |
| 34-SAMSS-611 | Safety Relief Valves – Conventional and Balanced Types | Minimum requirements for conventional and balanced industrial safety relief valves; modifies API STD 526. Data sheet SA-8020-611-ENG. Issue seen: 20 Mar 2013. | S | [scribd 34-SAMSS-611](https://es.scribd.com/document/295779795/34-SAMSS-611) |
| 34-SAMSS-621 | ESD Systems – Hard-Wired – Solid-State (Nonprogrammable) | Solid-state hard-wired ESD logic. Excludes PLC-based ESD (34-SAMSS-623) and relay ESD (34-SAMSS-622). Issue seen: 2005. | C | [pdfcoffee 34-SAMSS-621](https://pdfcoffee.com/34-samss-621-pdf-free.html), [pdfcoffee J-001](https://pdfcoffee.com/saes-j-001-3-pdf-free.html) |
| 34-SAMSS-622 | ESD Systems – Electromagnetic Relay | Relay-based ESD logic. | S | [pdfcoffee J-001](https://pdfcoffee.com/saes-j-001-3-pdf-free.html) |
| 34-SAMSS-623 | Programmable controller-based ESD systems (exact title not seen) | PLC-based ESD systems, including cabinet requirements that reference 34-SAMSS-820. Minor revision late 2004. | S | [pdfcoffee 34-SAMSS-621](https://pdfcoffee.com/34-samss-621-pdf-free.html), [scribd ALERT-OLD](https://www.scribd.com/document/508178538/ALERT-OLD) |
| 34-SAMSS-625, -627, -629 | Exist (Scribd/pdfcoffee listings); titles not confirmed (2nd-pass search returned nothing) | Probably the 62x control/ESD-system family. | U (title) | [pdfcoffee 625](https://pdfcoffee.com/34-samss-625pdf-pdf-free.html), [scribd 627](https://www.scribd.com/document/549908228/34-SAMSS-627), [scribd 629](https://www.scribd.com/document/549908231/34-SAMSS-629) |
| 34-SAMSS-634 | Local emergency isolation valve (ZV) control systems (exact title not seen) | Local ZV control panels and smart ZV controllers, including partial-stroke testing. | S | [scribd 34-SAMSS-634](https://www.scribd.com/document/370514106/174038738-34-SAMSS-634-pdf) |
| 34-SAMSS-711 | Control Valves | Control valve purchase specification. Issues seen: 4 Jan 2012, 11 Oct 2017 (next planned update Oct 2020). | C | [scribd 711](https://www.scribd.com/document/468687176/34-SAMSS-711-pdf), [Valve World](https://valve-world.net/?p=53143) |
| 34-SAMSS-716 | Pneumatic Actuators – On-Off Service | Pneumatic actuators for on-off valves. Issue seen: 10 Aug 2009. **Not** the MOV specification. | S | [pdfcoffee 716](https://pdfcoffee.com/34-samss-716-pdf-free.html) |
| 34-SAMSS-717 | Hydraulic Valve Actuator Systems | Hydraulic actuators. | S | [scribd 717](https://www.scribd.com/document/486500518/34-SAMSS-717) |
| 34-SAMSS-718 | Electric Motor Operated Valve Actuators | MOV actuators; excludes electric actuators for wellhead surface safety valves. Issue seen: 26 Jan 2009. | S | [scribd 718](https://www.scribd.com/document/536743257/34-SAMSS-718), [pdfcoffee 718](https://pdfcoffee.com/34-samss-718-pdf-free.html) |
| 34-SAMSS-820 | Instrument Control Cabinets – Indoor (scope wording: instrument control panels, control cabinets and marshalling cabinets for electrically unclassified air-conditioned buildings) | Indoor panels and cabinets. Issues seen: 28 May 2007, 13 Jul 2016. | C | [scribd 820](https://www.scribd.com/document/494624754/424411678-34-samss-820), [pdfcoffee 820](https://pdfcoffee.com/34-samss-820-pdf-free.html) |
| 34-SAMSS-821 | Instrument Control Cabinets – Outdoor | Outdoor panels and cabinets. All of 34-SAMSS-820 applies unless superseded. Issues seen: 5 Oct 2005, 22 Jul 2012. | C | [scribd 821](https://www.scribd.com/document/536743247/34-SAMSS-821), [pdfcoffee 821](https://pdfcoffee.com/34-samss-821-pdf-free.html) |
| 34-SAMSS-831 | Instrumentation for Packaged Units | Instrumentation on pre-engineered, pre-assembled, pre-wired skid-mounted packages; not custom-engineered packages. Issue seen: 25 Mar 2021 (next planned update Mar 2024). | C | [studylib 831](https://studylib.net/doc/27696645/34-samss-831), [scribd SAIC-J-6022](https://www.scribd.com/document/324772531/SAIC-J-6022-Rev-0-pdf) |
| 34-SAMSS-846 | Exists (Scribd/pdfcoffee listings); title not confirmed | — | U (title) | [scribd 846](https://www.scribd.com/document/549907783/34-SAMSS-846) |
| 34-SAMSS-911 | Instrument Asset Management Systems *(2nd pass)* | IAMS purchase specification; SAES-J-905 requires IAMS to comply with it. | S | [pdfcoffee J-905](https://pdfcoffee.com/saes-j-905-pdf-free.html), [pdfcoffee J-001](https://pdfcoffee.com/saes-j-001-3-pdf-free.html) |
| 34-SAMSS-913 | Instrumentation and Thermocouple Cable | Instrument and thermocouple cable construction (jacket, colours and so on). Referenced by SAES-J-902. | S | [scribd QA/QC module](https://www.scribd.com/presentation/609393585/Training-Module-QA-QC), [mirror J-902](https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-31108---Tecnicas---Riyas/RFQ-Files/SAES-J-902) |

### 2.4 23-SAMSS (Process automation systems)

| Number | Title (as found) | Scope | Conf. | Source |
|---|---|---|---|---|
| 23-SAMSS-010 | Distributed Control Systems | DCS purchase specification. Tied to the process-automation Restricted Vendor List (including FF-capable DCS). | S | [scribd SAES-Z-002](https://www.scribd.com/doc/239724008/Saes-z-002-Locked-by-Badr), [scribd SAIC-J-6806](https://www.scribd.com/document/525615451/SAIC-J-6806) |
| 23-SAMSS-020 | Supervisory Control and Data Acquisition (SCADA) Systems | SCADA purchase specification. | S | [es.scribd 23-SAMSS-020](https://es.scribd.com/document/319694317/23-SAMSS-020) |
| 23-SAMSS-030 | Exists (Scribd listing); title not confirmed | — | U (title) | [scribd 23-SAMSS-030](https://www.scribd.com/document/585773935/23-SAMSS-030) |
| 23-SAMSS-071 | not found (searched again in 2nd pass) | — | U | — |
| 23-SAMSS-072 | Data Acquisition and Historization Systems | Plant historian / data acquisition. | S | [scribd SABP-Z-019](https://www.scribd.com/document/509522885/SABP-Z-019) |

### 2.5 Related SAEP / SABP / SAIC / other SAES

| Number | Title / subject (as found) | Conf. | Source |
|---|---|---|---|
| SAEP-15 | Preparation of process-automation Restricted Vendor Lists (RVL) | S | [scribd SAEP-15](https://www.scribd.com/document/429080803/SAEP-15-pdf) |
| SAEP-99 | Process automation network security (cites SAES-Z-010) | S | [scribd Z-010](https://www.scribd.com/document/415401236/SAES-Z-010-pdf) |
| SAEP-301 | Establishing and maintaining Mandatory Saudi Aramco Engineering Requirements (MSAERs) *(2nd pass)* | S | [scribd SAEP-301](https://www.scribd.com/document/607475675/SAEP-301) |
| SAEP-302 | Instructions for obtaining a waiver of a Mandatory Saudi Aramco Engineering Requirement (see §1.5) | S | [scribd SAEP-302](https://www.scribd.com/document/683056429/SAEP-302), [scribd SAEP-302 older](https://www.scribd.com/document/83925264/SAEP-302) |
| SAEP-303 | Engineering reviews of project proposals and detailed design packages *(2nd pass)*. Copies dated 1 Jun 2008, 13 Dec 2011, 21 Nov 2016 | S | [scribd SAEP-303](https://www.scribd.com/document/473260763/SAEP-303-pdf), [scribd SAEP-303 (2)](https://www.scribd.com/document/397353670/SAEP-303-PDF), [pdfcoffee SAEP-303](https://pdfcoffee.com/saep-303-pdf-pdf-free.html) |
| SAEP-12 / SAEP-14 | Project Execution Plan / Project Proposals (SAEP-14 schedules must include SAEP-303 review times) *(2nd pass)* | S | [scribd SAEP-14](https://www.scribd.com/document/661288589/SAEP-14), [scribd INDX-SAEP](https://www.scribd.com/doc/239415248/INDX-SAEP) |
| SAEP-318 | Pressure relief valve programme (applies to RVs, which SAES-J-600 also calls PZVs) | S | [scribd SAEP-318](https://www.scribd.com/document/473260773/SAEP-318-pdf) |
| SAEP-1400 | Instrumentation vendor technical evaluation by 9COM (Instrumentation Standards Committee) | S | [scribd SAEP-1400](https://www.scribd.com/document/398466940/SAEP-1400-pdf) |
| SAEP-1151 (?) | Inspection requirements (slideshare "saep1151inspection-requirement") | S | [slideshare](https://www.slideshare.net/slideshow/saep1151inspection-requirementpdf/258302250) |
| SABP-J-900 | Best practice on FF/instrumentation in hazardous areas (cites J-904 for Ex ic) | S | [scribd SABP-J-900](https://round-lake.dustinice.workers.dev:443/https/www.scribd.com/document/493616203/SABP-J-900) |
| SABP-Z-057 | Network security best practice (cites Z-010) | S | [scribd SABP-Z-057](https://round-lake.dustinice.workers.dev:443/https/www.scribd.com/document/509522913/SABP-Z-057) |
| SAES-B-058 | Emergency Shutdown, Isolation and Depressuring (refers to SAES-J-601 for instrumentation and alarms) | S | [pdfcoffee B-058](https://pdfcoffee.com/saes-b-058-pdf-free.html) |
| SAES-B-068 | Electrical Area Classification (only listed IS equipment in Zone 0, per J-903) | S | [scribd B-068](https://www.scribd.com/document/655719750/SAES-B-068) |
| SAES-B-014 | Safety Requirements for Plant and Operations Support Buildings (references J-801) | S | [scribd B-014](https://www.scribd.com/document/405891268/SAES-B-014) |
| SAES-K-002 | HVAC (monitoring per J-801, via SAIC-K-4044) | S | [pdfcoffee SAIC-K-4044](https://pdfcoffee.com/saudi-aramco-inspection-checklist-pressurized-building-hvac-requirements-saic-k-4044-30-apr-13-hvac-pdf-free.html) |
| SAES-P-103 | Batteries and UPS Systems (referenced by J-902) | S | [scribd J-902](https://www.scribd.com/document/426879234/SAES-J-902-pdf) |
| SAES-P-111 | Grounding (referenced by J-902) | S | [scribd J-902](https://www.scribd.com/document/426879234/SAES-J-902-pdf) |
| SAES-T-xxx | Telecom series. Index document: **SAES-T-000** "Telecommunications Standards Introduction and Indices" (2007 copy). I&C-adjacent titles seen *(2nd pass)*: **SAES-T-481** In-Plant Voice Paging System; **SAES-T-625** fiber optic cable for inter-/intra-building (on-premises) use; **SAES-T-624** fiber optic test requirements (attenuation limits at 1,300/1,550 nm, cited from T-625); **SAES-T-916** communications building cable (fiber connectors per T-625 clause 5.6); **SAES-T-911** conduit system design (cites T-603 and T-628, titles not seen). Other numbers seen without titles: T-101, T-494, T-795, T-912, T-914. | S (titles from snippets of unofficial copies) | [scribd SAES-T-625](https://www.scribd.com/document/475001065/SAES-T-625-PDF), [scribd SAES-T-911](https://www.scribd.com/document/453306409/SAES-T-911), [scribd SAES-T-101](https://www.scribd.com/document/475001025/SAES-T-101-pdf), [scribd T-914](https://www.scribd.com/document/475001111/SAES-T-914-PDF), [scribd T-912](https://www.scribd.com/document/475001105/SAES-T-912-PDF) |
| SAES-Y-301 | Custody measurement standard covering **radar tank gauging systems** (hydrocarbon custody, not general process level) *(2nd pass)* | S | [scribd SAES-Y-301](https://www.scribd.com/document/493616156/SAES-Y-301) |
| SATIP-J-300-01 | Typical inspection plan for level instrument installations (cited by SAIC-J-6022) *(2nd pass)* | S | [scribd SAIC-J-6022](https://www.scribd.com/document/324772531/SAIC-J-6022-Rev-0-pdf) |
| SAIC-J-6022 | Inspection checklist – packaged units (cites 34-SAMSS-831) | S | [scribd](https://www.scribd.com/document/324772531/SAIC-J-6022-Rev-0-pdf) |
| SAIC-J-6904 | Inspection checklist – intrinsically safe systems (cites J-903) | S | [scribd](https://www.scribd.com/document/226927140/SAIC-J-6904-Rev-0) |
| SAIC-J-6806 | Inspection checklist – ESD / power supply (cites 34-SAMSS-820) | S | [scribd](https://www.scribd.com/document/525615451/SAIC-J-6806) |
| SAIC-J-6803, -6804, -6017, -6019, -6030, -6111 | Other J-series inspection checklists (subjects not confirmed individually) | S (numbers) | [6803](https://www.scribd.com/document/525616682/SAIC-J-6803), [6804](https://www.scribd.com/document/525616683/SAIC-J-6804), [6017](https://www.scribd.com/document/526010667/SAIC-J-6017), [6019](https://www.scribd.com/document/525219377/SAIC-J-6019), [6030](https://www.scribd.com/document/525610883/SAIC-J-6030), [6111](https://www.scribd.com/document/226926965/SAIC-J-6111-Rev-0) |

**Count (after the 2nd pass):** of the roughly 80 document numbers tracked above, about 21 are confirmed (number, title and scope in two or more sources, or on aramco.com), about 50 are secondary-source only, and about 10 are still unverified or title-unknown (J-410, J-510, J-800, 34-SAMSS-112/113/625/627/629/846, 23-SAMSS-030/071). See §8.

---

## 3. Per-topic requirements

Each bullet carries its own tag and source. Where the only evidence is a cross-reference, the bullet says so.

### 3.1 Instruments general / basic design criteria (SAES-J-003, SAES-J-002)

**Ambient design temperatures (SAES-J-003).**
- The 2004 issue of SAES-J-003 requires instruments and control systems to operate continuously, without degrading the manufacturer's guaranteed performance, at these ambient conditions [secondary source] ([scribd J-003](https://www.scribd.com/document/476010936/SAES-J-003), [pdfcoffee J-003](https://pdfcoffee.com/saes-j-003-pdf-free.html)):

| Location | Max | Min |
|---|---|---|
| Indoor, air-conditioned | 35 °C | 10 °C |
| Outdoor, sheltered | 55 °C | 0 °C |
| Outdoor, unsheltered (direct sun) | 65 °C | 0 °C |

- The 2013 issue (13 May 2013; previous issue 31 Dec 2012; next planned update 6 Sep 2016) has an "Environmental Conditions" section (8.1 temperature). The values were not visible in public snippets, so whether they changed is not confirmed. A targeted 2nd-pass search for the 55 °C / 65 °C values and for any 2016+ issue of SAES-J-003 found nothing. **Always check the project revision.** [secondary source] ([pdfcoffee J-003](https://pdfcoffee.com/saes-j-003-pdf-free.html))
- Context *(2nd pass)*: the sheltered/outdoor split matches the location classes of ISA-71.01 (Class C sheltered, Class D outdoor) and IEC 60654-1, which Aramco's table probably follows; the numeric limits of those standards were not visible. [secondary source for the class names; inference for the link] ([ISA S71.01 preview](https://webstore.ansi.org/preview-pages/ISA/preview_ANSI+ISA+S71.01-1985.pdf), [IEC 60654-1 preview](https://webstore.ansi.org/preview-pages/IEC/preview_iec60654-1%7Bed2.0%7Db.img.pdf))
- Other J-series standards point back to J-003 for ambient conditions; for example SAES-J-200 requires all pressure instruments and accessories to meet the ambient-condition requirements of SAES-J-003. [secondary source] ([scribd J-200](https://www.scribd.com/document/439171375/SAES-J-200-Pressure))
- In practice: data sheets for outdoor electronics (transmitters, positioners, analyzers, junction-box components, field panels) must show a rated operating range that covers the 65 °C unsheltered case, or the item must be sun-shaded. LCD displays and electrolytic components are common failure points. [general knowledge — verify]
- SAES-J-003 is also generally understood to cover humidity, dust and sand, corrosive atmosphere (the coastal/offshore marine environment of the Arabian Gulf and Red Sea), instrument air quality and units of measure. [general knowledge — verify]

**Units.** Aramco practice uses SI/metric with specific conventions, for example pressure in kPa(g) alongside psig, as in the SAES-J-700 actuator volume-tank criterion "930 kPag (135 psig)". [secondary source for the dual-unit example] ([scribd SAIC-L-2043](https://www.scribd.com/document/457762664/SAIC-L-2043))

**Technically acceptable manufacturers (SAES-J-002).**
- Older public indexes list SAES-J-002 as "Technically Acceptable Instrument Manufacturers": a list of manufacturers and models accepted per instrument type. [secondary source] ([instrumentqcnotes](http://instrumentqcnotes.blogspot.com/2015/03/introduction-it-is-branch-of.html), [englogs](https://englogs.com/saudi-aramco-engineering-standard-instrumentation-system/))
- Current practice uses 9COM-based vendor/plant approval (SAEP-1400 for instrumentation) and RVLs for process automation systems (SAEP-15). Whether SAES-J-002 is still active or has been cancelled is **not confirmed**. The latest dated evidence is a **major revision of 30 Nov 2004** in an Aramco revision alert; a 2nd-pass search for a cancellation or "superseded by SAEP-1400" notice found nothing. See §4. [general knowledge — verify for the current status; secondary source for the 2004 revision] ([scribd ALERT-OLD](https://www.scribd.com/document/508178538/ALERT-OLD))
- The parallel process-automation document, **SAES-Z-002**, works the same way: it identifies acceptable manufacturers, with Restricted lists for host systems (DCS, SCADA) and Recommended lists for subsystems (ESD, RTU). See §3.16. [secondary source] ([scribd Z-002](https://www.scribd.com/document/354870462/SAES-Z-002-LOCKED-BY-BADR-pdf))

**Materials and sour service.**
- Aramco projects normally specify 316/316L stainless steel for wetted parts, instrument tubing and fittings as a minimum. NACE MR0175/ISO 15156 compliance is required for sour (H2S) service, which is common in Saudi gas and crude handling. [general knowledge — verify: not confirmed in public excerpts]
- "Instrument manifold, tubing and fittings" is a named Aramco iKTVA localization category, which confirms they are a distinct, high-volume purchased commodity. [confirmed] ([aramco iKTVA instrumentation deck](https://www.aramco.com/-/media/downloads/iktva/instrumentation.pdf))
- Tubing wall thickness, compression-fitting brand consistency (no inter-mixing of brands) and seamless tube are typical requirements in Aramco I&C installation specifications and inspection checklists. [general knowledge — verify]

**Enclosure ratings.** Outdoor field electronics usually need at least IP65/NEMA 4X, and hazardous-area certification to the area classification under SAES-B-068 (Class I Div/Zone). Ex d (flameproof) has historically been the dominant protection method on Aramco sites (see §3.14). [general knowledge — verify for the rating; secondary source for the Ex d practice] ([Control Global](https://www.controlglobal.com/articles/2015/foundation-fieldbus-in-hazardous-areas/))

**Accessibility.** Instruments and valve accessories (adjustments, gauges) must be readable and accessible from grade or from a permanent platform, walkway or fixed ladder. This is stated for control valves in SAES-J-700 and is typical throughout the J-series. [secondary source] ([scribd SAIC-L-2043](https://www.scribd.com/document/457762664/SAIC-L-2043))

### 3.2 Symbols, identification, drawings and forms (SAES-J-004, SAES-J-005)

- **SAES-J-004** adopts **ISA-5.1** as the basis for instrument symbols and tag identification and adds a section of "Exceptions to ISA-5.1". The 2011 issue cites ISA-5.1 (Reaffirmed 13 July 1992), which is the 1984 edition, not ANSI/ISA-5.1-2009. Aramco-specific letter codes therefore follow the 1984 base plus Aramco exceptions, so the 2009 ISA changes may not apply. [secondary source] ([scribd J-004](https://www.scribd.com/document/668988283/SAES-J-004))
- **Aramco-specific tag letters in common use:** **ZV** for an emergency isolation / ESD valve (Aramco uses "ZV", not "XV" or "SDV", for its safety isolation valves) and **PZV** for a pressure relief valve. "PZV" is confirmed in SAES-J-600 as cited by SAEP-318. "ZV" is confirmed in the SAES-J-700 cross-reference ("ESD valves (ZVs)") and in 34-SAMSS-634 ("Emergency Isolation Valves (ZV's)"). [confirmed] ([scribd SAEP-318](https://www.scribd.com/document/473260773/SAEP-318-pdf), [scribd SAIC-L-2043](https://www.scribd.com/document/457762664/SAIC-L-2043), [scribd 34-SAMSS-634](https://www.scribd.com/document/370514106/174038738-34-SAMSS-634-pdf))
- **EIV** (Emergency Isolation Valve) appears as a term distinct from ZV in the SAES-J-700 excerpt ("ESD valves (ZVs), nor … emergency isolation valves (EIVs)"). SAES-B-058 defines an emergency isolation valve as one that moves to its fail-safe position on fire, rupture or loss of containment. [secondary source] ([scribd SAIC-L-2043](https://www.scribd.com/document/457762664/SAIC-L-2043), [es.scribd YERP B-058 replacement](https://es.scribd.com/document/178151012/100-YER-PE-YSS-0048))
- **SAES-J-005** "Instrumentation Drawings and Forms" defines the required deliverables (instrument index, data sheets on Aramco ISS forms, loop drawings, hook-ups, location plans, cable schedules and so on). [secondary source for the title; general knowledge — verify for the deliverables list] ([scribd J-001 2008](https://www.scribd.com/document/680621562/SAES-J-001))
- **Instrument Specification Sheets (ISS)** are Aramco forms numbered 8020-nnn-ENG after the matching SAMSS. Example: ISS 8020-611-ENG for PRVs (conventional and balanced). Vendors fill Aramco's forms, not their own. [secondary source] ([scribd SAEP-318](https://www.scribd.com/document/473260773/SAEP-318-pdf))
- **Drawing format:** general drawing requirements fall under SAES-A-202 (drafting) and related A-series standards. [secondary source: A-202 appears in a mirrored RFQ file list] ([mirror SAES-A-202](https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-31108---Tecnicas---Riyas/RFQ-Files/SAES-A-202))
- **P&ID extraction note (for this tool):** on Aramco P&IDs, expect ZV (ESD/isolation valve), PZV (relief valve), ISA-5.1-1984 letters, and Aramco-specific notations for "fail-safe" positions and ESD levels. Map ZV to "ESD/SIS on-off valve" and PZV to "PSV" when normalising tags. [general knowledge — verify]

### 3.3 Flow measurement (SAES-J-100, 34-SAMSS-114/117/118)

- **SAES-J-100** was historically titled "Process Flow Metering". A 2020 issue is cited as "Process Measurement", which suggests a consolidated scope; this is not confirmed. In the 2020 text, clause 4.1.2 says that instruments selected for ESD service must also meet SAES-J-601. [secondary source] ([mirror SAES-J-100](https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-31108---Tecnicas---Riyas/RFQ-Files/SAES-J-100), [scribd J-100](https://www.scribd.com/document/494872706/SAES-J-100))
- SAES-J-100 refers to **34-SAMSS-117** for turbine meters and **34-SAMSS-118** for positive displacement meters. [secondary source] ([scribd J-100](https://www.scribd.com/document/494872706/SAES-J-100))
- **34-SAMSS-114** covers ultrasonic flow meters for gas custody measurement (2007 copy). An Aramco procedure cites it together with 34-SAMSS-001 for multiphase metering work. [secondary source] ([pdfcoffee 34-SAMSS-114](https://pdfcoffee.com/34-samss-114-pdf-free.html), [scribd SAEP-146](https://www.scribd.com/document/473260753/SAEP-146-pdf))
- **Custody / hydrocarbon measurement** in Aramco falls under a separate SAES/SAEP regime (custody transfer and hydrocarbon accounting), with meter proving and API MPMS references. Treat custody metering as outside the plain J-100 process-metering scope unless the project says otherwise. [general knowledge — verify]
- **Market evidence:** Aramco uses venturi meters (WIKA venturis for gas exploitation), V-Cone meters (reported in OGJ), and Coriolis meters (9COM 6000002915 "Flowmeter; Coriolis Mass" appears in SAEP-1400 listings). [secondary source] ([WIKA blog](https://blog.wika.com/en/wika-insight/venturis-meet-desert-challenges/), [OGJ V-Cone](https://www.ogj.com/home/article/17216022/saudi-plants-install-v-cone-meters), [Pipeliner venturi](https://www.pipeliner.com.au/internationalnews/venturi-meters-for-saudi-aramco/), [scribd SAEP-1400](https://www.scribd.com/document/398466940/SAEP-1400-pdf))
- **Localization:** process flowmeters, custody measurement and multiphase flowmeters are named Aramco iKTVA instrumentation opportunity areas (2022 and 2025 workshops). [confirmed] ([aramco iKTVA instrumentation deck](https://www.aramco.com/-/media/downloads/iktva/instrumentation.pdf))
- **Orifice and installation clauses** *(2nd pass)*. All [secondary source], from search snippets of unofficial copies ([scribd J-100](https://www.scribd.com/document/494872706/SAES-J-100), [pdfcoffee J-100](https://pdfcoffee.com/saes-j-100-pdf-free.html), [mirror J-100 2020](https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-31108---Tecnicas---Riyas/RFQ-Files/SAES-J-100)):
  - The 2009 issue is structured as additions and exceptions to **PIP PCCFL001** (Process Industry Practices, flow measurement), with clause numbers keyed to PIP sections.
  - **Flange taps are mandatory for all orifice meter installations** (2009 issue, an *exception* to PIP 3.2.14(b)). Tap connections must follow **Standard Drawing AC-036413 or AB-036414**.
  - **Straight runs:** the 2009 issue adds its own **Table 1** for straight-run requirements (addition to PIP 3.2.17). The 2020 issue has appendices giving minimum straight-run lengths for **orifice plates without flow conditioners per ISO 5167-2** and for **classical venturi tubes per ISO 5167-4**. Table values were not visible.
  - The 2009 issue also requires a **flanged drop-out spool upstream** of the meter and limits the **thermowell location to no more than 20 nominal pipe diameters downstream** of the meter (as paraphrased in a search summary; check the exact wording).
  - Orifice calculation data sheet: Aramco ISS form **3175-ENG** is used in place of the ISA S20.21 form (2009 issue).
  - The 2020 issue cites drawing **AB-036019 "Thermowell – Assembly and Detail"**, and its revision notes mention **FEA and CFD requirements for helical thermowells** (helical-strake designs). It also cites level library drawings DB-950046 and DB-950047 (see §3.5).
- **Still not confirmed:** beta-ratio limits (a 2nd-pass search for a d/D ≤ 0.7 limit found the value only in an unidentified non-Aramco document "GS 130-5"), flange rating rules for tap flanges, tapping orientation for gas/liquid/steam, permitted meter types per service, and DP turndown limits. [general knowledge — verify] ([scribd GS 130-5](https://www.scribd.com/document/414532387/Gs130-5))

### 3.4 Pressure (SAES-J-200)

- **Title confirmed as "Pressure"** [secondary source] ([scribd J-200](https://www.scribd.com/document/494872703/Saes-j-200-Pressure)).
- **Publicly visible clauses** *(2nd pass)*, all [secondary source] from snippets of the 2008 and 2013 copies ([scribd J-200 (2)](https://www.scribd.com/document/439171375/SAES-J-200-Pressure), [scribd J-200 (3)](https://www.scribd.com/document/519224007/SAES-J-200)):
  - **Scope:** minimum mandatory requirements for the design and installation of pressure and differential-pressure (D/P) instruments, **in addition to PIP PCCPR001** (Process Industry Practice, pressure measurement criteria).
  - **Pressure gauges shall have safety glass** (2008 issue). The snippet continues with a truncated sentence starting "Plastic…" (probably about plastic windows; wording not visible) and says **hermetically sealed switch contacts are preferable** (pressure switches).
  - **All pulsation dampeners (snubbers), siphons, diaphragm seals and similar accessories shall be shown on the P&IDs.**
  - Instruments and accessories must meet the **ambient-condition requirements of SAES-J-003**, and locally mounted instruments the **area-classification requirements of SAES-B-068**.
  - Clause **4.4.1** adds requirements for **pressure transmitters in gas and vapour service** (content cut off in the snippet; probably mounting above the tap / self-draining impulse lines — unconfirmed).
  - Typical installations are referred to **Saudi Aramco Library Drawings** (numbers not visible).
- **Transmitter vs gauge rule** (when a transmitter is required instead of a local gauge): not found. [gap]
- Typical requirements found on Aramco projects, **still unconfirmed**: [general knowledge — verify]
  - gauges with 316SS internals, solid-front / blow-out-back safety pattern, and a nominal 100 mm (4") dial;
  - normal operating pressure in the middle portion of the scale;
  - over-range protection or snubbers for pulsating service;
  - diaphragm seals for viscous, corrosive or solidifying services;
  - transmitter isolation by manifolds (2-valve or 3/5-valve);
  - separate process taps for ESD and control transmitters (see §3.9).
- **Localization:** "Pressure Regulators & Valve actuators" is a named iKTVA instrumentation opportunity. [confirmed] ([aramco iKTVA deck](https://www.aramco.com/-/media/downloads/iktva/instrumentation.pdf))

### 3.5 Level (SAES-J-300)

- **Title confirmed as "Level"** [secondary source] ([englogs](https://englogs.com/saudi-aramco-engineering-standard-instrumentation-system/), [paktechpoint](https://paktechpoint.com/saudi-aramco-engineering-standard-for-electrical-instrumentation-and-cp/)). No J-300 clause text surfaced, even in the 2nd pass.
- **Related documents** *(2nd pass)*, all [secondary source]:
  - SAES-J-400 excludes level measurement and points to SAES-J-300. ([scribd J-400](https://www.scribd.com/document/519224174/SAES-J-400))
  - Older J-001 indexes list level data-sheet forms **ISS 8020-312-ENG "Level Gauge Glasses"** and **ISS 8020-314-ENG "Level Instruments"**. ([pdfcoffee J-001](https://pdfcoffee.com/saes-j-001-3-pdf-free.html), [scribd J-001](https://www.scribd.com/document/680621562/SAES-J-001))
  - Library drawings **DB-950046 "Instrument Piping Detail for Liquid Level Gauge Glasses"** and **DB-950047** (pneumatic level instruments) are cited by SAES-J-100. ([pdfcoffee J-100](https://pdfcoffee.com/saes-j-100-pdf-free.html))
  - **SATIP-J-300-01** is the typical inspection plan for level installations (cited by SAIC-J-6022). ([scribd SAIC-J-6022](https://www.scribd.com/document/324772531/SAIC-J-6022-Rev-0-pdf))
  - **Radar tank gauging** for hydrocarbon custody is governed by **SAES-Y-301** (custody measurement), not J-300. ([scribd SAES-Y-301](https://www.scribd.com/document/493616156/SAES-Y-301))
  - SAEP-1400's 9COM commodity list treats "Glass: Level Gauge" and radar tank gauging as separate commodity groups, and Aramco sourcing lists tie glass level gauges to **34-SAMSS-010**. ([scribd SAEP-1400](https://www.scribd.com/document/398466940/SAEP-1400-pdf), [Aramco India sourcing list Jan 2024](https://india.aramco.com/-/media/aramcoindia/sourcing-list/sourcing-list-jan-2024.pdf))
  - A displacer "≤ 48 in (1,200 mm) range" rule appeared in a Scribd level specification ("J-03") that does **not** name Aramco; do not attribute it to J-300. ([scribd J-03](https://www.scribd.com/document/396454916/J-03))
- **Level measurement** is a named iKTVA opportunity (Jan 2025 workshop). [confirmed] ([aramco iKTVA deck](https://www.aramco.com/-/media/downloads/iktva/instrumentation.pdf))
- Typical topics, **unconfirmed**: [general knowledge — verify]
  - restrictions on tubular glass gauges (use reflex/transparent or magnetic gauges);
  - acceptance of guided-wave radar and DP level transmitters;
  - displacer usage limits;
  - bridle/standpipe design;
  - independent level taps for ESD versus control;
  - interface measurement guidance.

### 3.6 Temperature (SAES-J-400)

- **Title confirmed as "Temperature"** [secondary source] ([scribd J-400](https://www.scribd.com/document/519224174/SAES-J-400)). Copy seen: issue date **28 Jun 2009**, next planned update 2013 (so certainly superseded).
- **Publicly visible clauses** *(2nd pass)*, [secondary source] from snippets of the 2009 copy ([scribd J-400](https://www.scribd.com/document/519224174/SAES-J-400)):
  - **Clause 5.2.2: weld-in thermowells shall only be used when ASME or Saudi Aramco standards or specifications require welded connections.** In other words, flanged (or otherwise removable) thermowells are the default.
  - A **mechanical protection sleeve** shall be considered for temperature sensors in areas with mechanical hazards (trigger conditions truncated).
  - Section **8.1.1** covers **filled-system** temperature instruments (the restriction itself was cut off).
  - J-400 excludes level measurement (see SAES-J-300).
- **Thermowell drawing and vibration:** SAES-J-100 (2020) cites **AB-036019 "Thermowell – Assembly and Detail"** and requires **FEA and CFD** for **helical (strake) thermowells**. [secondary source] ([pdfcoffee J-100](https://pdfcoffee.com/saes-j-100-pdf-free.html))
- **ASME PTC 19.3 TW** current edition is 2016, reaffirmed 2025; it covers mechanical (stress and wake-frequency) design only. Whether J-400 cites it by name was not confirmed. [confirmed for the ASME status] ([ANSI webstore PTC 19.3 TW](https://webstore.ansi.org/standards/asme/asmeptc19tw2016r2025), [ASME PTC 19.3 TW](https://www.asme.org/codes-standards/find-codes-standards/thermowells))
- "Temperature measurement" is a named iKTVA localization item (2022 deck). [confirmed] ([aramco iKTVA deck](https://www.aramco.com/-/media/downloads/iktva/instrumentation.pdf))
- **Thermocouple extension cable** is covered by **34-SAMSS-913** "Instrumentation and Thermocouple Cable". A vendor (Saudi Cable) describes thermocouple extension conductors to ANSI MC96.1 / IEC 60584. [secondary source] ([scribd QA/QC module](https://www.scribd.com/presentation/609393585/Training-Module-QA-QC), [Saudi Cable special cables](https://www.saudicable.com/products/special-cables/))
- Typical topics, **unconfirmed**: [general knowledge — verify]
  - thermowell design to ASME PTC 19.3 TW (wake-frequency calculation) — partly supported by the J-100 FEA/CFD clause above;
  - flanged thermowells in hydrocarbon service — consistent with J-400 clause 5.2.2 above (weld-in only where welded connections are required);
  - RTD (Pt100) versus thermocouple selection;
  - minimum line size for thermowells;
  - head-mounted transmitters.

### 3.7 Analyzers and gas detection (SAES-J-502, SAES-J-505, 34-SAMSS-514)

- **SAES-J-502 "Analyzer Shelters"** governs analyzer house design. [secondary source] ([englogs](https://englogs.com/saudi-aramco-engineering-standard-instrumentation-system/))
- **SAES-J-505 "Combustible Gas and Hydrogen Sulfide in Air Detection Systems"** governs the design of fixed gas detection (detector siting, alarm levels, voting, interface to ESD/F&G). [secondary source for the title] ([englogs](https://englogs.com/saudi-aramco-engineering-standard-instrumentation-system/))
- **34-SAMSS-514** is the purchase specification for stationary combustible gas and H2S detection and monitoring systems. Publicly visible requirement: **H2S monitor accuracy of ±4 ppm or ±10% of the applied test gas concentration, whichever is greater**. [secondary source] ([scribd 34-SAMSS-514](https://www.scribd.com/document/517672324/34-SAMSS-514))
- **Typical industry setpoints** (not Aramco-specific): combustible gas low alarm at 20% LFL and high at 40% LFL (Det-Tronics). H2S detection by electrochemical sensors. Use these only as context; the Aramco values are in SAES-J-505. [secondary source: vendor] ([Det-Tronics 505 manual](https://www.det-tronics.com/content/documents/95-8472-4.3%20(505%20CGS).pdf))
- **Gas monitoring** and **leak detection** are named iKTVA instrumentation opportunities (2025). [confirmed] ([aramco iKTVA deck](https://www.aramco.com/-/media/downloads/iktva/instrumentation.pdf))
- A separate analyzer standard may exist (SAES-J-510 was suggested in the brief), but this was **not confirmed**. [unverified]
- H2S is pervasive in Aramco gas plants (Khurais, Shaybah, Hawiyah, Haradh, Wasit, Fadhili, Jafurah sour/unconventional gas). Gas detection layouts and toxic-gas ESD causes are a major review focus. [general knowledge — verify]

### 3.8 Control valves (SAES-J-700, 34-SAMSS-711)

**SAES-J-700 "Control Valves" (application/installation).** All items below are [secondary source], from a Scribd checklist extract citing J-700 and an Aramco engineering-encyclopedia module ([scribd SAIC-L-2043](https://www.scribd.com/document/457762664/SAIC-L-2043), [pdfcoffee Control Valve Selection](https://pdfcoffee.com/control-valve-selection-pdf-free.html)):
- **Control valves shall not be used as ESD valves (ZVs) or as emergency isolation valves (EIVs).** This is a key Aramco rule: no dual-purpose control/shutdown valves. Where a SIF needs to close the line, a separate ZV is required.
- **Pneumatic actuator volume tanks** (used for fail-action or stroking reserve) are designed for a maximum of **930 kPag (135 psig) at 82 °C** and built to **ASME Section VIII Div. 1**.
- **Accessibility:** valve adjustments and gauges must be readable from grade or a permanent platform, walkway or fixed ladder.
- **Seat leakage:** shutoff classification is referenced to ANSI/FCI 70-2 (formerly ANSI B16.104) test criteria in a section 4.1.7 of SAES-J-700 (older issue numbering).
- Revision history: a minor revision in August 2004, with later issues since.

**34-SAMSS-711 "Control Valves" (purchase specification).** [confirmed]
- Owned by the Instrumentation Standards Committee. Issues seen: 4 Jan 2012 and 11 Oct 2017 (next planned update 11 Oct 2020; a newer issue probably exists). ([scribd 711](https://www.scribd.com/document/468687176/34-SAMSS-711-pdf), [scribd 711 older](https://2.gy-118.workers.dev/:443/https/www.scribd.com/document/341217972/34-SAMSS-711))
- The manufacturer is responsible for the design, construction and durability of the valve. Topics covered include body/trim requirements and globe valve guiding. [secondary source]
- A search summary also attributed applicability "to control valves used in on/off service or interlock applications" to a document in this family. Whether that clause is from 34-SAMSS-711 or from a separate on/off specification is **not resolved**. [secondary source — ambiguous]
- **Scope boundary:** 04-SAMSS-035 (general requirements for valves) excludes valves under SAMS Class 34 (control, safety-relief, relief, surge-relief, solenoid, pilot valves). Those fall under 34-SAMSS. [secondary source] ([es.scribd 04-SAMSS-035](https://es.scribd.com/document/382959447/04-SAMSS-035-ARAMCO-General-Reuirement-for-Valves-pdf))
- **Vendor example:** Severn Glocon reported supplying 16″ x 24″ Class 300 control valves for sour-gas-to-flare service to Saudi Aramco, with double-acting pneumatic actuators, smart positioners and side-mounted handwheels. This illustrates typical Aramco severe-service features. [secondary source: vendor] ([Valve World](https://valve-world.net/?p=53143))
- **Typical (unconfirmed) Aramco control valve practice:** [general knowledge — verify]
  - smart HART positioners;
  - noise limit of 85 dBA at 1 m;
  - sizing to IEC 60534;
  - valve size at least half the line size;
  - min/normal/max travel windows on the data sheet;
  - sour-service trim per NACE MR0175;
  - fire-safe requirements where applicable;
  - bypass/block valve philosophy per P&ID.

### 3.9 ESD / ZV / emergency isolation and SIS (SAES-J-601, SAES-B-058, 34-SAMSS-621/622/623/634)

**SAES-J-601 "Emergency Shutdown and Isolation Systems".** [confirmed for the title]
- The issue seen in a 2006 index is dated 29 Jun 2005 (previous 31 Mar 2001, next planned update Feb 2010). It is still cross-referenced by SAES-J-100 (Oct 2020) and SAES-Z-001 (2012 draft), so it remains the governing instrumentation standard for ESD and isolation. ([scribd INDX-SAES](https://www.scribd.com/document/527150981/INDX-SAES), [mirror J-100](https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-31108---Tecnicas---Riyas/RFQ-Files/SAES-J-100))
- **Relationship to SAES-B-058** (Emergency Shutdown, Isolation and Depressuring): B-058 (loss prevention) decides *where* ESD, isolation and depressuring are required. It refers to SAES-J-601 for "other pertinent instrumentation and alarm requirements". [secondary source] ([pdfcoffee B-058](https://pdfcoffee.com/saes-b-058-pdf-free.html))
- **SAES-Z-001** excludes ESD systems (covered by J-601) from the PCS scope except for their interfaces. **Keep the ESD system separate from the DCS.** [secondary source] ([pdfcoffee Z-001](https://pdfcoffee.com/saes-z-001-pdf-pdf-free.html))
- **SAES-J-100 clause 4.1.2:** instruments selected for ESD service must also meet SAES-J-601. [secondary source]
- **SIL / IEC 61508/61511:** later issues of SAES-J-601 are widely understood to require SIL determination and verification aligned with IEC 61511. Typical elements are separate sensors for ESD and control, 2oo3 voting on critical initiators, de-energize-to-trip design, and proof-test intervals. **No public excerpt confirming the SIL clauses was found.** [general knowledge — verify]
- *(2nd pass)* Three targeted searches (J-601 + SIL/IEC 61511/2oo3; J-601 + proof-test interval; "SAEP-250" SIL) returned no Aramco text. No issue of J-601 later than 29 Jun 2005 surfaced; the project-variant **YERP-SAES-J-601** (Yanbu, referenced by YERP-SAES-B-058 issued 29 Apr 2008) shows the standard was still being adapted in 2008. The SIL determination method (risk graph vs LOPA), voting rules, proof-test intervals and the existence/number of an Aramco SIL-assessment SAEP all remain **unconfirmed**; do not quote "SAEP-250" as Aramco's SIL procedure. [secondary source for the YERP reference] ([es.scribd YERP-PE-YSS-0048](https://es.scribd.com/document/178151012/100-YER-PE-YSS-0048))
- A separate J-60x standard covers boilers: **SAES-J-602 "Burner Management, Combustion and Waterside Control Systems for Watertube Boilers"** (31 Jan 2005 issue in the 2006 index). Use it, not J-601, for boiler BMS questions. [secondary source] ([scribd INDX-SAES](https://www.scribd.com/document/527150981/INDX-SAES))

**ZV (emergency isolation valve) testing and local control (34-SAMSS-634).** [secondary source] ([scribd 34-SAMSS-634](https://www.scribd.com/document/370514106/174038738-34-SAMSS-634-pdf))
- 34-SAMSS-634 covers local emergency isolation valve control systems, including **smart ZV controllers** with **partial-stroke testing**.
- **All ZVs must be designed and installed so that they can be functionally tested while on-line (in service).**
- Partial-stroke testing *complements* full-stroke testing; it does not replace it. PST is used to meet the required functional test interval between scheduled shutdowns, and full-stroke tests are done during shutdowns.
- Aramco has patented ZV-related test devices (for example a locally actuated partial stroke testing system and a pneumatic EIV switchover kit), which shows how much attention it pays to ZV testability. [confirmed: USPTO] ([US 10557564](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10557564), [US 12152615](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12152615))

**ESD logic solver technologies (34-SAMSS-62x).**
- **34-SAMSS-621** covers hard-wired solid-state (nonprogrammable) ESD systems. It excludes PLC-based ESD (34-SAMSS-623) and relay-based ESD (34-SAMSS-622). [confirmed] ([pdfcoffee 621](https://pdfcoffee.com/34-samss-621-pdf-free.html))
- **34-SAMSS-622** covers electromagnetic relay ESD systems. [secondary source]
- **34-SAMSS-623** covers programmable-controller-based ESD; it references 34-SAMSS-820 for cabinets. [secondary source]
- Modern Aramco projects generally use TÜV-certified safety PLCs from the process-automation RVL for ESD. Hard-wired solid-state or relay systems are kept for small or remote facilities and simple trips. [general knowledge — verify]

**Inspection:** SAIC-J-6806 covers ESD and power supply inspection (cabinet construction per 34-SAMSS-820). [secondary source] ([scribd SAIC-J-6806](https://www.scribd.com/document/525615451/SAIC-J-6806))

**Important rule (repeated):** control valves must **not** be used as ZVs or EIVs (SAES-J-700). [secondary source]

### 3.10 Pressure relief devices (SAES-J-600, 34-SAMSS-611, SAEP-318, SAES-J-605)

- **SAES-J-600 "Pressure Relief Devices"** (2005 issue in the 2006 index) covers relief device selection and installation. Aramco tags relief valves **PZV**. [confirmed] ([scribd Indx-saes 2006](https://www.scribd.com/document/527150957/Indx-saes-Oct-2006))
- **SAEP-318** (relief valve programme; copy seen 2015) applies to relief valves "also defined as PZV in SAES-J-600" on fixed, mobile, skid-mounted and packaged equipment. It covers the relief-valve data, testing and maintenance programme (bench testing, set-pressure records). [secondary source] ([scribd SAEP-318](https://www.scribd.com/document/473260773/SAEP-318-pdf), [scribd relief valve procedure](https://www.scribd.com/document/507299437/Relief-Valves-Procedure))
- **34-SAMSS-611** covers conventional and balanced-bellows industrial safety relief valves and modifies **API STD 526**. Data sheet **ISS 8020-611-ENG**. Issue seen 20 Mar 2013. [secondary source] ([es.scribd 34-SAMSS-611](https://es.scribd.com/document/295779795/34-SAMSS-611))
  - General engineering background: conventional valves suit back-pressure below about 10% of set; balanced valves protect the bonnet, spring and guide and reduce back-pressure effects. [secondary source] ([projectmaterials](https://blog.projectmaterials.com/valves/safety-valve-asme-api/))
- **Pilot-operated PRVs** are probably covered by a separate 34-SAMSS (number not confirmed). [unverified]
- **SAES-J-605 "Surge Relief Protection Systems"** covers surge relief on pipelines and loading systems. [secondary source] ([scribd Indx-saes 2006](https://www.scribd.com/document/527150957/Indx-saes-Oct-2006))
- Typical Aramco PSV practice, **unconfirmed**: [general knowledge — verify]
  - sizing per API 520/521;
  - inlet loss below 3% and built-up back-pressure limits;
  - car-sealed-open isolation valves with spare PSV philosophy where on-line testing is needed;
  - discharge piping self-draining to flare;
  - set-pressure tolerance and blowdown per API 526/ASME VIII.

### 3.11 Valve actuators: MOV, pneumatic, hydraulic (34-SAMSS-716/717/718)

**Correction to a common assumption:** **34-SAMSS-716 is "Pneumatic Actuators – On-Off Service", not MOVs.** The MOV specification is **34-SAMSS-718** "Electric Motor Operated Valve Actuators". [secondary source, consistent across two copies] ([pdfcoffee 716](https://pdfcoffee.com/34-samss-716-pdf-free.html), [scribd 718](https://www.scribd.com/document/536743257/34-SAMSS-718))

- **34-SAMSS-716** (10 Aug 2009 copy) sets minimum requirements for pneumatic actuators in on-off service, for example ZV actuators. [secondary source]
- **34-SAMSS-717** covers hydraulic valve actuator systems. [secondary source] ([scribd 717](https://www.scribd.com/document/486500518/34-SAMSS-717))
- **34-SAMSS-718** (26 Jan 2009 copy) sets minimum requirements for electric motor-operated valve actuators. It **excludes electric actuators for wellhead surface safety valves**. [secondary source]
- **Vendor inconsistency:** one supplier (Rotex) claims its electro-hydraulic actuators for the Jafurah project meet "34-SAMSS-716". Vendor compliance statements can mis-cite specifications, so always check against the actuator type. [secondary source] ([DirectIndustry Rotex](https://trends.directindustry.com/rotex-automation-limited/project-61940-1158162.html))
- **9COM approvals for actuators** exist for Emerson Bettis (Houston) and Emerson Shafer (gas-over-oil/hydraulic). [confirmed: vendor-hosted approval letters] ([Emerson Bettis 9COM letter](https://emerson.com/documents/automation/approval-aramco-9com-approval-letter-houston-bettis-en-202308.pdf), [Emerson Shafer 9COM letter](https://emerson.com/documents/automation/approval-saudi-aramco-9com-approval-letter-shafer-en-86406.pdf))
- **Valve actuators** are a named iKTVA localization category in both the 2022 and 2025 decks. [confirmed] ([aramco iKTVA deck](https://www.aramco.com/-/media/downloads/iktva/instrumentation.pdf))
- Typical MOV topics, **unconfirmed**: [general knowledge — verify]
  - intelligent, non-intrusive actuators;
  - integral control with local/remote selector;
  - network interface (Modbus, FF or Profibus per project);
  - torque sizing margin;
  - ESD-rated MOVs requiring fire-proofing of actuator and cable where the MOV performs isolation duty under SAES-B-058.

### 3.12 Panels, cabinets, packaged units and control buildings (34-SAMSS-820/821/831, SAES-J-801)

**34-SAMSS-820 (indoor)** covers instrument control panels, control cabinets and marshalling cabinets located in **electrically unclassified, air-conditioned buildings**. Issues seen: 2007, 2016. It is referenced by other specifications (for example the PLC/ESD cabinet requirements) for cabinet construction and wiring. [confirmed] ([scribd 820](https://www.scribd.com/document/494624754/424411678-34-samss-820), [pdfcoffee 820](https://pdfcoffee.com/34-samss-820-pdf-free.html))

**34-SAMSS-821 (outdoor)** sets the minimum requirements for instrument control panels and cabinets **in outdoor areas**. All of 34-SAMSS-820 applies unless 821 supersedes it, so 820 is the baseline and 821 adds outdoor-specific requirements (enclosure, sun/heat, hazardous area). Issues seen: 2005, 2012. [confirmed] ([scribd 821](https://www.scribd.com/document/536743247/34-SAMSS-821), [pdfcoffee 821](https://pdfcoffee.com/34-samss-821-pdf-free.html))

**34-SAMSS-831 "Instrumentation for Packaged Units"** (25 Mar 2021 copy). [confirmed] ([studylib 831](https://studylib.net/doc/27696645/34-samss-831))
- Applies to pre-engineered, pre-assembled, pre-wired **skid-mounted** packages. It does **not** apply to custom-engineered packages, which must meet the full mandatory SAES set.
- **Alarm and shutdown systems must be fail-safe.**
- **Fused terminals** are required for power distribution, alarm and shutdown circuits.
- Package wiring that interfaces with plant wiring must **terminate in junction boxes** at the skid edge.
- Instruments are mounted as close to the process connection as practical.
- Inspection: SAIC-J-6022. [secondary source] ([scribd SAIC-J-6022](https://www.scribd.com/document/324772531/SAIC-J-6022-Rev-0-pdf))
- **Pitfall:** vendors often claim "standard package" status to apply 34-SAMSS-831 instead of the full SAES-J set. Aramco reviewers challenge this when the package is project-specific. [general knowledge — verify]

**SAES-J-801 "Control Buildings"** covers control buildings. **HVAC system monitoring must comply with SAES-J-801** (cited in HVAC inspection checklist SAIC-K-4044 via SAES-K-002). SAES-B-014 (plant and operations support buildings) lists J-801 as a reference. [secondary source] ([pdfcoffee SAIC-K-4044](https://pdfcoffee.com/saudi-aramco-inspection-checklist-pressurized-building-hvac-requirements-saic-k-4044-30-apr-13-hvac-pdf-free.html), [scribd B-014](https://www.scribd.com/document/405891268/SAES-B-014))
- Typical content, **unconfirmed**: [general knowledge — verify]
  - blast resistance per the building's siting study (SAES-B-014);
  - positive pressurisation;
  - HVAC redundancy for the equipment rooms (to hold the 35 °C indoor design limit of SAES-J-003);
  - raised floors / cable entry sealing;
  - a separate rack room versus operator console room;
  - Process Interface Buildings (PIBs) / Remote Instrument Buildings near the units, with fibre to the Central Control Room (CCR).

### 3.13 Power, wiring and grounding for instrumentation (SAES-J-902, 34-SAMSS-913)

**SAES-J-902 "Electrical Systems for Instrumentation"** sets design criteria for installing power and wiring systems for electrical instrumentation. Issues: 2013, 2017, 26 Mar 2020 (next planned update 26 Mar 2025). [confirmed] ([scribd J-902](https://www.scribd.com/document/426879234/SAES-J-902-pdf), [mirror J-902](https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-31108---Tecnicas---Riyas/RFQ-Files/SAES-J-902))
- **Cross-references:** SAES-P-103 (Batteries and UPS Systems) and SAES-P-111 (Grounding). UPS and earthing details come from those P-series standards. [secondary source]
- **IS systems:** J-902 limits intrinsically safe systems to **Zone 0** applications, or to cases where the vendor's standard product is already IS. IS systems must be installed per SAES-J-903. [secondary source, clauses cited as 10-4/10-5 in a checklist extract] ([scribd SAIC-J-6904](https://www.scribd.com/document/226927140/SAIC-J-6904-Rev-0))
- **FF wiring** must be installed per SAES-J-904. [secondary source] ([Control Global](https://www.controlglobal.com/network/industrial-networks/article/11321803/foundation-fieldbus-in-hazardous-areas))
- **Cable:** 34-SAMSS-913 "Instrumentation and Thermocouple Cable" governs cable construction. A QA/QC training module cites its jacket-application and colour clauses (6.3.17, 6.5.27). [secondary source] ([scribd QA/QC](https://www.scribd.com/presentation/609393585/Training-Module-QA-QC))
- **Saudi Cable Company** holds Aramco 9COM approvals for its cable products. [confirmed: vendor-hosted] ([Saudi Cable 9COM](https://www.saudicable.com/wp-content/uploads/2025/12/9Com-Saudi-Aramco_SCC-New-1.pdf))
- Typical content, **unconfirmed**: [general knowledge — verify]
  - redundant UPS-fed 120 VAC or 24 VDC instrument power;
  - separate distribution for ESD and DCS;
  - segregation of IS/non-IS, analog/digital and power/signal cables in trays and junction boxes;
  - an isolated instrument earth / signal reference bar connected to the plant grid at a single point per SAES-P-111;
  - shields grounded at one end only (control room);
  - armoured cable direct-buried or in trays;
  - junction-box material (316SS or GRP) and entries via certified glands;
  - spare core and spare terminal allowances (commonly 20%).

### 3.14 Intrinsic safety and hazardous-area practice (SAES-J-903, SAES-B-068)

- **SAES-J-903 "Intrinsically Safe Systems"** (2005 issue in the 2006 index) covers IS system design and installation. [confirmed for the title] ([scribd INDX-SAES](https://www.scribd.com/document/527150981/INDX-SAES))
- Installation rules cited in SAIC-J-6904 (secondary source; [scribd SAIC-J-6904](https://www.scribd.com/document/226927140/SAIC-J-6904-Rev-0)):
  - **Dedicated IS junction boxes**: IS wiring kept separate from non-IS wiring.
  - **Multi-core cables must not mix IS and non-IS circuits.**
- **SAES-B-068 (Electrical Area Classification):** only listed (certified) IS equipment may be installed in Zone 0, per SAES-J-903. [secondary source] ([scribd B-068](https://www.scribd.com/document/655719750/SAES-B-068))
- **Aramco protection-method culture:** a Control Global article (written with Aramco involvement) reports that Aramco has historically **not relied heavily on IS** and has mainly used **Ex d (flameproof)** in classified areas. It used **Ex nL (non-incendive, energy-limited)** for FF spurs to allow live maintenance, and was considering migrating toward IS/Ex ic designs. [secondary source] ([Control Global 2015](https://www.controlglobal.com/articles/2015/foundation-fieldbus-in-hazardous-areas/))
- **Hazardous-area classification method:** Aramco uses a Class/Division and Zone system under SAES-B-068 (NEC/API RP 500/505 lineage). Equipment certification must match the classification method used on the area classification drawings. [general knowledge — verify]

### 3.15 FOUNDATION fieldbus (SAES-J-904, SABP-J-900)

- **SAES-J-904** covers the design, specification, installation, configuration, commissioning and maintenance of **FOUNDATION fieldbus-based control systems** (as described in SAES-Z-010). [confirmed] ([pdfcoffee Z-010](https://pdfcoffee.com/saes-z-010-pdf-pdf-free.html))
- **Hazardous-area requirements** cited in SABP-J-900, a 2016 best practice that points to J-904 ([scribd SABP-J-900](https://round-lake.dustinice.workers.dev:443/https/www.scribd.com/document/493616203/SABP-J-900)) [secondary source]:
  - **Field devices in Zone 2 must be certified Ex ic** (per SAES-J-904).
  - **Wiring blocks (device couplers) in Zone 2 must be certified Ex ic.**
  - **Spur cable: FF Type A** (per J-904).
- **Spur protection:** Aramco used **Ex nL** on FF spurs to allow live maintenance, with a planned move toward IS/Ex ic. The article (by Aramco engineers) states the Zone 2 scheme as **Ex nA for the trunk and Ex nL for the spurs**. [secondary source] ([Control Global](https://www.controlglobal.com/network/industrial-networks/article/11321803/foundation-fieldbus-in-hazardous-areas))
- **Segment length and current limits** *(2nd pass)*, as summarised from the SABP-J-900 best practice (which cites J-904) [secondary source — search summary of an unofficial copy; check whether these are J-904 requirements or SABP guidance] ([scribd SABP-J-900](https://round-lake.dustinice.workers.dev:443/https/www.scribd.com/document/493616203/SABP-J-900)):
  - **total segment length ≤ 1,900 m** (trunk plus spurs; matches the IEC 61158-2 Type A cable limit);
  - **each spur ≤ 120 m**;
  - wiring blocks (device couplers) with **short-circuit current limiting that clamps at about 55 mA DC** per spur.
- **Devices per segment:** no Aramco number was found. An Aramco engineer told Control Global that Aramco has **increased the number of devices per segment as confidence in the technology grew**, without giving a figure. Generic FF/Profibus PA limits are up to 32 devices per segment, with many hosts limiting to 16. [secondary source] ([Control Global](https://www.controlglobal.com/network/industrial-networks/article/11321803/safety-foundation-fieldbus-in-hazardous-areas), [Power Magazine primer](https://www.powermag.com/a-fieldbus-primer/))
- **Voltage margin at the furthest device:** not found in any public J-904 excerpt. [gap]
- The YERP FF specification (which applies J-904 "except as noted") includes a section on **FF field JB segment design/loading**, but its numbers were not visible. [secondary source] ([scribd YERP FF](https://www.scribd.com/doc/142169992/192-YER-PE-I35-0011))
- **Aramco endorsement of fieldbus:** an Aramco expatriate article, "Fieldbus: a solution for plant engineers", describes Aramco's adoption of FF. [secondary source] ([aramcoexpats](https://aramcoexpats.com/articles/fieldbus-a-solution-for-plant-engineers))
- **DCS for FF:** process-automation RVLs list DCS vendors qualified under **23-SAMSS-010** for FF systems. [secondary source] ([scribd SAES-Z-002](https://www.scribd.com/doc/239724008/Saes-z-002-Locked-by-Badr))
- **Project variant:** the YERP FF specification says all Saudi Aramco standards apply to FF systems except as noted. [secondary source] ([scribd YERP FF](https://www.scribd.com/doc/142169992/192-YER-PE-I35-0011))
- Typical segment rules found on Aramco FF projects, **unconfirmed** (check against J-904): [general knowledge — verify]
  - a maximum number of devices per segment (commonly 12 to 16 including spares, with spare capacity for future devices; the Aramco interview above suggests the limit has been relaxed over time);
  - a maximum of one final control element per segment, or a "risk-ranking" limit on critical loops per segment;
  - **no ESD/SIF functions on FF** (ESD stays hard-wired 4–20 mA / discrete to the SIS);
  - redundant power conditioners;
  - segment voltage at the furthest device of at least 9 V with margin;
  - maximum segment and spur lengths per IEC 61158-2 (1,900 m / 120 m now supported by SABP-J-900, see above);
  - macrocycle loading limits;
  - FF device registration (ITK) and DD files validated against the host;
  - segment checkout with an FF diagnostic tool at commissioning;
  - FF Engineering Guidelines (FieldComm AG-181) commonly used as the companion reference. ([FieldComm AG-181](https://www.FieldCommgroup.org/sites/default/files/imce_files/technology/documents/Ff_system_engineering_guidelines_version_3.2.1.pdf))

### 3.16 DCS / PCS / SCADA / networks (SAES-Z-001/002/004/010, 23-SAMSS-010/020/072)

- **SAES-Z-001 "Process Control Systems"** covers PCS design and **includes process control networks**. It **excludes ESD (SAES-J-601) and SCADA (SAES-Z-004) except for their interfaces to the PCS**. It also covers installation of proprietary PCS (per Z-010). Public copy: draft dated 22 Jul 2012. [confirmed] ([pdfcoffee Z-001](https://pdfcoffee.com/saes-z-001-pdf-pdf-free.html), [scribd Z-010](https://www.scribd.com/document/415401236/SAES-Z-010-pdf))
- **SAES-Z-002:** a 2006 copy (issue 28 May 2006, next planned update 2011) shows "Process Automation Systems" in its header. It identifies acceptable manufacturers of process automation systems and does not cover purchasing for SAMSS stock replenishment. Its listings are **Restricted Vendor Lists** for host systems (**DCS, SCADA**) and **Recommended Vendor Lists** for subsystems (for example **ESD, RTU**); recommended products are those evaluated by P&CSD (Process & Control Systems Department) and found technically acceptable. RVLs are prepared under **SAEP-15**. Other documents (e.g. SABP-Z-002E for compressor control) require systems to be "technically acceptable under SAES-Z-002". [secondary source; details added in 2nd pass] ([scribd Z-002](https://www.scribd.com/doc/239724008/Saes-z-002-Locked-by-Badr), [scribd Z-002 (2)](https://www.scribd.com/document/354870462/SAES-Z-002-LOCKED-BY-BADR-pdf), [scribd SAEP-15](https://www.scribd.com/document/429080803/SAEP-15-pdf), [scribd SABP-Z-002E](https://www.scribd.com/document/403474712/SABP-Z-002E-pdf))
- **SAES-Z-004 "Supervisory Control and Data Acquisition (SCADA) System"** (10 Nov 2013 copy) applies to anyone designing new, upgraded or expanded SCADA in Aramco facilities, and refers to SAES-Z-010 for the PAN. [confirmed] ([pdfcoffee Z-004](https://pdfcoffee.com/saes-z-004-pdf-free.html))
- **SAES-Z-010 "Process Automation Networks"** covers the plant-wide **PAN** that links the individual PCNs and provides the interface to the corporate WAN. It is based on **IEEE 802.3 (Ethernet)** (2009 issue) and applies to all process automation networks based on standard protocols. [confirmed] ([scribd Z-010](https://www.scribd.com/document/415401236/SAES-Z-010-pdf), [pdfcoffee Z-010](https://pdfcoffee.com/saes-z-010-pdf-pdf-free.html))
- **23-SAMSS-010** is the **DCS** purchase specification and **23-SAMSS-020** the **SCADA** purchase specification. [secondary source] ([es.scribd 23-SAMSS-020](https://es.scribd.com/document/319694317/23-SAMSS-020))
- **23-SAMSS-072** covers **Data Acquisition and Historization Systems** (plant historians, PI-type). [secondary source] ([scribd SABP-Z-019](https://www.scribd.com/document/509522885/SABP-Z-019))
- A public Saudi government checklist (EXPRO) for a "DCS Block Diagram" review indicates the kind of DCS deliverable review used in Saudi public-sector projects. It is not Aramco, but similar in style. [secondary source] ([expro.gov.sa checklist](https://expro.gov.sa/api/uploads/Checklist%20%20Distributed%20Control%20System%20DCS%20Block%20Diagram.docx))
- Typical DCS requirements on Aramco projects, **unconfirmed**: [general knowledge — verify]
  - redundant controllers, power supplies and network;
  - I/O card redundancy for critical loops;
  - spare capacity, typically 20% installed spare I/O and 20% spare space, plus processor/memory loading limits (for example below 50–60% at FAT);
  - time synchronisation (GPS/NTP);
  - an alarm management philosophy (ISA-18.2 / EEMUA 191);
  - Integrated FAT (IFAT) of DCS + SIS + third-party interfaces;
  - a Main Automation Contractor (MAC) model on large projects.

### 3.17 Cybersecurity

- **SACS-002 "Third Party Cybersecurity Standard"** is published on aramco.com for suppliers and contractors. It defines the cyber controls third parties must meet when handling Aramco data or connecting to Aramco systems. [confirmed] ([SACS-002 on aramco.com](https://SaudiAramco.com/-/media/downloads/working-with-us/ccc/sacs-002-third-party-cybersecurity-standard.pdf))
- **Process-automation network security** is covered by **SAEP-99** and the best practice **SABP-Z-057**, both of which cite SAES-Z-010. [secondary source] ([scribd Z-010](https://www.scribd.com/document/415401236/SAES-Z-010-pdf))
- Aramco's 2023 annual report risk section discusses cybersecurity risk to its operations, which shows the corporate-level priority. [confirmed: aramco.com] ([Aramco ARA 2023 risk](https://aramco.com/-/media/images/investors/annual-report/2023/ara-2023-risk-english.pdf))
- National framework: Saudi NCA Operational Technology Cybersecurity Controls (OTCC) apply to critical national infrastructure including Aramco OT. [general knowledge — verify]
- Typical project requirements, **unconfirmed**: [general knowledge — verify]
  - IEC 62443 zone/conduit segmentation;
  - a DMZ between PCN/PAN and the corporate network;
  - no direct internet connectivity;
  - hardened hosts with whitelisting;
  - removable-media control;
  - a vendor remote-access prohibition or controlled-access process;
  - a cyber security assessment before connection.

---

## 4. Vendor approval: 9COM, RVL and plant approval

**9COM numbers.**
- A **9COM** is Aramco's material classification code (a 10-digit number beginning with 6000…). It describes a **commodity or class of materials**, not a specific catalogued item. Non-catalogued 9COM items are not stocked by Aramco but may be stocked by suppliers. [secondary source] ([scribd SAEP-1400](https://www.scribd.com/document/398466940/SAEP-1400-pdf))
- Example: **9COM 6000002915 "Flowmeter; Coriolis Mass"** appears in SAEP-1400 listings. [secondary source]
- **SAEP-1400** (Instrumentation Standards Committee) ties the **technical evaluation of instrumentation manufacturers to 9COM numbers**. A manufacturer is technically evaluated per 9COM and per manufacturing plant. [secondary source] ([scribd SAEP-1400](https://www.scribd.com/document/398466940/SAEP-1400-pdf))

**Plant approval letters.**
- Aramco issues manufacturers letters confirming that a specific **manufacturing plant (Plant ID)** is approved for named **9COMs**, with any "facility limitations". Public examples: Emerson Shafer and Emerson Bettis Houston. [confirmed: vendor-hosted letters] ([Shafer](https://emerson.com/documents/automation/approval-saudi-aramco-9com-approval-letter-shafer-en-86406.pdf), [Bettis Houston](https://emerson.com/documents/automation/approval-aramco-9com-approval-letter-houston-bettis-en-202308.pdf)); also Saudi Cable ([SCC 9COM](https://www.saudicable.com/wp-content/uploads/2025/12/9Com-Saudi-Aramco_SCC-New-1.pdf)).
- A **Plant ID** identifies each physical manufacturing location. A **Vendor ID** identifies the supplier or authorised distributor. **Approval is per plant**: the same brand made at a non-approved factory is **not** approved. [secondary source]
- Aramco Americas/AOC publish supplier registration FAQs and SAEP-31 appendices for supplier qualification. [confirmed: aramco.com] ([Aramco Americas FAQ](https://americas.aramco.com/en/partnering-with-us/current-supplers/frequently-asked-questions), [SAEP-31 Appendix A](https://europe.aramco.com/-/media/aramcoaoc/procurement/saep-31-appendix-a.docx))

**Restricted Vendor Lists (RVL).**
- For **process automation systems** (DCS, SCADA, ESD/PLC, possibly analyzers and historians), an RVL is the **exclusive list of vendors and product lines** qualified for each class of equipment, prepared under **SAEP-15**. DCS vendors for FF systems appear against 23-SAMSS-010, and SCADA vendors against 23-SAMSS-020. [secondary source] ([scribd Z-002](https://www.scribd.com/doc/239724008/Saes-z-002-Locked-by-Badr))
- Analogous regulated vendor lists exist in other disciplines, for example **SAES-K-110** "Regulated Vendors List for Compressors, Expanders, Gears and Steam Turbines" (2016). This confirms the general "regulated/restricted vendor list" mechanism. [secondary source] ([pdfcoffee SAES-K-110](https://pdfcoffee.com/download/saes-k-110-pdf-free.html))

**Sourcing lists.** Aramco publishes sourcing/registration opportunity lists (AOC, Aramco India, Aramco China) inviting suppliers to register for specific SAMSS/commodity areas. [confirmed: aramco.com] ([Aramco India sourcing list Jul 2026](https://india.aramco.com/-/media/aramcoindia/sourcing-list/3-jul-2026-sourcing-list-india.pdf), [AOC sourcing list Jan 2026](https://europe.aramco.com/-/media/aramcoaoc/sourcing-list/aoc-1st-jan-2026-sourcing-list.pdf))

**Practical EPC rules** [general knowledge — verify]:
1. Check every instrument line item on the requisition against the vendor's **9COM approval for that plant** before PO. Request the approval letter or a screenshot from the Aramco supplier system.
2. If the vendor is not approved, the options are: (a) choose an approved source, or (b) request Aramco's evaluation per SAEP-1400. Option (b) is slow and not guaranteed.
3. Bid tabulations (TBE) sent to Aramco should show the 9COM, the approved plant and any deviations explicitly.

---

## 5. iKTVA and localization

- **iKTVA** (In-Kingdom Total Value Add) is Aramco's localization programme. It scores bidders on in-Kingdom spend, Saudi workforce, training and supplier development. It is a weighted factor in tender evaluation. [confirmed] ([aramco.com iKTVA](https://www.aramco.com/en/what-we-do/commercial-ecosystems/iktva))
- **Instrumentation localization deck (iKTVA Forum, January 14, 2025)** lists about ten instrumentation opportunities: **leak detection, level measurement, flow measurement, custody measurement, multiphase flowmeters, gas monitoring, pressure regulators and valve actuators**, among others. A 2022 deck covered **process flowmeters, temperature measurement, instrument manifolds, tubing and fittings, and valve actuators**. [confirmed] ([aramco iKTVA instrumentation deck](https://www.aramco.com/-/media/downloads/iktva/instrumentation.pdf))
- Aramco reported reaching its localization target (about 70% local content benchmark per press coverage). [secondary source] ([MEED](https://guest.meed.com/?p=15362), [astrsa blog](https://astrsa.com/blog/aramco-iktva-70-percent-localization-200000-jobs))
- Major automation vendors have signed iKTVA MoUs with Aramco, for example Emerson in 2022. [confirmed: vendor press release] ([Emerson MoU](https://s1-live.emerson.com/en-ae/news/automation/22-1-mou-agreement-signed-saudi-aramco-iktva))
- **EPC implications:**
  - Expect iKTVA plans in bids.
  - Expect preference or mandates for in-Kingdom manufacturing or assembly of local-content categories (for example cabinets, junction boxes, cable, tubing/fittings, certain transmitters/actuators).
  - Expect the requirement to use **Saudi-based approved plants** where they exist. A locally assembled product needs its own 9COM plant approval.
  
  [general knowledge — verify]

---

## 6. Project execution, design review and inspection

**Project phases and reviews.** [general knowledge — verify throughout this subsection]
- Aramco capital projects follow a gated process:
  1. Business Case / Study.
  2. **DBSP** (Design Basis Scoping Paper).
  3. **Project Proposal (PP)**, roughly 30% engineering, often done by a separate GES+/PP contractor.
  4. **Detailed Design** with formal reviews at roughly **60% and 90%**.
  5. Issued-for-Construction (IFC).
  6. Construction, pre-commissioning and commissioning.
  7. Mechanical Completion Certificate.
- Reviews are formal and comment-tracked. Aramco's Project Management Team (PMT) and **Consulting Services Department (CSD)** I&C specialists review against the mandatory SAES/SAMSS set.
- **SAEP-303** is confirmed *(2nd pass)* as the procedure for **formal engineering reviews of project proposals and detailed design packages** (and other mandatory engineering documents) by Saudi Aramco reviewing organisations. Copies dated 1 Jun 2008, 13 Dec 2011 and 21 Nov 2016 circulate. **SAEP-14** (Project Proposals) requires the schedule to include the review times specified in SAEP-303; **SAEP-12** is the Project Execution Plan procedure. [secondary source] ([scribd SAEP-303](https://www.scribd.com/document/473260763/SAEP-303-pdf), [pdfcoffee SAEP-303](https://pdfcoffee.com/saep-303-pdf-pdf-free.html), [scribd SAEP-14](https://www.scribd.com/document/661288589/SAEP-14))
- The "60% / 90%" review milestones above were **not** found in any public SAEP-303 or SAEP-14 snippet; treat them as typical project practice. [general knowledge — verify]
- Typical I&C deliverables at each review: instrument index, data sheets (ISS), I/O list, cause & effect diagrams, SIL assessment/verification reports, control narratives, system architecture, FF segment drawings and calculations, cable schedules, hook-ups, location layouts, cabinet GAs, power/heat load calculations and control building layouts.

**Vendor document review** uses Aramco's SDRL (Supplier Document Requirements List) and approval-code categories on each vendor document. [general knowledge — verify]

**Inspection.**
- Aramco Inspection (Vendor Inspection Division and the site inspection department) uses **SATIPs** (Typical Inspection Plans) and **SAIC** (inspection checklists) per discipline, for example:
  - SAIC-J-6022 (packaged units);
  - SAIC-J-6904 (IS systems);
  - SAIC-J-6806 (ESD / power supply).
  
  [secondary source] ([scribd SAIC-J-6022](https://www.scribd.com/document/324772531/SAIC-J-6022-Rev-0-pdf), [scribd SAIC-J-6904](https://www.scribd.com/document/226927140/SAIC-J-6904-Rev-0), [scribd SAIC-J-6806](https://www.scribd.com/document/525615451/SAIC-J-6806))
- Purchase-order inspection requirements are set by an Inspection Requirements form attached to the PO (often called "Form 175" for the commodity). The procedure covering inspection requirements appears in public copies as SAEP-1151 (2017 previous issue). [secondary source] ([slideshare SAEP-1151](https://www.slideshare.net/slideshow/saep1151inspection-requirementpdf/258302250))
- **ERTQA** (Aramco's quality/testing requirements document for suppliers) is published on aramco.com. [confirmed: aramco.com] ([aramco ERTQA](https://www.aramco.com/-/media/downloads/working-with-us/ertqa.pdf))
- **Calibration:** instrument calibration plans and kick-off meetings (KOM) for calibration are typical construction-phase deliverables. [secondary source] ([scribd KOM for calibration](https://www.scribd.com/presentation/726216420/KOM-for-Instrument-Calibration))

---

## 7. Typical Aramco review comments / pitfalls

The comments in this list are **typical** comments compiled from public evidence and EPC experience. Items tagged [secondary source] are backed by a cited rule; the rest are [general knowledge — verify].

1. **Using a control valve for ESD/isolation duty.** SAES-J-700 prohibits it. Add a separate ZV. [secondary source]
2. **Wrong actuator specification cited.** Writing 34-SAMSS-716 for an MOV is wrong: 716 covers pneumatic on-off actuators, 717 hydraulic and 718 electric MOV. [secondary source]
3. **ZV not testable on-line.** 34-SAMSS-634 requires ZVs to be functionally testable in service (for example by PST). Missing PST, a bypass for testing, or test facilities on the P&ID will draw a comment. [secondary source]
4. **ESD instrumentation not meeting SAES-J-601.** J-100 says ESD instruments must also meet J-601. Shared taps or transmitters between ESD and control are a classic comment. [secondary source for the cross-reference; general knowledge for shared taps]
5. **ESD functions in the DCS.** SAES-Z-001 excludes ESD from the PCS. The SIS must be separate, with only interfaces to the DCS. [secondary source]
6. **Ambient rating below 65 °C** for outdoor unsheltered electronics, or no sunshade. SAES-J-003 (2004 values; check the current issue). [secondary source]
7. **Vendor/plant not 9COM-approved** for the item and manufacturing location. Approval is per plant. [secondary source]
8. **Packaged unit treated as "standard" under 34-SAMSS-831** when it is actually custom-engineered. Also: skid-edge junction boxes missing, non-fused terminals in alarm/shutdown circuits, or non-fail-safe shutdown logic. [secondary source for the 831 rules]
9. **IS/non-IS mixed in one multicore or junction box.** SAES-J-903 / SAIC-J-6904. IS used outside Zone 0 without justification (SAES-J-902 limits IS to Zone 0 or vendor-standard IS products). [secondary source]
10. **FF device or wiring block in Zone 2 not certified Ex ic**, or wrong spur cable type (must be Type A). SAES-J-904 per SABP-J-900. [secondary source]
11. **Outdoor cabinet specified to 34-SAMSS-820 only.** Outdoor panels need 34-SAMSS-821, which incorporates 820. [secondary source]
12. **Instrument accessories not accessible from grade/platform.** SAES-J-700 and general J-series practice. [secondary source]
13. **Data sheets on vendor forms instead of Aramco ISS forms** (8020-xxx-ENG). [secondary source for form existence; general knowledge for the comment]
14. **Symbols and tags not per SAES-J-004** (ISA-5.1 plus Aramco exceptions), for example using SDV/XV instead of ZV, or PSV instead of PZV where the project follows Aramco tagging. [secondary source for ZV/PZV usage]
15. **Missing waiver.** A deviation from a mandatory SAES/SAMSS accepted informally in a TBE without a SAEP-302 waiver. SAEP-302 requires approval before the non-compliance is implemented. [secondary source for the SAEP-302 rule; general knowledge for the comment pattern]
16. **Revision mismatch.** Designing to a Scribd copy or an outdated revision rather than the contract revision listed in the project specification. [general knowledge — verify]
17. **Sour-service compliance not stated** (NACE MR0175/ISO 15156) for wetted parts, bolting or tubing in H2S service. [general knowledge — verify]
18. **H2S detector accuracy or alarm settings not per 34-SAMSS-514 / SAES-J-505** (for example the ±4 ppm / ±10% accuracy). [secondary source]
19. **Network architecture lacking a PAN/PCN separation or DMZ** (SAES-Z-010, SAEP-99), and no SACS-002 compliance from vendors with remote access. [secondary source / confirmed for SACS-002 existence]
20. **Thermocouple extension cable not to 34-SAMSS-913** (jacket and colour coding). [secondary source]
21. **Surge relief omitted** on pipeline/loading systems where SAES-J-605 applies. [secondary source for the standard's existence]
22. **Inconsistent vendor compliance claims.** Vendors sometimes cite the wrong SAMSS; verify each claimed compliance against the specification's actual scope. [secondary source: Rotex example]
23. **Orifice taps not flange taps**, or tap details not per AC-036413/AB-036414 (SAES-J-100). [secondary source] *(2nd pass)*
24. **Weld-in thermowell** specified where no ASME/Aramco rule requires a welded connection (SAES-J-400 cl. 5.2.2); helical-strake thermowell offered without FEA/CFD justification (SAES-J-100 2020). [secondary source] *(2nd pass)*
25. **Snubbers, siphons or diaphragm seals missing from the P&ID** (SAES-J-200). [secondary source] *(2nd pass)*

---

## 8. Gaps and open items

*Updated after the 2nd research pass (November 2026). Items resolved in that pass are listed first so the chatbot knows they have moved out of the gap list.*

**Resolved in the 2nd pass (now [secondary source] with links in §2–§6):**
- SAES-J-602 = Burner Management, Combustion and Waterside Control Systems for Watertube Boilers.
- SAES-J-905 and 34-SAMSS-911 = Instrument Asset Management Systems (IAMS).
- SAEP-302 (waiver) and SAEP-303 (engineering reviews) confirmed by number and scope; SAEP-301 (MSAERs), SAEP-12, SAEP-14 added.
- SAES-J-100: flange taps mandatory, tap drawings AC-036413/AB-036414, own straight-run table (2009) / ISO 5167-2 and -4 appendices (2020), drop-out spool, thermowell ≤ 20 D downstream, ISS 3175-ENG, AB-036019 thermowell drawing, FEA/CFD for helical thermowells.
- SAES-J-200: PIP PCCPR001 basis, safety-glass gauges, accessories on P&IDs, J-003 / B-068 cross-references.
- SAES-J-400: weld-in thermowells only where welded connections are required (cl. 5.2.2); 2009 issue date.
- SAES-J-300: related forms (ISS 8020-312/314-ENG), drawings (DB-950046/950047), SATIP-J-300-01, SAES-Y-301 for radar tank gauging.
- SABP-J-900 FF limits: segment ≤ 1,900 m, spur ≤ 120 m, ~55 mA spur current limit.
- SAES-Z-002 content (restricted vs recommended vendor lists).
- 34-SAMSS-001 (multiphase meters & water-cut meters) and 34-SAMSS-010 (number only) added.
- SAES-T documents relevant to I&C (T-000 index, T-481 paging, T-624/625 fiber, T-911 conduit, T-916 building cable).

**Documents still not confirmed (number or title not found publicly):**
- SAES-J-410, SAES-J-510, SAES-J-800: no evidence these exist after two searches. Do not cite them.
- 34-SAMSS-112, 34-SAMSS-113, 23-SAMSS-071: not found after two searches.
- 34-SAMSS-625, -627, -629, -846, 23-SAMSS-030: documents exist (listings), titles still not found.
- 34-SAMSS-010: title not seen.
- SAES-T-603 and SAES-T-628 titles; titles of T-101, T-494, T-795, T-912, T-914.
- "SAEP-250" as an Aramco SIL procedure: not found; do not cite.

**Content gaps (requirements still not publicly confirmable):**
- SAES-J-100: orifice beta-ratio limits, tap-flange rating rules, Table 1 values, meter selection per service, DP turndown.
- SAES-J-200: the transmitter-versus-gauge rule; clause 4.4.1 gas/vapour transmitter text; gauge dial size and over-range rules.
- SAES-J-300: all clause text (gauge-glass restrictions, displacer limits, GWR/DP preferences, ESD-tap separation).
- SAES-J-400: minimum line size for thermowells, insertion length, RTD vs TC selection, whether PTC 19.3 TW is cited by name.
- SAES-J-601: SIL determination method, voting, proof-test intervals, ZV requirements, and whether any issue after 2005 exists.
- SAES-J-904: devices per segment, valves per segment, voltage margin at the furthest device, spare capacity; whether the SABP-J-900 length limits are also J-904 requirements.
- SAES-J-902 UPS and earthing specifics (they sit partly in SAES-P-103/P-111).
- SAES-J-003: whether the 2004 ambient table (35/55/65 °C) changed in 2012/2013 or later; no issue after 13 May 2013 found.
- Whether SAES-J-002 is still active or has been replaced by SAEP-1400 / 9COM evaluation (latest evidence: 30 Nov 2004 major revision).
- Exact SAES-Z-002 title and any revision after 2006.
- Standard drawing prefix meaning (AA/AB/AC/AD) and a full list of instrument hook-up drawing numbers.
- SAEP-302 approval authorities and SAEP-303 review milestones (60/90% not found).

**Hosts that need allowing for deeper research:** pdfcoffee.com, ask.instrumentationtools.com, www.scribd.com, www.aramco.com and justrite-elynox-bootcamp.pages.dev were unreachable from both research sessions (ENOTFOUND). Scribd document text was only visible through search snippets. Allowing scribd.com and pdfcoffee.com would let the J-100/J-200/J-400 copies be read in full.

**Recommendation for chatbot users:** for any requirement tagged [general knowledge — verify] or [secondary source], answer with the document number and ask the engineer to check the clause in the project's controlled copy. For clause-level questions, ask the user to paste the relevant clause from their licensed copy.

---

## 9. Source list

Official / primary (aramco.com, vendor approvals, USPTO):
- https://www.aramco.com/-/media/downloads/iktva/instrumentation.pdf
- https://www.aramco.com/en/what-we-do/commercial-ecosystems/iktva
- https://SaudiAramco.com/-/media/downloads/working-with-us/ccc/sacs-002-third-party-cybersecurity-standard.pdf
- https://www.aramco.com/-/media/downloads/working-with-us/ertqa.pdf
- https://aramco.com/-/media/images/investors/annual-report/2023/ara-2023-risk-english.pdf
- https://americas.aramco.com/en/partnering-with-us/current-supplers/frequently-asked-questions
- https://europe.aramco.com/-/media/aramcoaoc/procurement/saep-31-appendix-a.docx
- https://india.aramco.com/-/media/aramcoindia/sourcing-list/3-jul-2026-sourcing-list-india.pdf
- https://europe.aramco.com/-/media/aramcoaoc/sourcing-list/aoc-1st-jan-2026-sourcing-list.pdf
- https://emerson.com/documents/automation/approval-saudi-aramco-9com-approval-letter-shafer-en-86406.pdf
- https://emerson.com/documents/automation/approval-aramco-9com-approval-letter-houston-bettis-en-202308.pdf
- https://www.saudicable.com/wp-content/uploads/2025/12/9Com-Saudi-Aramco_SCC-New-1.pdf
- https://www.saudicable.com/products/special-cables/
- https://s1-live.emerson.com/en-ae/news/automation/22-1-mou-agreement-signed-saudi-aramco-iktva
- https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10557564
- https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12152615

Articles / vendors / industry:
- https://www.controlglobal.com/network/industrial-networks/article/11321803/foundation-fieldbus-in-hazardous-areas
- https://www.controlglobal.com/articles/2015/foundation-fieldbus-in-hazardous-areas/
- https://aramcoexpats.com/articles/fieldbus-a-solution-for-plant-engineers
- https://valve-world.net/?p=53143
- https://trends.directindustry.com/rotex-automation-limited/project-61940-1158162.html
- https://blog.wika.com/en/wika-insight/venturis-meet-desert-challenges/
- https://www.ogj.com/home/article/17216022/saudi-plants-install-v-cone-meters
- https://www.pipeliner.com.au/internationalnews/venturi-meters-for-saudi-aramco/
- https://www.det-tronics.com/content/documents/95-8472-4.3%20(505%20CGS).pdf
- https://blog.projectmaterials.com/valves/safety-valve-asme-api/
- https://www.FieldCommgroup.org/sites/default/files/imce_files/technology/documents/Ff_system_engineering_guidelines_version_3.2.1.pdf
- https://guest.meed.com/?p=15362
- https://astrsa.com/blog/aramco-iktva-70-percent-localization-200000-jobs
- https://expro.gov.sa/api/uploads/Checklist%20%20Distributed%20Control%20System%20DCS%20Block%20Diagram.docx

Secondary (document-sharing listings, blogs, forums; unofficial copies, used for number/title/scope only):
- https://pdfcoffee.com/saes-j-001-3-pdf-free.html
- https://www.scribd.com/document/680621562/SAES-J-001
- https://www.scribd.com/document/476010934/SAES-J-001
- https://kishorekaruppaswamy.wordpress.com/wp-content/uploads/2011/10/saudi-arabian-engineering-standardssaes-j-001.pdf
- https://kishorekaruppaswamy.wordpress.com/wp-content/uploads/2011/10/saudi-arabian-engineering-standardssaes-j-002.pdf
- https://kishorekaruppaswamy.wordpress.com/wp-content/uploads/2011/10/saudi-arabian-engineering-standards-saes-j-601.pdf
- https://www.scribd.com/document/476010944/SAES-J-002
- http://instrumentqcnotes.blogspot.com/2015/03/introduction-it-is-branch-of.html
- https://englogs.com/saudi-aramco-engineering-standard-instrumentation-system/
- https://paktechpoint.com/saudi-aramco-engineering-standard-for-electrical-instrumentation-and-cp/
- https://www.scribd.com/document/553817194/SAES-J-003
- https://www.scribd.com/document/476010936/SAES-J-003
- https://pdfcoffee.com/saes-j-003-pdf-free.html
- https://www.scribd.com/document/668988283/SAES-J-004
- https://www.scribd.com/document/527150981/INDX-SAES
- https://www.scribd.com/document/527150957/Indx-saes-Oct-2006
- https://www.scribd.com/document/494872706/SAES-J-100
- https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-31108---Tecnicas---Riyas/RFQ-Files/SAES-J-100
- https://www.scribd.com/document/494872703/Saes-j-200-Pressure
- https://www.scribd.com/document/519224174/SAES-J-400
- https://www.scribd.com/document/473260773/SAEP-318-pdf
- https://www.scribd.com/document/507299437/Relief-Valves-Procedure
- https://es.scribd.com/document/295779795/34-SAMSS-611
- https://es.scribd.com/document/178151012/100-YER-PE-YSS-0048
- https://pdfcoffee.com/saes-b-058-pdf-free.html
- https://www.scribd.com/document/370514106/174038738-34-SAMSS-634-pdf
- https://www.scribd.com/document/457762664/SAIC-L-2043
- https://pdfcoffee.com/control-valve-selection-pdf-free.html
- https://www.scribd.com/document/508178538/ALERT-OLD
- https://www.scribd.com/document/468687176/34-SAMSS-711-pdf
- https://es.scribd.com/document/382959447/04-SAMSS-035-ARAMCO-General-Reuirement-for-Valves-pdf
- https://pdfcoffee.com/34-samss-716-pdf-free.html
- https://www.scribd.com/document/486500518/34-SAMSS-717
- https://www.scribd.com/document/536743257/34-SAMSS-718
- https://www.scribd.com/document/494624754/424411678-34-samss-820
- https://pdfcoffee.com/34-samss-820-pdf-free.html
- https://www.scribd.com/document/536743247/34-SAMSS-821
- https://pdfcoffee.com/34-samss-821-pdf-free.html
- https://studylib.net/doc/27696645/34-samss-831
- https://www.scribd.com/document/324772531/SAIC-J-6022-Rev-0-pdf
- https://pdfcoffee.com/34-samss-114-pdf-free.html
- https://www.scribd.com/document/473260753/SAEP-146-pdf
- https://www.scribd.com/document/517672324/34-SAMSS-514
- https://www.scribd.com/document/329480655/34-SAMSS-514-Dec-26-2013
- https://pdfcoffee.com/34-samss-621-pdf-free.html
- https://pdfcoffee.com/34-samss-625pdf-pdf-free.html
- https://www.scribd.com/document/549908228/34-SAMSS-627
- https://www.scribd.com/document/549908231/34-SAMSS-629
- https://www.scribd.com/document/549907783/34-SAMSS-846
- https://www.scribd.com/presentation/609393585/Training-Module-QA-QC
- https://www.scribd.com/document/426879234/SAES-J-902-pdf
- https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-31108---Tecnicas---Riyas/RFQ-Files/SAES-J-902
- https://www.scribd.com/document/226927140/SAIC-J-6904-Rev-0
- https://www.scribd.com/document/655719750/SAES-B-068
- https://www.scribd.com/document/405891268/SAES-B-014
- https://pdfcoffee.com/saudi-aramco-inspection-checklist-pressurized-building-hvac-requirements-saic-k-4044-30-apr-13-hvac-pdf-free.html
- https://round-lake.dustinice.workers.dev:443/https/www.scribd.com/document/493616203/SABP-J-900
- https://www.scribd.com/doc/142169992/192-YER-PE-I35-0011
- https://pdfcoffee.com/saes-z-001-pdf-pdf-free.html
- https://www.scribd.com/doc/239724008/Saes-z-002-Locked-by-Badr
- https://pdfcoffee.com/saes-z-004-pdf-free.html
- https://www.scribd.com/document/415401236/SAES-Z-010-pdf
- https://pdfcoffee.com/saes-z-010-pdf-pdf-free.html
- https://es.scribd.com/document/319694317/23-SAMSS-020
- https://www.scribd.com/document/585773935/23-SAMSS-030
- https://www.scribd.com/document/509522885/SABP-Z-019
- https://round-lake.dustinice.workers.dev:443/https/www.scribd.com/document/509522913/SABP-Z-057
- https://www.scribd.com/document/429080803/SAEP-15-pdf
- https://www.scribd.com/document/398466940/SAEP-1400-pdf
- https://pdfcoffee.com/download/saes-k-110-pdf-free.html
- https://www.scribd.com/document/525615451/SAIC-J-6806
- https://www.scribd.com/document/525616682/SAIC-J-6803
- https://www.scribd.com/document/525616683/SAIC-J-6804
- https://www.scribd.com/document/526010667/SAIC-J-6017
- https://www.scribd.com/document/525219377/SAIC-J-6019
- https://www.scribd.com/document/525610883/SAIC-J-6030
- https://www.scribd.com/document/226926965/SAIC-J-6111-Rev-0
- https://www.scribd.com/document/475001025/SAES-T-101-pdf
- https://www.slideshare.net/slideshow/saep1151inspection-requirementpdf/258302250
- https://www.scribd.com/presentation/726216420/KOM-for-Instrument-Calibration
- https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-31108---Tecnicas---Riyas/RFQ-Files/SAES-A-202

2nd-pass additions (November 2026):
- https://pdfcoffee.com/saes-j-100-pdf-free.html
- https://www.scribd.com/document/439171375/SAES-J-200-Pressure
- https://www.scribd.com/document/519224007/SAES-J-200
- https://pdfcoffee.com/saes-j-905-pdf-free.html
- https://www.scribd.com/document/683056429/SAEP-302
- https://www.scribd.com/document/83925264/SAEP-302
- https://www.scribd.com/document/607475675/SAEP-301
- https://www.scribd.com/document/473260763/SAEP-303-pdf
- https://www.scribd.com/document/397353670/SAEP-303-PDF
- https://pdfcoffee.com/saep-303-pdf-pdf-free.html
- https://www.scribd.com/document/661288589/SAEP-14
- https://www.scribd.com/doc/239415248/INDX-SAEP
- https://www.scribd.com/document/354870462/SAES-Z-002-LOCKED-BY-BADR-pdf
- https://www.scribd.com/document/403474712/SABP-Z-002E-pdf
- https://www.scribd.com/document/493616156/SAES-Y-301
- https://www.scribd.com/document/444577400/SAIC-J-6022-Rev-0
- https://www.scribd.com/document/396454916/J-03
- https://www.scribd.com/document/414532387/Gs130-5
- https://www.scribd.com/document/475001065/SAES-T-625-PDF
- https://www.scribd.com/document/453306409/SAES-T-911
- https://www.scribd.com/document/475001111/SAES-T-914-PDF
- https://www.scribd.com/document/475001105/SAES-T-912-PDF
- https://india.aramco.com/-/media/aramcoindia/sourcing-list/sourcing-list-jan-2024.pdf
- https://india.aramco.com/-/media/aramcoindia/sourcing-list/30-sept_2025-sourcing-list-aa-india.pdf
- https://europe.aramco.com/-/media/aramcoaoc/pdf/aramco-materials-sourcing-list.pdf
- https://www.controlglobal.com/network/industrial-networks/article/11321803/safety-foundation-fieldbus-in-hazardous-areas
- https://www.powermag.com/a-fieldbus-primer/
- https://webstore.ansi.org/standards/asme/asmeptc19tw2016r2025
- https://www.asme.org/codes-standards/find-codes-standards/thermowells
- https://webstore.ansi.org/preview-pages/ISA/preview_ANSI+ISA+S71.01-1985.pdf
- https://webstore.ansi.org/preview-pages/IEC/preview_iec60654-1%7Bed2.0%7Db.img.pdf
