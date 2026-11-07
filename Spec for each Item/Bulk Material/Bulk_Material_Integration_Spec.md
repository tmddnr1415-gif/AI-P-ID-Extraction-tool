# Bulk Material (Instrument Hook-up Material / Cable Hook-up Material) – Integration Specification

## 1. 개요 (Scope)
- **Instrument Hook-up Material**: Tubing, Tube fitting, Instrument valve/Manifold, Pipe fitting(소구경), Impulse line, Air header/Air distribution, Support/Stanchion, Sunshade, Heat tracing/Insulation box.
- **Cable Hook-up Material**: Instrument cable (Single/Multi-pair, Fieldbus, Thermocouple extension, Fire resistant), Junction box, Cable gland, Cable tray/Ladder/Conduit, Earthing material, Marshalling accessory, Cable tag/Marker.

## 2. 적용 Code & Standard
| 구분 | Standard |
|---|---|
| Hook-up 설계 | **API RP 551/552**, ISA-RP 12.6, Project Hook-up drawing |
| Tubing | **ASTM A269 (SS316 seamless)**, ASTM A213, Monel(B165) / 6Mo |
| Tube fitting | Twin-ferrule compression (ASME B31.3 적합), ISO 19879 |
| Instrument valve/Manifold | MSS SP-99, MSS SP-105, ASME B16.34 |
| Thread | ASME B1.20.1 (NPT) |
| Cable 구조 | **IEC 60502-1**, **BS EN 50288-7**, BS 5308 |
| 난연/내화 | **IEC 60332-1/-3 Cat.A** (Flame retardant), **IEC 60331** (Fire resistant – F&G/ESD), IEC 61034 (Smoke), IEC 60754 (LSZH halogen free) |
| Fieldbus cable | IEC 61158-2 Type A |
| TC extension | IEC 60584-3 |
| Cable gland | **IEC 60079-14** (Barrier gland Ex d), IEC 62444, EN 62444 |
| Junction box | IEC 60079-0/-7 (Ex e)/-11 (Ex i), IEC 60529 (IP66) |
| Cable tray | IEC 61537, NEMA VE 1 |
| 접지 | IEC 60079-14, IEEE 1100, Project Earthing philosophy |
| 국내 | KCs 방폭 인증, KEC (전기설비기술기준) |

## 3. Instrument Hook-up Material 요구사항
- Tubing: SS316 seamless, **½" OD × 0.049" (Impulse)**, ¼"/⅜" (Air), Hardness ≤ 80 HRB (Fitting 호환), Off-shore/염분 → **6Mo/Super duplex** 또는 PVC sheathed.
- Fitting: Twin-ferrule, **동일 Manufacturer tube–fitting 혼용 금지**, Intermix 불허.
- Valve: Needle/Ball, Gauge valve(Block & bleed), **2/3/5-valve manifold** (Pressure/DP), Rating ≥ Piping class.
- Air supply: Header (SS/Galvanized), Take-off ball valve, AFR, Spare take-off 20%.
- Impulse line slope 1:12 (Liquid – TX 하향, Gas – TX 상향), Condensate pot (Steam), Seal pot.
- Winterization: Heat tracing (Steam/Electrical), Insulated TX box.
- Support: Stanchion (2" pipe), Tube tray, SS316 clamp/U-bolt.
- **Hook-up drawing** 별 Bill of Material (BOM) 산출 → MTO.

## 4. Cable Hook-up Material 요구사항
- Instrument cable: Tinned copper, 1.0~1.5 mm², **Individually & Overall screened** (Al/Mylar + Drain), XLPE/PE insulation, **LSZH/PVC Sheath**, Armoured (SWA/GSWB) for direct burial/Outdoor.
- Color: **IS = Light blue sheath**, Non-IS = Black/Grey.
- Fire resistant cable (IEC 60331): F&G, ESD, PAGA 등 Fire 시 기능 유지 회로.
- Multi-pair: Spare pair ≥ 10~20%.
- Junction box: SS316 / GRP, Ex e or Ex i, IP66, Terminal spare ≥ 20%, IS/Non-IS 분리 JB.
- Cable gland: Ex d/Ex e double compression, Armour clamping, Barrier gland (Ex d enclosure Zone 1 요건).
- Tray/Ladder: HDG / SS316 / FRP, **Segregation**: IS – Non-IS – Power(≥ 300~600 mm 이격), Fill ratio ≤ 40~50%.
- Earthing: IS earth bar, Instrument earth, Screen 단일점(Control room 측) 접지.

## 5. Integration Interface
| 대상 | 내용 |
|---|---|
| 계기(TX/Valve/Gauge) | Process connection, Electrical entry (M20/½" NPT), Ex 일치 |
| DCS/IPS/FGS | Marshalling cabinet, Cable schedule, Multi-pair 할당 |
| Piping | Root valve battery limit, Tapping |
| Electrical | Tray route 공유·이격, Earthing grid, Heat tracing 전원 |
| Civil/Structure | Trench, Duct bank, Support steel |
| Instrument Air system | Header sizing, Air consumption |

### Battery Limit (일반)
- Instrument: Root valve 이후 ~ 계기, 계기 ~ JB ~ Cabinet.
- Piping: Root valve 까지.
- Electrical: Main tray(공용) / Power cable.

## 6. Test & Inspection
- Tubing: Material cert (3.1), Hardness, Hydro/Pneumatic leak test (Hook-up 완료 후).
- Cable: Routine test (Conductor resistance, Insulation resistance, Capacitance/Inductance – IS 계산용 L/R), Type test (Flame/Fire).
- JB/Gland: Ex certificate, IP test.
- Site: Megger test, Continuity, Loop check, Tubing leak test.

## 7. Vendor Document Requirement
- Data sheet, Material cert, Test report, Ex certificate, Catalog, Cable parameter (C, L, L/R), Drum schedule.

## 8. Integration Checklist
- [ ] Hook-up drawing 표준화 & MTO (Surplus 5~10%)
- [ ] Tube/Fitting 단일 Manufacturer 확정
- [ ] Cable type 선정 (IS/Non-IS, FR/Fire resistant, Armour)
- [ ] Segregation & Tray route 협의 (Electrical)
- [ ] Ex gland/JB 등급 일치
- [ ] Spare (Pair, Terminal, Take-off) 확보
- [ ] IS Loop 계산용 Cable parameter 확보

> 참고 Vendor: Swagelok, Parker, Hy-Lok(국내), DK-Lok(국내), Nexans, Prysmian, LS전선, 대한전선, CMP / Hawke (Gland), Stahl / Eaton (JB).
