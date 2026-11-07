# Field Gauge (Pressure, Temperature, Level, Flow 등) – Integration Specification

## 1. 개요 (Scope)
- 현장 국부 지시계(Local indicator, 비전송형): **Pressure Gauge(PG), DP Gauge(PDG), Temperature Gauge(TG, Bimetal/Filled system), Level Gauge(LG – Tubular/Reflex/Transparent/Magnetic), Flow Indicator(Rotameter/Variable area, Sight glass)** 및 Thermowell, Diaphragm seal, Snubber/Siphon 등 Accessory.

## 2. 적용 Code & Standard
| 구분 | Standard |
|---|---|
| Pressure gauge | **ASME B40.100**, EN 837-1/-2/-3 |
| Temperature gauge | ASME B40.200, EN 13190 |
| Thermowell | **ASME PTC 19.3 TW-2016** (Wake frequency calc.) |
| Diaphragm seal | ASME B40.100 / EN 837 |
| Level gauge | Manufacturer std, ASME B31.3 (Pressure parts), API RP 551 |
| Rotameter | VDI/VDE 3513 |
| 일반 설치 | **API RP 551** (Process measurement), ISA-5.1 (Symbol) |
| Sour | NACE MR0175 |
| 국내 | 계량법 (해당 시), KS B 5305 (압력계) |

## 3. 기술 요구사항
### 3.1 Pressure / DP Gauge
- Dial size: **100 mm (4")** 일반, 150 mm (원거리 판독).
- Accuracy: **±1.0% FS (Grade 1A)**, 일반 Normal 운전값이 Range의 **30~70%(약 2/3 지점)**.
- Case: SS316, **Solid-front / Blow-out back (Safety pattern)**, Liquid filled (진동/맥동).
- Over-range protection 130%, Snubber(맥동), Siphon(Steam), **Diaphragm seal**(부식/점성/고형분).
- Connection: ½" NPT(M) bottom/back.

### 3.2 Temperature Gauge
- Bimetal (Every-angle), Dial 100~150 mm, Accuracy ±1% FS, Gas/Liquid-filled (원격·진동).
- **Thermowell 필수** (Bar-stock, Flanged 1½" Class 등 Project std), Wake frequency 계산.

### 3.3 Level Gauge
- Transparent (고압, Interface, 착색 액체), Reflex (Clean liquid), **Magnetic (Toxic/Flammable, 고온)**.
- Visible length = LT range 를 커버, Overlap 50 mm 이상 (다단 설치 시).
- Gauge cock with **Ball check (Excess flow)**, Vent/Drain, Frost extension (저온), Illuminator(필요 시).
- Magnetic type: Float sizing (SG, P, T), Switch/TX 부착 가능.

### 3.4 Flow Indicator
- Variable area (Glass tube / Metal tube with indicator), Accuracy ±2~3%, Purge/Utility 소유량.

## 4. Integration Interface
| 대상 | 내용 |
|---|---|
| Process/Mechanical | Design P/T, Range, Fluid, Nozzle (Vessel LG nozzle 위치·Orientation) |
| Piping | Root valve, Tapping point, Thermowell connection (Line size ≥ 2" 이상 권장, 소구경은 Expander) |
| DCS | **신호 없음** (단, Magnetic LG 의 Switch/TX 부착 시 DCS/IPS 연계) |
| Hook-up | Gauge valve(Block & bleed manifold), Impulse tubing, Support |
| Operation | 판독 위치·방향, 플랫폼 접근성 |

## 5. Test & Inspection
- Calibration certificate (Traceable), Hydro test (Level gauge body 1.5× design), Thermowell PMI/Hydro, Material cert (3.1), Wake frequency report.

## 6. Vendor Document Requirement
- Data sheet, Dimensional drawing, Calibration certificate, Material cert, Thermowell calculation, IOM.

## 7. Integration Checklist
- [ ] Range 선정 (Normal = 약 50~70%)
- [ ] Diaphragm seal/Snubber/Siphon 적용 기준
- [ ] Thermowell 재질/길이 & Wake frequency
- [ ] Level gauge visible length vs Nozzle / LT range 일치
- [ ] Safety pattern case 적용 (Gas, 고압)

> 참고 Vendor: WIKA, Ashcroft, Badotherm, Nagano Keiki, KSR Kuebler, Klinger, 국내 – 우진, 한국계측기 등.
