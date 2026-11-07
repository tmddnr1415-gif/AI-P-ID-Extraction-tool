# Instrument & Control – Integration Spec Index

| # | Item | 포함 범위 | 파일 |
|---|---|---|---|
| 1 | DCS | Main control, HMI, Historian, 3rd-party interface | [DCS](DCS/DCS_Integration_Spec.md) |
| 2 | IPS | SIS / ESD / PSD / BMS | [IPS](IPS/IPS_Integration_Spec.md) |
| 3 | MMS | Vibration / Machine protection (API 670) | [MMS](MMS/MMS_Integration_Spec.md) |
| 4 | CCS | Anti-surge / Performance / Load sharing | [CCS](CCS/CCS_Integration_Spec.md) |
| 5 | FGS | Fire & Gas detection, Mapping | [FGS](FGS/FGS_Integration_Spec.md) |
| 6 | Ball Valve | ESDV, SDV, BDV, XV | [Ball Valve](Ball%20Valve/Ball_Valve_Integration_Spec.md) |
| 7 | Globe Valve | Control Valve, PRV, MOV | [Globe Valve](Globe%20Valve/Globe_Valve_Integration_Spec.md) |
| 8 | Butterfly Valve | Control Valve, MOV | [Butterfly Valve](Butterfly%20Valve/Butterfly_Valve_Integration_Spec.md) |
| 9 | PSV | Conventional / Bellows / Pilot, PVRV | [PSV](PSV/PSV_Integration_Spec.md) |
| 10 | Field Gauge | PG, PDG, TG, LG, FI, Thermowell | [Field Gauge](Field%20Gauge/Field_Gauge_Integration_Spec.md) |
| 11 | Transmitter | PT, PDT, TT, LT, FT | [Transmitter](Transmitter/Transmitter_Integration_Spec.md) |
| 12 | Bulk Material | Instrument hook-up, Cable hook-up | [Bulk Material](Bulk%20Material/Bulk_Material_Integration_Spec.md) |

## 공통 Integration 원칙
1. **Safety 신호(IPS/FGS/MMS Trip)는 Hardwired**, 통신은 감시용 (Read-only).
2. 모든 시스템 간 Interface 는 **ICD(Interface Control Document / Data map)** 로 상호 승인.
3. Field 기기는 **HART 7 / NAMUR NE43·NE107** 통일, AMS 연계.
4. Ex 등급(IEC 60079/KCs), Cyber security(IEC 62443), 기능안전(IEC 61511) 일관 적용.
5. FAT → SIT(통합시험) → SAT → Loop check → Commissioning 단계별 검증.

> 본 문서는 국제 Code/Standard 및 일반 EPC 실무 기준으로 정리한 Template 이며, 수치(Spare %, Stroke time, Setpoint 등)는 Project Specification/Client 요건에 따라 확정 필요.
