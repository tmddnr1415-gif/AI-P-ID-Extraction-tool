# 23회차 [D] — 상수 전수 조사

**코드를 한 줄도 고치지 않았다.  조사만 한다.**
재현: `python3 spike/constant_survey.py` (도면을 열지 않는다 · 소스와 결과 json 만 읽는다)

## 0. 한 눈에

| 갈래 | 뜻 | 개수 |
| --- | --- | ---: |
| **유도** | 그 도면에서 재서 정한다 | **AL NOUF1 23 · TC2 21** (도면틀 17~19 + 범례 5 + 승수표 1 중 실제로 잰 것) |
| **설정** | `config/project_*.yaml` 이 값을 준다 — **사람이 적은 값이다** | 잎 키 **210개** (22절) |
| **상수** | 코드에 박혀 있다 | dataclass 기본값 **71개 중 39개**가 config 로도 못 바꾼다 |

dataclass 71개 내역 — `detect_symbols.Layout` 27(설정 가능 16) ·
`detect_valves.ValveLayout` 24(설정 가능 4) · `extract_titleblocks.Layout` 20(설정 가능 12).

**★ "설정 가능" 은 "유도" 가 아니다.**  210개 잎 키 중 22회차 `_fit_layout` 이
그 도면에서 재서 덮는 것은 **15칸**(TC2 실측)뿐이고, 나머지는 사람이 적어 둔
AL NOUF1 실측값이다.  이 회차의 금지 사항이 가리키는 것이 바로 그 자리다 —
**`project_tc2.yaml` 에 손으로 적으면 하드코딩을 파일로 옮긴 것이다.**

## 1. 이미 피해가 확인된 것

각 항목: 위치 · 값 · 갈래 · 못 재면 어떻게 되나(**조용/시끄러움**) · 세 프로젝트 · 유도 가능성 · 표본이 늘면 좋아지는가

### ㉠ 개정 이력 표 기하 6칸

```
extract_titleblocks.py:114-119
hist_rule_x0_max 1975.0 · hist_rule_x1_min 2320.0 · hist_rule_y (1200,1390)
hist_rev_col (1971,1988) · hist_date_col (1992,2070) · hist_row_inset 1.2
```

| | |
| --- | --- |
| 갈래 | **설정**(config `title_block.*`) — 유도되지 않는다 |
| 못 재면 | **조용하다.**  이력 행 0줄 → REV `?` · 신뢰도 LOW.  분석은 성공으로 끝난다 |
| AL NOUF1 | 맞는다 (58/58 HIGH) |
| TC2 | **x 1975~2320 이 종이(가로 1191pt) 밖** → 0/60 |
| SADARA | 네 칸은 `project_sadara.yaml` 이 덮고 여섯은 AL NOUF1 값을 물려받는다 (21회차 [5]) |
| 유도 가능성 | **가능해 보인다** — 칸 자체는 `REV. DATE DESCRIPTION` 캡션으로 이미 찾는다(`CAPTIONS["history"]`). 그 캡션 아래의 가로 괘선을 세면 행이 나온다. 지금은 그 값을 쓰지 않고 상수를 쓴다 |
| 표본이 늘면 | **아니오.**  이건 표본 문제가 아니라 안 재는 문제다 |

### ㉡ 도면번호 형식

```
config/project_alnouf1.yaml:49
formats.drawing_no: '^[A-Z0-9]{4}-[A-Z0-9]{7}-[A-Z0-9]{3}-\d{4}$'
```

| | |
| --- | --- |
| 갈래 | **설정** |
| 못 맞으면 | **조용하다** (한 장도 못 읽을 때만 22회차 `TitleBlockUnreadable` 로 멈춘다).  그 장은 `page_kind=UNKNOWN` 이 되어 통째로 빠진다 |
| AL NOUF1 | 58/58 |
| TC2 | **56/60** — p25~p27 은 가운데가 6자(`D02J-31PGB0-M05-0001`), p28 은 칸에 번호가 없다 |
| SADARA | (하네스 결과 참조) |
| 유도 가능성 | **가능하다.**  도면번호 칸 안의 낱말에서 자릿수를 세면 된다 — 지금도 칸은 유도한다.  ⚠ 다만 "형식" 은 **문서마다 하나** 라는 가정이 필요하고 TC2 는 6자·7자가 섞인다 |
| 표본이 늘면 | **예.**  프로젝트가 늘수록 "이 업계가 쓰는 도면번호 모양" 의 분포가 쌓여 느슨한 공통형을 근거 있게 정할 수 있다 |

