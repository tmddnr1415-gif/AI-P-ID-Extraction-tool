# 실패 리포트 — Phase 0 spike 2b (측정 재정의)

검출 규칙은 추가하지 않았습니다. 이번 변경은 **조인 기준 확정**과 **전체 Excel 로 확인된 앵커 매핑 수정** 두 가지뿐입니다.


## A. 조인 기준 — 페이지 단위

### 도면번호 공유 3건의 귀속 판정

Excel `SYSTEM` 열을 페이지의 `drawing_title` 과 토큰 대조(접두 일치 허용)해 행 단위로 귀속시켰습니다.

**`D00P-10LBG10-M05-0001`** — pages [12, 15]  
Excel SYSTEM: Aux. Steam System  
- p12: P&ID FOR AUXILIARY STEAM SYSTEM GROUP 10 → **13행**
- p15: P&ID FOR GT FLASH PIPE SYSTEM UNIT 11 → **0행**

**`D00P-00GHC10-M05-0001`** — pages [46, 47]  
Excel SYSTEM: Demineralized Water Distribution System  
- p46: P&ID FOR DESAL. WATER SUPPLY SYSTEM → **0행**
- p47: P&ID FOR DEMINERALIZED WATER DISTRIBUTION SYSTEM (1 OF 2) → **16행**

**`D00P-00GMA10-M05-0001`** (p52 / p55) — Excel 전체에 `GMA` 를 포함한 `P&ID No.` 가 **한 건도 없습니다**. 귀속시킬 행 자체가 없으므로 두 페이지 모두 `PDF_ONLY` 입니다.


### 3개 집합

| 집합 | 규모 | 처리 |
|---|---|---|
| `MATCHED` | 35페이지 / Excel 536행 | **규칙 성능은 여기서만 측정** |
| `EXCEL_ONLY` | 5도면 / 21행 | 검출 불가, 점수에서 제외 |
| `PDF_ONLY` | 17페이지 | 정답 없음, 점수에서 제외 |

#### EXCEL_ONLY — Excel 에만 있는 도면

| 도면번호 | 행 수 | Excel SYSTEM |
|---|---|---|
| `D00P-00EGD00-M05-0003` | 2 | Fuel Oil Supply System |
| `D00P-00EKG10-M05-0004` | 2 | Fuel gas Supply System |
| `D00P-00GBL10-M05-0001` | 11 | Desal Water Supply System |
| `D00P-10LCQ10-M05-0001` | 5 | HRSG Blowdown System |
| `D00P-11LCM10-M05-0002` | 1 | GT Flash Pipe System |

**원인 판정** — 위 5건은 모두 PDF 안에 해당 도면이 **다른 번호로 존재**합니다. 도면 누락이 아니라 채번 불일치입니다.

| Excel 도면번호 | 행 | Excel SYSTEM | PDF 상의 실제 페이지 | 그 페이지의 타이틀블록 번호 | 일치도 |
|---|---|---|---|---|---|
| `D00P-00EGD00-M05-0003` | 2 | Fuel Oil Supply System | p34 — P&ID FOR GT FUEL OIL SUPPLY SYSTEM | `D00P-11EGD00-M05-0001` | 1.0 |
| `D00P-00EKG10-M05-0004` | 2 | Fuel gas Supply System | p25 — P&ID FOR GT FUEL GAS SUPPLY SYSTEM | `D00P-11EKG10-M05-0001` | 1.0 |
| `D00P-00GBL10-M05-0001` | 11 | Desal Water Supply System | p46 — P&ID FOR DESAL. WATER SUPPLY SYSTEM | `D00P-00GHC10-M05-0001` | 1.0 |
| `D00P-10LCQ10-M05-0001` | 5 | HRSG Blowdown System | p13 — P&ID FOR HRSG BLOWDOWN SYSTEM UNIT 11 | `D00P-11LCQ10-M05-0001` | 1.0 |
| `D00P-11LCM10-M05-0002` | 1 | GT Flash Pipe System | p15 — P&ID FOR GT FLASH PIPE SYSTEM UNIT 11 | `D00P-10LBG10-M05-0001` | 1.0 |

#### PDF_ONLY — Excel 에 행이 없는 페이지

