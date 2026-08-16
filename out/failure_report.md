# 전수 적용 실패 리포트 — Phase 0 spike 2b

page 6 에서 검증한 규칙을 **그대로** 전 페이지에 적용한 결과입니다. 새 규칙은 추가하지 않았습니다.

- Excel 총 563행 중 `P&ID No.` 가 있는 557행이 조인 대상 (나머지 6행은 SPARE)

- 검출 620행 / 정답 557행 / 일치 456행

- **재현율 81.9%, 정밀도 73.5%**


## 조인 무결성 — 지표를 왜곡하는 요인

- Excel 에는 있으나 **PDF 에 해당 도면이 없는** 도면번호 5건 / 21행 → 검출 불가, 전부 재현율 손실로 계상됨
  - `D00P-00EGD00-M05-0003` (2행)
  - `D00P-00EKG10-M05-0004` (2행)
  - `D00P-00GBL10-M05-0001` (11행)
  - `D00P-10LCQ10-M05-0001` (5행)
  - `D00P-11LCM10-M05-0002` (1행)
- PDF 에는 있으나 **Excel 에 행이 없는** 도면 14건 / 검출 31행 → 전부 정밀도 손실로 계상됨
- **도면번호를 공유하는 페이지** 3건 — 1:N 조인이라 서로 다른 도면의 검출이 한 번호로 합산됩니다
  - `D00P-00GHC10-M05-0001` pages [46, 47] 검출 54 / Excel 16
    - p46: P&ID FOR DESAL. WATER SUPPLY SYSTEM
    - p47: P&ID FOR DEMINERALIZED WATER DISTRIBUTION SYSTEM (1 OF 2)
    - Excel SYSTEM: Demineralized Water Distribution System
  - `D00P-00GMA10-M05-0001` pages [52, 55] 검출 6 / Excel 0
    - p52: P&ID FOR CHEMICAL WASTE WATER TRANSFER SYSTEM
    - p55: P&ID FOR WASTE WATER TRANSFER SYSTEM (SEA WATER / STORM WATER)
    - Excel SYSTEM: (행 없음)
  - `D00P-10LBG10-M05-0001` pages [12, 15] 검출 12 / Excel 13
    - p12: P&ID FOR AUXILIARY STEAM SYSTEM GROUP 10
    - p15: P&ID FOR GT FLASH PIPE SYSTEM UNIT 11
    - Excel SYSTEM: Aux. Steam System

## 규칙 조합별 성능

| 활성 규칙 | 검출 | 정답 | 일치 | 재현율 | 정밀도 |
|---|---|---|---|---|---|
| 둘 다 끔 | 759 | 557 | 461 | 82.8% | 60.7% |
| SCT 만 | 727 | 557 | 459 | 82.4% | 63.1% |
| 벤더마크 만 | 622 | 557 | 458 | 82.2% | 73.6% |
| 둘 다 | 620 | 557 | 456 | 81.9% | 73.5% |

## 버블 치수 분포 (페이지별 실측)

| 스타디움 (긴변 x 짧은변) | 개수 | 사용 페이지 수 |
|---|---|---|
| 68.0 x 22.6 | 558 | 29 |
| 85.1 x 28.4 | 361 | 20 |
| 67.9 x 22.6 | 138 | 22 |
| 85.0 x 28.4 | 98 | 17 |
| 50.0 x 16.6 | 8 | 1 |
| 54.5 x 18.2 | 6 | 2 |
| 49.9 x 16.6 | 5 | 1 |
| 10.3 x 5.1 | 2 | 1 |

## 벤더 마크 표기 방식 (규칙이 적용 가능한 범위)

| 표기 방식 | 페이지 수 | 규칙 적용 | 페이지 |
|---|---|---|---|
| 벡터 글리프 (page 6 방식) | 19 | 가능 | [6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 20, 25, 30, 35, 47, 52, 53, 54, 56] |
| 텍스트 `(*)` / `(**)` | 7 | **불가 — 규칙이 못 봄** | [26, 27, 28, 32, 46, 49, 51] |
| 마크 없음 | 26 | 해당 없음 | [15, 17, 18, 19, 21, 22, 23, 24, 29, 31, 33, 34, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 55, 57, 58] |

## 실패 유형별 집계

| 유형 | 케이스 | 행 수 |
|---|---|---|
| `NO_ANCHOR` | 15 | 32 |
| `AMBIGUOUS_GEOMETRY` | 5 | 6 |
| `SCOPE_CONFLICT` | 3 | 5 |
| `VENDOR_MARK_UNDEFINED` | 0 | 0 |
| `TYPE_MAPPING_MISS` | 19 | 58 |
| `OVER_DETECT` | 38 | 164 |

## 유형별 대표 사례


### `NO_ANCHOR` — 15 케이스 / 32 행

**D00P-10MAN10-M05-0001** (계통 `MAN`, TYPE `FIT`, 5행)  
P&ID FOR BYPASS STEAM SYSTEM GROUP 10 (1 OF 2)  
추정 원인: no 'FIT' anchor found in any bubble on this drawing  

