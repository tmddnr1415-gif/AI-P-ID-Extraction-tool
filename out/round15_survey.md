# 15회차 [B] — 실태 조사 6문항

작성 2026-09-06 · HEAD `4783db8` 기준 · 대상 `data/pid_total.pdf` (58장)
전량 분석 1회 · 유도 단계 계측 1회 · 범례 4장을 뺀 PDF 1회 (전부 이 기계 실측)

> 고치기 전에 지금 무엇이 어떻게 도는지 먼저 답한다.  13회차 [B] 에서 조사가
> 범위를 줄였던 것과 같은 자리다.

---

## 0. 기준선 재현 ([A])

전량 분석 1회로 **전 항목이 문서값과 일치**했다.

| 항목 | 문서 | 실측 |
| --- | --- | --- |
| `fingerprint` | 69ad281f | **69ad281f** |
| 행 수 | 1029 | **1029** (FIELD 885 · MOV 76 · PNEUMATIC 45 · BFV 23) |
| Q'ty | 1911 | **1911** |
| 등급 | 704 / 48 / 51 / 22 · SKIP 204 | **같음** |
| 글리프 | H4 / M32 | **같음** |
| 판정축 | ⓪218 ①127 ②35 ②a9 ②b84 ③32 ④524 | **같음** |
| 문형 출처 | 234 / 39 / 756 | **같음** |

**드리프트 1건** — 분석 시간이 문서의 `약 353초` 가 아니라 **406.2초**였다.
이것은 벽시계이고 지문에 들어가지 않는다(`timings` 는 의도적으로 제외).  같은
기계에서 잰 값이 회차마다 다르므로 회귀 항목이 아니라 **관측치**로 적는다.

---

## 1. 범례에서 유도하는 값이 정확히 무엇인가

`pipeline.analyse` 의 `legend_rules` · `unit_multipliers` 두 단계가 **열 가지**를
유도한다.  그중 **범례 장을 읽는 것은 여덟**이고, 둘은 아니다.

### (가) 범례 장에서 나오는 여덟

| # | 이름 | 어느 장 · 어느 텍스트 | 값 (AL NOUF1 실측) |
| --- | --- | --- | --- |
| 1 | `butterfly` | p2 `LINE VALVES` 의 `BUTTERFLY`/`BALL` 행 | tick_length 3.0 · tick_reach_radii 1.498 · bar_reach_radii 2.822 · bar_min_radii 2.378 · circle_diameter 6.06 |
| 2 | `actuator_stem` | p3 `VALVES ACTUATORS` 열 | stem_gap 0.0 · stem_offaxis 0.03 · stem_length 19.86 · centre_to_body 26.97 |
| 3 | `pneumatic` | p3 `PNEUMATIC` 행 (DIAPHRAGM 돔 · CYLINDER) | dome_flat 14.22 · dome_depth 7.11 · dome_aspect 0.5 · cylinder_side 14.16 · cylinder_aspect 1.003 · cylinder_divider 0.5 |
| 4 | `line_styles` | `ELECTRIC SIGNAL` 행의 파선 | dash_len 7.2 · dash_gap 3.6 · **min_run 16.968** · join_slack 0.8 |
| 5 | `isa_table` | p3 `FIRST LETTER` / `SUCCEEDING LETTERS` 표 | 첫 문자 **25** · 후속 문자 13 |
| 6 | `equipment_symbols` | p2 `EQUIPMENT` 표 | **17행** (`HORIZONTAL CENTRIFUGAL PUMP` · `PLATE TYPE HEAT EXCHANGER` …) |
| 7 | `component_words` | p≤5 가 인쇄한 중간 부품 낱말 | **3** (`STRAINER` · `FILTER` · `TRAP`) — 전부 출처 `LEGEND` |
| 8 | `unit_multipliers` | p5 `UNIT IDENTIFICATION NUMBERS` | `00:1 · 10:2 · 11:4 · 12:4 · 20:2 · 21:4 · 22:4` (PLANTx1 · GROUPx2 · UNITx4) |

`equipment_vocab` (61낱말 · LEGEND 47 + CLIENT 14) 은 6번의 **순수 함수**이고
config 의 `equipment_words` 를 더한 것이므로 별도 항목으로 세지 않는다.

### (나) 같은 단계에 있지만 범례에서 나오지 않는 둘