| 페이지 | 도면번호 | 도면명 | 검출 |
|---|---|---|---|
| p13 | `D00P-11LCQ10-M05-0001` | P&ID FOR HRSG BLOWDOWN SYSTEM UNIT 11 | 5 |
| p15 | `D00P-10LBG10-M05-0001` | P&ID FOR GT FLASH PIPE SYSTEM UNIT 11 | 1 |
| p19 | `D00P-10PUE00-M05-0001` | P&ID FOR CONDENSER WATERBOX AIR REMOVAL SYSTEM GROUP 10 | 0 |
| p25 | `D00P-11EKG10-M05-0001` | P&ID FOR GT FUEL GAS SUPPLY SYSTEM | 9 |
| p29 | `D00P-00PAB10-M05-0004` | P&ID FOR SEAL PIT SYSTEM | 0 |
| p34 | `D00P-11EGD00-M05-0001` | P&ID FOR GT FUEL OIL SUPPLY SYSTEM | 1 |
| p42 | `D00P-10QFA10-M05-0001` | P&ID FOR COMPRESSED AIR SYSTEM | 10 |
| p45 | `D00P-00QJA10-M05-0001` | P&ID FOR SERVICE GAS SYSTEM | 0 |
| p46 | `D00P-00GHC10-M05-0001` | P&ID FOR DESAL. WATER SUPPLY SYSTEM | 16 |
| p50 | `D00P-00GHB10-M05-0002` | P&ID FOR SERVICE WATER DISTRIBUTION SYSTEM (2 OF 2) | 0 |
| p52 | `D00P-00GMA10-M05-0001` | P&ID FOR CHEMICAL WASTE WATER TRANSFER SYSTEM | 30 |
| p53 | `D00P-00GMB10-M05-0001` | P&ID FOR OILY WASTE WATER TRANSFER SYSTEM (1 OF 2) | 24 |
| p54 | `D00P-00GMB10-M05-0002` | P&ID FOR OILY WASTE WATER TRANSFER SYSTEM (2 OF 2) | 21 |
| p55 | `D00P-00GMA10-M05-0001` | P&ID FOR WASTE WATER TRANSFER SYSTEM (SEA WATER / STORM WATER) | 15 |
| p56 | `D00P-00GQA10-M05-0001` | P&ID FOR SANITARY SEWER TRANSFER SYSTEM | 18 |
| p57 | `D00P-00QCA00-M05-0001` | P&ID FOR CHEMICAL DOSING SYSTEM | 0 |
| p58 | `D00P-11QUA10-M05-0001` | P&ID FOR SAMPLING SYSTEM UNIT 11 | 0 |

## B. 앵커 사전 수정

| 코드 | 조치 | 근거 |
|---|---|---|
| `FE` | 비대상 → **Field 대상** | Excel `FE` 18행. `D00P-10MAN10-M05-0001` 행 61/71/82 (`... SPRAY WATER FLOW ELEMENT`), 해당 p10 도면의 FE 버블 3개와 일치 |
| `LSH`/`LSHH`/`LSL` | **→ `LS` 매핑** | Excel `LS` 22행, 설명이 `... LEVEL HIGH HIGH` / `... LEVEL HIGH`. `D00P-10LBC40-M05-0001` 행 20~23, 해당 p7 도면에 LSHH 4 + LSH 4 |
| `ZS` | **추가하지 않음** | Excel `TYPE` 열에 `ZS` **0행**. 이전 리포트에서 `ZS` 옆의 숫자는 같은 페이지의 *다른* TYPE 결손이었고 ZS 자체의 행 수가 아니었습니다 |
| `LG` | **추가하지 않음** | Excel `TYPE` 열에 `LG` **0행**. 위와 동일 |

### 한 페이지 표본으로 굳어진 규칙 재점검 (전체 Excel 대조)

| 규칙 | 근거 | 판정 |
|---|---|---|
| `FE` = 비대상 | Excel FE **18행** | ❌ 오류 — 이번에 철회 |
| `FT` = 비대상 | Excel `FIT` **31행**. `D00P-10MAN10-M05-0001` 이 `FIT` 5행을 요구하고 p10 도면에 `FT` 버블이 정확히 5개 | ⚠️ **오류로 보임 — 이번 지시 목록 밖이라 미적용** |
| `TW` = 비대상 | Excel `TYPE` 에 `TW` 0행 | ✅ 유지 |
| `TT`→`TIT`, `PT`→`PIT` | Excel 에 `TT`/`PT` TYPE 0행, `TIT` 99 / `PIT` 108행 | ✅ 유지 |
| `MOV` = 밸브 | Excel Field 리스트에 밸브 TYPE 없음 | ✅ 유지 |

