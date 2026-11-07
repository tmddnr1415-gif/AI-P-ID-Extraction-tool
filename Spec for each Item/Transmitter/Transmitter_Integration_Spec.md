# Transmitter (Pressure, Temperature, Level, Flow 등) – Integration Specification

## 1. 개요 (Scope)
- DCS/IPS/FGS/CCS 로 신호를 전송하는 Smart Transmitter 일체.
  - **Pressure / DP TX** (PT, PDT), **Temperature TX** (TT – RTD/TC 입력, Head-mount/Field-mount), **Level TX** (DP, Guided-wave radar, Non-contact radar, Displacer, Ultrasonic, Nuclear), **Flow** (DP–Orifice/Venturi/Annubar, Coriolis, Magnetic, Vortex, Ultrasonic, Thermal mass), Analyzer는 별도.

## 2. 적용 Code & Standard
| 구분 | Standard |
|---|---|
| 일반 | **API RP 551**, IEC 61298 (Performance), IEC 60770 |
| 통신 | **HART 7**, FOUNDATION Fieldbus H1 (IEC 61158), Profibus PA, WirelessHART (IEC 62591) |
| 신호 | **NAMUR NE43** (Fault ≤3.6 / ≥21 mA), **NE107** (Diagnostic status), NE21 (EMC) |
| 기능안전 | **IEC 61508 SIL 2 (SC 3)** 인증 – IPS/FGS 용 |
| Flow 요소 | **ISO 5167** (Orifice/Venturi), AGA 3/7/9 (Custody), API MPMS, ISO 10790 (Coriolis) |
| Temperature | IEC 60751 (Pt100 Class A), IEC 60584 (TC), ASME PTC 19.3 TW |
| 위험지역 | **IEC 60079-0/1/11** (Ex d / Ex ia), ATEX, IECEx, **KCs (국내 방폭)** |
| 보호등급 | IEC 60529 – IP66/67 |
| Sour | NACE MR0175 |

## 3. 기술 요구사항
- Output: **4–20 mA + HART** (기본), FF/Profibus 시 Project 선택.
- Accuracy: Pressure ±0.065~0.075% of span, Temp TX ±0.1 °C(디지털), Coriolis ±0.1%, Mag ±0.2~0.5%, Radar ±2~3 mm.
- Long-term stability, Turndown ≥ 100:1 (Pressure).
- Housing: Dual compartment, SS316/Aluminum (Low copper, Epoxy coat), Local LCD indicator.
- Wetted: SS316L 기본, Hastelloy/Monel/Tantalum (부식), Remote/Direct seal (Capillary, 고온/점성).
- **SIS 용**: SIL 2 인증, FMEDA 데이터, BPCS 와 **별도 Tapping/TX** (독립성), Write protection.
- Temperature: Dual element RTD/TC (SIS), Sensor matching (CVD), Thermowell wake frequency.
- Level: Radar 는 Still-well/Bridle, Dielectric 검토; DP는 Wet/Dry leg 보정; Displacer 대체 시 GWR 우선.
- Flow: Straight run (Upstream/Downstream D), β ratio 0.2~0.7, ΔP 범위, Velocity 제한.
- Response time (CCS 등 고속): ≤ 100 ms, Damping 0.
- 전원: 24 VDC Loop-powered (2-wire), 4-wire (Coriolis/Mag – 24 VDC/AC).

## 4. Integration Interface
| 대상 | 신호 | 원칙 |
|---|---|---|
| DCS | AI 4–20 mA HART / FF | Scaling·Unit 일치, NE43 Fault 처리 |
| IPS/SIS, FGS | AI 4–20 mA HART (SIL) | Voting(1oo2/2oo3), Deviation alarm, Hardwired |
| CCS | 고속 AI | Damping 최소 |
| **AMS/IAMS** | HART pass-through / FF | Device diagnostic, Calibration 관리 |
| Junction box / Cable | IS(Blue) / Non-IS 분리, Shielded twisted pair | IS Entity 계산 |
| Hook-up | 2/3/5-valve manifold, Impulse tubing, Heat tracing, Sunshade, Stanchion | Hook-up drawing 준수 |
| Process/Piping | Tapping 위치, Straight run, Nozzle | |

## 5. Test & Inspection
- Calibration (5-point up/down), Hydro/Leak test (Wetted parts), Insulation, HART comm., PMI.
- Flow element: Bore 측정, Coriolis/Mag **Wet calibration certificate**.
- SIL/Ex certificate 확인, Custody 시 Witness calibration.
- Site: Loop check, Zero trim (설치 자세 보정).

## 6. Vendor Document Requirement
- Data sheet (ISA-20 / IEC 61987), Sizing calc. (Flow element, Radar), Dimensional drawing, Calibration cert, Material cert, Ex cert, SIL cert/Safety manual, DD/EDDL/DTM file, IOM.

## 7. Integration Checklist
- [ ] Protocol (HART/FF/PA) – DCS 와 일치, DD file 확보
- [ ] SIS 용 TX 분리 및 SIL 인증
- [ ] Range/Scaling (Process data) 확정
- [ ] Ex 등급 (Zone, Gas group, T-class) 및 IS 계산
- [ ] Straight run / Tapping / Nozzle 협의
- [ ] Hook-up type 지정 (Winterization 포함)

> 참고 Vendor: Emerson (Rosemount, Micro Motion), Endress+Hauser, Yokogawa, ABB, Siemens, Honeywell, VEGA, KROHNE.
