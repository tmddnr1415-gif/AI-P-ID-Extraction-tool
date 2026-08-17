# 밸브 규칙 프로젝트 종속 값 인벤토리 (스파이크 4)

`out/project_deps.md` 와 같은 기준입니다.

| 판정 | 의미 |
|---|---|
| `LEGEND` | Symbol & Legend(p2~p5)에서 유도 가능 → 코드 유지 |
| `PROJECT` | 도면/NOTES/Excel 양식에서 유도 → config |
| `UNKNOWN` | 출처 불명 → 조사 필요, 튜닝 금지 |

**집계: `LEGEND` 12건 / `PROJECT` 8건 / `UNKNOWN` 5건 (총 25건)**

판정 근거는 전부 실측입니다. "아마 그럴 것 같다"는 UNKNOWN 으로 넘겼습니다.

---

## LEGEND — 코드 유지 (12건)

| # | 항목 | 위치 | 근거 (실측) |
|---|---|---|---|
| VL1 | **나비넥타이 몸체 규칙** (교차 대각선 2 + 양끝 바) | `find_bodies` | 범례 p2 `LINE VALVES` GATE 행: 대각선 2개가 같은 bbox `(895.9,551.3,912.9,561.2)`, 양끝 세로바 `x=895.9`·`912.9`. 크기 17.0×9.9 |
| VL2 | **글로브 = 허리 중앙 원반** | `_waist_object` | 같은 표 GLOBE 행: 나비넥타이는 GATE 와 동일, 추가로 원 `(900.9,592.4,908.0,599.5)` 7.1×7.1, 중심이 몸체 중심과 **정확히 일치**. 7.1/9.9 = **0.72** |
| VL3 | **니들 = 허리의 좁은 쐐기** (종횡비로 원반과 구분) | `_wedge_at_waist`, `disc_aspect` 하한 0.70 | NEEDLE 행의 채움 `(903.3,830.5,905.6,837.6)` = 2.3×7.1, **종횡비 0.32**. 글로브 원반은 1.00. 0.70 은 두 실측값 사이 |
| VL4 | **다이어프램 = 몸체 위 열린 호** | `_arc_above` | DIAPHRAGM 행: 몸체 상단 `y0=926.1`, 그 위에 곡선 `(897.4,923.8,911.5,926.9)` — **2.3pt 돌출** |
| VL5 | **버터플라이 vs 볼 = 베인 틱** | `_vane_ticks` | BUTTERFLY 행: 원 6.1 + 짧은 사선 2개(각 길이 **3.0**), 중심 기준 정반대. BALL 행: 원 7.2, **틱 없음**. p26 실측도 동일(원 6.0, 틱 3.05×2) |
| VL6 | **체크 = 반쪽 나비넥타이** (대각선 1개) | `find_bodies` | CHECK 행에 대각선이 1개뿐 |
| VL7 | **채움 = 몸체 종류가 아니라 개폐 상태** | `Body.state`, `_triangles_filled` | 범례 p2 `VALVE OPERATION`: 빈 나비넥타이 = OPEN DURING NORMAL OPERATION, 검은 나비넥타이 = CLOSED (둘 다 `ALL VALVES EXCEPT BUTTERFLY`), 빈 원 / 검은 원 = 버터플라이 전용 OPEN / CLOSED. 검은 나비넥타이도 대각선 2개는 그대로 있음(`fs` 4장 + `s` 대각선 2) |
| VL8 | **양끝 바 간격 범위** | `bar_reach` 3.4 / `bar_min` 1.1 (반지름 배수) | BUTTERFLY 6.1 원에 바 ±8.5 → **2.79 반지름**, BALL 7.2 원에 바 ±8.5 → **2.36 반지름** |
| VL9 | **액추에이터 어휘** (원 `M` / 상자 `H` / 원 `E/H` / 상자 `S` / 돔·실린더 / `I/P` / 상자 `X` / T바) | `ACT_LETTERS` | 범례 p3 `VALVES ACTUATORS` 가 8종을 라벨과 함께 직접 그림 |
| VL10 | **액추에이터 울타리 크기 하한** | `act_box` 하한 9.0 | 범례 p3 모터·E/H 원 **14.2×14.2**, 유압/솔레노이드/X 상자 **14.2×34.0**. 글로브 허리 원반은 7.1 → 9.0 이 둘 사이 |
| VL11 | **액추에이터는 줄기로 몸체에 연결된다** | `_actuator_stem` | 범례 p3 의 8행 전부, p4 `VALVE BODY WITH ACTUATOR` 의 MOV 도 예외 없이 줄기를 그림 |
| VL12 | **자력식은 별도 그룹** (NONE ≠ SELF ACTING) | `deliverable_class` | 범례 p3 이 `SELF-ACTUATED DEVICES`(PSV/PRV/BPRV)를 고유 심볼로 따로 둠. 줄기에 아무것도 없는 것은 수동 밸브지 자력식이 아님 |