| 이름 | 어디서 나오나 | 값 |
| --- | --- | --- |
| `connector_reach` | **도면 218개 커넥터**의 거리 분포 90분위. 함수 주석이 "범례는 off-page 커넥터를 아예 그리지 않는다" 고 못박고 있다 | `source: MEASURED` · 70.2pt |
| `pattern` · `position_words` | **config** (`description.*`). 페이지를 읽지 않는다 | — |

### (다) §11 의 "config 19건" 은 범례가 아니라 **도면 58장**이다

`applied_rules.layout` 의 항목 수가 정확히 **19**이고, 그것이 그 숫자다.
범례가 아니라 **용지와 타이틀블록 칸**에서 잰다 (17 DERIVED + 2 UNAVAILABLE).

```
sheet.width_pt · sheet.height_pt · regions.drawing_area · regions.notes_area ·
regions.notes_text_x_max · title_block.{project_name_region, project_name_min_height,
title_region, title_min_height, dwg_no_region, rev_box, sheet_box} ·
broken_line.{brk_max_mark, brk_max_gap}(UNAVAILABLE) · text.dedup_exact_duplicates ·
vendor_marks.glyph_sizes · review_markup.{script_ranges, requires_fill} ·
sct_scope.box_from_both_edges
```

**이 19건은 프로필에 담으면 안 된다.**  다음 개정본의 도면이 답해야 할 값이고,
옛 값으로 굳히면 용지가 바뀐 개정본에서 조용히 틀린다.

---

## 2. 유도 시점과 소요 시간

파이프라인 순서: `open_pdf → layout → titleblock_glyphs → titleblocks →
legend_rules → unit_multipliers → (장별 검출) → …`

**전량 분석 1회 (406.2초)의 단계별**

| 단계 | 초 | 비중 |
| --- | ---: | ---: |
| layout (선분 캐시 + 용지 측정) | 232.11 | 57.1% |
| valves.actuators | 65.80 | 16.2% |
| titleblock_glyphs | 20.60 | 5.1% |
| titleblocks | 20.38 | 5.0% |
| instruments | 15.64 | 3.9% |
| **legend_rules** | **6.10** | **1.5%** |
| **unit_multipliers** | **0.00** | **0.0%** |

**`legend_rules` 6.10초 안쪽을 다시 쪼갠 실측** (같은 문서 · 별도 계측 1회)

| 호출 | 초 | 범례 장을 읽나 |
| --- | ---: | --- |
| `dv.derive_layout` (butterfly + actuator_stem + pneumatic) | **1.399** | ○ |
| `pipe_graph.derive_line_styles` | 0.272 | ○ |
| `isa_table.derive` | 0.003 | ○ |
| `dequip.derive_symbols` | 0.088 | ○ |
| `dequip.derive_component_words` | 0.003 | ○(+도면) |
| `projectconfig.derive_unit_multipliers` | 0.001 | ○ |
| **범례 몫 합계** | **≈1.77** | |
| `pipe_graph.derive_connector_reach` | **3.727** | ✕ (도면 218개) |
| `desc.derive_pattern` · `dcand.derive_position_words` · `derive_vocabulary` | 0.000 | ✕ (config) |

**⚠ 그러므로 재사용으로 줄어드는 시간은 최대 1.77초, 406초의 0.4% 다.**
`legend_rules` 6.10초의 **61%(3.73초)는 커넥터 거리이고 그것은 범례 값이 아니라
개정본의 도면이 답해야 하는 값**이라 재사용 대상이 아니다.
**이 회차의 성과에 속도를 적지 않는다.**

다른 단계도 범례에 의존하는가 — **아니다.**  `valves.glyph_library`(0.01초)는
밸브 검출 결과에서 만들고, `titleblock_glyphs`(20.60초)는 타이틀블록 글자에서
만든다.  범례 유도의 산물(`dv.LAYOUT` · `pipe_style.values` · `isa` ·
`equip_symbols`)을 **쓰는** 단계는 많지만, 범례 장을 다시 읽는 곳은 없다.

---

## 3. 유도 결과는 어디에 있는가

| 층 | 무엇이 | 분석이 끝나면 |
| --- | --- | --- |
| 메모리 | `dv.LAYOUT` · `pipe_style` · `isa` · `equip_symbols` · `equip_vocab` · `component_words` · `mult` | **사라진다** |
| `job.engine_json` (DB) | `legend`(5키: butterfly/actuator_stem/pneumatic/line_styles/connector_reach — `source`·`note`·`values` 만) · `multipliers`(`source`·`note`·`table` 만) · `glyphs` · `applied_rules.layout` · `description_build.isa_table` | 남는다 |
| 파일 | **없다** | — |

