# 스파이크 3 — Q'ty 승수 검증

승수 출처: **LEGEND** — legend p5: GROUPx2, PLANTx1, UNITx4


| unit_code | 승수 | 스코프 | 범례 표기 |
|---|---|---|---|
| `00` | ×1 | PLANT | POWER PLANT COMMON |
| `10` | ×2 | GROUP | FIRST GROUP COMMON (INCL. FIRST GROUP STG) |
| `11` | ×4 | UNIT | FIRST GROUP #1 GTG / HRSG |
| `12` | ×4 | UNIT | FIRST GROUP #2 GTG / HRSG |
| `20` | ×2 | GROUP | SECOND GROUP COMMON (INCL. SECOND GROUP STG) |
| `21` | ×4 | UNIT | SECOND GROUP #1 GTG / HRSG |
| `22` | ×4 | UNIT | SECOND GROUP #2 GTG / HRSG |

승수는 config 상수가 아니라 **범례 p5 의 UNIT IDENTIFICATION NUMBERS 표를 파싱해 유도**합니다. 표에 그룹이 2개·그룹당 유닛이 2개로 적혀 있어 PLANT ×1 / GROUP ×2 / UNIT ×4 가 그대로 나옵니다. 그룹 구성이 다른 프로젝트에서는 같은 코드가 다른 승수를 내놓습니다.


## 정확도

| 집합 | 페이지 | 산정 Q'ty | Excel Q'ty | 차이 |
|---|---|---|---|---|
| 주석 없는 페이지 (기준) | 24 | 834 | 765 | +69 |
| 개정 주석 있는 페이지 (별도 계상) | 11 | 329 | 311 | +18 |
| MATCHED 전체 | 35 | 1163 | 1076 | +87 |

## 승수별

| 승수 | 페이지 | 심볼 | 산정 | Excel | 차이 |
|---|---|---|---|---|---|
| ×1 | 7 | 94 | 94 | 59 | +35 |
| ×2 | 15 | 260 | 520 | 482 | +38 |
| ×4 | 2 | 55 | 220 | 224 | -4 |

## 계통별 (오차 큰 순)

| 계통 | 페이지 | 산정 | Excel | 차이 |
|---|---|---|---|---|
| `GHC` | 1 | 34 | 16 | +18 |
| `PAC` | 1 | 48 | 32 | +16 |
| `LBA` | 2 | 62 | 48 | +14 |
| `EGD` | 1 | 35 | 23 | +12 |
| `PGB` | 6 | 306 | 299 | +7 |
| `LAC` | 1 | 88 | 92 | -4 |
| `GKB` | 1 | 10 | 7 | +3 |
| `PAB` | 1 | 6 | 4 | +2 |
| `QFB` | 1 | 2 | 1 | +1 |
| `MAJ` | 1 | 16 | 16 | +0 |
| `LCM` | 1 | 18 | 18 | +0 |
| `LBG` | 1 | 26 | 26 | +0 |
| `LBC` | 2 | 42 | 42 | +0 |
| `LAB` | 1 | 132 | 132 | +0 |
| `EKG` | 3 | 9 | 9 | +0 |

## NEEDS_REVIEW

**총 1건** (SCOPE_OVERRIDE_UNRESOLVED 1)

| 종류 | 페이지 | 도면번호 | unit_code | 수량 | 사유 |
|---|---|---|---|---|---|
| `SCOPE_OVERRIDE_UNRESOLVED` | p38 | `D00P-10PGB10-M05-0004` | `10` | 시트 승수 유지 | scope keyword ['PLANT COMMON'] found on this drawing: some items take a different multiplier from the sheet's x2, but attributing an item to the scoped equipment needs line tracing (design.md §7, Phase 2). Quantity left at the sheet multiplier. |

`MULTIPLIER_UNDEFINED` — unit_code 가 범례 표에 없는 경우입니다. 이번 문서에서는 **0건**(등장하는 코드가 전부 범례에 있음). 정의에 없는 코드(예: `30`)가 나오면 수량을 **비우고** 사유와 함께 보냅니다.

`SCOPE_OVERRIDE_UNRESOLVED` — 도면 안에 승수 예외 키워드가 있지만 어느 항목이 그 설비에 속하는지 판정하지 못한 경우입니다. 설비 점선 박스 검출에 `brk_max_mark`(UNKNOWN 항목) 튜닝이 필요하므로 **건드리지 않고** 시트 승수를 유지한 채 검토로 보냅니다.


