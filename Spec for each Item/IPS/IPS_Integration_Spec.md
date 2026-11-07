# IPS (Instrumented Protection System / SIS / ESD) – Integration Specification

## 1. 개요 (Scope)
- 공정 위험을 안전 상태로 이행시키는 **Safety Instrumented System (SIS)**. ESD(Emergency Shutdown), PSD(Process Shutdown), BMS(Burner Management) 등을 포함.
- 범위: Safety Logic Solver, Safety I/O, Cabinet, ESD Hardwired Console/Matrix Panel, SOE, Engineering Station, DCS Interface, Field Sensor/Final Element 의 SIF 관점 요구사항.

## 2. 적용 Code & Standard
| 구분 | Standard |
|---|---|
| 기능안전 | **IEC 61511-1/2/3 (ISA 84.00.01)**, IEC 61508 (SIL Certified HW/SW) |
| 위험성 평가 | HAZOP, **LOPA**, SIL Assessment / Verification (PFDavg 계산) |
| Burner | NFPA 85/86, EN 746-2 (해당 시) |
| Offshore | API RP 14C, ISO 10418 |
| 사이버보안 | IEC 62443 |
| 통신 | Modbus TCP, OPC UA, Safe-Ethernet(내부) |

## 3. 기능안전 요구사항
- Logic Solver: **TÜV SIL 3 인증** (IEC 61508), 최소 SIL 요구 만족.
- Architecture: 1oo2D / 2oo3 (TMR) / QMR, Redundant CPU·I/O·Power.
- SIF별 **SRS (Safety Requirement Specification)** 작성: Trip setpoint, Response time, Safe state, Bypass, Reset, Proof test interval.
- Sensor/Final Element Voting: 1oo1, 1oo2, 2oo3 (SIL 및 Spurious trip 고려).
- **De-energize to Trip** 원칙 (예외: Fire 관련 Energize-to-trip 은 Line monitoring 필수).
- PFDavg, HFT(Hardware Fault Tolerance), SFF, Systematic Capability 검증.
- 응답시간: Logic solver ≤ 100 ms (전체 SIF는 Process Safety Time의 1/2 이하).

## 4. Independence & Separation
- **DCS와 물리적/기능적 분리** (Controller, I/O, Sensor, Final element – BPCS와 공용 금지 원칙).
- 동일 Vendor 통합(Integrated) 시에도 Independent hardware & network, 공통원인고장(CCF) 분석.
- Cabinet 분리 또는 명확한 구획, 별도 UPS feed 권장.

## 5. Integration Interface
| 상대 | 방식 | Data | 원칙 |
|---|---|---|---|
| DCS | Redundant Modbus TCP / Vendor native / OPC UA | Trip status, First-out, Bypass status, Diagnostic, Pre-alarm | **SIS→DCS Read only**. DCS→SIS Write는 Reset/Bypass request 등 승인 항목만, Safety layer 검증 |
| ESD Console (Matrix panel) | **Hardwired** | ESD push button, Lamp, Override key switch | Hardwired 필수 |
| FGS | Hardwired (Confirmed fire/gas → ESD) | ESD initiation | Safety 신호는 통신 금지 |
| CCS / MMS | Hardwired | Compressor trip, Vibration HH trip | |
| MCC | Hardwired (Trip relay, Interposing) | Motor trip, Run status | |
| Package Vendor SIS | Hardwired (Trip/Permissive), Serial (Status) | | |
| SOE | 내부 1 ms 해상도, GPS Time sync | | |
| Field | Smart TX (HART, SIL2 cert.), SOV, ESD Valve, PST(Partial Stroke Test) | | |

## 6. Hardware 요구사항
- I/O: AI(4–20 mA HART with NAMUR NE43), DI(Line monitored, EOL resistor), DO(SIL rated, Line monitored), Relay.
- Spare: Installed 10~20%, Space 20%.
- IS 회로: SIL 인증 Barrier/Isolator.
- Power: Dual UPS feed, Redundant 24 VDC.
- Interposing Relay: SIL 인증 Safety relay.

## 7. Software / Configuration
- **Cause & Effect Matrix** 기반 Logic, IEC 61131-3 Limited Variability Language (FBD) 사용.
- Bypass/Override: Key switch 또는 Password, 시간 제한, 알람·로그 기록, 동시 Bypass 수 제한.
- Reset: Manual reset 원칙 (Auto restart 금지).
- MOC(Management of Change), Version control, Program change audit trail, Write protection.

## 8. Test & Inspection
- **FAT**: 100% C&E Logic test, I/O, Redundancy fault injection, Response time 측정, DCS interface.
- **SIT**: DCS/FGS/CCS 통합 시험.
- **SAT / Loop Check / Validation (IEC 61511 §15)**: SIF 기능 검증, Final element stroke time.
- **Proof Test**: 주기 및 절차서 제공 (PST 포함).
- **FSA (Functional Safety Assessment)** Stage 1~5.

## 9. Vendor Document Requirement
- Safety Manual, SIL Certificate, SRS, C&E, FDS, Architecture, I/O List, PFD Calculation, Reliability data (λDU, λSD 등), FAT/SAT Procedure/Report, Bypass philosophy, Proof test procedure.

## 10. Integration Checklist
- [ ] SIL Assessment(LOPA) 완료 및 SRS 승인
- [ ] BPCS-SIS 독립성/CCF 검토
- [ ] Safety 신호 Hardwired 확인
- [ ] DCS 통신 Write 범위 제한
- [ ] Bypass/Reset 철학 확정
- [ ] PFDavg 계산 (Sensor+Logic+Final element)
- [ ] Proof test interval 및 PST 정의
- [ ] FSA 일정

> 참고 Vendor: Triconex (Schneider), Honeywell Safety Manager, Yokogawa ProSafe-RS, HIMA HIMax/HIQuad, Emerson DeltaV SIS, ABB 800xA HI.