**빠져 있는 것이 있다.** `db.store_result` 가 `engine_json` 에 담는 키는 열 개로
고정돼 있고, 그 목록에 **`equipment` 가 없다.**  즉 범례 기기 표 17행과 어휘
61낱말은 **어디에도 남지 않는다** — 분석이 끝나면 다시 볼 수 없다.
`multipliers` 도 `table` 만 남고 `scopes`·`labels`(범례가 인쇄한 유닛 이름)는
버려진다.  `Derived.evidence`(어느 쪽 어느 좌표에서 쟀는지)도 전부 버려진다.

프로젝트 폴더(`app/_data/projects/{이름}/`)에는 `project.json` ·
`id_registry.json` · `axis_overrides.json` 이 있고 **범례 관련 파일은 없다.**

---

## 4. ★ 범례 장을 못 찾으면 어떻게 되는가 — 실제로 돌려 봤다

`data/pid_total.pdf` 에서 범례 4장(p2·p3·p4·p5)만 뺀 **54쪽 PDF** 를 만들어
`pipeline.analyse` 를 그대로 돌렸다.

### 결과: **분석이 예외로 죽는다.**

```
File "app/engine/pipe_graph.py", line 177, in derive_connector_reach
    if b - a < style["min_run"]:
KeyError: 'min_run'
```

원인은 두 단계다.

1. `derive_line_styles` 가 `ELECTRIC SIGNAL` 행을 못 찾아 `_fallback` 으로 가는데,
   `config` 의 `valves.legend_fallback` 에는 `butterfly`·`actuator_stem`·`pneumatic`
   **셋만** 있고 `line_styles` 가 **없다.**  그래서
   `source: NEEDS_REVIEW · values: {}` 가 된다 — 여기까지는 설계대로다
   ("근거가 없으면 아무 것도 가정하지 않는다").
2. 그런데 그 빈 값이 그대로 다음 호출로 넘어가고, `derive_connector_reach` 는
   `style["min_run"]` 을 **있다고 가정**한다.  → `KeyError`.

화면에는 `_failure_reason` 이 만든 일반 문구가 뜬다 ("이 PDF 를 열지 못했습니다"
계열).  **사용자는 범례가 없어서 실패했다는 것을 알 수 없다.**

### 죽기 전에 항목별로는 무슨 일이 벌어지나 (항목 단위로 따로 측정)

| 항목 | 범례 있을 때 | 범례 없을 때 | 위험 |
| --- | --- | --- | --- |
| `butterfly` | LEGEND | **CONFIG_FALLBACK · 값은 완전히 같음** | 조용함 — 이 프로젝트라서 같을 뿐 |
| `actuator_stem` | LEGEND | **CONFIG_FALLBACK · 값 같음** | 같음 |
| `pneumatic` | LEGEND | **CONFIG_FALLBACK · 값 같음** | 같음 |
| `line_styles` | LEGEND (min_run 16.968) | **NEEDS_REVIEW · `{}`** | **KeyError 로 죽음** |
| `isa_table` | LEGEND · 25자 | **MISSING · 0자** | Description 변수어가 통째로 빈다 |
| `equipment_symbols` | 17행 | **0행** | 주어가 통째로 빈다 |
| `component_words` | 3낱말 · 출처 **LEGEND** | 3낱말 · 출처 **DRAWING** | 조용히 출처만 바뀜 |
| `unit_multipliers` | LEGEND · **7코드** | **CONFIG_FALLBACK · 3코드**(`00·10·11`) | **12·20·21·22 가 UNDEFINED → Q'ty 가 조용히 달라진다** |

**이것이 이 회차의 동기다.**  실패 방식이 둘로 갈린다: `line_styles` 는 시끄럽게
죽고(사유는 말하지 않고), 나머지 일곱은 **조용히 다른 값으로 계속 간다.**
특히 `unit_multipliers` 는 행 수도 지문도 그럴듯하게 나오면서 수량만 틀린다.

---

## 5. 같은 PDF 를 두 번 분석하면 유도 결과가 같은가

**완전히 같다.**  서로 다른 두 프로세스(전량 분석 1회 · 유도 계측 1회)의 결과를
항목별로 대조했다.