**D00P-10MAN10-M05-0002** (계통 `MAN`, TYPE `FIT`, 5행)  
P&ID FOR BYPASS STEAM SYSTEM GROUP 10 (2 OF 2)  
추정 원인: no 'FIT' anchor found in any bubble on this drawing  

**D00P-00GBL10-M05-0001** (계통 `GBL`, TYPE `LIT`, 4행)  
  
추정 원인: no page in the PDF carries this drawing number  


### `AMBIGUOUS_GEOMETRY` — 5 케이스 / 6 행

**D00P-10LCA10-M05-0002** (계통 `LCA`, TYPE `FIT`, 2행)  
P&ID FOR CONDENSATE SYSTEM GROUP 10 (2 OF 2)  
추정 원인: anchors found but no single enclosing bubble  
- p17 `CV` @ [807.5, 296.9]  규칙: -
- p17 `CV` @ [1074.5, 402.7]  규칙: -

**D00P-00PAB10-M05-0001** (계통 `PAB`, TYPE `PIT`, 1행)  
P&ID FOR SEAWATER INTAKE SYSTEM (1 OF 3)  
추정 원인: anchors found but no single enclosing bubble  
- p26 `MOV` @ [1080.2, 650.5]  규칙: -

**D00P-00PAB10-M05-0002** (계통 `PAB`, TYPE `PIT`, 1행)  
P&ID FOR SEAWATER INTAKE SYSTEM (2 OF 3)  
추정 원인: anchors found but no single enclosing bubble  
- p27 `RO` @ [303.3, 940.8]  규칙: -
- p27 `HV` @ [1000.6, 600.7]  규칙: -
- p27 `MOV` @ [1003.6, 614.5]  규칙: -


### `SCOPE_CONFLICT` — 3 케이스 / 5 행

**D00P-10LCA10-M05-0001** (계통 `LCA`, TYPE `PI`, 2행)  
P&ID FOR CONDENSATE SYSTEM GROUP 10 (1 OF 2)  
추정 원인: excluded by a scope rule but the Excel keeps the row  
- p16 `PI` @ [677.0, 318.0]  규칙: VENDOR_MARK
- p16 `PI` @ [657.0, 877.3]  규칙: VENDOR_MARK
- p16 `PI` @ [1348.0, 1144.3]  규칙: VENDOR_MARK

**D00P-11LAB00-M05-0001** (계통 `LAB`, TYPE `RO`, 2행)  
P&ID FOR HRSG FEEDWATER SYSTEM UNIT 11  
추정 원인: excluded by a scope rule but the Excel keeps the row  
- p20 `RO` @ [1118.5, 809.4]  규칙: SCT_SUPPLIER_SCOPE
- p20 `RO` @ [1118.5, 1300.0]  규칙: SCT_SUPPLIER_SCOPE

**D00P-10LCA10-M05-0001** (계통 `LCA`, TYPE `TI`, 1행)  
P&ID FOR CONDENSATE SYSTEM GROUP 10 (1 OF 2)  
추정 원인: excluded by a scope rule but the Excel keeps the row  
- p16 `TI` @ [798.7, 877.3]  규칙: VENDOR_MARK


### `VENDOR_MARK_UNDEFINED` — 0 케이스 / 0 행

해당 없음.


### `TYPE_MAPPING_MISS` — 19 케이스 / 58 행

**D00P-10LBA30-M05-0001** (계통 `LBA`, TYPE `LS`, 8행)  
P&ID FOR LP STEAM SYSTEM GROUP 10  
추정 원인: bubble holds a tag the anchor dictionary does not cover: LSH, LSHH  
- p9 `LSH` @ [953.0, 645.1]  규칙: -
- p9 `LSHH` @ [823.4, 659.2]  규칙: -
- p9 `LSH` @ [938.8, 1259.1]  규칙: -

**D00P-10LBC40-M05-0001** (계통 `LBC`, TYPE `LS`, 8행)  
P&ID FOR CRH STEAM SYSTEM GROUP 10  
추정 원인: bubble holds a tag the anchor dictionary does not cover: LSH, LSHH, PP  
- p7 `LSHH` @ [1481.9, 674.0]  규칙: -
- p7 `LSH` @ [1611.6, 688.2]  규칙: -
- p7 `LSHH` @ [1481.9, 1271.0]  규칙: -

**D00P-11LAB00-M05-0001** (계통 `LAB`, TYPE `FIT`, 8행)  
P&ID FOR HRSG FEEDWATER SYSTEM UNIT 11  
추정 원인: bubble holds a tag the anchor dictionary does not cover: ZS  
- p20 `ZS` @ [488.1, 638.5]  규칙: -
- p20 `ZS` @ [521.4, 1152.3]  규칙: -


### `OVER_DETECT` — 38 케이스 / 164 행

**D00P-00GHC10-M05-0001** (계통 `GHC`, TYPE `PI`, 18행)  
P&ID FOR DESAL. WATER SUPPLY SYSTEM  
추정 원인: detected 18 vs excel 0  
- p46 `PI` @ [1367.3, 495.9]  규칙: -
- p46 `PI` @ [1142.7, 514.2]  규칙: -
- p46 `PI` @ [1367.3, 639.9]  규칙: -