### ㉢ 승수표 파싱

```
projectconfig.py:183  HEADING = ("UNIT", "IDENTIFICATION", "NUMBERS")
projectconfig.py:184  _CODE_RE = ^\d{1,2}$
projectconfig.py:207  y_span = 260.0
projectconfig.py:250  if len(rows) < 3: continue
```

| | |
| --- | --- |
| 갈래 | **상수** 넷 |
| 못 찾으면 | **조용하다.**  `unit_multiplier_fallback`(00/10/11)으로 떨어지고 표에 없는 코드는 Q'ty 가 빈다 |
| AL NOUF1 | LEGEND 7코드 |
| TC2 | **CONFIG_FALLBACK.**  두 이유가 겹친다 — 도면이 머리말을 `UNIT IDENTIFICATION NUMERS` 로 **오타**냈고, 숫자 코드가 `00`·`31` **둘**뿐인데 3행을 요구한다.  유닛 `31` 23장이 전부 UNDEFINED → Q'ty 못 셈 262/607 |
| SADARA | 20회차 기록 — 82행 전량 `qty=None` (표에 `00` 만 있는데 행은 `10LBA10` 계열) |
| 유도 가능성 | 머리말은 **철자 허용치**(편집거리 1)로, 행 수 요구는 **2행 이상**으로 낮출 수 있다.  둘 다 도면 세 개가 근거를 준다 |
| 표본이 늘면 | **예.**  "이 표가 실제로 어떻게 인쇄되는가" 의 사례가 쌓인다 |

### ㉣ 액추에이터 규칙

```
legend_rules.py:346   if not (8.0 <= min(b.width, b.height) <= 40.0)   ← 범례에서 액추에이터 후보 크기
legend_rules.py:338   column = (head.x0 - 260, head.x0 + 40)
legend_rules.py:365   -0.3 <= gap <= 4.0 · (y1-y0) > 2.0 · abs(x-cx) <= 2.0
legend_rules.py:371   if len(stems) < 2 → CONFIG_FALLBACK
config valves.legend_fallback.actuator_stem  {gap 0.0, offaxis 0.03, length 19.86, centre_to_body 26.97}
config valves.actuator_reach 90.0 · actuator_offaxis 12.0 · tag_reach 190.0
```

| | |
| --- | --- |
| 갈래 | **상수**(범례 판독) + **설정**(폴백 값) |
| 못 재면 | **조용하다.**  AL NOUF1 값으로 떨어지고, 그 값이 안 맞으면 액추에이터가 0개가 되며 **밸브 탭이 통째로 빈다** |
| AL NOUF1 | LEGEND (폴백과 **같은 숫자**라 값으로는 구분되지 않는다 — 15회차) |
| TC2 | **CONFIG_FALLBACK.**  범례 열 안 원이 지름 **7.1pt** 로 크기 띠 8.0 아래이고, 더 근본적으로 **TC2 범례는 액추에이터를 밸브 몸체 없이 그려 스템 자체가 없다**.  결과 MOV 0행(도면 태그 58개) |
| SADARA | (하네스 결과 참조) |
| 유도 가능성 | **범례에서는 불가능하다 — 잴 대상이 도면에 없다.**  대안은 도면 본문에서 재는 것(실측: 원 지름 7.08 · 원↔몸체 간격 7.48 · 중심↔중심 13.52) 인데, 그것은 "액추에이터를 이미 알아본 뒤" 재는 값이라 순환이다.  **이 회차가 찾은 범용성의 실제 한계다** |
| 표본이 늘면 | **부분적으로.**  "액추에이터 원은 버블보다 작다" 같은 **비례 관계**를 여러 문서에서 확인하면 절대 치수 없이 규칙을 세울 수 있다 — 다만 그건 새 규칙이고 이번 회차의 조사 범위 밖이다 |

### ㉤ 체인 파선 상한 — 조용한 실패 **후보**