| 항목 | source 일치 | 값 일치 |
| --- | --- | --- |
| butterfly · actuator_stem · pneumatic | ○ | ○ |
| line_styles (커넥터 섞기 전) | ○ | ○ |
| connector_reach | ○ | ○ |
| unit_multipliers | ○ | ○ |
| isa_table (첫 문자 25자 전부) | ○ | ○ |
| equipment_symbols | 17 = 17 | ○ |

13회차가 같은 문서를 두 번 분석해 **쪽 단위로 값이 다른 쪽 0** 을 이미 확인했고,
`tests/test_determinism.py` 가 지문 동일성을 강제한다.

### 그래서 사실대로 적는다 — **일관성 이득은 "한 문서 안에서는" 없다**

프롬프트가 미리 갈라 놓은 두 갈래 중 **"흔들리지 않는다" 쪽**이다.
같은 PDF 를 두 번 돌려서 값이 달라지는 일은 없으므로, 프로필의 값어치는
*재현성*이 아니라 **문서가 달라질 때**에 있다:

- 개정본에 범례 장이 **없을 때** (§4 — 지금은 죽거나 조용히 틀린다)
- 개정본의 범례 장이 **다를 때** (재작도·축척 변경 — 지금은 아무도 모른다)

즉 [C][D] 의 근거는 §5 가 아니라 **§4** 이고, [E](변경 감지)가 이 회차에서
가장 값이 큰 부분이다.

---

## 6. 프로젝트 · Rev 구조 — 프로필을 어디에 붙이나

**한 분석 = 한 리비전**이고, 셋 다 `job` 표의 열이다 (13회차 `_ADDED_COLUMNS`).

```
job.project        '' 이면 프로젝트에 안 묶인 분석 (지금도 있는 선택지)
job.revision       'A' · 'B' · …
job.compared_with  무엇과 비교했나
```

디스크 쪽 장부는 `app/_data/projects/{안전한이름}/` 이고, 이미 세 파일이 산다.

```
projects/AL NOUF1/project.json        리비전 목록 (revisions: [{revision, job_id, …}])
projects/AL NOUF1/id_registry.json    안정 ID 대장 (Rev.A 에서 한 번만 부여)
projects/AL NOUF1/axis_overrides.json ④행 FROM/TO 사람 확정 (6회차)
```

**결론: 프로필은 `projects/{이름}/legend_profile.json` — 프로젝트 단위다.**
근거 넷:

1. 요구가 프로젝트 단위다 ("같은 PJT 다른 Rev 는 기존 이력 Symbol 기반").
2. `revisions.projects_root()` 가 `paths.data_dir()` 를 쓰므로 exe 에서는 **exe 옆
   `pid_data/`** 다 — 갈음(코드 덮어쓰기)으로 사라지지 않는다.
3. 폴더가 프로젝트로 갈려 있어 **다른 프로젝트가 공유할 길이 구조적으로 없다.**
4. 이미 같은 성격의 파일(`id_registry` · `axis_overrides`)이 그 자리에 있고,
   둘 다 "Rev.A 에서 정하고 이후 Rev 가 물려받는" 것이다 — 프로필과 같은 수명이다.

Rev 단위가 아닌 이유: Rev 단위면 물려받을 것이 없어 요구를 못 지킨다.

---

## 7. 이 조사가 줄인 범위

| 안 만들어도 되는 것 | 왜 |
| --- | --- |
| 프로필 저장소(폴더 · 이름 규칙 · 격리) | `revisions.project_dir` 이 이미 있다 |
| 프로젝트 ↔ 분석 연결 | `job.project`/`revision` 이 이미 있다 |
| 결정성 보강 | §5 — 이미 결정적이다 |
| `connector_reach` · `layout` 19건 캐시 | §1(나)(다) — 범례 값이 아니다. **담으면 해롭다** |

| 반드시 만들어야 하는 것 | 왜 |
| --- | --- |
| 범례 8항목의 저장·복원 | 지금은 메모리에서 사라지고 `equipment` 는 DB 에도 없다 (§3) |
| 범례 없이 완주 | §4 — 지금은 `KeyError` 로 죽는다 |
| 범례 없고 프로필도 없을 때의 **사유 있는 실패** | §4 — 지금은 일반 문구뿐이다 |
| 범례 변경 감지 | §5 — 조용히 옛 규칙을 쓰는 것이 유일하게 남는 위험이다 |
| 재사용/유도를 화면에 표시 | 없으면 위 넷을 확인할 방법이 없다 |
