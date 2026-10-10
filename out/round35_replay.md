# [D] 재현 실행 — 되살린 순서 · 최종 지문 · 열별 차이

worktree `/tmp/r35_strip` (본선 HEAD `1b967ee` 에서 딴 것 · 엔진 수정은 전부 여기).
탐침: `/tmp/r35_probe.pdf` = `pid_total.pdf` p1~p10 (범례 p2~p4 + P&ID 6장).
**탐침 기준(본선 엔진 · 상수 전부 있음): 199행 · `0087c236` · Q'ty 398.**
worktree 엔진에 상수를 하나도 안 지운 상태(`R35_NO_STRIP`)도 **같은 199 · `0087c236`** —
sentinel 패치 자체는 아무 것도 움직이지 않는다.

## D-0 절차를 두 번 고쳤다 (스스로 뒤집은 것)

1. **import 시점에 지우면 유도가 얹힐 기회가 없다.**  첫 루프(`replay_probe.json`)는
   20회 상한을 **몇 초 만에** 다 썼다 — 전부 import 시점의 `re.compile` · `float()` ·
   사전 순회(`anchors.type_map` 을 잎 하나씩 15회)였다.  이것은 "유도 없이는 못 도는 값"
   이 아니라 **내 sentinel 이 변환기에서 터진 것**이다.  그 기록은 남기되(§D-1) 판정에
   쓰지 않는다.
2. **그래서 "유도가 얹힌 뒤" 지운다.**  `project.code` 만 load 때 표식 문자열로 바꿔
   `_fit_layout` 이 낯선 프로필 경로(측정값 overlay)를 타게 하고, overlay 직후에
   **overlay 가 옮기지 않은** 잎만 sentinel 로 바꾼 뒤 `_rebind_config` 로 다시 조립한다.
   조립 함수의 변환기(`float/tuple/int/re.compile`)는 sentinel 을 통과시킨다 — 값으로
   **쓰는** 순간에만 터진다.  이제 멈춤 = *유도가 기회를 가졌는데도 그 값이 필요하다*.
3. 사전 복원 2단계(`stage2_prerestored.json`)는 한 번 시도했다가 **버렸다** — 2번이
   되면 필요 없다.
4. **유도가 답한 키는 값이 설정과 같아도 지우지 않는다** (D-4 에서 세 번째로 고침).  strip 훅이
   "overlay 가 옮긴 키" 만 건너뛰었는데, 유도값이 설정과 **같으면** overlay 는 옮김으로 기록하지 않아
   그 키가 지워지고 — 그러면 유도가 방금 낸 값까지 버리는 셈이다.  58장 실측: `vendor_marks.glyph_sizes`
   가 탐침 10장에서는 `[[4,4]]`(≠설정)라 살았고, 58장에서는 정의줄 18장이 두 크기를 다 주어
   설정과 같아져 지워졌고 `read_mark_dictionary` 에서 멈췄다 (`full58_try1.json` · 377초).
   이제 `items` 의 키 전부를 건너뛴다 — 판정은 "유도가 답하는가" 이지 "유도가 설정을 바꾸는가" 가 아니다.

## D-1 1단계 기록 (import 시점 · 판정에 안 씀)

되살린 20: `formats.drawing_no · date · revision · unit_code_segment · unit_code_chars` ·
`anchors.type_map.{TT PT LT PDT DPIT FT LG TI PI LI FI TIT PIT LIT PDIT}`.
전부 0.2~0.4초에 멈춤 = 분석 시작 전.

## D-2 2단계 — 유도 뒤 지우기 (`replay_late_pass1.json` · `replay_pass2_final.json`)

### 되살린 순서 — 유도 뒤 지우기 (1차 4회 + 2차 21회 · **상한 20 에서 멈춤** · 표의 마지막 행은 되살리지 않은 다음 차례)

1차(`replay_late_pass1.json`)는 세 개를 되살린 뒤 4번째에서 `description.*` 잎에 걸렸다.
`description` 49개는 발주처 557행에서 센 값(D)이고 지문에 닿지 않으며 코드가 잎 하나씩
읽으므로, **하나씩 되살리면 상한을 정보 없이 다 쓴다.**  그래서 2차는 **런타임 D 표
91개**(description · excel · valves.excel/deliverables/valve_type_actuator/cv·xv_tags
· scope · revision · client_form · supplier_interface_span · multi_signal_bundle ·
qty_scope_overrides)를 **한 덩이로 미리 되살리고**(판정은 어차피 ㉣-D) 1차의 셋을 더한
상태에서 다시 하나씩 갔다 (`pass2_prerestored.json`).  `anchors.*`·`formats.revision` 은
유도 이야기가 있어 지운 채 두었다.