---

## PROJECT — config 이동 완료 (8건)

전부 `config/project_alnouf1.yaml` 의 `valves:` 블록으로 옮겼습니다.

| # | 항목 | config 키 | 근거 |
|---|---|---|---|
| V1 | **액추에이터 도달 거리** 90.0 | `valves.actuator_reach` | 범례가 아니라 도면 실측: p6·p30 은 줄기 26.9pt, p33 은 최대 80pt. 범례는 고정 거리 하나만 그리고 범위를 말하지 않음 |
| V2 | **줄기 축 이탈 허용** 12.0 | `valves.actuator_offaxis` | 위와 동일. 작도 관행 |
| V3 | **태그 버블 도달 거리** 190.0 | `valves.tag_reach` | p6 MOV 버블 실측. 지시선은 길이 제한이 없으므로 규칙이 아니라 관행 |
| V4 | **밸브 Excel 시트·열** (`3.0_Valve List`, NO=1, P&ID=2, TYPE=3, Q'ty=4, SYSTEM=5, DESC=12) | `valves.excel` | 발주처 양식. 계기 리스트(`2.0_Instrument List`)와 시트명도 열 순서도 다름 |
| V5 | **납품서 ↔ 몸체 계열** (CZI=BUTTERFLY, CZH=GATE/GLOBE/**BALL**) | `valves.deliverables` | 각 파일 헤더의 `DESCRIPTION` 줄. CZH 는 제목이 GATE & GLOBE 지만 볼 몸체 MOV 도 담고 있어 계열에 BALL 을 포함해야 함 |
| V6 | **`VALVE TYPE` 어휘** MOV / MOV_I / HOV / CV | `valves.valve_type_actuator` | 이 문자열들은 범례에 없음. 납품서 표기이고 몸체가 아니라 구동 방식 |
| V7 | **CV vs XV 태그 분리** | `valves.cv_tags`, `valves.xv_tags` | 태그 어휘 자체는 범례(p3 CONTROL DEVICE, p4 차단 태그)지만 **두 납품서로 가르는 기준**은 발주처 관행 |
| V8 | **스트로크 글자 서명** (M 4획 / H 3획 / X 2획) | `valves.stroked_letters` | **범례는 M·H·S·X 를 텍스트로 인쇄합니다.** 즉 범례만 봐서는 이 회사 CAD 스트로크 폰트가 글자를 어떻게 조립하는지 알 수 없습니다. 서명은 p26(H)·p33(M) 도면에서 읽었으므로 PROJECT |

---

## UNKNOWN — 조사 필요, 이번에 튜닝하지 않음 (5건)

| # | 항목 | 위치 | 왜 UNKNOWN 인가 |
|---|---|---|---|
| VU1 | **세그먼트 길이 상한** 60.0 | `seg_span` | 범례 최대 밸브 치수는 34.0(유압 실린더 상자). 60 은 여유값이고 유도 근거가 없음. 성능 필터라 결과에 영향은 없지만 근거는 없음 |
| VU2 | **바 커버리지 여유** 1.2 / **끝단 허용** 0.8 | `bar_cover`, `bar_axis_tol` | 1pt 미만의 작도 정밀도 여유. 범례에서 유도되지 않음 |
| VU3 | **허리 중심 허용 오차** 2.0 | `centre_tol` | 범례 글로브 원반은 중심 오차 **0.0**. 2.0 이 어디서 왔는지 근거 없음 |
| VU4 | **범례 실측값 주변 창 폭** (`body_short`, `body_ratio`, `waist_ratio`, `tick_span`, `tick_reach`) | `ValveLayout` | 창의 **중심값**은 전부 범례 실측(17.0×9.9, 0.72, 3.0 …)이지만 **폭**은 유도된 것이 아님. 다른 축척으로 그린 도면을 통과시키려는 의도지만 검증되지 않음 |
| VU5 | **닫힘 판정 면적 임계** 0.30 | `_triangles_filled` | 검은 나비넥타이의 `fs` 4장이 몸체 bbox 의 몇 %를 덮는지 범례에서 계산하지 않았음 |

**UNKNOWN 은 이번에도 손대지 않았습니다.** 계기 쪽 UNKNOWN 5건과 함께 Phase 3 조사
대상입니다.

---

## 승수 예외 1건 — 보류 유지 (NEEDS_REVIEW)

`D00P-10PGB10-M05-0004`(p38) `(PLANT COMMON)` 건은 그대로 둡니다. 귀속 판정에
필요한 설비 점선 박스 검출이 `brk_max_mark`(UNKNOWN) 튜닝을 요구하므로 건드리지
않았고, `out/qty_report.md` 의 NEEDS_REVIEW 로 남습니다. 영향 Q'ty 3 / 1120 = 0.3%.
