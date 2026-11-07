# Ball Valve (On-off / ESD / Control Ball Valve) – Integration Specification

## 1. 개요 (Scope)
- 계장 범위 Ball Valve: **ESDV, SDV, BDV, XV** 와 Actuator, Accessory(SOV, Limit switch, Positioner/PST, Booster, QEV, Air filter regulator) 일체.

### 1.1 포함 Valve 유형별 요구사항
| 구분 | 용도 | Control System | Fail Action | 주요 요구사항 |
|---|---|---|---|---|
| **ESDV** (Emergency Shutdown Valve) | Unit/Plant 경계, 재고(Inventory) 격리 | **IPS/SIS** | Fail-Close (Spring return) | SIL 2~3, Fire-safe(API 607) + **Fire-proof actuator/Cable** (UL 1709/Jet fire 기준, 15~30 min), Full bore, Tight shut-off (ISO 5208 Rate A), **PST 필수**, Stroke time ≤ 1 s/inch 또는 PST 기준 |
| **SDV** (Shutdown Valve) | 설비/Equipment 단위 Process shutdown | **IPS/SIS** (PSD) | Fail-Close (일반) | SIL 1~2, Line monitored SOV/LS, Manual reset, PST 권장 |
| **BDV** (Blowdown Valve) | 비상 감압(Depressuring) → Flare | **IPS/SIS** | **Fail-Open** | API 521 감압(15 min 내 50% 또는 6.9 barg), Fire-proofing, Low temp(J-T 냉각) 재질 검토, 개방 시간 명시, 소음/진동(AIV) 검토 |
| **XV** (On-off Valve) | 공정 Sequence/절환, Batch, 비안전 격리 | **DCS** (또는 Package PLC) | Process 요건 (FC/FO/FL) | Open/Close LS, SOV (Non-SIL 가능), Stroke time 요건, Double-acting 허용 |

- 공통: ESDV/SDV/BDV 는 **SIF Final element** → Valve+Actuator+SOV 전체 FMEDA/SIL 인증 데이터, Proof test 절차 제출.
- XV 와 SDV 의 SOV/LS 사양은 Project Standard 로 통일하되, SIS 계열은 SIL 인증품 적용.

## 2. 적용 Code & Standard
| 구분 | Standard |
|---|---|
| Valve 설계 | **API 6D** (Pipeline), **API 608** (Metal ball), ISO 17292, ASME B16.34 |
| Face-to-face | ASME B16.10 |
| Flange | ASME B16.5 / B16.47 |
| Fire safe | **API 607 / ISO 10497 / API 6FA** |
| 누설시험 | **API 598**, ISO 5208 (Rate A for soft seat), API 6D, FCI 70-2 (Control) |
| Fugitive emission | **ISO 15848-1/-2**, API 641 |
| Sour service | NACE MR0175/ISO 15156, MR0103 |
| Actuator | ISO 5211 (Mounting), EN 15714, API 6DX |
| 기능안전 | IEC 61508 (SIL capable – Valve+Actuator+SOV) |
| 위험지역 | IEC 60079 / ATEX / IECEx |

## 3. Valve 기술 요구사항
- Type: Floating(소구경) / **Trunnion mounted** (일반 ≥ 4" Class 300 이상 또는 Project 기준).
- Bore: Full bore (Pigging, ESD 고속 차단), Reduced bore 허용 시 명시.
- Seat: Soft (PTFE, PEEK, Devlon) / Metal seated (고온, Erosive, Tight shut-off 시 Hard coating – Tungsten carbide/Chrome carbide).
- Shut-off: ESD 계열 **ISO 5208 Rate A** 또는 Project 요구 (Class V/VI for control).
- Features: Anti-static device, Blow-out proof stem, DBB/DIB (Double block & bleed) 필요 여부, Cavity relief.
- Material: Body (A105, LF2, F316, Duplex), Trim (Project material table).

## 4. Actuator & Accessory
- Actuator: Pneumatic **Spring-return (Fail-Close/Fail-Open)** – ESD 용 필수, Double acting 은 Volume tank 포함.
- Sizing: 최대 Breakaway torque × **Safety factor 1.25~1.5** (Min. supply pressure 기준).
- **Stroke time**: ESD Close ≤ 1 s/inch (일반 기준) 또는 Process safety time 기준; BDV Open 시간 명시.
- SOV: SIL 인증, Ex d/Ex ia, 24 VDC, Low power, **De-energize to trip**, 2oo2/1oo2 구성 검토.
- Limit switch: Proximity (NAMUR) or Mechanical, Open/Close 2점, Ex 인증.
- **PST(Partial Stroke Test)** : Smart positioner/PST device (ESD valve).
- Manual override: Hand-wheel/Hydraulic hand pump (필요 시).

## 5. Integration Interface
| 대상 | 신호 | 비고 |
|---|---|---|
| IPS/SIS | DO → SOV (Trip), DI ← Limit switch | Line monitoring, SIL loop 계산 |
| DCS | DO/DI (On-off XV), HART (Positioner/PST diagnostic) | |
| AMS/IAMS | HART / FF 진단 | Valve signature |
| Instrument Air | 5.5~7 barg (Min/Normal/Max 명시) | Filter regulator 포함 |
| Piping | Face-to-face, Weight, Support, Flange rating | 중량물(Actuator) 지지 |

## 6. Test & Inspection
- Shell / Seat hydro test, Low pressure gas seat test (API 6D/598).
- Fire test 인증서 (Type test).
- Fugitive emission type test (ISO 15848).
- **Functional test with actuator**: Stroke time, SOV/Limit switch 동작, PST.
- PMI, NDE (RT/UT/MT/PT) per Class/Material, Hardness (Sour).
- SIL certificate / FMEDA data.

## 7. Vendor Document Requirement
- Data sheet, GA drawing (Valve+Actuator), Torque & Actuator sizing calculation, Material certificate (EN 10204 3.1/3.2), Test report, Wiring/Pneumatic diagram, SIL certificate, Ex certificate, IOM manual.

## 8. Integration Checklist
- [ ] Fail action & Stroke time 확정 (Process/Safety)
- [ ] Shut-off class & Fire safe 요구 확인
- [ ] Actuator sizing (Min air pressure)
- [ ] SOV / Limit switch / PST 사양 통일 (Project standard)
- [ ] SIL 검증용 신뢰도 데이터 입수
- [ ] Piping 과 Face-to-face/Weight/Orientation 협의

> 참고 Vendor: Cameron (SLB), Baker Hughes, PetrolValves, Perar, Valvitalia, KTM (Emerson), Kitz, 국내 – 삼신밸브, 한국밸브 등.
