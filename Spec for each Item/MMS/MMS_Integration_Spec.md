# MMS (Machine Monitoring System / Vibration Monitoring) – Integration Specification

## 1. 개요 (Scope)
- 회전기계(Compressor, Turbine, Pump, Fan, Gearbox, Motor)의 **진동(Radial vibration), 축변위(Axial position), Keyphasor, 베어링 온도, 속도(Overspeed), Rod drop** 등을 감시·보호.
- 구성: Proximity probe/Extension cable/Driver, Accelerometer/Velocity sensor, RTD/TC, Monitoring Rack, Condition Monitoring S/W(Diagnostic server).

## 2. 적용 Code & Standard
| 구분 | Standard |
|---|---|
| Machinery Protection | **API 670 (5th Ed.)** – Machinery Protection Systems |
| 진동 평가 | ISO 20816 (舊 ISO 10816/7919), API 617/610/612/618 |
| Overspeed | API 670, API 612, IEC 61508 (SIL 인증 Overspeed 시) |
| 위험지역 | IEC 60079 |
| 통신 | Modbus TCP/RTU, OPC UA |

## 3. 기능 요구사항
- Proximity probe: 8 mm, 200 mV/mil (7.87 V/mm), 5 m 또는 9 m system length (API 670).
- Radial vibration: 축당 X-Y 2개 (90° 배치), Axial: Dual voting (2oo2/2oo3).
- Keyphasor 1개/shaft, Bearing temp: Dual element RTD.
- Alarm: Alert(A) / Danger(D) 2단계, Danger → Trip (Voting 및 Time delay 1~3 s).
- Trip multiply, Trip bypass 기능, OK status(Channel fault) 감시.
- Overspeed: 독립 3채널 (2oo3), 응답 ≤ 40 ms, SIL 2/3 인증 권장.
- Buffered output (BNC) – Portable analyzer 연결.

## 4. Integration Interface
| 상대 | 방식 | Data | 원칙 |
|---|---|---|---|
| IPS/SIS | **Hardwired relay (Danger, NC/De-energize to trip)** | Machine trip | Safety 신호는 Hardwired |
| CCS / UCP(Unit Control Panel) | Hardwired relay + 4–20 mA | Trip, Alarm, Speed | |
| DCS | **Redundant Modbus TCP/RTU** (+ 4–20 mA 주요 값) | Direct value, Alarm status, Channel OK | 감시용, Read-only |
| Condition Monitoring S/W | Ethernet (Vendor protocol) | Waveform, Orbit, Spectrum | DMZ 경유 원격 진단 |
| Time sync | NTP | Event 기록 | |

- Modbus Register map (Tag, Address, Scaling, Unit) 은 ICD 로 DCS Vendor 와 상호 승인.

## 5. Hardware 요구사항
- Rack: Redundant Power supply, Hot-swappable module, Cabinet 설치 (Control room / LER).
- Field: Junction box (Proximitor housing) – IP65 이상, 위험지역 Ex 인증.
- Cable: Triaxial extension cable(Probe), Shielded twisted pair, Probe-driver system calibrated 세트 공급.
- Spare channel ≥ 10%.

## 6. Test & Inspection
- **FAT**: Module test, Alarm/Trip simulation, Voting logic, Communication test.
- **Mechanical Running Test (Machine Vendor 공장)**: 실제 Probe로 진동 측정, API 670 System calibration.
- **SIT**: DCS/IPS/CCS interface 시험.
- **Site**: Probe gap voltage 설정 (-10 VDC 근방), Loop check.

## 7. Vendor Document Requirement
- Probe arrangement drawing, Rack configuration, Setpoint list, Interconnection wiring, Modbus map, Calibration certificate, Ex certificate, FAT procedure/report, O&M manual.

## 8. Integration Checklist
- [ ] Machine Vendor 와 Probe 위치/수량 확정 (API 670 Data sheet)
- [ ] Alarm/Trip setpoint 및 Voting/Time delay 확정
- [ ] Trip 신호 IPS Hardwired 구성
- [ ] DCS Modbus map 승인
- [ ] Probe system length & calibration 일치
- [ ] 원격 진단 S/W 네트워크 보안(DMZ) 검토

> 참고 Vendor: Baker Hughes Bently Nevada (3500/3701), Emerson AMS 6500, SKF, Brüel & Kjær Vibro, Shinkawa.
