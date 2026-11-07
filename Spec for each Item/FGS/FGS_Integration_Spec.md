# FGS (Fire & Gas System) – Integration Specification

## 1. 개요 (Scope)
- 화재·가연성가스·독성가스 누출을 감지하여 **경보, 소화설비 작동, ESD 개시, HVAC 차단** 등을 수행하는 Safety system.
- 범위: F&G Logic Solver, I/O, Detector(Flame, Heat, Smoke, Flammable Gas, Toxic Gas H₂S/CO, Open-path), MAC(Manual Alarm Call point), Beacon/Sounder, Mimic/Matrix panel, Fire suppression 연계.

## 2. 적용 Code & Standard
| 구분 | Standard |
|---|---|
| 기능안전 | **IEC 61511**, IEC 61508 (SIL 2 이상 일반) |
| F&G 설계 | **ISA-TR84.00.07** (F&G mapping/Coverage), NFPA 72 (Fire alarm), EN 54 |
| Gas detector | IEC 60079-29-1/-2/-4, EN 50402 (SIL) |
| Flame detector | FM 3260, EN 54-10 |
| 소화설비 | NFPA 15/16/2001, NFPA 12 |
| Offshore | ISO 13702, API RP 14C/14G |
| 국내 | 산업안전보건법, 화재예방법, KGS Code (해당 시) |

## 3. 기능 요구사항
- Logic Solver: SIL 2 이상 인증 (일반 SIL 3 capable), Redundant.
- **Fire & Gas Mapping** (Geographic/Scenario coverage) 기반 Detector 수량/배치, Coverage 목표 (예: 90%/85%).
- Voting: Confirmed fire/gas = **2ooN** (예: 2oo3) → Executive action, 1ooN → Alarm.
- Gas setpoint 예: LEL 20% (Low) / 40~50% (High), H₂S 10/20 ppm 등 (Project philosophy).
- Energize-to-Act 회로는 **Line monitoring (Open/Short)** 필수.
- Inhibit/Override: 알람/로그, 시간 제한.
- Fire alarm panel(Building) 은 NFPA 72/EN 54 인증 FACP로 별도 구성 후 FGS 연계 가능.

## 4. Integration Interface
| 상대 | 방식 | Data | 원칙 |
|---|---|---|---|
| IPS/ESD | **Hardwired** | Confirmed F&G → ESD/Blowdown initiate | Safety=Hardwired |
| DCS | Redundant Modbus TCP / OPC UA | Detector value, Alarm, Fault, Inhibit status | Read-only, 감시용 |
| Fire Alarm Panel (Building FACP) | Hardwired + Serial (Modbus) | Zone alarm/fault | |
| Fire Water / Deluge / Clean agent | Hardwired (Release, Status) | Deluge valve, Pump start | Line monitored |
| HVAC | Hardwired | Damper close, Fan stop (Gas at intake) | |
| PAGA / CCTV / Beacon | Hardwired / Serial | Alarm tone, Zone | |
| Electrical (ECMS) | Hardwired | Ex 아닌 설비 전원 차단 | |
| Field detector | 4–20 mA HART, Addressable loop, Relay | | Fault level <3.6 mA (NAMUR NE43) |

## 5. Hardware 요구사항
- I/O: AI(4–20 mA, HART), DI(Line monitored), DO(Line monitored, SIL), Addressable loop module.
- Field: Ex d / Ex ia 인증, IP66/67, Sunshade/Weather protection, Calibration gas port.
- Spare: Installed 10~20%, Space 20%.
- Power: Dual UPS + Battery (최소 30분~수 시간, Project 요건).

## 6. Test & Inspection
- **FAT**: C&E 100%, Voting, Line monitoring fault injection, DCS interface.
- **SIT**: IPS/DCS/HVAC/Fire water 통합.
- **Site**: Detector bump test/Calibration (Gas), Flame simulator test, Deluge 연동 시험.

## 7. Vendor Document Requirement
- F&G Philosophy, F&G Mapping report, C&E, Detector layout, SIL certificate, Safety manual, I/O List, FAT/SAT report, Calibration certificate.

## 8. Integration Checklist
- [ ] F&G Mapping 및 Coverage 목표 승인
- [ ] Voting/Setpoint 철학 확정
- [ ] ESD/HVAC/Fire water 연동 Hardwired
- [ ] Line monitoring 적용 확인
- [ ] Building FACP 와의 경계(Battery limit) 정의
- [ ] DCS ICD 승인

> 참고 Vendor: Honeywell, Det-Tronics (Eagle Quantum), Drager, MSA, Emerson, HIMA, Yokogawa ProSafe, Triconex.