| # | 멈춘 상수 | 현재 값 | 등급 |
|---|---|---|---|
| 1 | `tb.zoom` | `24.0` | A |
| 2 | `cfg.formats.drawing_no` | `"^[A-Z0-9]{4}-[A-Z0-9]{7}-[A-Z0-9]{3}-\\` | A |
| 3 | `cfg.formats.date` | `"^\\d{1,2}\\.\\s?[A-Z]{3}\\.\\d{4}$"` | B |
| 4 | `ds.cap_span` | `(7.0, 50.0)` | A |
| 5 | `ds.side_slack` | `1.5` | C |
| 6 | `cfg.vendor_marks.blob_span` | `[1.5, 8.0]` | C |
| 7 | `cfg.vendor_marks.cluster_gap` | `2.0` | C |
| 8 | `cfg.vendor_marks.glyph_span` | `[3.0, 8.0]` | C |
| 9 | `cfg.vendor_marks.note_line_gap` | `20.0` | C |
| 10 | `ds.mark_side` | `10.0` | C |
| 11 | `cfg.vendor_marks.above` | `25.0` | C |
| 12 | `cfg.broken_line.brk_max_mark` | `28.3` | A |
| 13 | `ds.brk_min_marks` | `6` | A |
| 14 | `ds.brk_max_gap` | `6.0` | A |
| 15 | `ds.brk_bridge` | `26.0` | A |
| 16 | `ds.brk_min_span` | `40.0` | A |
| 17 | `cfg.vendor_marks.package_box.edge_cover` | `0.35` | C |
| 18 | `cfg.sct_scope.text_tol` | `30.0` | C |
| 19 | `ds.brk_corner_tol` | `3.0` | C |
| 20 | `cfg.vendor_marks.package_box.mark_margin` | `20.0` | C |
| 21 | `ds.anchor_slack` | `3.0` | C |
| 22 | `cfg.sct_scope.drop_x_tol` | `2.0` | C |
| 23 | `cfg.sct_scope.drop_end_tol` | `1.5` | C |
| 24 | `cfg.qty_note.same_words` | `[IDENTICAL, SIMILAR, SAME, TYPICAL]` | ?(27회차 신설) — 코드 기본값과 같은 값 |

★ **표의 24행 중 앞 23개(되살린 것)가 "유도가 얹힌 뒤에도 필요한 값" 이다** — `_fit_layout` 이 overlay 한
뒤(측정값 20칸 · `moved.json`)에도 검출이 이 값들을 읽는다.  상한에서 멈췄을 때
다음 차례는 `cfg.qty_note.same_words` 였다.

**완주하지 못했다.**  그러므로 "유도만으로 AL NOUF1 을 재현한다" 는 **이 회차의 방법으로는
성립하지 않는다** — 23개(3+20)를 되살려도 아직 멈춘다.  남은 묶음은 [E] 에서
"묶음 하나만 지우기" 로 갈랐다 (`groups.json`).

## D-3 묶음 토글 — 전부 되살린 상태에서 **한 묶음만** 지운다 (`spike/r35_groups.py` · `groups.json`)

상한 20 뒤에 남은 상수를 [E] 로 가르는 방법이다.  되살리기가 아니라 "지웠을 때 도는가" 를 묻는다 —
회당 1번, 탐침 10장, 결과를 탐침 기준 `0087c236` 과 대조한다.

| 묶음 | 상수 | 결과 | 시간 |
|---|---:|---|---|
| `formats.revision` | 1 | 완주 199 · `0087c236` · 398 | 172.4초 |
| `anchors(25)` | 25 | 완주 199 · `0087c236` · 398 | 161.4초 |
| `valves.legend_fallback(15)` | 15 | 완주 199 · `0087c236` · 398 | 170.5초 |
| `unit_multiplier_fallback(3)` | 3 | 완주 199 · `0087c236` · 398 | 165.7초 |
| `qty_note(3)` | 3 | 멈춤 `cfg.qty_note.same_words` | 106.9초 |
| `valves.actuator_reach/offaxis/tag_reach(3)` | 3 | 멈춤 `cfg.valves.tag_reach` | 148.4초 |
| `vendor_marks.glyph_sizes` | 1 | 완주 199 · `0087c236` · 398 | 162.3초 |
| `vendor_marks.x_slack+note_row_tol` | 2 | 완주 199 · `0087c236` · 398 | 164.4초 |
| `dv dataclass(15)` | 15 | 멈춤 `dv.seg_span` | 128.0초 |
| `ds dataclass 나머지` | 13 | 완주 199 · `0087c236` · 398 | 170.8초 |
| `tb.title_line_tol` | 1 | 완주 199 · `0087c236` · 398 | 164.1초 |

읽는 법:
* **완주 · 같은 지문** = 그 묶음은 이 경로에서 읽히지 않거나(㉠) 유도가 대신한다(㉡).  어느 쪽인지는
  `_fit_layout` 이 얹는 키 목록(`moved.json` · 20칸)과 범례 출처로 가른다 — `formats.revision` 과
  `vendor_marks.glyph_sizes` 는 **strip 훅이 애초에 건너뛴 키**(유도가 얹었으므로)라 "지워도 같다" 가 아니라
  "지운 적이 없다" 이고, `valves.legend_fallback` · `unit_multiplier_fallback` 은 범례 p2·p3·p5 가 답해 폴백이 읽히지 않는다.
