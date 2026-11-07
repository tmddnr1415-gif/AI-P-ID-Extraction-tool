# CCS (Compressor Control System) – Integration Specification

## 1. 개요 (Scope)
- 원심/축류 Compressor 의 **Anti-surge control, Performance(Capacity) control, Load sharing, Speed control(Turbine governor), Sequence(Start/Stop)** 를 수행하는 전용 고속 제어 시스템.
- 범위: Controller(Redundant), I/O, Anti-surge Valve 제어 요구, Operator Interface, DCS/IPS/MMS Interface.

## 2. 적용 Code & Standard
| 구분 | Standard |
|---|---|
| Compressor | API 617 (Centrifugal), API 672, API 618(Recip.) |
| Turbine | API 612 (Steam turbine), API 616 (Gas turbine), API 611 |
| Governor | API 612 / NEMA SM 23 |
| Machinery protection | API 670 |
| 기능안전 | IEC 61511 (Overspeed/ESD 연계 시) |
| 통신 | Modbus TCP/RTU, OPC UA |

## 3. 기능 요구사항
- **Anti-surge control**: Surge line/Control line 설정, Surge margin 기반 PID + Recycle trip(Open loop) 기능, Surge counter.
- Scan time: **≤ 40 ms (Anti-surge loop)**, Valve full stroke ≤ 1~2 s (Opening).
- Performance control: Suction/Discharge pressure, Flow, Speed.
- Load sharing: 병렬 운전 Compressor 간 Equidistant from surge line 기반.
- Decoupling: Anti-surge ↔ Performance loop 간섭 보상.
- Speed control: Steam/Gas turbine Governor 또는 VSD 연계.
- Redundancy: Controller/Power/Network Hot-standby.

## 4. Integration Interface
| 상대 | 방식 | Data | 원칙 |
|---|---|---|---|
| DCS | **Redundant Modbus TCP** (또는 OPC UA) + 일부 Hardwired | PV, SP, Surge margin, Valve position, Alarm, Mode | DCS→CCS Write: Remote SP, Start/Stop request (승인 Tag만) |
| IPS/SIS | **Hardwired** | ESD Trip, Compressor trip, Permissive | Safety 신호 통신 금지 |
| MMS | Hardwired (Trip) + Modbus (Speed, Vibration) | Overspeed, Vibration | |
| Anti-surge Valve | 4–20 mA (HART), Position feedback, SOV(Trip open) | | **Fast-acting positioner/Booster** 필요 |
| Field TX | 4–20 mA, 고속 응답 (Flow DP, Pressure, Temp) | | TX 응답시간 ≤ 100 ms (Damping 최소) |
| Turbine Governor / VSD | 4–20 mA / Serial | Speed SP/feedback | |
| UCP/Package PLC | Hardwired / Modbus | Lube oil, Seal gas status | |

## 5. Hardware 요구사항
- 전용 Cabinet, Redundant Controller, Dual 24 VDC PSU, UPS dual feed.
- 고속 AI/AO, DI/DO, Speed pickup(Magnetic pickup) 입력.
- Spare I/O 10~20%.

## 6. Test & Inspection
- **FAT**: Dynamic simulation (Compressor model 기반) 으로 Surge/Trip/Load sharing 검증.
- **SIT**: DCS/IPS/MMS 연계.
- **Site**: Surge test(Map 검증), Loop tuning, Performance test.

## 7. Vendor Document Requirement
- Control narrative/FDS, Surge map(Compressor vendor 제공), Control configuration, I/O List, Modbus map, Cabinet drawing, Simulation FAT report, Tuning record.

## 8. Integration Checklist
- [ ] Compressor Performance curve / Surge map 입수
- [ ] Anti-surge valve 사이징 & Stroke time 요건 (Valve vendor 협의)
- [ ] 고속 TX 사양 (Damping, Response time)
- [ ] DCS ICD 및 Write 범위 확정
- [ ] Trip 신호 Hardwired 확인
- [ ] Load sharing 구성 (병렬 대수)
- [ ] Dynamic simulation 범위 확정

> 참고 Vendor: CCC (Compressor Controls Corp., Honeywell), Woodward, Emerson (DeltaV + Anti-surge), Siemens, Yokogawa, Triconex(TMR 기반).
