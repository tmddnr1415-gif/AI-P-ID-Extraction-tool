# 03 — QatarEnergy & Gulf Operator I&C Practice (QatarEnergy / QatarEnergy LNG, ADNOC, Shell DEP, Saudi Aramco, KOC/KNPC, PDO)

*Knowledge-base file for the I&C expert chatbot. Compiled November 2026 from public web sources. Read the confidentiality note and confidence labels before quoting anything from this file.*

---

## How to use this file / confidentiality note

**What this file is.** This is a reference map of the I&C standards and project practice that Gulf national oil companies and major operators publicly describe. It tells an engineer **what kind of document governs a topic, what it is likely called and numbered, what public sources say about it, and how sure we are**. It does **not** replace the controlled document. On any real project, the binding text is the revision listed in the contract's "Applicable Documents"/"Order of Precedence" list.

**Confidentiality.** QatarEnergy (QE), QatarEnergy LNG, ADNOC, Saudi Aramco, KOC/KNPC, PDO and Shell DEPs are proprietary or controlled documents. Some of them leak onto document-sharing sites (Scribd, pdfcoffee, kupdf, Studocu, Course Hero). This file:
- records only document **numbers, titles, scope statements and publicly described requirements**;
- does **not** reproduce clause text;
- never invents a clause number or a numeric limit. If a number is not confirmed, it is labelled.

**Confidence labels used throughout:**

| Label | Meaning |
|---|---|
| **[confirmed]** | Stated by the operator itself, by an official press release, or by an operator-hosted document seen in search results. A link follows. |
| **[secondary source]** | Seen only on a document-sharing site, in trade press quoting unnamed sources, a forum, a blog or an index copy. The number or title is probably right, but the revision and current status are unknown. |
| **[general knowledge — verify]** | Common industry knowledge that could not be confirmed with a public link during this research. Treat it as a hypothesis to check against the project's contract documents. |

**How the chatbot should answer with this file:**
1. If an engineer asks "what does QE spec X say about Y?", answer with the *typical* requirement plus its confidence label. Always tell them to check the project's own revision of the spec.
2. If an engineer quotes a clause from their project copy, **their copy wins** over anything in this file.
3. Never present a [general knowledge — verify] item as a client requirement in a deliverable or in a comment response.

**Research limits.** WebFetch could not reach most hosts during this research: adnoc.ae, pdfcoffee.com, studylib.net, blogspot and pages.dev all failed DNS resolution in the sandbox. The web-search budget also ran out before the ADNOC, KOC, PDO and Aramco sections were fully researched. Most facts here therefore come from search-result summaries and snippets, not full-document reads. See §8 Gaps. A short 2nd pass (November 2026) added QE-LNG document-numbering procedures, a Ras Laffan dry-bulb/wet-bulb pair, Qatar solar-resource data, KOC and PDO numbering; items from that pass are marked *(2nd pass)*.

---

## Table of contents

