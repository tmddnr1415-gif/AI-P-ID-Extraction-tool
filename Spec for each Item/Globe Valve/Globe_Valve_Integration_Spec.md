# Globe Valve (Control Valve) – Integration Specification

## 1. 개요 (Scope)
- Globe type 의 **Control Valve, PRV, MOV** 와 Actuator, Positioner, Accessory 일체.

### 1.1 포함 Valve 유형별 요구사항
| 구분 | 용도 | Control System | 주요 요구사항 |
|---|---|---|---|
| **Control Valve** (FV/PV/LV/TV) | 유량/압력/액위/온도 조절 | **DCS** (CCS – Anti-surge) | IEC 60534 Sizing, Noise ≤ 85 dBA, Smart positioner (HART/FF), Fail action, Leakage Class IV~VI (아래 §3~4 상세) |
| **PRV** (Self-actuated Pressure Regulating Valve) | Utility(N₂, Fuel gas, IA, Steam), Blanketing 감압/배압 조절 | **없음 (Self-contained)** – DCS 는 상·하류 PT 로 감시 | 외부 동력 불필요, Pilot-operated/Direct-acting, Set range & Droop/Offset, Sensing line(Impulse) 위치, Upstream 고장 시 하류 과압 보호(PSV 별도), IEC 60534/EN 334(Gas) 적용, Rangeability·Lock-up 성능 |
| **MOV** (Motor Operated Globe Valve) | 원격 On-off/Throttling (Steam, Water, 대구경 Isolation) | **DCS** (Hardwired 또는 Fieldbus) | Electric actuator (Intelligent, IP68, Ex d), Torque/Limit switch, Modulating 시 S4/S9 Duty·4–20 mA, Interface: Open/Close/Stop cmd, Open/Closed/Fault/Remote-Local status, Modbus/Profibus/HART 옵션, MCC/Power 경계 (380~440 VAC) |

- PRV 는 계기 신호가 없으므로 **Instrument Index/Datasheet** 로만 관리하되, Process(Set point), Piping(Sensing line) 과 협의 필수.
- MOV 는 Electrical(Power feeder, Cable) 과 Instrument(Control signal) 의 **Battery limit** 을 Interface matrix 로 명확히 정의.

## 2. 적용 Code & Standard
| 구분 | Standard |
|---|---|
| Sizing | **IEC 60534-2-1 / ISA-75.01.01** (Cv/Kv 계산) |
| 소음 | **IEC 60534-8-3 (Gas), 8-4 (Liquid)** – 일반 85 dBA @1 m 이하 |
| Body/Pressure | ASME B16.34, IEC 60534-3 |
| Face-to-face | **ISA-75.08 / IEC 60534-3-1** |
| 누설 | **ANSI/FCI 70-2 / IEC 60534-4** (Class IV, V, VI) |
| Fugitive emission | ISO 15848-1, API 624 (참고) |
| Positioner | HART 7 / FOUNDATION Fieldbus / Profibus PA, NAMUR NE107 |
| Sour | NACE MR0175/ISO 15156 |
| 위험지역 | IEC 60079 |
| Data sheet | IEC 60534-7, ISA-20 Form |

## 3. 기술 요구사항
- **Sizing**: Min/Normal/Max 조건에서 Travel 10~80% (Max ≤ 80~90%, Min ≥ 10%), Rangeability 확보.
- Characteristic: Equal % (일반), Linear (Level/Constant ΔP), Quick opening (On-off).
- **Cavitation/Flashing** 검토 → Anti-cavitation trim (Multi-stage), Hardened trim (Stellite).
- **Noise/Velocity**: Outlet velocity 제한 (Gas Mach < 0.3~0.5), Low-noise trim (Multi-hole cage).
- Leakage Class: 일반 IV, Tight shut-off V/VI.
- Bonnet: Standard / Extension (고온·저온) / Bellows seal (독성·Lethal).
- Packing: PTFE V-ring / Graphite, Low-E (ISO 15848 Class B/C).
- Body material/Trim material: Project Piping class 준용.

## 4. Actuator & Positioner
- Actuator: Pneumatic Spring-diaphragm (일반) / Piston (고추력), Fail action (FC/FO/FL) 명시.
- Thrust sizing: Shut-off ΔP 기준, Safety factor 1.25 이상.
- **Smart Positioner** (HART 4–20 mA / FF): Valve diagnostic, Travel feedback, NE107 status.
- Accessory: AFR, Volume booster, QEV, SOV (Trip 시), Limit switch, Lock-up valve (Fail-lock).
- Stroke time (Anti-surge 등 특수용도): 별도 지정 (예: Open ≤ 2 s).

## 5. Integration Interface
| 대상 | 신호 | 비고 |
|---|---|---|
| DCS | AO 4–20 mA (HART) / FF, AI(Position TX 옵션) | Fail-safe at signal loss |
| IPS/SIS | DO → SOV (Trip to fail position), DI ← Limit switch | Control valve 를 SIF final element 로 쓸 경우 별도 검증 |
| CCS | 고속 AO, Booster | Anti-surge 용 |
| AMS/IAMS | HART/FF diagnostic | Valve signature, Step response |
| Instrument Air | Supply pressure 명시 | |
| Piping | Face-to-face, Reducer, Line size, Insulation, Access | |

## 6. Test & Inspection
- Hydrostatic shell test, Seat leakage test (FCI 70-2 Class), Packing leak test.
- **Functional test**: Stroke, Dead band, Hysteresis, Linearity (≤ 1%), Step response, Fail action.
- Positioner calibration & HART communication.
- PMI, NDE, Material cert (EN 10204 3.1).
- Noise/Cv type test data 제출.

## 7. Vendor Document Requirement
- Sizing calculation (Cv, Noise, Velocity, Cavitation index), Data sheet, GA, Actuator sizing, Material cert, Test report, Wiring diagram, Ex cert, IOM manual, Spare list.

## 8. Integration Checklist
- [ ] Process data (Min/Nor/Max, ΔP, Fluid property) 확정
- [ ] Noise 85 dBA 및 Velocity 제한 확인
- [ ] Fail action / Leakage class
- [ ] Positioner protocol (HART/FF) DCS 와 일치
- [ ] SOV/Limit switch 필요 여부 (C&E 기준)
- [ ] Piping layout (Bypass, Block valve, Access) 협의

> 참고 Vendor: Emerson Fisher, Flowserve (Valtek), Samson, Metso/Valmet (Neles), Baker Hughes Masoneilan, IMI CCI, Koso, 국내 – 한국에머슨, PK Valve 등.