## C. SCT 규칙 — 기본 비활성

- 끈 상태: 검출 598 / TP 520 / 재현율 97.0% / 정밀도 87.0%
- 켠 상태: 검출 596 / TP 518 / 재현율 96.6% / 정밀도 86.9%
- 코드는 유지하고 `--enable-rule SCT_SUPPLIER_SCOPE` 로 켤 수 있습니다. 비활성 사유는 `detect_symbols.py` 의 `DEFAULT_DISABLED` 주석에 근거와 함께 기록했습니다.

## 1. 측정 재정의 전후 비교

| 변형 | 검출 | Excel | 일치 | 재현율 | 정밀도 |
|---|---|---|---|---|---|
| v1 규칙 + 도면 조인 (2b 발표값) | 573 | 557 | 455 | 81.7% | 79.4% |
| v1 규칙 + 페이지 조인 | 525 | 536 | 455 | 84.9% | 86.7% |
| v2 규칙 + 글리프 마크만 (2c 기준선) | 572 | 536 | 490 | 91.4% | 85.7% |
| v3 규칙 + 벤더 규칙 없음 | 717 | 536 | 524 | 97.8% | 73.1% |
| v3 규칙 + 글리프 | 610 | 536 | 520 | 97.0% | 85.2% |
| v3 규칙 + 글리프 + 텍스트 | 604 | 536 | 520 | 97.0% | 86.1% |
| **v3 규칙 + 글리프 + 텍스트 + 패키지박스 (새 기준선)** | 598 | 536 | 520 | 97.0% | 87.0% |
| v3 규칙 + 전부 + SCT on | 596 | 536 | 518 | 96.6% | 86.9% |

## 2. 계통별 정확도 (MATCHED, 재현율 오름차순)