* **`anchors(25)` 의 완주는 증거가 아니다** — `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로
  굳고 `_rebind_config` 이 다시 만들지 않으므로, 유도 뒤에 잎을 sentinel 로 바꿔도 검출은 옛 표를 읽는다.
  **이 방법으로는 시험할 수 없다** — [E] 에 "시험불가" 로 따로 센다.
* **`qty_note(3)` 의 멈춤은 sentinel 의 결과다** — `note_vocabulary` 가 `if got` 로 잎을 보는데 config 값이
  코드 기본값(`_DEFAULT_SAME` 등)과 **같다**.  키를 실제로 빼면 코드가 같은 낱말을 쓴다 → ㉠ (코드 대조로 판정).
* **`dv dataclass(15)` 는 `dv.seg_span` 에서 멈췄다** — 나머지 14개는 개별 실측이 안 됐다(미실측).
  `valves.actuator_reach/offaxis/tag_reach(3)` 도 `tag_reach` 에서 멈춰 둘이 미실측이다.
* `ds dataclass 나머지(13)` 완주의 대부분은 **config 잎이 기본값을 덮는** 자리다 (`_layout_from_config` 실측 11개) —
  같은 수가 두 곳에 있고 살아 있는 쪽은 config 다.

★ **`moved.json` 이 보여 준 것 — 유도가 AL NOUF1 에서 실제로 얹는 20칸에 `sct_scope.box_from_both_edges None→True`
가 있다.**  본선 AL NOUF1 프로필은 이 값을 **끈 채로** 지문 `fb85b039` 를 냈고(§3 "켜면 b1c6745b"), 낯선 프로필
경로는 켠다.  즉 "유도만으로" 돌린 58장 결과가 본선과 다르면 그 첫 후보는 지운 상수가 아니라 **overlay 자체**다 —
그래서 D-4 는 두 번 돈다.

## D-4 전량 58장 확인 (`spike/r35_full58.py` · `full58.json` · `overlay.json` · `moved58.json`)

탐침 지문은 10장의 것이라 최종 지문은 58장에서만 말한다.  두 번 돌렸다 — 둘의 차이가 "지운 상수" 의 효과이고,
둘째와 본선의 차이가 "낯선 프로필 경로(유도 overlay)" 자체의 효과다.

| 실행 | 지운 상수 | 행 · 지문 · Q'ty | 시간 | 본선 |
|---|---:|---|---|---|
| ㉠/㉡ 묶음 61개 지움 (되살린 138) | 61 | **1037 · `fb85b039` · 1931** | 542.5초 | 같음 |
| 아무것도 안 지움 — 유도 overlay 만 | 0 | **1037 · `fb85b039` · 1931** | 539.6초 | 같음 |
| (첫 시도 — 훅 결함, D-0 4) | 61 | 멈춤 `cfg.vendor_marks.glyph_sizes` | 377.3초 | — |

`moved58.json` — 58장에서 `_fit_layout` 이 실제로 얹은 **19칸**: `regions.*` 3 · `title_block.*` 12 ·
`formats.revision` `^[A-Z][0-9]?$ → ^[A-Z]$` · `text.dedup_exact_duplicates` · `review_markup.requires_fill` ·
**`sct_scope.box_from_both_edges None → True`**.  유도했지만 안 옮긴 6: `sheet.*` 2(같음) · `vendor_marks.glyph_sizes`
(58장에서는 `[[4,4],[5.2,5.2]]` 로 설정과 같음) · `review_markup.script_ranges` · **`broken_line.brk_max_mark 18.6` ·
`brk_max_gap 4.1` — `UNAVAILABLE`** (재고 버린다: 두 문서에서 18.6 / 7.6 인데 필요한 경계는 26.3 / 21.3).

읽는 법:
1. **"유도만으로 AL NOUF1 을 재현한다" 는 61개까지는 성립한다** — 낯선 프로필 경로 + ㉠/㉡ 61개 제거로
   `fb85b039 · 1037 · 1931` 이 그대로 나온다.  나머지 138개(㉣ 26 · ㉣-D 91 · 미실측 19 · project.code · 그리고 시험불가
   25 는 61 안에 들어 있다)는 되살린 채였다 — 이것이 남은 일 목록이다 (`out/round35_remaining.md`).
2. **overlay 19칸은 지문을 한 칸도 안 옮긴다.**  `box_from_both_edges True` 도 그렇다 — §3 의 "켜면 b1c6745b" 는
   별표 SCOPE 이전(a38fe8ac 기준)의 실측이고 지금은 성립하지 않는다.  단 **지문 밖 열은 이 실행이 기록하지 않았다**:
   `formats.revision ^[A-Z]$` 는 `A1` 장(30회차 [10])의 REV 를 바꿀 수 있다 → 조사 목록.
3. **brk_max_mark 는 ㉢ 가 아니라 ㉣ 다** — 유도가 18.6 을 재고 스스로 버리므로(UNAVAILABLE) 설정 28.3 이 읽힌다.
   "유도가 대신했는데 지문이 다르다" 가 아니라 "유도가 답을 거부한다" 이다.