## 같은 도면 안의 승수 예외

`qty_scope_overrides` 키워드가 발견된 페이지: **1건**

- p38 `D00P-10PGB10-M05-0004` — 키워드 ['PLANT COMMON'], 산정 48 vs Excel 45

### `(PLANT COMMON)` 가설 — **검증됨, 다만 적용은 보류**

`D00P-10PGB10-M05-0004`(p38)에서 확인했습니다.

- 도면에 `AUXILIARY BOILER COOLER` 라벨이 있고 **바로 아래 줄에 `(PLANT COMMON)`**
  이 붙어 있습니다 (좌표 `(327.6, 814.9)`).
- Excel 에서 이 도면의 Q'ty=1 인 3행은 전부 이 설비 것입니다 —
  `AUXILIARY BOILER COOLER CCW SUPPLY PRESSURE`(PI),
  `... CCW RETURN TEMPERATURE`(TI), `... CCW RETURN PRESSURE`(PI).
  같은 도면의 나머지 21행은 Q'ty=2 입니다.
- 도면을 렌더링해 확인한 결과 해당 설비의 계기는 정확히 **PI 2 + TI 1** 이고,
  각각 `(243.5, 473.4)` `(410.7, 1135.4)` `(410.5, 1184.4)` 에 있습니다.

**가설은 맞습니다.** 그런데 "어느 계기가 이 설비 소속인가"를 판정하려면 설비를
지나는 수직 배관을 따라가야 합니다. 실제로:

- 설비 점선 박스는 대시가 길어 현재 broken-line 검출기에 안 잡힙니다
  (`brk_max_mark` 는 UNKNOWN 항목이라 이번에 튜닝하지 않았습니다).
- 라벨 x 범위로 묶으면 옆 설비의 `(LUBE OIL` 텍스트가 섞여 들어와 엉뚱한 계기가
  포함되고 정작 `(243.5, …)` 는 빠집니다.

그래서 **승수 강제 적용을 하지 않았습니다.** 설계안 §8.3(불확실하면 값을 비우고
검토로 보낸다)에 따라 키워드 발견 사실만 기록합니다. 이 예외가 지표에 주는 영향은
3행 × (2−1) = **Q'ty 3 과다**로, 전체 대비 0.3% 수준입니다.
올바른 귀속은 §7 라인 추적(Phase 2)이 들어와야 가능합니다.


## Note 문구 교차검증

NOTES 에 열거된 GROUP#/UNIT# 개수를 세어 범례 유도 승수와 대조했습니다 (문장 해석 없이 **열거 개수만** 셉니다). 이 도면들의 Note 는 `THIS P&ID IS FOR GROUP#10, ... IDENTICAL FOR GROUP#20` 처럼 **자기 그룹까지 포함해** 열거하므로 열거 개수가 곧 승수입니다.

열거가 있는 페이지 16건 중 **16건 일치**, 0건 불일치.


## 개정 주석이 있는 페이지 (별도 계상)

`out/revision_gap.md` 의 도면들입니다. Excel 이 도면 개정을 반영하지 않았으므로 이 페이지의 Q'ty 차이는 검출기 오차로 볼 수 없습니다.

| 페이지 | 도면번호 | 산정 | Excel | 차이 |
|---|---|---|---|---|
| p10 | `D00P-10MAN10-M05-0001` | 64 | 64 | +0 |
| p11 | `D00P-10MAN10-M05-0002` | 64 | 64 | +0 |
| p16 | `D00P-10LCA10-M05-0001` | 56 | 58 | -2 |
| p17 | `D00P-10LCA10-M05-0002` | 20 | 20 | +0 |
| p26 | `D00P-00PAB10-M05-0001` | 8 | 5 | +3 |
| p27 | `D00P-00PAB10-M05-0002` | 8 | 5 | +3 |
| p31 | `D00P-10PCB10-M05-0001` | 30 | 30 | +0 |
| p32 | `D00P-00EGD00-M05-0001` | 16 | 9 | +7 |
| p35 | `D00P-10PGB10-M05-0001` | 46 | 38 | +8 |
| p44 | `D00P-00SCB10-M05-0001` | 0 | 1 | -1 |
| p49 | `D00P-00GHB10-M05-0001` | 17 | 17 | +0 |
