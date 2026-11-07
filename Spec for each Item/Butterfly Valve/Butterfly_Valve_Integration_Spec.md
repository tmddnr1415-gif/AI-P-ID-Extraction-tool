# Butterfly Valve (Control / On-off) – Integration Specification

## 1. 개요 (Scope)
- 대구경·저압손 유체(Cooling water, Air, Flue gas, Utility, 저압 Hydrocarbon)의 **Control 및 On-off** 용 Butterfly Valve (Concentric/Resilient-seated, Double offset/High-performance, **Triple offset (TOV)**) 와 Actuator/Accessory 일체.

### 1.1 포함 Valve 유형별 요구사항
| 구분 | 용도 | Control System | 주요 요구사항 |
|---|---|---|---|
| **Control Valve** (Butterfly) | 대구경·저 ΔP 유량/압력 조절 (CW, Air, Flue gas, Compressor suction throttling) | **DCS** (CCS) | 유효 개도 20~70°, Dynamic torque 검토, Smart positioner (HART/FF), Noise IEC 60534-8, Fail action, Leakage Class IV~VI |
| **MOV** (Motor Operated Butterfly) | 대구경 원격 Isolation/On-off (CW, Fire water, Utility) | **DCS** (Hardwired / Modbus / Profibus) | Intelligent electric actuator + Gear box, Torque/Limit switch, Open/Close/Stop cmd, Status/Fault/Remote-Local, Operating time, Ex d·IP68, MCC Power 경계 |

## 2. 적용 Code & Standard
| 구분 | Standard |
|---|---|
| Valve | **API 609** (Category A/B), ISO 10631, MSS SP-67/68, AWWA C504 (Water) |
| Pressure/Temp | ASME B16.34 |
| Face-to-face | API 609, ISO 5752, ASME B16.10 |
| Body type | Wafer, Lug, Double flanged |
| Flange | ASME B16.5 / B16.47 Series A/B |
| 누설 | API 598, ISO 5208, FCI 70-2 (Control) |
| Fire safe | API 607 / ISO 10497 |
| Fugitive emission | ISO 15848-1 |
| Control sizing | IEC 60534-2-1, Noise IEC 60534-8 |
| Actuator | ISO 5211, EN 15714 |
| 위험지역 | IEC 60079 |

## 3. 기술 요구사항
- Type selection
  - Concentric (Rubber lined): Water/Utility, 저온·저압.
  - **Double offset (HPBV)**: Class 150~300, Soft/Metal seat.
  - **Triple offset (TOV)**: 고온·고압, Zero leakage, Fire-safe, Metal seat.
- Control 용도: 유효 개도 **20~70°** 범위 (Characteristic ≈ Equal % 근사), Torque/Dynamic torque 검토.
- Disc–Piping 간섭 확인 (Disc clearance with pipe ID / Lining).
- Shaft: Blow-out proof, Anti-static.
- Shut-off: TOV – ISO 5208 Rate A/API 598 Zero leakage, Control – Class IV~VI.

## 4. Actuator & Accessory
- Pneumatic Rack & Pinion / **Scotch-yoke** (대구경), Spring-return (Fail action) 또는 Double acting.
- Electric actuator (MOV) – Utility 대구경 On-off 시 (Intelligent type, Modbus/Profibus/Hardwired).
- Sizing: Seating/Unseating torque + Dynamic torque, Safety factor 1.25~1.5.
- Smart positioner (HART/FF), SOV, Limit switch, Hand-wheel (Gear operator).

## 5. Integration Interface
| 대상 | 신호 | 비고 |
|---|---|---|
| DCS | AO (HART/FF) – Control, DO/DI – On-off | MOV: Open/Close/Stop cmd, Status, Fault |
| IPS/SIS | DO → SOV, DI ← LS | ESD 용도 시 SIL 검증 |
| Electrical (MOV) | 380/440 VAC Power, MCC 연계 | Motor control 회로 경계 정의 |
| Instrument Air | Supply pressure | |
| Piping | Wafer/Lug bolt length, Disc clearance, Line flange | |

## 6. Test & Inspection
- Shell / Seat test (API 598), Fire test certificate.
- Functional test (Stroke time, Fail action, Positioner calibration).
- Torque test 결과 제출, PMI/NDE (Class 별).

## 7. Vendor Document Requirement
- Data sheet, Sizing (Cv/Noise), Torque calculation, GA, Material cert, Test report, Wiring/Pneumatic diagram, Ex cert, IOM.

## 8. Integration Checklist
- [ ] Type (Concentric/HPBV/TOV) 및 Body type 선정
- [ ] Control 시 개도 범위 & Characteristic 확인
- [ ] Disc clearance vs Pipe ID (Schedule/Lining)
- [ ] Actuator type (Pneumatic/Electric) & Power 경계
- [ ] Shut-off/Fire safe 요구

> 참고 Vendor: Emerson (Vanessa, Keystone), Bray, Adams, Zwick, Flowserve (Durco), Samson, Metso (Neles), 국내 – 삼진정밀, 신영밸브 등.