**D00P-00EGD00-M05-0002** (계통 `EGD`, TYPE `PI`, 12행)  
P&ID FOR FUEL OIL SUPPLY SYSTEM (2/2)  
추정 원인: detected 12 vs excel 0  
- p33 `PI` @ [1196.7, 215.6]  규칙: -
- p33 `PI` @ [1353.9, 208.5]  규칙: -
- p33 `PI` @ [1353.9, 427.5]  규칙: -

**D00P-00PAB10-M05-0001** (계통 `PAB`, TYPE `LIT`, 10행)  
P&ID FOR SEAWATER INTAKE SYSTEM (1 OF 3)  
추정 원인: detected 10 vs excel 0  
- p26 `LIT` @ [970.9, 826.1]  규칙: -
- p26 `LIT` @ [1250.6, 826.1]  규칙: -
- p26 `LIT` @ [1524.2, 826.1]  규칙: -


## 계통별 정확도 (재현율 오름차순)

| 계통 | 도면 | 검출 | Excel | 일치 | 재현율 | 정밀도 | 대표 도면명 |
|---|---|---|---|---|---|---|---|
| `GBL` | 1 | 0 | 11 | 0 | 0.0% | n/a |  |
| `LCQ` | 2 | 5 | 5 | 0 | 0.0% | 0.0% | P&ID FOR HRSG BLOWDOWN SYSTEM UNIT 11 |
| `SCB` | 1 | 0 | 1 | 0 | 0.0% | n/a | P&ID FOR SERVICE AIR DISTRIBUTION SYSTEM |
| `QFB` | 1 | 1 | 2 | 1 | 50.0% | 100.0% | P&ID FOR INSTRUMENT AIR DISTRIBUTION SYS |
| `GHB` | 2 | 18 | 17 | 9 | 52.9% | 50.0% | P&ID FOR SERVICE WATER DISTRIBUTION SYST |
| `LAB` | 1 | 19 | 33 | 19 | 57.6% | 100.0% | P&ID FOR HRSG FEEDWATER SYSTEM UNIT 11 |
| `LBC` | 2 | 13 | 21 | 13 | 61.9% | 100.0% | P&ID FOR CRH STEAM SYSTEM GROUP 10 |
| `LBA` | 2 | 17 | 24 | 16 | 66.7% | 94.1% | P&ID FOR HP STEAM SYSTEM GROUP 10 |
| `LAC` | 1 | 16 | 23 | 16 | 69.6% | 100.0% | P&ID FOR FGH & TCA COOLING SYSTEM UNIT 1 |
| `MAN` | 2 | 48 | 64 | 48 | 75.0% | 100.0% | P&ID FOR BYPASS STEAM SYSTEM GROUP 10 (1 |
| `LCA` | 2 | 33 | 41 | 32 | 78.0% | 97.0% | P&ID FOR CONDENSATE SYSTEM GROUP 10 (1 O |
| `EKG` | 5 | 18 | 11 | 9 | 81.8% | 50.0% | P&ID FOR FUEL GAS SUPPLY SYSTEM (1 OF 3) |
| `LBG` | 1 | 12 | 13 | 11 | 84.6% | 91.7% | P&ID FOR AUXILIARY STEAM SYSTEM GROUP 10 |
| `EGD` | 4 | 55 | 35 | 30 | 85.7% | 54.5% | P&ID FOR FUEL OIL SUPPLY SYSTEM (1/2) |
| `PAB` | 4 | 50 | 14 | 12 | 85.7% | 24.0% | P&ID FOR SEAWATER INTAKE SYSTEM (1 OF 3) |
| `GKB` | 1 | 12 | 7 | 6 | 85.7% | 50.0% | P&ID FOR POTABLE WATER SUPPLY SYSTEM |
| `LCM` | 2 | 9 | 10 | 9 | 90.0% | 100.0% | P&ID FOR CLEAN DRAIN SYSTEM FOR GROUP 10 |
| `PGB` | 7 | 177 | 170 | 170 | 100.0% | 96.0% | P&ID FOR CLOSED COOLING WATER SYSTEM GRO |
| `GHC` | 1 | 54 | 16 | 16 | 100.0% | 29.6% | P&ID FOR DESAL. WATER SUPPLY SYSTEM |
| `PAC` | 1 | 24 | 16 | 16 | 100.0% | 66.7% | P&ID FOR CIRCULATING WATER SYSTEM FOR GR |
| `PCB` | 1 | 15 | 15 | 15 | 100.0% | 100.0% | P&ID FOR AUX. COOLING WATER SYSTEM FOR G |
| `MAJ` | 1 | 8 | 8 | 8 | 100.0% | 100.0% | P&ID FOR CONDENSER AIR REMOVAL SYSTEM GR |
| `GMA` | 1 | 6 | 0 | 0 | n/a | 0.0% | P&ID FOR CHEMICAL WASTE WATER TRANSFER S |
| `QFA` | 1 | 10 | 0 | 0 | n/a | 0.0% | P&ID FOR COMPRESSED AIR SYSTEM |