```
config broken_line.brk_max_mark 28.3   (16회차에 AL NOUF1 에서 유도)
```

`_fit_layout` 은 이 값을 그 도면에서 재려 하지만 두 문서 모두 `UNAVAILABLE` 로
채택하지 않는다 (AL NOUF1 18.6 · **TC2 7.0**).  그래서 **TC2 는 28.3 이라는 AL NOUF1
숫자로 판정한다** — 절반 축척 문서에 두 배 값이다.  피해가 확인되지는 않았다
(TC2 는 별표 사전이 비어 벤더 축 자체가 서지 않는다).  **다음 회차가 확인할 자리다.**

### ㉥ 벤더 별표 크기

```
config vendor_marks.glyph_sizes [[4.0,4.0],[5.2,5.2]]   (AL NOUF1 유도값)
```

TC2 는 `_fit_layout` 이 **`[]` 로 잰다** — 그 문서에는 별표 크기 사전이 없다.
`vendor_marks.above 25.0` · `side 10.0` · `x_slack 6.0` 은 전부 AL NOUF1 실측(19회차)이고
TC2 에서 다시 재지 않는다.  TC2 는 SCOPE 가 SCT 602 · VENDOR 5 다.

## 2. 아직 피해가 확인되지 않은 상수 — 목록

**`detect_symbols.Layout` 27개 중 설정으로도 못 바꾸는 11개**
`cap_span (7.0,50.0)` · `cap_ratio (1.6,2.4)` · `brk_corner_tol 3.0` · `side_tol 0.8` ·
`side_slack 1.5` · `anchor_slack 3.0` · `box_edge_cover` · `box_mark_margin` ·
`brk_max_gap 6.0` · `brk_bridge 26.0` · `brk_min_marks 6` · `brk_min_span 40.0`

이 중 **버블 검출(`cap_span`·`cap_ratio`)은 절반 축척에서도 통했다** — 크기가 아니라
"두 캡 + 잇는 직선" 이라는 **모양**을 보기 때문이다 (TC2 버블 34×11).
**이것이 범용 규칙의 본보기다.**  나머지는 전부 pt 단위 절대 치수다.

**`detect_valves.ValveLayout` 24개 중 설정으로도 못 바꾸는 20개**
`seg_span` · `body_short (5.0,30.0)` · `body_ratio` · `bar_axis_tol` · `bar_cover` ·
`centre_tol` · `waist_ratio` · `disc_aspect` · `arc_above 6.0` · `tick_span` ·
`tick_reach` · `bar_reach` · `bar_min` · `stem_slack` · `act_box (9.0,34.0)` 등.
**TC2 에서 몸체는 389개가 잡혔다** — `body_ratio`·`waist_ratio` 처럼 **비율**로 된 것이
축척을 안 타기 때문이다.  걸린 것은 `act_box` 같은 **절대 치수**다.

**`extract_titleblocks.Layout` 20개 중 8개는 픽셀 단위 판독 상수**
`zoom 24.0` · `grid (28,20)` · `ink_frac 0.75` · `blank_above 245` · `min_ink_px 20` ·
`char_gap_px 6` · `ratio_high 2.5` · `ratio_medium 1.5`.
`zoom` 이 렌더 배율이라 **종이가 절반이면 글자도 절반 픽셀**이 된다 — TC2 의
REV 신뢰도가 전부 LOW 인 데에 이 축도 겹쳐 있을 수 있다 (미확인).

## 3. 이 조사가 말하는 것

1. **비율·모양으로 된 규칙은 절반 축척을 넘었다** (버블 · 몸체 · 회전 정규화).
   **절대 pt 로 된 규칙은 전부 걸렸다.**  이것이 이 도구의 범용성 경계다.
2. **조용한 실패가 다섯 자리에서 확인됐다** — 이력 표 · 도면번호 형식 · 승수표 ·
   액추에이터 · 별표 크기.  전부 "폴백" 이고 전부 **분석은 성공으로 끝난다**.
3. **유도로 바꿀 수 있는 것과 없는 것이 갈린다.**  이력 표·도면번호·승수표는
   잴 대상이 도면에 **있다**.  액추에이터는 TC2 범례에 **없다** — 그것이 실제 한계다.
