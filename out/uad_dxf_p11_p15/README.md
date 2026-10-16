# UAD DXF p11~p15 — 식별 결과 화면 (측정 전용 · 엔진 0줄)

55회차 결과(`out/round55/UAD_DXF.json` · 449행 · 지문 `003078d7`)를 **그대로 열어**
브라우저로 찍었습니다 — 재분석하지 않았고 렌더 함수를 직접 부르지 않았습니다.
그림 20장 · 한 장 묶음 `out/uad_dxf_p11_p15.pdf`.

| 장 | 도면번호 | 등급 | 행 | 상자 | 범례 칸 합 | 그리드 행 | 태그 붙은 행 | 속성/블록글자/기하 | PDF 행 |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 11 | 1A5J-00EKD00-M05-0001 | 1급 | 26 | 26 | 26 | 26 | 26 | 22 / 0 / 4 | 0 |
| 12 | 1A5J-00EKD00-M05-0002 | 1급 | 17 | 17 | 17 | 17 | 17 | 14 / 3 / 0 | 0 |
| 13 | 1A5J-00EKD00-M05-0003 | 1급 | 26 | 26 | 26 | 26 | 26 | 23 / 2 / 1 | 1 |
| 14 | 1A5J-00EKD00-M05-0004 | 1급 | 28 | 28 | 28 | 28 | 28 | 28 / 0 / 0 | 0 |
| 15 | 1A5J-00EKD00-M05-0005 | 기하 | 8 | 8 | 8 | 8 | 2 | 2 / 2 / 4 | 0 |

다섯 장 합 **105행**입니다.  같은 다섯 장을 PDF 로 읽으면 **1행** 입니다 (45회차 저장 결과) — 그 다섯 장은 **글자가 전부 획(SHX)** 이라 PDF 경로가 타이틀블록조차 못 읽었고, 45회차에 사람이 도면번호를 적어 준 뒤에도 계기 행이 서지 않았습니다.  DXF 는 같은 글자를 속성으로 들고 있어 읽힙니다.
**33회차 등식** (범례 칸 합 = 상자 수 = 행 수 = 그리드 행 수) 어긋난 장: **0**.

## 그림 파일

| 파일 | 무엇 |
| --- | --- |
| `p<n>_1_raw.png` | ① 도면만 (오버레이 칸 전부 끔 · 맞춤) |
| `p<n>_2_overlay.png` | ② 식별 오버레이 + 범례 (맞춤) |
| `p<n>_2b_overlay_zoom.png` | ②b 계기가 가장 몰린 구역 (확대 5.1배) |
| `p<n>_3_grid.png` | ③ 그 장 행 전부 (검색창에 도면번호) |
| `p<n>_4_pdf_overlay.png` | **찍지 못했습니다** — 이 작업 환경에 UAD **PDF 가 없습니다** (`data/` 에 `pid_total.pdf` · `TC2_260821.pdf` · `uad_dxf.zip` 뿐이고 `spike/projects_3p.json` 이 가리키는 `data/UAD_binding.pdf` 도 없습니다). 아래 표의 `PDF 행` 열은 45회차에 저장된 결과(`out/round45/UAD_after.json` · 301행)에서 셌습니다. |

확대 구역은 고르지 않고 **셌습니다** — 그 장 검출 상자의 중심으로 170pt 정사각 창을 훑어 가장 많이 든 자리를 집습니다 (`spike/dxf_shots_p11_p15.py` 의 `dense_window`). 확대율은 다섯 장 모두 맞춤 0.34 → 1.72 (5.1배)입니다.

## 장별 내역

**p11** · 1A5J-00EKD00-M05-0001 · 등급 1급 · 26행

- TYPE: PI 8, PDIA 3, PDIT 3, (빈칸) 3, LIA 2, FSA 2, FS 1, PIA 1, PIT 1, LIT 1, GATE 1
- 판독 경로: 속성 22 · 블록 안 글자 0 · 기하 4
- 검토 사유: MULTIPLIER_FROM_CONFIG 26, DXF_GEOMETRY_FALLBACK 4, TAGGED_VALVE_NO_ACTUATOR 4
- 미판정 심볼 16건 — 속성 TYPE 이 이 문서 ISA 표로 풀리지 않음 1, 범례 장에 없는 블록 15 · `PIP BLIND FLANGE` 3, `Ball Valve (Close)` 3, `PIP FLANGED NOZZLE` 3, `INTERLOCK-1` 3, `RO` 1

**p12** · 1A5J-00EKD00-M05-0002 · 등급 1급 · 17행

- TYPE: PI 3, FE 2, LIA 2, FIA 2, TIA 2, PDIA 2, (빈칸) 2, PIA 1, FIT 1
- 판독 경로: 속성 14 · 블록 안 글자 3 · 기하 0
- 검토 사유: MULTIPLIER_FROM_CONFIG 17, TAGGED_VALVE_NO_ACTUATOR 2
- 미판정 심볼 20건 — 속성 TYPE 이 이 문서 ISA 표로 풀리지 않음 4, 범례 장에 없는 블록 16 · `PIP FRONT FACING NOZZLE` 3, `PIP FLANGED NOZZLE` 3, `PIP BLIND FLANGE` 3, `Ball Valve (Close)` 3, `INTERLOCK-1` 2

