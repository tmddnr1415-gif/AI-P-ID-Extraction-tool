# DCS (Distributed Control System) – Integration Specification

## 1. 개요 (Scope)
- 플랜트 공정의 연속 제어(Regulating Control), 시퀀스 제어, 운전 감시, 알람 관리, 히스토리안 기능을 수행하는 **Main Control System**.
- 모든 Package/Subsystem(IPS/SIS, FGS, CCS, MMS, Vendor PLC 등)의 **통합 HMI 및 Data Hub** 역할.
- 적용 범위: Controller, I/O, Marshalling/System Cabinet, Operator/Engineering Workstation, Historian, Network, 3rd-party Interface, Software 일체.

## 2. 적용 Code & Standard
| 구분 | Standard |
|---|---|
| 기능안전/구분 | IEC 61508 (참고), IEC 61511 (SIS 분리 원칙) |
| 제어 시스템 | IEC 61131-3 (Programming), IEC 61131-2 (I/O) |
| 사이버보안 | **IEC 62443** (3-2 Zone/Conduit, 3-3 SL-2 이상) |
| 알람 관리 | **ISA-18.2 / IEC 62682**, EEMUA 191 |
| HMI | **ISA-101**, EEMUA 201 |
| 통신 | IEC 61158 (Fieldbus), IEC 61784, HART 7, Modbus TCP/RTU, OPC UA (IEC 62541) |
| EMC/환경 | IEC 61000-6-2/-4, IEC 60068, ISA-71.04 (G3 Corrosion) |
| 배치제어 | ISA-88 (해당 시) / ISA-95 (MES 연계) |
| 위험지역 | IEC 60079 시리즈 |

## 3. System Architecture 요구사항
- **Redundancy**: Controller (1:1 Hot standby), Power Supply (N+1 / Dual feed), Control Network (Dual ring/star), I/O Communication module, Server (Redundant).
- **Bumpless switchover**: Controller 절체 시 출력 변동 없음, 절체 시간 < 1 scan.
- **Spare capacity** (일반 EPC 기준)
  - Installed spare I/O: **10~20%** (각 type 별)
  - Space spare (Cabinet/Slot): **20~25%**
  - Controller CPU load ≤ **50~60%**, Memory ≤ 60%, Network load ≤ 40~50%
- Scan time: Fast loop 100~250 ms, 일반 Loop 500 ms~1 s.
- Network 계층 (Purdue Model): L0/L1 Field & Control – L2 Supervisory (HMI) – L3 Operations (Historian, APC) – **L3.5 DMZ** – L4 Business.

## 4. Integration Interface (타 시스템 연계)
| 상대 시스템 | Interface 방식 | 주요 Data | 비고 |
|---|---|---|---|
| IPS/SIS | Redundant Modbus TCP / Vendor native (Integrated) / OPC UA | Trip status, Bypass, First-out, Diagnostic | **Trip 신호는 Hardwired**, Read-only 원칙, SIS write 금지(Bypass 등 특별 승인 제외) |
| FGS | Serial/TCP Modbus, Hardwired (Common alarm) | Detector status, Alarm, Fault | Fire 알람은 Hardwired 백업 |
| CCS (Compressor) | Redundant Modbus TCP / Hardwired | Speed, Surge margin, Load sharing | Setpoint write는 승인된 Tag만 |
| MMS (Machine Monitoring) | Modbus TCP / OPC | Vibration, Axial displacement, Bearing Temp | Trip은 IPS로 Hardwired |
| Package PLC (Vendor) | Modbus TCP/RTU, Profibus, Hardwired | Status, Alarm, Start/Stop | Interface list(Tag/Register map) 필수 |
| MCC / Electrical (ECMS/PMS) | Hardwired (Start/Stop/Run/Trip), IEC 61850 / Modbus | Motor status, Current | |
| Fieldbus 기기 | FF H1, Profibus PA, HART-IP | PV, Diagnostic | AMS/IAMS 연계 |
| Historian / MES / ERP | OPC UA via DMZ | Process data | 단방향(Data diode) 고려 |
| Time Sync | NTP/PTP (GPS master) | SOE 정밀도 ±1 ms | |

