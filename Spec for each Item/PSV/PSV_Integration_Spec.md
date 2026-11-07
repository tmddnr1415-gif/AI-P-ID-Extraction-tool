# PSV (Pressure Safety / Relief Valve) – Integration Specification

## 1. 개요 (Scope)
- 설비 과압 보호용 **Spring-loaded (Conventional / Balanced bellows) 및 Pilot-operated PSV**, Thermal relief valve, Vacuum/Pressure relief(PVRV), Rupture disc 조합 포함.

## 2. 적용 Code & Standard
| 구분 | Standard |
|---|---|
| 설계/사이징 | **API 520 Part I (Sizing), Part II (Installation)** |
| 과압 시나리오 | **API 521 / ISO 23251** (Relief & Depressuring) |
| Orifice/치수 | **API 526** (Flanged steel PRV), API 527 (Seat tightness) |
| 시험/검사 | API 576 (Inspection), API 527 |
| 압력용기 | **ASME Section VIII Div.1 (UG-125~UG-140, UV Stamp)**, ASME Sec. I (Boiler – V stamp) |
| 국제 | ISO 4126 시리즈, PED 2014/68/EU (CE) |
| 저장탱크 | API 2000 / ISO 28300 (PVRV) |
| Sour | NACE MR0175 |
| 국내 | 고압가스안전관리법 (KGS), 산업안전보건법 – **안전밸브 성능검사(KCs)**, 에너지법 |

## 3. 기술 요구사항
- Set pressure ≤ MAWP, Accumulation: 10% (Single), 16% (Multiple), 21% (Fire case).
- Type selection
  - Conventional: Built-up back pressure ≤ 10% of set.
  - **Balanced bellows**: Variable back pressure ≤ 30~50%, Corrosive/Dirty.
  - **Pilot operated**: Set ≥ 90~95% operating, 대용량, 저압.
- Orifice designation: API 526 (D~T), Certified coefficient (ASME NB Red book).
- Inlet pressure loss **≤ 3% of set pressure**, Outlet back pressure 검토 (API 520 Part II).
- Two-phase / Choked flow 사이징 (API 520 Annex C/ HEM/ Omega method).
- Option: Lifting lever (Steam/Air), Cap, Test gag, Soft seat, Heating jacket.
- Material: Body/Bonnet/Spring/Nozzle/Disc – Service 별, Low temp impact test.

## 4. Integration Interface
| 대상 | 내용 | 비고 |
|---|---|---|
| Process | Relief load, Governing case, Fluid property | API 521 시나리오 |
| Piping | Inlet/Outlet line sizing, Reaction force, Flare header, Lock-open/Car-sealed isolation valve | Inlet ΔP 3% rule |
| Flare system | Back pressure (Superimposed/Built-up) | Flare network 해석과 Iteration |
| DCS (선택) | **Valve open/lift detection (Proximity switch/Acoustic monitor)**, Bellows leak detector (PT) | Fugitive/Release 감시 |
| Mechanical (Vessel) | Nozzle, MAWP, Fire area | |
| 인허가 | KGS/KOSHA 검사, ASME UV Stamp | |

## 5. Test & Inspection
- **Set pressure (Pop) test**, Blow-down 조정 (해당 시).
- **Seat tightness test (API 527)** – Air bubble count.
- Hydro test (Inlet body / Outlet body 분리 Pressure).
- Bellows leak test, Back pressure test.
- Material cert (3.1), PMI, NDE.
- 국내 설치 시 **안전밸브 성능검사(KCs)** 및 정기 검사(산안법/고압법 주기).

## 6. Vendor Document Requirement
- Data sheet (API 520 form), Sizing calculation, Certified capacity(NB), GA/Section drawing, Material cert, Test certificate, Nameplate drawing, IOM, 인증서(ASME UV, PED, KCs).

## 7. Integration Checklist
- [ ] Relief scenario & Governing case 확정 (Process)
- [ ] Back pressure 확인 → Type 결정
- [ ] Inlet loss 3% / Outlet sizing 검토 (Piping)
- [ ] Isolation valve (CSO/LO) 및 Spare PSV 구성
- [ ] 인증 요구 (ASME/PED/KGS/KCs) 확정
- [ ] Lift detection 등 DCS 연계 필요 여부

> 참고 Vendor: Emerson (Anderson Greenwood Crosby), Baker Hughes (Consolidated), LESER, Curtiss-Wright (Farris), Spirax Sarco (Steam), 국내 – 조양, 한국안전밸브 등.