**p13** · 1A5J-00EKD00-M05-0003 · 등급 1급 · 26행

- TYPE: LIT 8, PI 6, (빈칸) 5, LIA 4, PDIA 1, PICA 1, TIA 1
- 판독 경로: 속성 23 · 블록 안 글자 2 · 기하 1
- 검토 사유: MULTIPLIER_FROM_CONFIG 26, TAGGED_VALVE_NO_ACTUATOR 5, DXF_GEOMETRY_FALLBACK 1
- 미판정 심볼 11건 — 범례 장에 없는 블록 11 · `Ball Valve (Close)` 3, `INTERLOCK-1` 3, `PIP FLANGED NOZZLE` 3, `PIP BLIND FLANGE` 2

**p14** · 1A5J-00EKD00-M05-0004 · 등급 1급 · 28행

- TYPE: TIT 8, PDIT 4, TICA 4, PDIA 4, GATE 4, (빈칸) 4
- 판독 경로: 속성 28 · 블록 안 글자 0 · 기하 0
- 검토 사유: MULTIPLIER_FROM_CONFIG 28, TAGGED_VALVE_NO_ACTUATOR 4
- 미판정 심볼 10건 — 속성 TYPE 이 이 문서 ISA 표로 풀리지 않음 4, 범례 장에 없는 블록 6 · `RO` 4, `Ball Valve (Close)` 3, `PIP BLIND FLANGE` 3

**p15** · 1A5J-00EKD00-M05-0005 · 등급 기하 · 8행

- TYPE: TP 4, TIT 1, PIT 1, TIA 1, PIA 1
- 판독 경로: 속성 2 · 블록 안 글자 2 · 기하 4
- 검토 사유: MULTIPLIER_FROM_CONFIG 8, DXF_GEOMETRY_FALLBACK 4
- 미판정 심볼 8건 — 범례 장에 없는 블록 8 · `STREAM NUM` 3, `PIP BLIND FLANGE` 3, `REDUCER01` 1, `Ball Valve (Close)` 1

## 요구 20종 — 이 다섯 장에서

| 종류 | 행 | 종류 | 행 | 종류 | 행 | 종류 | 행 |
| --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| PIT | 2 | TIT | 9 | TI | 0 | PI | 17 |
| TG | 0 | PG | 0 | FE | 2 | FIT | 1 |
| SG | 0 | LIT | 9 | LS | 0 | MOV | 0 |
| XV | 0 | PCV | 0 | PV | 0 | LV | 0 |
| TV | 0 | FV | 0 | AIT | 0 | TW | 0 |

`TG`·`PG`·`SG`·`PV`·`LV`·`TV`·`FV` 는 51회차가 네 도면 전수로 **0건**임을 확인한 것들이고, 이 다섯 장에도 그 낱말이 인쇄돼 있지 않습니다.  `MOV`·`XV`·`PCV`·`AIT`·`TW` 도 이 다섯 장에는 없습니다 (UAD 다른 장에는 있습니다 — 55회차 20종 표).

## 빠진 것 — 목록만 (이 자리에서 고치지 않습니다)

| 무엇 | 장 · 건 | 왜 | 판단 |
| --- | --- | --- | --- |
| `RO` (제한 오리피스) | p11 1 · p14 4 | 속성 TYPE 이 `RO` 인데 **이 문서 ISA 표가 `R`·`O` 를 정의하지 않습니다** | 도면이 말하지 않는 것이라 지어내지 않았습니다 (51회차 `ZSO` 와 같은 자리).  PDF 경로는 이 문서에서 `RO` 3행을 냅니다 — 어느 쪽이 맞는지는 **실무 판단** |
| `INST_LOCAL MOUNTED` 블록 4개 | p12 4 | TYPE 자리에 **태그 문자열**(`00EGD21CP501` …)이 들어 있어 ISA 로 안 풀립니다 — 그 블록에서 속성 역할이 갈리지 않았습니다 | 55회차 `attribute_roles` 의 한계.  **다음 회차 후보** |
| `Ball Valve (Close)` 13 · `INTERLOCK-1` 8 | 다섯 장 | 범례 장에 없는 블록 | 밸브·인터록 심볼이고 범례가 뜻을 정하지 않았습니다 — 등록 화면 몫 |
| `PIP BLIND FLANGE` 14 · `PIP FLANGED NOZZLE` 9 · `PIP FRONT FACING NOZZLE` 3 · `REDUCER01` · `STREAM NUM` 3 | 다섯 장 | 범례 장에 없는 블록 | 배관 부속·흐름 번호라 **행이 아닌 것이 맞습니다** |
| 태그는 있는데 TYPE 이 빈 행 14 | p11 3 · p12 2 · p13 5 · p14 4 | 밸브 태그(`…AA191`)인데 몸체·액추에이터를 못 읽었습니다 | 53회차 [B-3] 그대로 — 탭을 지어내지 않고 검토로 올립니다 (`TAGGED_VALVE_NO_ACTUATOR`) |
| 모든 행에 `MULTIPLIER_FROM_CONFIG` | 105/105 | 이 DXF 에 승수표도 유닛 노트도 없습니다 | 30회차 [13] 과 같습니다 — 31회차 사람 지정 자리가 답합니다 |