### Interface 원칙
1. **Safety 관련 신호는 Hardwired**, 통신은 감시용.
2. Interface Data Map (Tag, Register, Data Type, Scaling, Unit, R/W) 을 Interface Control Document(ICD)로 관리.
3. 통신 장애 시 Fail-safe 동작 및 Comm. fault 알람 정의.
4. Watchdog / Heartbeat 신호 상호 교환.

## 5. Hardware 요구사항
- I/O Type: AI (4–20 mA HART), AO (4–20 mA HART), DI (24 VDC, Dry contact / NAMUR), DO (24 VDC / Relay), RTD/TC, Pulse.
- Intrinsic Safety: IS Barrier/Isolator 또는 IS I/O card (Ex ia / Ex ib), Entity / FISCO 계산서 제출.
- Universal / Configurable I/O (Electronic marshalling) 검토 – Late change 대응.
- Cabinet: IP42 (Indoor, 공조실), 하부 Cable entry, 내부 조명/콘센트, Temp 감시, 중량/발열량 데이터 제출.
- Power: Dual 230 VAC UPS feed, 24 VDC redundant PSU with diode/ORing module, Fuse/MCB 감시.
- Earthing: IS earth, Instrument clean earth, Protective earth 분리.

## 6. Software / HMI
- ISA-101 High-performance graphic (회색 배경, 알람만 색상), Level 1~4 Display hierarchy.
- Alarm philosophy 수립 → Alarm rationalization (Priority, Setpoint, Consequence, Response time).
- 10 alarms/10 min/operator 이하 목표 (EEMUA 191).
- Historian: 1 s 해상도, 최소 1~2년 온라인 보관.
- Function: Control narrative, Cause & Effect(비안전), Interlock, Sequence, APC 인터페이스.
- Engineering: Online change, Version control, Audit trail, User role(Operator/Engineer/Admin).

## 7. Cyber Security (IEC 62443)
- Zone & Conduit 설계, Firewall/DMZ, Antivirus/Whitelisting, Patch management, Backup & Recovery.
- USB/Port 통제, Account 관리, Centralized log(SIEM), Security Level 목표 SL-2(최소).

## 8. Test & Inspection
| 단계 | 내용 |
|---|---|
| **FAT** | HW 검사, I/O loop simulation 100%, Redundancy 절체, 통신 interface 시뮬레이션, Graphic/Alarm 검증, Load test |
| **IFAT/SIT** | DCS ↔ IPS/FGS/CCS/MMS/Package 통합 시험 (실제 HW 또는 Simulator) |
| **SAT** | 현장 설치 후 전원/네트워크/진단 확인 |
| Loop Check | 현장 계기 ~ HMI 전 구간 |
| Commissioning | Loop tuning, Sequence 동작 시험 |

## 9. Vendor Document Requirement (VDR)
- System Architecture, Network Diagram, Cabinet GA/Wiring, I/O List & Assignment, Power/Heat Calculation, Interface Data Map, Functional Design Spec (FDS), Graphic Spec, Alarm DB, FAT/SAT Procedure & Report, O&M Manual, Spare part list, Cyber Security Plan.

## 10. Integration Checklist
- [ ] Interface 대상 시스템/Protocol/Redundancy 확정
- [ ] ICD(Data Map) 상호 승인
- [ ] Hardwired vs Soft signal 구분 (Safety=Hardwired)
- [ ] Time sync / SOE 정책
- [ ] Spare 요건 (I/O, Space, Load) 충족 확인
- [ ] Cyber Security Zone/Conduit 승인
- [ ] FAT/SIT 범위에 3rd-party 시스템 포함
- [ ] IS 계산 및 Earthing 확인

> 참고: 주요 Vendor – Honeywell (Experion PKS), Emerson (DeltaV), Yokogawa (CENTUM VP), ABB (800xA), Schneider (Foxboro EcoStruxure), Siemens (PCS 7/PCS neo).