1. [QatarEnergy document system & numbering](#1-qatarenergy-document-system--numbering)
2. [QatarEnergy / QP index table](#2-qatarenergy--qp-index-table)
3. [Procurement, vendor lists, Tawteen / ICV](#3-procurement-vendor-lists-tawteen--icv)
4. [Project practice & lessons (NFE / NFS / NFW / NFPS, others)](#4-project-practice--lessons)
5. [Site design conditions (Qatar, UAE, KSA, Oman, Kuwait)](#5-site-design-conditions)
6. [Shell DEP / ADNOC AGES / Aramco / KOC / PDO index](#6-shell-dep--adnoc--others-index)
7. [Typical client review comments (Gulf operators)](#7-typical-client-review-comments)
8. [Gaps & next research steps](#8-gaps--next-research-steps)
9. [Source list](#9-source-list)

---

## 1. QatarEnergy document system & numbering

### 1.1 Corporate identity changes (important for document titles)

| Period | Name | Notes |
|---|---|---|
| 1974 – ~2001 | **QGPC** — Qatar General Petroleum Corporation | Many legacy engineering standards still carry "QGPC" on the cover (e.g. the ES.2.14.0070 cable standard below). [secondary source] — [Scribd ES.2.14.0070](https://www.scribd.com/document/485459233/ES-2-14-0070RAElectricalPowerControlCables-pdf) |
| ~2001 – Oct 2021 | **QP** — Qatar Petroleum | "QP" standards, philosophies and Pre-qualified Manufacturers lists date from this period. |
| Oct 2021 → | **QatarEnergy (QE)** | Rebranded in 2021. Corporate HSE standards are now numbered `CORP-HSE-STD-xxx`. [confirmed] — [QE CORP-HSE-STD-080](https://qatarenergy.qa/en/SupplyManagement/Tenders/SupplyManagmentFiles/CORP-HSE-STD-080%20CORPORATE%20STANDARD%20FOR%20MANAGING%20HSE%20IN%20CONTRACTS.pdf) |
| Qatargas + RasGas merged 2018; renamed **QatarEnergy LNG** in 2022 | LNG operating company at Ras Laffan | Legacy Qatargas and RasGas documents keep their own numbering (see §1.4). [general knowledge — verify] |

### 1.2 Legacy QGPC/QP "ES" Engineering Standards family

Public fragments show a QGPC/QP engineering-standard family with the prefix **"ES."**, laid out as `ES.<discipline>.<section>.<serial>`:

- **ES.2.14.0070** — *Electrical power & control cables* for QGPC projects. Scope covers 33 kV, 11 kV, 6.6 kV, 3.3 kV and LV power, control and earthing cables. [secondary source] — [Scribd](https://www.scribd.com/document/485459233/ES-2-14-0070RAElectricalPowerControlCables-pdf)
- **ES.2.03.0001** — *QGPC Engineering Design Philosophy* (electrical). ES.2.14.0070 cites it, including an appendix on cable glands. [secondary source] — same Scribd document
- **ES.2.06.0001** — *QGPC Electrical Installation Practices*. ES.2.14.0070 also cites it. [secondary source] — same
- **ES.0.06.0021** — *Project Dossier* requirements for Qatar Petroleum projects. [secondary source] — [Scribd ES-0-06-0021](https://www.scribd.com/document/440845386/ES-0-06-0021-Project-Dossier)
- **ES.D.10** — *Draughting* standard. QP and any consultant or contractor providing design services to QP are required to follow it. [secondary source] — [Scribd ES-D-10](https://www.scribd.com/document/466429022/ES-D-10-Draughting-pdf)

**How to read the numbering.** The known examples suggest that the first digit is a discipline group: "0" for general/project and "2" for electrical. They also suggest the next pair is a document type: ".03." for philosophy and ".06." for installation practice. **This is an inference from three or four numbers, not a confirmed scheme.** [general knowledge — verify]. No public hit confirmed which "ES.x" group holds instrumentation. Searches for "ES.2" with "instrumentation" returned only the electrical documents. [confirmed absence in search, Nov 2026]

### 1.3 Other QP/QE number formats seen

| Format | Example | Status |
|---|---|---|
| `CORP-HSE-STD-nnn` / `CORP-HSE-PRC-nnn` | CORP-HSE-STD-080 *Corporate Standard for Managing HSE in Contracts*; CORP-HSE-PRC-080 *Corporate Procedure for Managing HSE in Contracts* | [confirmed] — [STD-080](https://qatarenergy.qa/en/SupplyManagement/Tenders/SupplyManagmentFiles/CORP-HSE-STD-080%20CORPORATE%20STANDARD%20FOR%20MANAGING%20HSE%20IN%20CONTRACTS.pdf), [PRC-080](https://www.qatarenergy.qa/en/SupplyManagement/Tenders/Documents/HSE/CORP-HSE-PRC-080%20CORPORATE%20PROCEDURE%20FOR%20MANAGING%20HSE%20IN%20CONTRACTS.pdf) |
| `QGL-xxx-nnn` (Industrial Cities guidelines) | QGL-LHH-001 *Heat Stress Guidelines* (Industrial Cities Directorate, 2015) | [confirmed] — [QE IC regulations](https://qatarenergy.qa/en/Whatwedo/IndustrialCities/Documents/Regulations/HSE/QGL-LHH-001%20Heat%20Stress%20Guidelines%20For%20ICD%20102015.pdf) |
| `QSP-xxx-nn` (quality/system procedures) | "QSP-QAC-09" (Qatar Petroleum) — title and content not visible | [secondary source] — [Scribd](https://www.scribd.com/document/595666553/QATAR-PETROLUM-QSP-QAC-09) |
| `QP-STD-E&I-100 – Instrumentation Systems` | Named by a single engineering blog | **[unverified — low reliability]**. One blog, no operator source. Do not quote it as a real number. |
| PPML (QP "Pre-qualified/Preferred … Manufacturers List"?) | "QP-PPML-Q4-2021" | [secondary source] — [Scribd](https://www.scribd.com/document/625318634/QP-PPML-Q4-2021). The meaning of the acronym was not confirmed. See §3.2. |
| General Terms & Conditions of Purchase | GTCP (Schedule C) Rev 4 (10/21); Appendix D Rev 5 (01/24) | [confirmed] — [GTCP Rev 4](https://www.qatarenergy.qa/en/SupplyManagement/Tenders/Documents/General%20Terms%20and%20Conditions%20of%20Purchase%20(GTCP)%20(Schedule%20C)%20-%20Rev%204%20(1021).pdf), [Appendix D](https://www.qatarenergy.qa/en/SupplyManagement/Tenders/Documents/Appendix%20D%20to%20General%20Terms%20and%20Conditions%20of%20Purchase%20(Schedule%20C)%20Rev%205%20(0124).pdf) |

### 1.4 Project-level documents (NFE/NFS/NFPS and others)

On mega-projects, the client's corporate standards are usually turned into **project specifications** owned by the EPC contractor or the FEED contractor. These follow a project document-numbering system. One publicly indexed example:

- **200-51-IN-SPC-00057** — *Specification for Instrument Cables & Cable Glands*, "COMP3" project (North Field Production Sustainability, NFPS, offshore). It is a Saipem document, appearing in a third-party RFQ example set. [secondary source — title only; content not read] — [search listing](https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-32705---Saipem-COMP3/RFQ-Files/200-51-IN-SPC-00057_00) (host not reachable from this sandbox)
  - **Numbering pattern:** `<area/unit>-<discipline code 51?>-IN-SPC-<serial>`. Here "IN" is the instrumentation discipline and "SPC" the document type (specification). [inference — verify]
- **Qatargas "Onshore Control and Shutdown Philosophy."** It describes the control system interfacing with the Fire & Gas System (FGS) and other subsystems. [secondary source] — [Scribd CONTROL-SD](https://www.scribd.com/document/722624967/CONTROL-SD)

**QatarEnergy LNG (ex-Qatargas / RasGas) numbering procedures** *(added Nov 2026, 2nd pass)*. All [secondary source]: seen only as search snippets of files in third-party RFQ example sets (Saipem COMP2/COMP3, NFPS offshore); the host was unreachable for a full read.
- The procedures sit in a **`PRJ-PJL-PRC-nnn`** series. Files seen: **PRJ-PJL-PRC-004** (rev 07), **PRJ-PJL-PRC-005** (rev 21) and **PRJ-PJL-PRC-008** (rev 17, *QatarEnergy LNG Equipment Numbering Philosophy*; this revision added a PRV tag structure, section 4.4.1, and covers valve and cable tags). — [PRC-005 listing](https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-32705---Saipem-COMP3/RFQ-Files/PRJ-PJL-PRC-005_21), [PRC-004 listing](https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-21699---Saipem-COMP2/RFQ-Files/PRJ-PJL-PRC-004_07), [PRC-008 listing](https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-32705---Saipem-COMP3/RFQ-Files/PRJ-PJL-PRC-008_17)
- **Engineering document number** (procedure effective 12 Sep 2021): five hyphen-separated segments, **System Number – Unit Number – Discipline – Document Type – Sequence Number**. The sequence number is five characters starting at 00001, unique for each System/Unit/Discipline/Document-Type combination. Which PRC number holds this rule is not certain (most likely PRC-005).
- **Vendor document number:** three segments, **QG contract/project number (XXXXA_YY) – purchase order number (10 digits) – sequence number (5 digits)**. The same procedure says the legacy RasGas document **RG-DFO-002 "Facilities Document Metadata"** was merged into it, which is how the RasGas numbering was absorbed.
- **Equipment/tag numbering** (Qatargas procedure effective 11 Jan 2022): an "intelligent" scheme in which **System and Unit codes** are integral to document, drawing, equipment and component tag numbers. Stand-alone new projects that are not extensions of the existing Qatargas South or RLTO (Ras Laffan Terminal Operations) assets follow the Qatargas equipment and document numbering.
- **Practical rule:** on a QE-LNG brownfield or NFx tie-in job, get PRJ-PJL-PRC-008 (tags) and the document-numbering procedure from the contract's applicable-documents list before building the instrument index; the instrument tag format itself was not visible in public snippets. [general knowledge — verify]

**Practical rule for the chatbot.** On QE/QE-LNG projects, the documents an instrument engineer actually works to are usually these: (a) the project Instrument Design Basis/Philosophy; (b) project specifications for each equipment class (transmitters, control valves, on/off valves, analysers, cables, JBs, F&G detectors, DCS/SIS/FGS); (c) the client's Approved Manufacturers List. Corporate QE standards sit behind them in the order of precedence. [general knowledge — verify]

---

## 2. QatarEnergy / QP index table

Legend: **C** = confirmed (official/operator-hosted), **S** = secondary source, **U** = unverified/general knowledge, **I** = inferred existence (a typical document type; no public number found).

| Number | Title | Scope (public description) | Conf. | Source |
|---|---|---|---|---|
| ES.2.14.0070 | Electrical Power & Control Cables (QGPC) | 33 kV down to LV power, control and earthing cables for QGPC projects | S | [Scribd](https://www.scribd.com/document/485459233/ES-2-14-0070RAElectricalPowerControlCables-pdf) |
| ES.2.03.0001 | QGPC Engineering Design Philosophy (electrical) | Design philosophy; has a cable gland appendix | S (cited by ES.2.14.0070) | same |
| ES.2.06.0001 | QGPC Electrical Installation Practices | Installation practices | S (cited) | same |
| ES.0.06.0021 | Project Dossier | Required project dossier / handover documentation | S | [Scribd](https://www.scribd.com/document/440845386/ES-0-06-0021-Project-Dossier) |
| ES.D.10 | Draughting | Drawing standard binding on QP and its consultants/contractors | S | [Scribd](https://www.scribd.com/document/466429022/ES-D-10-Draughting-pdf) |
| CORP-HSE-STD-080 | Corporate Standard for Managing HSE in Contracts | Contractor HSE management, including appendices on contractor compounds | C | [qatarenergy.qa](https://qatarenergy.qa/en/SupplyManagement/Tenders/SupplyManagmentFiles/CORP-HSE-STD-080%20CORPORATE%20STANDARD%20FOR%20MANAGING%20HSE%20IN%20CONTRACTS.pdf) |
| CORP-HSE-PRC-080 | Corporate Procedure for Managing HSE in Contracts | Procedure that goes with STD-080 | C | [qatarenergy.qa](https://www.qatarenergy.qa/en/SupplyManagement/Tenders/Documents/HSE/CORP-HSE-PRC-080%20CORPORATE%20PROCEDURE%20FOR%20MANAGING%20HSE%20IN%20CONTRACTS.pdf) |
| QGL-LHH-001 | Heat Stress Guidelines (Industrial Cities Directorate, 10/2015) | Worker heat stress. Gives the Qatar summer climate as 33–50 °C with RH up to 100 % | C | [qatarenergy.qa](https://qatarenergy.qa/en/Whatwedo/IndustrialCities/Documents/Regulations/HSE/QGL-LHH-001%20Heat%20Stress%20Guidelines%20For%20ICD%20102015.pdf) |
| GTCP Sched. C Rev 4 / App. D Rev 5 | General Terms & Conditions of Purchase | Commercial/technical purchase conditions | C | [GTCP](https://www.qatarenergy.qa/en/SupplyManagement/Tenders/Documents/General%20Terms%20and%20Conditions%20of%20Purchase%20(GTCP)%20(Schedule%20C)%20-%20Rev%204%20(1021).pdf) |
| QP-PPML (quarterly issue, e.g. Q4-2021) | QP manufacturers list (exact title unconfirmed) | Probably a list of pre-qualified manufacturers or products by commodity | S | [Scribd](https://www.scribd.com/document/625318634/QP-PPML-Q4-2021) |
| QP-STD-E&I-100 | "Instrumentation Systems" | — | U (blog only; possibly made up) | none credible |
| — | QP/QE Instrumentation Design Philosophy / Instrument Engineering Standard | Field instruments, installation, materials, hazardous area | I | none public |
| — | QP/QE Fire & Gas Philosophy | F&G detection, voting, cause & effect | I | none public |
| — | QP/QE ESD / SIS Philosophy (IEC 61511 based) | Shutdown hierarchy, SIL determination | I | none public |
| — | QP/QE Telecommunication Philosophy | PAGA, CCTV, radio, LAN | I | none public |
| — | QP/QE Control Systems / Cybersecurity standard | DCS/SIS network segregation, IEC 62443 | I | none public |
| 200-51-IN-SPC-00057 | Specification for Instrument Cables & Cable Glands — COMP3 (NFPS), Saipem | Project specification | S (title only) | listing (host unreachable) |

**Note on "I" rows.** Every Gulf NOC has these philosophies, and QE-LNG project tenders reference them. No public number or title for them was found in this research. If a user asks for "the QP F&G philosophy number", say it is not publicly confirmed and ask for the project's applicable-documents list.

---

## 3. Procurement, vendor lists, Tawteen / ICV

### 3.1 Tendering mechanics

- From **1 December 2023**, QatarEnergy buys tenders online through the **Mushtaryat Portal**. The earlier pages described buying through a registered SAP vendor ID. [confirmed] — [QE Buy tenders online](https://qatarenergy.qa/en/SupplyManagement/Tenders/Pages/Buytendersonline.aspx)
- Vendor registration is **mandatory** before an RFQ or tender document can be issued to a company. [confirmed] — [QE How to tender (purchasing)](https://qatarenergy.qa/en/SupplyManagement/Tenders/Pages/Howtotenderpurchasingdepartment.aspx)
- Technical offers must include detailed manufacturer technical specifications and catalogues. Leaving them out may lead to disqualification. [confirmed] — [QE How to tender (contracts)](https://www.qatarenergy.qa/en/SupplyManagement/Tenders/Pages/Howtotendercontractsdepartment.aspx)
- QatarEnergy LNG runs its own supplier registration and portal. [confirmed — page exists] — [qatarenergylng.qa/Suppliers](https://www.qatarenergylng.qa/Suppliers)

### 3.2 Approved / pre-qualified manufacturer lists

- QP issued a periodic manufacturers list (**"PPML"**). Quarterly issues circulate, e.g. "Q4 2021". [secondary source] — [Scribd](https://www.scribd.com/document/625318634/QP-PPML-Q4-2021)
- **Typical practice** [general knowledge — verify]:
  - EPC contracts attach the client's approved vendor list (AVL) or approved manufacturer list (AML), broken down by commodity (pressure transmitters, control valves, ESD valves, gas detectors, analyser shelters, DCS/SIS, etc.).
  - A vendor not on the list needs a **deviation or "new vendor" request**. That request usually needs technical pre-qualification, references (often installed base in the Middle East or at that operator), and a QA/QC audit.
  - Instrument datasheets go back with comments like "Vendor not in approved list — provide pre-qualification" or "Model not previously approved by Company".
- The **IOGP S-718** quality-requirements specification (for basic process measurement instruments, from the JIP33 programme) is increasingly referenced by Gulf operators for supplier QA. [confirmed — document exists] — [IOGP S-718Q Addendum 1, 2023-12](https://www.iogp.org/bookstore/wp-content/uploads/sites/2/2023/12/Quality-Reqs-for-Basic-Process-Measurement-Instruments-Addendum-1-S-718Qv2023-12.pdf). Whether a given QE project has adopted it is [general knowledge — verify].

### 3.3 Tawteen and In-Country Value (ICV)

- **Tawteen** is QatarEnergy's energy-sector supply-chain localisation programme. It has three pillars: new investment opportunities, supplier development, and an **ICV policy**. [confirmed] — [Gulf Times, launch](https://www.gulf-times.com/story/618648/qp-to-enhance-localisation-of-energy-sectors-supply-chain); [QAFAC Tawteen page](https://www.qafac.com.qa/tawteen)
- **ICV evaluation in energy-sector tenders** started in **July 2020**. [confirmed] — [Gulf Times 2020](https://www.gulf-times.com/story/666876/qp-announces-start-of-icv-evaluation-in-energy-sector-tenders-from-july); [The Peninsula 29/06/2020](https://thepeninsulaqatar.com/article/29/06/2020/Qatar-Petroleum-announces-start-of-In-Country-Value-evaluation-in-energy-sector-tenders-starting-July)
- The **ICV digital portal** was launched in March 2022. Suppliers use it to register, get certified and track their localisation. [confirmed] — [The Peninsula 31/03/2022](https://thepeninsulaqatar.com/article/31/03/2022/qatarenergy-launches-tawteen-in-country-value-digital-portal)
- The ICV certificate is validated **annually by an independent third party**. Accounting firms such as KPMG are appointed as certifiers. [confirmed] — [KPMG Qatar](https://kpmg.com/qa/en/services/audit/tawteen-icv-in-country-value-certification.html)
- Programme officials said that all companies wishing to bid in the energy sector must get an ICV certificate. [confirmed — QNA report] — [QNA 01/12/2023](https://www.qna.org.qa/en/News-Area/News/2023-12/01/0032-qatarenergy-reviews-tawteen,-icv-programs-within-activities-of-made-in-qatar). The details of thresholds and exemptions were reported differently by different sources. One secondary report cites a QAR 20 million revenue threshold and an exemption for companies under two years old. [secondary source — verify]
- An **Enhanced ICV programme** was announced in October 2024. It brings a refined ICV formula, an **"ICV+"** policy aimed at local manufacturers, and a "Blanket Score" policy for micro/small enterprises. QE reported that the sector's local contribution rose from about 14 % to 28.5 %. [confirmed] — [The Peninsula 07/10/2024](https://thepeninsulaqatar.com/article/07/10/2024/qatarenergy-announces-introduction-of-enhanced-in-country-value-program); [Gulf Times](https://www.gulf-times.com/article/692098/business/qatarenergy-launches-enhanced-in-country-value-programme)
- **What this means for I&C** [general knowledge — verify]:
  - ICV score is part of the commercial evaluation. Vendors with Qatar assembly, panel-building, calibration or service centres (e.g. system-cabinet integration, JB fabrication, valve repair shops) gain an advantage.
  - EPCs on NFE/NFS typically push localisable scopes to Qatar-based companies: cabinets, junction boxes, cable trays, insulation and painting, calibration.

---

## 4. Project practice & lessons

### 4.1 North Field Expansion overview

| Project | Scope | Onshore EPC | I&C / automation facts found | Conf. |
|---|---|---|---|---|
| **NFE** (North Field East) | 4 × ~8 Mtpa mega LNG trains at Ras Laffan; part of raising Qatar's capacity from 77 to 110 Mtpa | **Chiyoda + Technip Energies** JV (Feb 2021) | **Honeywell = Main Instrument & Control Contractor (MICC/MAC)**, awarded about 26 Oct 2020 | C — [Digital Refining](https://digitalrefining.com/news/1006346/technip-energies-and-chiyoda-awarded-major-lng-contract); [LNG Industry](https://www.lngindustry.com/liquid-natural-gas/09022021/technip-energies-and-chiyoda-awarded-major-lng-contract); [World Oil](https://worldoil.com/news/2020/10/22/honeywell-to-automate-world-s-largest-lng-project/); [MEED project profile](https://meedprojects.com/project-profile/?pid=229962) |
| **NFS** (North Field South) | 2 × 8 Mtpa trains | **Technip Energies + CCC** JV, ~US$10 bn EPCC (May 2023) | No public DCS/SIS/MAC award found. Air Products AP-X liquefaction technology; Baker Hughes main refrigerant compressors were reported | C (EPC) — [Gas Processing News](https://www.gasprocessingnews.com/news/2023/05/technip-energies-awarded-a-major-lng-contract-for-the-north-field-south-project-by-qatarenergy/); [The Peninsula](https://thepeninsulaqatar.com/article/16/05/2023/qatarenergy-awards-10-billion-worth-epc-contract-for-north-field-south-project); [OE Digital](https://www.oedigital.com/amp/news/505132-qatarenergy-awards-10b-epc-contract-to-technip-energies-led-joint-venture); AP-X — [The Energy Year](https://theenergyyear.com/?p=39749) |
| **NFW** (North Field West) | 2 × 8 Mtpa trains, "replication" of the NFS trains | **Technip Energies (leader) + CCC + Gulf Asia Contracting (GAC)** JV "T.ENCCCGAC" (EPCC award announced 25 Feb 2026) | No automation award found. First LNG expected by end-2031; MEES reported slippage beyond 2030 | C — [Technip Energies PR](https://www.ten.com/en/media/press-releases/technip-energies-awarded-major-lng-contract-north-field-west-project); [QNA](https://qna.org.qa/en/News-Area/News/2026-2/25/qatarenergy-awards-epc-contract-for-north-field-west-16-mtpa-lng-project); [LNG Prime](https://lngprime.com/contracts-and-tenders/qatarenergy-awards-north-field-west-epc-gig-to-technip-energies-jv/178516/); [MEES](https://www.mees.com/2026/2/27/oil-gas/qatars-nfw-lng-expansion-project-slips-beyond-2030/e1c54540-13e5-11f1-94ef-5b4d372885a7) |
| **NFPS** (North Field Production Sustainability) | Offshore compression/wellhead platforms ("COMP" packages) | e.g. Saipem on COMP3 (from a doc-number listing) | Project spec 200-51-IN-SPC-00057 (instrument cables & glands) exists | S |

**Clarification for users.** Yokogawa's 2026 MAC awards in the news are for **Commonwealth LNG (Louisiana)** and **LNG Canada Phase 2**. They are **not** for NFE. [confirmed] — [Yokogawa PR 2026](https://www.yokogawa.com/us/news/press-releases/2026/yokogawa-corporation-of-america-awarded-main-automation-contractor-role-for-commonwealth-lng-project/); [LNG Prime](https://lngprime.com/contracts-and-tenders/yokogawa-bags-commonwealth-lng-gig/191593/)

### 4.2 NFE Honeywell MICC scope (publicly described)

From the October 2020 announcements. Sources: [NS Energy](https://www.nsenergybusiness.com/?p=276091), [Chemical Processing](https://www.chemicalprocessing.com/automation/automation-it/news/11297197/qatargas-lng-project-will-deploy-honeywell-leap-approach), [Control.com](https://control.com/news/honeywell-to-automate-north-field-east-initiative-for-grand-scale-production-of-liquified-natural-gas-in-qatar/), [Hart Energy](https://hartenergy.com/news/honeywell-wins-contract-automate-worlds-largest-lng-project-190450), [Processing Magazine](https://www.processingmagazine.com/process-control-automation/instrumentation/article/55350840/honeywell-to-automate-large-lng-project-with-instrumentation-and-control-solutions) — all [confirmed, trade press quoting Honeywell]:

- **Control and safety platform:** Experion PKS control and safety solutions (in Honeywell's portfolio that means Experion PKS DCS with Safety Manager / Safety Manager SC; the product mapping is [general knowledge — verify]).
- **Execution:** Honeywell **LEAP** (Lean Execution of Automation Projects): virtualisation, **Universal I/O (UIO)**, **channel/universal channel technology**, **cloud engineering** and remote engineering. The stated aims were to reduce schedule risk and capex.
- **Field:** **Smart junction boxes** for both control and safety I/O, i.e. I/O marshalled or distributed in the field rather than in the CER. The stated aims were faster execution and lower installation cost.
- **Applications:** operator training simulator (OTS), multivariable/advanced process control, pipeline management, instrument asset management (IAMS), alarm management, plant information / operations systems, and cybersecurity technology and services.
- **Location:** integration into the **NFE main control building in Ras Laffan Industrial City**.
- The client at award time was **Qatargas, for Qatar Petroleum**.

**Lessons and implications for engineers on NFE-type jobs** [general knowledge — verify unless stated]:
- **UIO + smart JBs** mean that I/O type assignment (AI/AO/DI/DO) is late-binding. Instrument index and loop drawings still need a channel allocation, but a type change no longer forces a hardware change. Review comments shift towards *JB location, environmental rating and power/heat dissipation in the field*.
- Smart JBs in Ras Laffan sun need **sunshades, IP66 or better enclosures, and thermal derating checks**. Electronics in a field enclosure can exceed 70 °C internal in summer without shading or cooling. Ask for a vendor thermal calculation against the site max ambient plus solar gain.
- **One MAC across DCS/SIS/F&G** reduces the interface work, but the **SIS must still be independent of the BPCS** per IEC 61511. Expect separate SIS controllers, separate SIS I/O channels and separate field devices for SIFs. Shared smart JBs (one JB housing both control and safety I/O) usually raise a client query on segregation.
- **Remote engineering / cloud engineering** combines with QE cybersecurity demands. Expect a requirement for IEC 62443-aligned zones and conduits and for secure remote access. [general knowledge — verify]

### 4.3 Earlier Qatar I&C references (public)

- **QP offshore PS-2 & PS-3 platforms — EPIC upgrade of instruments and control systems (Yokogawa).** The existing ESD and F&G systems were Triconex with Wonderware HMIs, operating with separate HMIs. After the upgrade, the integrated system interfaces with ESD/FGS, power monitoring, wellhead monitoring and HVAC. [confirmed — vendor case study] — [Yokogawa reference](https://www.yokogawa.com/au/library/resources/references/epic-upgrade-of-instruments-control-systems-at-ps-2-ps-3-offshore-platforms)
- **Pearl GTL (Shell/QP, Ras Laffan):** Honeywell was awarded the automation/control system contract. [confirmed — press] — [Zawya](https://www.zawya.com/en/business/honeywell-awarded-automation-control-system-contract-for-pearl-gtl-project-cbwikx8s). Pearl GTL was engineered to **Shell DEPs**, which is one reason Shell DEP practice is relevant in Qatar. [general knowledge — verify]
- **First Qatargas LNG (1996–97):** a C3 booster compressor was used in hot summers because of high seawater temperature. This is an early sign that **summer ambient/seawater is a design-limiting case** at Ras Laffan. [confirmed — OGJ] — [OGJ](https://www.ogj.com/home/article/17225871/first-lng-from-north-field-overcomes-feed-start-up-problems)
- A Qatargas poster notes that summer ambient temperatures limit LNG run-down capacity through gas-turbine constraints. [secondary — as summarised in search] — see the same search context.

### 4.4 Typical QE / QE-LNG I&C technical requirements

All items in this subsection are **[general knowledge — verify]** unless a link is given. They describe the typical content of Gulf LNG project instrument specs, not quotations from QE documents.

| Topic | Typical requirement (verify on project) |
|---|---|
| Enclosure protection | IP65 minimum, often **IP66** (IEC 60529) for outdoor field instruments and JBs; **IP66/IP67** for junction boxes and coastal/offshore; IP67/IP68 for submersible or low-point items. |
| Materials | **316/316L SS** for tubing, fittings, manifolds, instrument enclosures in coastal areas, and nameplates. Aluminium housings are often only accepted copper-free (<0.4 % Cu) with epoxy paint, or are excluded offshore. Tubing is often seamless 316 SS (ASTM A269), with **6Mo or Alloy 625/825** tubing increasingly specified for offshore and splash zones because of pitting and crevice corrosion. |
| Sour service | Wetted parts in H₂S service to **NACE MR0175 / ISO 15156** (upstream) or **NACE MR0103 / ISO 17945** (refinery/downstream). North Field gas is sour, so the upstream and inlet facilities are sour. |
| Hazardous area | IEC 60079 zoning (Zone 1 / Zone 2, IIA/IIB T3 typical; **IIC for hydrogen**). Certification to **IECEx** and/or **ATEX**; Gulf operators usually prefer IECEx. Ex d for transmitters is common practice; Ex i for loops where specified. NEC/UL Class/Division is generally not accepted unless dual-certified. |
| Signal | 4–20 mA **HART** is the norm for conventional loops. **FOUNDATION fieldbus** has been used on some Gulf projects, but the NFE MAC approach used UIO with HART. Fieldbus versus HART is a project-philosophy decision; never assume it. |
| Sunshades / sun protection | Sunshades or canopies for transmitters, local indicators, analysers and field electronics exposed to direct sun; analyser shelters air-conditioned. Use UV-resistant cable sheaths and cable glands. |
| Temperature rating | Electronics specified for **ambient up to ~55–65 °C** plus solar gain, or derated with a sunshade. Black-bulb or solar-exposed metal surface figures of **~80–85 °C** appear in Gulf specs (see §5). |
| Instrument air | Dew point well below minimum ambient. Coastal-humid sites push towards desiccant dryers. |
| SIS | IEC 61511 lifecycle; SIL determination via LOPA/risk graph; SIL verification (PFDavg) with certified data (exida/SERH); **separate sensors for SIF** (no sharing with BPCS); 2oo3 transmitters typical for SIL 2/3 initiators. |
| F&G | Point IR and open-path gas detectors; flame (multi-IR/UV-IR); H₂S detectors (electrochemical/MOS) at sour plants; ultrasonic gas leak detection on high-pressure gas modules (LNG). Voting usually 2ooN for executive action. |
| Cables | Instrument cables to **BS EN 50288-7** (or IEC 60227/60502 practice), with **flame-retardant IEC 60332-3 Cat A**, LSZH/LS0H where specified, and **fire-resistant IEC 60331** for F&G, ESD and PA circuits that must survive fire. Lead sheath or armoured cable for buried runs in hydrocarbon-contaminated soil. |
| MAC | Single MAC on NFE (Honeywell). FAT/IFAT, SAT and an integrated FAT with packages are typical. Package PLCs with a standardised communication interface (Modbus TCP/OPC) to the DCS, or hardwired for safety. |

---

## 5. Site design conditions

**Warning.** Design-basis figures differ from **climatological records**. Each project's Design Basis or Site Conditions document defines what applies, e.g. "design ambient 50 °C for equipment; 55 °C inside non-air-conditioned enclosures; 85 °C black-bulb". Quote the project design basis, not this table.

### 5.1 Qatar (Ras Laffan, Mesaieed, Dukhan, offshore North Field)

| Parameter | Value / description | Conf. | Source |
|---|---|---|---|
| Summer temperature range | **33–50 °C**, with relative humidity **up to 100 %** | C (QE HSE guideline, climatic description) | [QGL-LHH-001](https://qatarenergy.qa/en/Whatwedo/IndustrialCities/Documents/Regulations/HSE/QGL-LHH-001%20Heat%20Stress%20Guidelines%20For%20ICD%20102015.pdf) |
| Max metal temperature in sun | **85 °C** with a design ambient of **50 °C**, from a Qatar construction specification (not a QE corporate standard) | S | [Scribd 19010 Specifications](https://www.scribd.com/document/420205335/19010-Specifications-Overall) — attribution to Qatar comes from the search summary; verify |
| Seawater temperature | High in summer; drove a C3 booster compressor on Qatargas 1 | C | [OGJ](https://www.ogj.com/home/article/17225871/first-lng-from-north-field-overcomes-feed-start-up-problems) |
| Typical LNG project design ambient (dry bulb, equipment) | ~**46–50 °C** max design dry bulb; minimum ~**5 °C** | U | [general knowledge — verify] |
| NFE construction-phase cooling design point *(2nd pass)* | **48 °C dry bulb / 34 °C wet bulb** "ambient design-stress" values used by Aggreko for an NFE contractor's temporary cooling at Ras Laffan. A vendor case study, not the NFE plant design basis, but the only public Ras Laffan dry-bulb/wet-bulb pair found | S (vendor) | [Aggreko NFE case study](https://bynder.aggreko.com/m/7da79919a63f8123/original/NFE-Case-Study-Cooling.pdf) |
| Wet-bulb / coincident humidity | High coincident humidity at coastal sites (Ras Laffan, Mesaieed) causes condensation in JBs and enclosures. Specify breathers/drains, anti-condensation heaters (where a power supply exists) or IP66 with drain plugs | U | [general knowledge — verify] |
| Dust/sand | Shamal winds bring sandstorms and fine dust. Affects open-path gas detectors (beam-block), flame detector windows, air intakes, analyser shelters (positive pressure plus filters) | U | [general knowledge — verify] |
| Solar radiation | Intense, ~1,000+ W/m² peak. Drives sunshade, UV-resistant cable and enclosure thermal calculations | U | [general knowledge — verify] |
| Solar resource (climatological) *(2nd pass)* | Ground measurements from 12 Qatari stations: mean global horizontal irradiation about **5.8 kWh/m²/day (≈2,116 kWh/m²/yr)**, around **7 kWh/m²/day March–September**, clearness index about 0.64 (clear skies most of the year). Daily energy, not the instantaneous peak W/m² or a black-bulb temperature | C (peer-reviewed / QEERI) | [HBKU GHI variability study](https://elmi.hbku.edu.qa/en/publications/variability-of-measured-global-horizontal-irradiation-throughout-/), [QEERI Qatar Solar Atlas](https://hbku.edu.qa/sites/default/files/qeeri_solar_atlas.pdf) |
| Corrosion category | Coastal/industrial. Typically treated as **ISO 12944 C5 (C5-M in older editions) or CX offshore**. Chlorides cause pitting of 316 SS under deposits, especially in tubing clamps and crevices | U | [general knowledge — verify] |
| Seismic | Low seismicity | U | [general knowledge — verify] |

**Site notes** [general knowledge — verify]:
- **Ras Laffan Industrial City (RLIC):** north-east coast (the 458 MW Ras Laffan solar farm is located there; [QNA 2025](https://qna.org.qa/en/News-Area/Special-News/2025-7/28/qatars-solar-energy-projects-green-energy-in-heart-of-desert)), LNG (QE-LNG trains 1–14 plus NFE/NFS/NFW), Pearl GTL, Oryx GTL. Humid, saline and dusty. RLIC is administered by QatarEnergy's Industrial Cities Directorate, which issues site-wide HSE regulations such as QGL-LHH-001 above.
- **Mesaieed Industrial City:** east coast south of Doha (site of the 417 MW Mesaieed PV plant; [QNA 2025](https://qna.org.qa/en/News-Area/Special-News/2025-7/28/qatars-solar-energy-projects-green-energy-in-heart-of-desert)), refinery, petrochemicals, fertiliser, QAFAC. Similar coastal regime.
- **Dukhan:** west coast onshore oil field. Inland desert sites have hotter dry-bulb peaks and lower humidity than RLIC, and more dust.
- **Offshore (North Field, Al-Shaheen, Bul Hanine, Maydan Mahzam, PS-2/PS-3):** marine atmosphere, CX corrosion class, and space/weight constraints. Expect stricter material specs (6Mo/Alloy 625 tubing, 316 SS or GRP enclosures).

### 5.2 UAE (ADNOC — Abu Dhabi onshore, offshore, Ruwais, Das Island)

- ADNOC's public AGES specifications include site and environmental data sections. Examples: **Structural Design Basis – Onshore (AGES-SP-01-003)**, Section 8 "Environmental data and site conditions"; synchronous motor and adjustable-speed drive specs, §8.3 "Environmental / Site Data". The numeric values were not visible in the search snippets. [confirmed — documents exist; values not read] — [ADNOC Structural Design Basis](https://www.adnoc.ae/-/media/Adnoc-v2/Files/Specs/2021/Engineering-Standards-and-Specifications-October14th/Structural-Design-Basis--Onshore-Spec.ashx); [ADNOC Synchronous Motor Spec](https://www.adnoc.ae/-/media/Adnoc-v2/Files/Specs/2021/Engineering-Standards-and-Specifications-October14th/Synchronous-Motor-Specification.ashx); [ADNOC Electrical ASD spec](https://www.adnoc.ae/-/media/adnoc-v2/files/specs/2021/engineering-standards-and-specifications-october14th/electrical-adjustable-speed-drive-system.ashx)
- Typical ADNOC project values heard in industry: design ambient ~**50–52 °C**, solar-exposed metal ~**85 °C**, RH up to 100 % at the coast, sandstorms. **[general knowledge — verify]**. A search for the "52 °C / 85 °C" combination did not find an ADNOC document that states it.

### 5.3 Saudi Arabia (Saudi Aramco)

- Saudi Aramco engineering standards (**SAES**), materials system specifications (**SAMSS**) and standard drawings define site conditions. The instrumentation SAES are the **SAES-J** series, e.g. SAES-J-100 (flow), SAES-J-200 (pressure), SAES-J-400 (temperature), SAES-J-600 (pressure relief), SAES-J-601 (emergency shutdown and isolation systems), SAES-J-902 (electrical systems for instrumentation). Instrument-specific SAMSS use the **34-SAMSS-xxx** range. These numbers and titles are now confirmed or secondary-sourced with links in **knowledge file 02 (Saudi Aramco)**; use that file for Aramco questions.
- The instrument ambient basis is **SAES-J-003**: its 2004 issue sets 35 °C (indoor air-conditioned), 55 °C (outdoor sheltered) and 65 °C (outdoor unsheltered) maximums; whether the 2013 issue changed these is unconfirmed. [secondary source — see file 02 §3.1]
- Typical Aramco design values heard in industry: outdoor design ambient ~**50 °C** with solar-exposed surfaces higher; the Eastern Province coast (Ras Tanura, Jubail) is extremely humid; inland is very dusty. **[general knowledge — verify]**

### 5.4 Oman (PDO)

- PDO uses a **DEP-based** system (Shell heritage) with its own **SP** (specification) and **PR** (procedure) documents. The SP/PR numbering is now confirmed by circulating copies (see §6.5). No PDO SP number for **instrumentation** was found. [secondary source for the numbering; gap for instrumentation]
- Climate: interior desert fields (Fahud, Nimr, Marmul, Qarn Alam) have dry-bulb extremes near 50 °C, low humidity and heavy dust. The southern coast (Dhofar) has a khareef monsoon. **[general knowledge — verify]**

### 5.5 Kuwait (KOC / KNPC / KIPIC)

- Kuwait has some of the highest recorded ambient temperatures in the region. Inland Mitribah's ~54 °C reading (2016) was accepted by the WMO as one of the highest reliably measured temperatures. **[general knowledge — verify]**. Project design ambient for KOC/KNPC work is typically ~**50–52 °C** with high dust loading. **[general knowledge — verify]**
- KOC and KNPC have their own engineering standards. KOC instrumentation standards use a **"KOC-I-nnn"** prefix: **KOC-I-026 "KOC Standard for Process Flow Measurement"** (Rev 0, 19 Dec 2019) is the confirmed example (see §6.4). [secondary source — upgraded from unverified in the 2nd pass]

### 5.6 Cross-region design checklist for I&C (all [general knowledge — verify])

1. Find the project's **max design ambient**, **solar-exposed surface temperature**, **min ambient**, **RH range**, **corrosion category**, **dust/sand classification** and **seismic zone** in the Design Basis.
2. Check every electronic device's **max operating temperature** against: max ambient + solar gain − sunshade benefit (or + enclosure internal rise). LCD displays often have lower limits than the electronics.
3. Check the **ambient temperature range of the Ex certificate**, typically −20 °C to +40 °C by default under IEC 60079-0 unless extended. Devices **must be certified for the site ambient, e.g. +60 °C**, which is a frequent cause of Gulf datasheet comments.
4. Check **IP rating plus breather/drain** strategy in humid coastal sites.
5. Specify **UV-resistant** cable outer sheaths, cable glands and plastic parts.
6. Analyser houses: **HVAC sized for the max ambient plus solar load**, positive pressure, gas detection at the HVAC inlet.

---

## 6. Shell DEP / ADNOC / others index

### 6.1 Shell DEPs (Design and Engineering Practice), 32-series (instrumentation)

The DEP titles below come mainly from **unofficial copies of the Shell DEP index** (e.g. an "Index of DEPs Version 28, February 2009" and later lists). Shell restructured many DEPs around 2011–2017, adding "-Gen." (generic) and regional suffixes such as "-CSPC". Revisions and titles may have changed since. Status: **[secondary source]** unless noted. Index copies: [pdfcoffee Shell DEP Index](https://pdfcoffee.com/shell-dep-index-pdf-free.html), [pdfcoffee edoc.pub list](https://pdfcoffee.com/download/edocpub248602254-shell-dep-listpdf-pdf-free.html), [kupdf Shell DEP list](https://kupdf.net/download/shell-dep-list_58a7fd1c6454a7cb55b1e8d0_pdf), [Hercules Shell standards list](https://www.herculesebooks.com/index/SHELL.PDF), [Scribd DEP table of contents](https://www.scribd.com/document/398693986/DEP-Shell-table-of-contents).

| DEP number | Title (as indexed) | Note vs. earlier assumed titles | Conf. | Source |
|---|---|---|---|---|
| **32.10.03.10-Gen.** | Instrumentation symbols and identification | — | S | index copies |
| **32.30.20.11-Gen.** | **Fire, gas and smoke detection systems** | Not "field instrumentation" | S | index copies |
| **32.31.00.32-Gen.** | **Instruments for measurement and control** | Correct ("field instrumentation" in effect) | S | index copies |
| **32.31.09.31-Gen.** | **Instrumentation for equipment packages** (a Sept 2011 edition is noted) | Sometimes mis-attributed to 32.31.00.32 | S | index copies |
| **32.31.50.10-Gen.** | On-line process analysers | — | S | index copies |
| **32.32.00.11-Gen.** | Custody transfer measurement (liquid) | — | S | index copies |
| **32.36.01.17-Gen.** | **Control valves – Selection, sizing and specification** (an old edition dated July 1987 is also cited) | Correct | S | index copies; [Scribd Shell DEP & MESC overview](https://www.scribd.com/document/366270322/kupdf-com-list-shell-dep-amp-mesc-spe-pdf) |
| **32.36.01.18-Gen.** | Selection and procurement of actuators for on-off valves (excludes control-valve actuators) | — | S | [pdfcoffee DEP 32.36.01.18-2014](https://pdfcoffee.com/dep32360118-2014-pdf-free.html) |
| **32.37.10.11-Gen.** | Installation of on-line instruments (also listed as "Instrument impulse lines" in some indexes) | — | S (title varies by index) | index copies |
| **32.37.20.10-Gen.** | Instrument signal lines (a "-CSPC" variant also exists) | — | S | index copies; [wixsite mention — low quality](https://imogenepittari529p.wixsite.com/tetvgohathe/post/shell-dep-32-37-20-10) |
| **32.71.00.10-Gen.** | Plant telecommunication | — | S | index copies |
| **32.80.10.10-Gen.** | **Instrumented protective functions (IPF)**. A copy is titled "Classification and implementation of instrumented protective functions" | Correct (SIS / IPF) | S | [wyrcad copy](https://www.wyrcad.com/shell-dep/32801010%20CLASSIFICATION%20AND%20IMPLEMENTATION%20OF%20INSTRUMENTED%20PROTECTIVE%20FUNCTIONS.pdf) |
| **32.80.10.14-Gen.** | Alarm management. It defines an IPF as initiator function + logic solver function + final element function | — | S | [pdfcoffee alarm management](https://pdfcoffee.com/download/alarm-management-13-pdf-free.html) |
| **32.80.10.30-CSPC** | Instrumented protective systems (technical specification) | — | S | index copies |
| **32.80.10.11** | Title not found | — | U | — |
| **32.01.23.17-Gen.** (Feb 2014) | Process Control Domain – Security requirements for suppliers. It has a section on secure connections to instrumented protective systems | — | S | [Scribd](https://www.scribd.com/document/691940985/32-01-23-17) |
| **32.01.20.12-Gen.** | Cited by the instrument asset management DEP; title not seen | — | U | [pdfcoffee IAMS spec 2017-02](https://pdfcoffee.com/spec-2017-02-shell-dep-instrument-asset-management-pdf-free.html) |
| (Instrument Asset Management DEP, "Spec 2017-02") | Instrument asset management | — | S | same |

**Common mis-attributions to correct:**
- DEP **32.31.00.32** is **"Instruments for measurement and control"**, the general field-instrument DEP. It is *not* "instrumentation for equipment packages". The packages DEP is **32.31.09.31**.
- DEP **32.36.01.17** is **control valves (selection, sizing, specification)**: confirmed by index copies.
- DEP **32.80.10.10** is **instrumented protective functions (IPF)**: confirmed by index copies and a document copy.
- DEP **32.30.20.11** is **fire, gas and smoke detection systems**, not "field instrumentation".

**Shell IPF methodology note.** Secondary sources describe SIL/IPF classification studies done "per IEC 61508/61511 and DEP 32.80.10.10" together. In other words, the DEP is Shell's implementation of the IEC 61511 lifecycle, and its IPF classification method uses a risk-graph-style approach. [secondary source] — [azsepakat functional safety page](https://www.azsepakat.com/index.php?option=com_content&view=article&id=12&Itemid=41); [IEC 61511 background](https://en.wikipedia.org/wiki/IEC_61511). The specific risk-graph calibration is [general knowledge — verify].

**Why Shell DEPs matter in Qatar.** Pearl GTL, Qatargas 4 (Shell partner) and many Shell-trained engineers and operators carried DEP practice into Qatari projects. QE project specs often look DEP-like, e.g. IPF terminology and "IPS" for the SIS logic solver. [general knowledge — verify]

### 6.2 ADNOC Group engineering specifications (AGES)

ADNOC publishes many AGES documents on adnoc.ae under "Engineering Standards and Specifications" (released October 2021). They are marked "ADNOC Classification: Public", even though the cover also says the content is proprietary. This makes ADNOC the **most publicly verifiable** Gulf operator. [confirmed — documents hosted on adnoc.ae]

ADNOC's own *Instrumentation, Control and Telecom procurement opportunities* (Make-it-in-the-Emirates) document lists the AGES-SP-04 series. [confirmed] — [ADNOC ICT procurement list](https://www.adnoc.ae/-/media/adnoc-v2/sub-brands/makeit/files/ict.ashx)

| Number | Title | Notes | Conf. | Source |
|---|---|---|---|---|
| **AGES-SP-04-001** | Process Control System Specification | DCS | C | [ADNOC ICT list](https://www.adnoc.ae/-/media/adnoc-v2/sub-brands/makeit/files/ict.ashx); [Process Control Spec](https://www.adnoc.ae/-/media/Adnoc-v2/Files/Specs/2021/Engineering-Standards-and-Specifications-October14th/Process-Control-Specification.ashx) |
| **AGES-SP-04-002** | Control Valve Specification | Methodology and requirements for selection and sizing of control valves and accessories, general and severe service | S (copy on Studocu) | [Studocu](https://www.studocu.com/row/document/abu-dhabi-national-oil-company-schools/instrumentation/9-ages-sp-04-002-control-valve-specification-1-1-1/111869265) |
| **AGES-SP-04-003** | Fire & Gas System Specification | F&G logic system | C | [ADNOC ICT list](https://www.adnoc.ae/-/media/adnoc-v2/sub-brands/makeit/files/ict.ashx) |
| **AGES-SP-04-004** | Emergency Shutdown (SIS) System Specification | Excludes solid-state ESD systems, field input devices and final elements | C (list) / S (scope from copy) | [ADNOC ICT list](https://www.adnoc.ae/-/media/adnoc-v2/sub-brands/makeit/files/ict.ashx); [Studocu](https://www.studocu.com/row/document/aspen-heights-british-school-abu-dhabi/a-level-geography/emergency-shutdown-sis-specification/114387107) |
| **AGES-SP-04-005** | Emergency Shutdown and On/Off Valve Specification | — | S (index on Studocu) | [Studocu index](https://www.studocu.com/row/document/abu-dhabi-national-oil-company-schools/instrumentation/9-ages-sp-04-002-control-valve-specification-1-1-1/111869265) |
| **AGES-SP-04-006** | Instrument and Control Cables Specification | Analogue and digital signal cables etc.; 30-year design life for continuous operation | C | [adnoc.ae I&C cables spec](https://www.adnoc.ae/-/media/adnoc-v2/files/specs/2021/instrument-and-control-cables-specification.ashx?la=en&hash=26FE74FA9E23A98B0929E88AC43C3216CC0C630E) |
| AGES-SP-04-007 … -010 | Not identified | — | U | — |
| **AGES-SP-04-011** | Fire and Gas Detectors | — | C | [ADNOC ICT list](https://www.adnoc.ae/-/media/adnoc-v2/sub-brands/makeit/files/ict.ashx) |
| **AGES-SP-04-015** | Machinery Instrument System Specification | Machinery protection / condition monitoring | C | same |
| **AGES-SP-04-018** | Programmable Logic Controllers | — | C | same |
| AGES-SP-01-003 | Structural Design Basis – Onshore | §8 environmental data & site conditions | C | [adnoc.ae](https://www.adnoc.ae/-/media/Adnoc-v2/Files/Specs/2021/Engineering-Standards-and-Specifications-October14th/Structural-Design-Basis--Onshore-Spec.ashx) |
| (number not captured) | Process Design Criteria | Process basis; probably includes site data | C (exists) | [adnoc.ae](https://www.adnoc.ae/-/media/adnoc-v2/files/specs/2021/engineering-standards-and-specifications-october14th/process-design-criteria.ashx) |
| (number not captured) | Isolation, Vent and Drain Philosophy | Relevant to instrument isolation/hook-up | C (exists) | [adnoc.ae](https://www.adnoc.ae/-/media/adnoc-v2/files/specs/2021/engineering-standards-and-specifications-october14th/isolation-vent-and-drain-philosophy.ashx) |
| (number not captured) | Piping Basis of Design | Piping, including small-bore/instrument connections | C (exists) | [adnoc.ae](https://www.adnoc.ae/-/media/adnoc-v2/files/specs/2021/engineering-standards-and-specifications-october14th/piping-basis-of-design.ashx) |
| (number not captured) | Electrical Engineering Design Guide | Electrical, including hazardous area | C (exists) | [adnoc.ae](https://www.adnoc.ae/-/media/adnoc-v2/files/specs/2021/engineering-standards-and-specifications-october14th/electrical-engineering-design-guide.ashx) |

**Numbering convention** [inference from the examples]: `AGES-<type>-<discipline>-<serial>`. Here "SP" means specification (other types seen include design guides and philosophies), "01" is structural/civil (from SP-01-003) and "04" is instrumentation, control & telecom.

**ADNOC project document example.** Saipem's Hail & Ghasha project (ADNOC) has a philosophy document numbered **1-CF0000-59-PHL-0001**. Only the document number appeared in the listing; its title was not visible. [secondary source] — listing at [pages.dev](https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-32855---Saipem-Hail--and--Ghasha/RFQ-Files/Reference-documents/1-CF0000-59-PHL-0001-00_00) (host unreachable here)

### 6.3 Saudi Aramco (reference only)

- The instrumentation SAES-J series and the **34-SAMSS** instrument material specifications are well known in the industry. Aramco historically issued a "Technically Acceptable Instrument Manufacturers" standard (SAES-J-002, last seen as a 2004 revision); current vendor approval runs through 9COM plant approvals (SAEP-1400). Numbers, titles and sources are in **knowledge file 02 (Saudi Aramco)**; use that file rather than this section. [see file 02 for tags]

### 6.4 KOC / KNPC (Kuwait)

- KOC has its own standards set. KNPC/KIPIC (e.g. Al-Zour refinery, Clean Fuels Project) used project specs drawing on Shell, Exxon and licensor practices. **[general knowledge — verify]**
- **KOC numbering** *(2nd pass)*: `KOC-<discipline letter>-<nnn>`, with revision and date appended on circulating copies. [secondary source — unofficial copies]

| Number | Title / scope | Conf. | Source |
|---|---|---|---|
| **KOC-I-026** (Rev 0, 19 Dec 2019) | KOC Standard for Process Flow Measurement: minimum requirements for design, selection, construction and installation of flowmeters at KOC facilities; partially supersedes older KOC documents 381/029 and 015-JH-1903 | S | [Scribd KOC-I-026](https://2.zoppoz.workers.dev:443/https/www.scribd.com/document/702513746/KOC-I-026-R0-19-12-2019) |
| KOC-Q-014 (R2, 08 Mar 2017) | QA/QC standard (not I&C) | S | [studylib KOC-Q-014](https://www.studylib.net/doc/28042388/koc-q-014-r2-08-03-2017) |
| KOC-P-004 (Part 10, Rev 2) | Pipeline coating (not I&C) — shows the prefix pattern | S | [Scribd KOC-P-004](https://www.scribd.com/document/648054358/Koc-p-004-Part-10-Rev-2) |
| KOC-S-005 | "Instrumentation General Specification" per a single blog; prefix inconsistent with KOC-I- | U — do not quote | [blog](https://instrumentengineer3.blogspot.com/2025/10/introduction-in-oil-gas-petrochemical.html) |

- Other KOC numbers seen in the same search (KOC-MP-014 to -016 and KOC-M-012 for valves) are not instrumentation. No KNPC instrumentation numbers were found. [secondary source]

### 6.5 PDO (Oman)

- PDO uses Shell-heritage DEPs plus PDO **SP-xxxx** specifications and **PR-xxxx** procedures. **ERD** (Engineering Reference Documents) remains **[general knowledge — verify]**; no source mentioned it in the 2nd pass.
- **PDO SP numbers seen** *(2nd pass)*, all [secondary source] (Scribd copies; footers reference PDO's Livelink document system). None is an instrumentation specification; searches for SP-1101, SP-1105, SP-1146 and SP-1150 returned nothing:

| Number | Title | Source |
|---|---|---|
| SP-1099 | Specification for Electrical Installation Practice (v05, Dec 2006) | [Scribd](https://www.scribd.com/document/429431786/Electrical-Installation-Requirements) |
| SP-1171 | Quality management system specification (product and service) | [Scribd](https://www.scribd.com/document/699597904/SP-1171) |
| SP-1177 | Specification for Welding of Class 1 Pipelines | [Scribd](https://www.scribd.com/document/411570128/SP-1177-V3-0) |
| SP-1211 | Onshore Pipeline Engineering (rev 6.1, Aug 2022 print) | [Scribd](https://www.scribd.com/document/637278036/SP-1211) |
| SP-1236 | Isolation Systems for Cathodically Protected Pipelines | [Scribd](https://www.scribd.com/document/563109110/SP-1236) |
| SP-2154 | On-plot valves (MESC and non-MESC categories) | [Scribd](https://www.scribd.com/document/637278030/SP-2154) |
| PR-1172 | Permit to Work Procedure | [Scribd](https://www.scribd.com/document/295105710/PR-1172-Permit-to-Work-Procedure) |

- Practical inference: PDO instrumentation requirements are probably carried mainly by Shell DEP 32-series documents (see §6.1) plus project specifications, but this is [general knowledge — verify].

### 6.6 International standards that Gulf operator specs invariably invoke

These are [general knowledge] but stable and non-controversial:

- IEC 61511 (SIS), IEC 61508
- IEC 60079 series (Ex) and IECEx
- IEC 60529 (IP)
- ISA-5.1 (symbols)
- ISA-75 / IEC 60534 (control valves)
- API RP 551/552/554/555/556
- API 670 (machinery protection)
- ISO 15156 / NACE MR0175
- IEC 62443 (OT cybersecurity)
- EEMUA 191 / ISA-18.2 (alarm management)
- IEC 60331 / 60332 (cable fire performance)
- BS EN 50288-7 (instrument cables)

---

## 7. Typical client review comments

These are **typical comment themes** seen on Gulf NOC and LNG project instrument deliverables. They are **[general knowledge — verify]**: patterns, not quotes from QE, ADNOC or other review sheets. Use them to pre-empt comments or to explain why a comment was raised.

### 7.1 Instrument datasheets
1. "Ex certificate ambient range does not cover site max design ambient — provide certificate valid to +60 °C (or project value)."
2. "Housing material: aluminium not acceptable in coastal/offshore environment — 316 SS required" (or "copper-free aluminium with epoxy coating per spec").
3. "IP rating to be IP66 minimum (IP67 where submersion possible)."
4. "Wetted parts in sour service to comply with NACE MR0175/ISO 15156 — vendor to confirm compliance and provide material certificates (EN 10204 3.1)."
5. "Provide sunshade; LCD rated temperature to be confirmed."
6. "Vendor/model not in Company approved manufacturer list — submit pre-qualification/deviation request."
7. "SIL certificate (IEC 61508, SC/SIL capability, λ values) required for SIF devices; certificate to be from accredited third party."
8. "HART revision / DD files / FDT-DTM to be compatible with IAMS of the MAC system."
9. "Range/span: normal operating point to be between 30 % and 70 % of calibrated range" (or the project-specific rule).
10. "Process connection: flanged per piping class; screwed connections not allowed on hydrocarbon service beyond the root valve" (or the project-specific rule).

### 7.2 Control valves / on-off valves
1. "Noise > 85 dB(A) at 1 m — provide low-noise trim or justify."
2. "Fire-safe certification (API 607/ISO 10497) required for ESD valves."
3. "Leakage class: ESD valves tight shut-off (e.g. API 598 / ISO 5208 Rate A) as per philosophy."
4. "Actuator sizing safety factor and stroking time vs. SRS requirement to be demonstrated; provide partial-stroke test capability for SIL-rated valves."
5. "Fugitive emission certification (ISO 15848-1) required" — increasingly common in QE and ADNOC sustainability-driven specs.

### 7.3 SIS / F&G
1. "SIF initiators shall not be shared with BPCS; separate tapping points."
2. "SIL verification to include proof-test coverage and realistic MTTR; common cause β factors to be justified."
3. "F&G detector coverage mapping to be performance-based (ISA TR84.00.07) — geographic and scenario coverage targets per F&G philosophy."
4. "Voting for executive action 2ooN; single detector alarm only."
5. "Cause & Effect charts to align with SRS and F&G philosophy; bypass/override management to be shown."

### 7.4 Cables, JBs, installation
1. "F&G, ESD and PA circuits to be fire-resistant IEC 60331."
2. "JB enclosures 316 SS IP66; cable glands Ex-certified, double-compression, brass nickel-plated / SS."
3. "Intrinsically safe and non-IS circuits to be segregated in separate JBs/multicores with light-blue identification."
4. "Hook-up drawings: tubing 316 SS seamless, double ferrule fittings, minimum wall thickness per spec; slope requirements for impulse lines."
5. "Instrument earth and IS earth to be separate from electrical earth; earth bar arrangement to be shown."

### 7.5 Systems / MAC
1. "Cybersecurity: architecture to follow IEC 62443 zones and conduits; remote access via DMZ only."
2. "Spare capacity: installed spare I/O ≥ 20 % and space for 20 % future" (or the project-specific numbers) "after FAT."
3. "Third-party package interfaces: safety-related signals hardwired; serial for monitoring only."
4. "OTS fidelity and model update obligations to be defined."
5. "Alarm rationalisation per EEMUA 191 / ISA-18.2 before FAT."

---

## 8. Gaps & next research steps

**Process limitations encountered:**
- **WebFetch was blocked** (DNS failure) for adnoc.ae, pdfcoffee.com, studylib.net, blogspot.com and pages.dev, so no full-document reads were possible. Facts depend on search-result summaries.
- **2nd pass (Nov 2026):** WebFetch still failed for scribd.com, aramco.com and pages.dev; only about 7 searches were spent on this file.
- **The web-search budget ran out** partway through, before the ADNOC detail, KOC, PDO, Aramco and climate searches were done. A follow-up session with more searches, or with these hosts allowed in the network settings, would let those sections be completed.

**Content gaps (highest priority first):**
1. **No public QE/QP instrumentation, F&G, SIS or telecom standard numbers were confirmed.** Only electrical, drafting, dossier and HSE "ES."/CORP numbers surfaced. "QP-STD-E&I-100" is unverified. *Next step:* ask project teams for the "Applicable QE Standards" list in any NFE/NFS/NFW ITB, or search QE tender notices on the Mushtaryat portal.
2. **NFS/NFW MAC and DCS/SIS/F&G vendors were not found** in public sources. They may be EPC-subcontracted without a press release. *Next step:* vendor press rooms (Honeywell, Yokogawa, Emerson, ABB, Schneider/AVEVA), MEED project profiles.
3. **Quantitative Qatar design basis** (max design dry bulb, wet bulb, black-bulb, min temperature, wind, dust, corrosion class) is still only confirmed at climatological level (33–50 °C, RH to 100 %; GHI ≈ 5.8 kWh/m²/day). The only public Ras Laffan design pair is a vendor's construction-cooling point (48 °C DB / 34 °C WB). No public black-bulb, design RH or peak W/m² figure for Ras Laffan or Mesaieed was found in the 2nd pass. *Next step:* ASHRAE climatic data for Doha, or the project Site Conditions document.
4. **ADNOC AGES-SP-04-007 to -010, -012 to -014, -016, -017** are unidentified. ADNOC site-condition numerics were not read.
5. **Shell DEP current revisions:** all titles come from index copies that are about 10–17 years old. DEP 32.80.10.11 and 32.01.20.12 titles were not found.
6. **Saudi Aramco SAES-J / 34-SAMSS** numbers are now covered in file 02. **KOC**: only KOC-I-026 (process flow measurement) found for instrumentation; the rest of the KOC-I series is unknown. **KNPC**: nothing found. **PDO**: SP/PR numbering confirmed (SP-1099, -1171, -1177, -1211, -1236, -2154; PR-1172) but **no instrumentation SP number** found; SP-1101/1105/1146/1150 not found.
7. **QP PPML acronym and structure**: the exact meaning and how it maps to the QE-LNG AVL were not confirmed.
8. **QE-LNG (ex-Qatargas/RasGas) document numbering**: partly resolved in the 2nd pass (PRJ-PJL-PRC-004/005/008 procedures; five-segment engineering document number; three-segment vendor number; RG-DFO-002 merged). Still missing: the instrument tag format inside PRJ-PJL-PRC-008, discipline and document-type code lists, and which PRC number holds the document-numbering rule. QE-LNG instrument/F&G/SIS philosophy numbers were not found.
9. **Fieldbus vs HART at QE-LNG**: NFE public material mentions UIO, smart JBs and IAMS but not the field protocol. Whether FOUNDATION fieldbus was used on earlier Qatargas/RasGas mega-trains was not confirmed.

---

## 9. Source list

**QatarEnergy / Qatar official & press**
- QE CORP-HSE-STD-080 — https://qatarenergy.qa/en/SupplyManagement/Tenders/SupplyManagmentFiles/CORP-HSE-STD-080%20CORPORATE%20STANDARD%20FOR%20MANAGING%20HSE%20IN%20CONTRACTS.pdf
- QE CORP-HSE-PRC-080 — https://www.qatarenergy.qa/en/SupplyManagement/Tenders/Documents/HSE/CORP-HSE-PRC-080%20CORPORATE%20PROCEDURE%20FOR%20MANAGING%20HSE%20IN%20CONTRACTS.pdf
- QE GTCP Rev 4 — https://www.qatarenergy.qa/en/SupplyManagement/Tenders/Documents/General%20Terms%20and%20Conditions%20of%20Purchase%20(GTCP)%20(Schedule%20C)%20-%20Rev%204%20(1021).pdf
- QE GTCP Appendix D Rev 5 — https://www.qatarenergy.qa/en/SupplyManagement/Tenders/Documents/Appendix%20D%20to%20General%20Terms%20and%20Conditions%20of%20Purchase%20(Schedule%20C)%20Rev%205%20(0124).pdf
- QE Buy tenders online (Mushtaryat) — https://qatarenergy.qa/en/SupplyManagement/Tenders/Pages/Buytendersonline.aspx
- QE How to tender (purchasing) — https://qatarenergy.qa/en/SupplyManagement/Tenders/Pages/Howtotenderpurchasingdepartment.aspx
- QE How to tender (contracts) — https://www.qatarenergy.qa/en/SupplyManagement/Tenders/Pages/Howtotendercontractsdepartment.aspx
- QatarEnergy LNG suppliers — https://www.qatarenergylng.qa/Suppliers
- QGL-LHH-001 Heat Stress Guidelines — https://qatarenergy.qa/en/Whatwedo/IndustrialCities/Documents/Regulations/HSE/QGL-LHH-001%20Heat%20Stress%20Guidelines%20For%20ICD%20102015.pdf
- Tawteen launch (Gulf Times) — https://www.gulf-times.com/story/618648/qp-to-enhance-localisation-of-energy-sectors-supply-chain
- ICV evaluation from July 2020 (Gulf Times) — https://www.gulf-times.com/story/666876/qp-announces-start-of-icv-evaluation-in-energy-sector-tenders-from-july
- ICV evaluation (The Peninsula) — https://thepeninsulaqatar.com/article/29/06/2020/Qatar-Petroleum-announces-start-of-In-Country-Value-evaluation-in-energy-sector-tenders-starting-July
- ICV digital portal (The Peninsula 2022) — https://thepeninsulaqatar.com/article/31/03/2022/qatarenergy-launches-tawteen-in-country-value-digital-portal
- Enhanced ICV (The Peninsula 2024) — https://thepeninsulaqatar.com/article/07/10/2024/qatarenergy-announces-introduction-of-enhanced-in-country-value-program
- Enhanced ICV (Gulf Times) — https://www.gulf-times.com/article/692098/business/qatarenergy-launches-enhanced-in-country-value-programme
- QNA Tawteen/ICV Dec 2023 — https://www.qna.org.qa/en/News-Area/News/2023-12/01/0032-qatarenergy-reviews-tawteen,-icv-programs-within-activities-of-made-in-qatar
- KPMG Tawteen ICV certification — https://kpmg.com/qa/en/services/audit/tawteen-icv-in-country-value-certification.html
- QAFAC Tawteen — https://www.qafac.com.qa/tawteen

**NFE / NFS / NFW / other Qatar projects**
- Honeywell NFE — https://worldoil.com/news/2020/10/22/honeywell-to-automate-world-s-largest-lng-project/
- Honeywell NFE — https://www.nsenergybusiness.com/?p=276091
- Honeywell NFE LEAP — https://www.chemicalprocessing.com/automation/automation-it/news/11297197/qatargas-lng-project-will-deploy-honeywell-leap-approach
- Honeywell NFE — https://control.com/news/honeywell-to-automate-north-field-east-initiative-for-grand-scale-production-of-liquified-natural-gas-in-qatar/
- Honeywell NFE — https://hartenergy.com/news/honeywell-wins-contract-automate-worlds-largest-lng-project-190450
- Honeywell NFE — https://www.processingmagazine.com/process-control-automation/instrumentation/article/55350840/honeywell-to-automate-large-lng-project-with-instrumentation-and-control-solutions
- Honeywell NFE (LNG Prime) — https://lngprime.com/?p=5847
- MEED NFE profile — https://meedprojects.com/project-profile/?pid=229962
- NFE EPC (Digital Refining) — https://digitalrefining.com/news/1006346/technip-energies-and-chiyoda-awarded-major-lng-contract
- NFE EPC (LNG Industry) — https://www.lngindustry.com/liquid-natural-gas/09022021/technip-energies-and-chiyoda-awarded-major-lng-contract
- NFS EPC — https://www.gasprocessingnews.com/news/2023/05/technip-energies-awarded-a-major-lng-contract-for-the-north-field-south-project-by-qatarenergy/
- NFS EPC — https://thepeninsulaqatar.com/article/16/05/2023/qatarenergy-awards-10-billion-worth-epc-contract-for-north-field-south-project
- NFS EPC — https://www.oedigital.com/amp/news/505132-qatarenergy-awards-10b-epc-contract-to-technip-energies-led-joint-venture
- NFS AP-X technology — https://theenergyyear.com/?p=39749
- NFW EPC (Technip Energies) — https://www.ten.com/en/media/press-releases/technip-energies-awarded-major-lng-contract-north-field-west-project
- NFW EPC (QNA) — https://qna.org.qa/en/News-Area/News/2026-2/25/qatarenergy-awards-epc-contract-for-north-field-west-16-mtpa-lng-project
- NFW EPC (LNG Prime) — https://lngprime.com/contracts-and-tenders/qatarenergy-awards-north-field-west-epc-gig-to-technip-energies-jv/178516/
- NFW schedule (MEES) — https://www.mees.com/2026/2/27/oil-gas/qatars-nfw-lng-expansion-project-slips-beyond-2030/e1c54540-13e5-11f1-94ef-5b4d372885a7
- Yokogawa Commonwealth LNG (not Qatar) — https://www.yokogawa.com/us/news/press-releases/2026/yokogawa-corporation-of-america-awarded-main-automation-contractor-role-for-commonwealth-lng-project/
- Yokogawa Commonwealth LNG (LNG Prime) — https://lngprime.com/contracts-and-tenders/yokogawa-bags-commonwealth-lng-gig/191593/
- Yokogawa QP PS-2/PS-3 — https://www.yokogawa.com/au/library/resources/references/epic-upgrade-of-instruments-control-systems-at-ps-2-ps-3-offshore-platforms
- Honeywell Pearl GTL — https://www.zawya.com/en/business/honeywell-awarded-automation-control-system-contract-for-pearl-gtl-project-cbwikx8s
- OGJ first Qatargas LNG — https://www.ogj.com/home/article/17225871/first-lng-from-north-field-overcomes-feed-start-up-problems

**Secondary (document-sharing) — QP/Qatar**
- ES.2.14.0070 — https://www.scribd.com/document/485459233/ES-2-14-0070RAElectricalPowerControlCables-pdf
- ES.0.06.0021 — https://www.scribd.com/document/440845386/ES-0-06-0021-Project-Dossier
- ES.D.10 — https://www.scribd.com/document/466429022/ES-D-10-Draughting-pdf
- QSP-QAC-09 — https://www.scribd.com/document/595666553/QATAR-PETROLUM-QSP-QAC-09
- QP PPML Q4 2021 — https://www.scribd.com/document/625318634/QP-PPML-Q4-2021
- Qatargas control & shutdown philosophy — https://www.scribd.com/document/722624967/CONTROL-SD
- 19010 Specifications Overall (85 °C / 50 °C) — https://www.scribd.com/document/420205335/19010-Specifications-Overall

**Shell DEP**
- DEP 32.80.10.10 copy — https://www.wyrcad.com/shell-dep/32801010%20CLASSIFICATION%20AND%20IMPLEMENTATION%20OF%20INSTRUMENTED%20PROTECTIVE%20FUNCTIONS.pdf
- Shell DEP index — https://pdfcoffee.com/shell-dep-index-pdf-free.html
- Shell DEP list — https://pdfcoffee.com/download/edocpub248602254-shell-dep-listpdf-pdf-free.html
- Shell DEP list — https://kupdf.net/download/shell-dep-list_58a7fd1c6454a7cb55b1e8d0_pdf
- Hercules Shell list — https://www.herculesebooks.com/index/SHELL.PDF
- DEP table of contents — https://www.scribd.com/document/398693986/DEP-Shell-table-of-contents
- DEP & MESC overview — https://www.scribd.com/document/366270322/kupdf-com-list-shell-dep-amp-mesc-spe-pdf
- DEP 32.36.01.18 — https://pdfcoffee.com/dep32360118-2014-pdf-free.html
- DEP 32.80.10.14 — https://pdfcoffee.com/download/alarm-management-13-pdf-free.html
- DEP 32.01.23.17 — https://www.scribd.com/document/691940985/32-01-23-17
- Instrument asset management DEP — https://pdfcoffee.com/spec-2017-02-shell-dep-instrument-asset-management-pdf-free.html
- Functional safety (IEC 61511 + DEP 32.80.10.10) — https://www.azsepakat.com/index.php?option=com_content&view=article&id=12&Itemid=41
- IEC 61511 — https://en.wikipedia.org/wiki/IEC_61511

**ADNOC**
- ICT procurement list — https://www.adnoc.ae/-/media/adnoc-v2/sub-brands/makeit/files/ict.ashx
- Process Control Specification — https://www.adnoc.ae/-/media/Adnoc-v2/Files/Specs/2021/Engineering-Standards-and-Specifications-October14th/Process-Control-Specification.ashx
- Instrument & Control Cables Specification — https://www.adnoc.ae/-/media/adnoc-v2/files/specs/2021/instrument-and-control-cables-specification.ashx?la=en&hash=26FE74FA9E23A98B0929E88AC43C3216CC0C630E
- AGES-SP-04-002 (Studocu) — https://www.studocu.com/row/document/abu-dhabi-national-oil-company-schools/instrumentation/9-ages-sp-04-002-control-valve-specification-1-1-1/111869265
- AGES-SP-04-004 (Studocu) — https://www.studocu.com/row/document/aspen-heights-british-school-abu-dhabi/a-level-geography/emergency-shutdown-sis-specification/114387107
- Structural Design Basis Onshore — https://www.adnoc.ae/-/media/Adnoc-v2/Files/Specs/2021/Engineering-Standards-and-Specifications-October14th/Structural-Design-Basis--Onshore-Spec.ashx
- Process Design Criteria — https://www.adnoc.ae/-/media/adnoc-v2/files/specs/2021/engineering-standards-and-specifications-october14th/process-design-criteria.ashx
- Isolation Vent & Drain Philosophy — https://www.adnoc.ae/-/media/adnoc-v2/files/specs/2021/engineering-standards-and-specifications-october14th/isolation-vent-and-drain-philosophy.ashx
- Piping Basis of Design — https://www.adnoc.ae/-/media/adnoc-v2/files/specs/2021/engineering-standards-and-specifications-october14th/piping-basis-of-design.ashx
- Electrical Engineering Design Guide — https://www.adnoc.ae/-/media/adnoc-v2/files/specs/2021/engineering-standards-and-specifications-october14th/electrical-engineering-design-guide.ashx
- Synchronous Motor Spec — https://www.adnoc.ae/-/media/Adnoc-v2/Files/Specs/2021/Engineering-Standards-and-Specifications-October14th/Synchronous-Motor-Specification.ashx
- Electrical ASD Spec — https://www.adnoc.ae/-/media/adnoc-v2/files/specs/2021/engineering-standards-and-specifications-october14th/electrical-adjustable-speed-drive-system.ashx

**2nd-pass additions (November 2026)**
- QE-LNG PRJ-PJL-PRC-005 (rev 21) listing — https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-32705---Saipem-COMP3/RFQ-Files/PRJ-PJL-PRC-005_21
- QE-LNG PRJ-PJL-PRC-004 (rev 07) listing — https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-21699---Saipem-COMP2/RFQ-Files/PRJ-PJL-PRC-004_07
- QE-LNG PRJ-PJL-PRC-008 (rev 17) listing — https://justrite-elynox-bootcamp.pages.dev/Reference-Examples/Q-32705---Saipem-COMP3/RFQ-Files/PRJ-PJL-PRC-008_17
- Aggreko NFE cooling case study (48 °C DB / 34 °C WB) — https://bynder.aggreko.com/m/7da79919a63f8123/original/NFE-Case-Study-Cooling.pdf
- HBKU GHI variability study — https://elmi.hbku.edu.qa/en/publications/variability-of-measured-global-horizontal-irradiation-throughout-/
- QEERI Qatar Solar Atlas — https://hbku.edu.qa/sites/default/files/qeeri_solar_atlas.pdf
- QNA Qatar solar projects (RLIC / MIC locations) — https://qna.org.qa/en/News-Area/Special-News/2025-7/28/qatars-solar-energy-projects-green-energy-in-heart-of-desert
- KOC-I-026 — https://2.zoppoz.workers.dev:443/https/www.scribd.com/document/702513746/KOC-I-026-R0-19-12-2019
- KOC-Q-014 — https://www.studylib.net/doc/28042388/koc-q-014-r2-08-03-2017
- KOC-P-004 — https://www.scribd.com/document/648054358/Koc-p-004-Part-10-Rev-2
- KOC-S-005 blog (unverified) — https://instrumentengineer3.blogspot.com/2025/10/introduction-in-oil-gas-petrochemical.html
- PDO SP-1099 — https://www.scribd.com/document/429431786/Electrical-Installation-Requirements
- PDO SP-1171 — https://www.scribd.com/document/699597904/SP-1171
- PDO SP-1177 — https://www.scribd.com/document/411570128/SP-1177-V3-0
- PDO SP-1211 — https://www.scribd.com/document/637278036/SP-1211
- PDO SP-1236 — https://www.scribd.com/document/563109110/SP-1236
- PDO SP-2154 — https://www.scribd.com/document/637278030/SP-2154
- PDO PR-1172 — https://www.scribd.com/document/295105710/PR-1172-Permit-to-Work-Procedure

**Other**
- IOGP S-718Q Addendum 1 — https://www.iogp.org/bookstore/wp-content/uploads/sites/2/2023/12/Quality-Reqs-for-Basic-Process-Measurement-Instruments-Addendum-1-S-718Qv2023-12.pdf