| 계통 | 페이지 | 검출 | Excel | 일치 | 재현율 | 정밀도 | 대표 도면명 |
|---|---|---|---|---|---|---|---|
| `SCB` | 1 | 0 | 1 | 0 | 0.0% | 0.0% | P&ID FOR SERVICE AIR DISTRIBUTION SYST |
| `QFB` | 1 | 1 | 2 | 1 | 50.0% | 100.0% | P&ID FOR INSTRUMENT AIR DISTRIBUTION S |
| `GHB` | 1 | 17 | 17 | 11 | 64.7% | 64.7% | P&ID FOR SERVICE WATER DISTRIBUTION SY |
| `PAB` | 3 | 22 | 14 | 12 | 85.7% | 54.5% | P&ID FOR SEAWATER INTAKE SYSTEM (1 OF  |
| `LCA` | 2 | 38 | 41 | 37 | 90.2% | 97.4% | P&ID FOR CONDENSATE SYSTEM GROUP 10 (1 |
| `LAC` | 1 | 22 | 23 | 22 | 95.7% | 100.0% | P&ID FOR FGH & TCA COOLING SYSTEM UNIT |
| `PGB` | 7 | 176 | 170 | 169 | 99.4% | 96.0% | P&ID FOR CLOSED COOLING WATER SYSTEM G |
| `MAN` | 2 | 64 | 64 | 64 | 100.0% | 100.0% | P&ID FOR BYPASS STEAM SYSTEM GROUP 10  |
| `LAB` | 1 | 33 | 33 | 33 | 100.0% | 100.0% | P&ID FOR HRSG FEEDWATER SYSTEM UNIT 11 |
| `EGD` | 2 | 51 | 33 | 33 | 100.0% | 64.7% | P&ID FOR FUEL OIL SUPPLY SYSTEM (1/2) |
| `LBA` | 2 | 31 | 24 | 24 | 100.0% | 77.4% | P&ID FOR HP STEAM SYSTEM GROUP 10 |
| `LBC` | 2 | 21 | 21 | 21 | 100.0% | 100.0% | P&ID FOR CRH STEAM SYSTEM GROUP 10 |
| `PAC` | 1 | 24 | 16 | 16 | 100.0% | 66.7% | P&ID FOR CIRCULATING WATER SYSTEM FOR  |
| `GHC` | 1 | 34 | 16 | 16 | 100.0% | 47.1% | P&ID FOR DEMINERALIZED WATER DISTRIBUT |
| `PCB` | 1 | 15 | 15 | 15 | 100.0% | 100.0% | P&ID FOR AUX. COOLING WATER SYSTEM FOR |
| `LBG` | 1 | 13 | 13 | 13 | 100.0% | 100.0% | P&ID FOR AUXILIARY STEAM SYSTEM GROUP  |
| `LCM` | 1 | 9 | 9 | 9 | 100.0% | 100.0% | P&ID FOR CLEAN DRAIN SYSTEM FOR GROUP  |
| `EKG` | 3 | 9 | 9 | 9 | 100.0% | 100.0% | P&ID FOR FUEL GAS SUPPLY SYSTEM (1 OF  |
| `MAJ` | 1 | 8 | 8 | 8 | 100.0% | 100.0% | P&ID FOR CONDENSER AIR REMOVAL SYSTEM  |
| `GKB` | 1 | 10 | 7 | 7 | 100.0% | 70.0% | P&ID FOR POTABLE WATER SUPPLY SYSTEM |

## 4~5. 실패 유형 재집계 (v1 규칙 → v3 규칙, MATCHED 기준)

| 유형 | v1 케이스 | v1 행 | v3 케이스 | v3 행 | 변화 |
|---|---|---|---|---|---|
| `NO_ANCHOR` | 7 | 23 | 1 | 1 | -22 |
| `AMBIGUOUS_GEOMETRY` | 8 | 13 | 6 | 9 | -4 |
| `SCOPE_CONFLICT` | 4 | 6 | 3 | 4 | -2 |
| `VENDOR_MARK_UNDEFINED` | 0 | 0 | 0 | 0 | +0 |
| `TYPE_MAPPING_MISS` | 12 | 39 | 2 | 2 | -37 |
| `OVER_DETECT` | 19 | 70 | 22 | 78 | +8 |

## 유형별 대표 사례 (v2 기준)


### `NO_ANCHOR` — 1 케이스 / 1 행

**p43 D00P-10QFB10-M05-0001** (계통 `QFB`, TYPE `PIT`, 1행)  
P&ID FOR INSTRUMENT AIR DISTRIBUTION SYSTEM  
추정 원인: no 'PIT' anchor found in any bubble on this page  


### `AMBIGUOUS_GEOMETRY` — 6 케이스 / 9 행

**p49 D00P-00GHB10-M05-0001** (계통 `GHB`, TYPE `PDIT`, 3행)  
P&ID FOR SERVICE WATER DISTRIBUTION SYSTEM (1 OF 2)  
추정 원인: anchors found but no single enclosing bubble  
- `PDIT` @ [1375.1, 323.8]  규칙: -
- `PIT` @ [1432.1, 323.8]  규칙: -
- `FIT` @ [1702.9, 758.7]  규칙: -

**p49 D00P-00GHB10-M05-0001** (계통 `GHB`, TYPE `PIT`, 2행)  
P&ID FOR SERVICE WATER DISTRIBUTION SYSTEM (1 OF 2)  
추정 원인: anchors found but no single enclosing bubble  
- `PDIT` @ [1375.1, 323.8]  규칙: -
- `PIT` @ [1432.1, 323.8]  규칙: -
- `FIT` @ [1702.9, 758.7]  규칙: -

**p26 D00P-00PAB10-M05-0001** (계통 `PAB`, TYPE `PIT`, 1행)  
P&ID FOR SEAWATER INTAKE SYSTEM (1 OF 3)  
추정 원인: anchors found but no single enclosing bubble  
- `MOV` @ [1080.2, 650.5]  규칙: -


### `SCOPE_CONFLICT` — 3 케이스 / 4 행

**p16 D00P-10LCA10-M05-0001** (계통 `LCA`, TYPE `PI`, 2행)  
P&ID FOR CONDENSATE SYSTEM GROUP 10 (1 OF 2)  
추정 원인: excluded by a scope rule but the Excel keeps the row  
- `PI` @ [677.0, 318.0]  규칙: VENDOR_MARK_GLYPH
- `PI` @ [657.0, 877.3]  규칙: VENDOR_MARK_GLYPH
- `PI` @ [1348.0, 1144.3]  규칙: VENDOR_MARK_GLYPH

**p16 D00P-10LCA10-M05-0001** (계통 `LCA`, TYPE `TI`, 1행)  
P&ID FOR CONDENSATE SYSTEM GROUP 10 (1 OF 2)  
추정 원인: excluded by a scope rule but the Excel keeps the row  
- `TI` @ [798.7, 877.3]  규칙: VENDOR_MARK_GLYPH

**p35 D00P-10PGB10-M05-0001** (계통 `PGB`, TYPE `TIT`, 1행)  
P&ID FOR CLOSED COOLING WATER SYSTEM GROUP 10 (1 OF 7)  
추정 원인: excluded by a scope rule but the Excel keeps the row  
- `TIT` @ [1518.9, 1483.1]  규칙: VENDOR_MARK_GLYPH


### `VENDOR_MARK_UNDEFINED` — 0 케이스 / 0 행

해당 없음.


### `TYPE_MAPPING_MISS` — 2 케이스 / 2 행

**p16 D00P-10LCA10-M05-0001** (계통 `LCA`, TYPE `RO`, 1행)  
P&ID FOR CONDENSATE SYSTEM GROUP 10 (1 OF 2)  
추정 원인: bubble holds a tag outside the anchor dictionary: AIT, PP, ZS  
- `PP` @ [677.2, 182.7]  규칙: -
- `PP` @ [719.7, 212.2]  규칙: -
- `PP` @ [762.2, 182.7]  규칙: -

**p21 D00P-11LAC10-M05-0001** (계통 `LAC`, TYPE `FE`, 1행)  
P&ID FOR FGH & TCA COOLING SYSTEM UNIT 11  
추정 원인: bubble holds a tag outside the anchor dictionary: ZSC, ZSO, ZT  
- `ZSC` @ [400.2, 465.9]  규칙: -
- `ZSO` @ [400.2, 488.5]  규칙: -
- `ZSO` @ [400.2, 718.5]  규칙: -


### `OVER_DETECT` — 22 케이스 / 78 행

**p33 D00P-00EGD00-M05-0002** (계통 `EGD`, TYPE `PI`, 12행)  
P&ID FOR FUEL OIL SUPPLY SYSTEM (2/2)  
추정 원인: detected 12 vs excel 0  
- `PI` @ [1196.7, 215.6]  규칙: VENDOR_MARK_UNDEFINED
- `PI` @ [1353.9, 208.5]  규칙: VENDOR_MARK_UNDEFINED
- `PI` @ [1353.9, 427.5]  규칙: VENDOR_MARK_UNDEFINED

**p47 D00P-00GHC10-M05-0001** (계통 `GHC`, TYPE `PI`, 12행)  
P&ID FOR DEMINERALIZED WATER DISTRIBUTION SYSTEM (1 OF 2)  
추정 원인: detected 12 vs excel 0  
- `PI` @ [1463.9, 440.2]  규칙: -
- `PI` @ [1173.6, 458.6]  규칙: -
- `PI` @ [1463.9, 584.2]  규칙: -

**p30 D00P-10PAC10-M05-0001** (계통 `PAC`, TYPE `LIT`, 8행)  
P&ID FOR CIRCULATING WATER SYSTEM FOR GROUP 10  
추정 원인: detected 8 vs excel 0  
- `LIT` @ [572.5, 761.4]  규칙: -
- `LIT` @ [713.8, 761.4]  규칙: -
- `LIT` @ [855.2, 761.4]  규칙: -


## 버블 치수 분포 (페이지별 실측)

| 스타디움 | 개수 | 페이지 수 |
|---|---|---|
| 68.0 x 22.6 | 558 | 29 |
| 85.1 x 28.4 | 361 | 20 |
| 67.9 x 22.6 | 138 | 22 |
| 85.0 x 28.4 | 98 | 17 |
| 50.0 x 16.6 | 8 | 1 |
| 54.5 x 18.2 | 6 | 2 |
