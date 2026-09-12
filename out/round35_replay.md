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

## D-1 1단계 기록 (import 시점 · 판정에 안 씀)

되살린 20: `formats.drawing_no · date · revision · unit_code_segment · unit_code_chars` ·
`anchors.type_map.{TT PT LT PDT DPIT FT LG TI PI LI FI TIT PIT LIT PDIT}`.
전부 0.2~0.4초에 멈춤 = 분석 시작 전.

## D-2 2단계 — 유도 뒤 지우기 (`replay_late_pass1.json` · `replay_pass2_final.json`)

### 되살린 순서 — 유도 뒤 지우기 (1차 4회 + 2차 21회 · **상한 20 에서 멈춤**)

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
| 24 | `cfg.qty_note.same_words` | `?` | ? |

★ **24개 전부가 "유도가 얹힌 뒤에도 필요한 값" 이다** — `_fit_layout` 이 overlay 한
뒤(측정값 ?칸)에도 검출이 이 값들을 읽는다.  상한에서 멈췄을 때
다음 차례는 `cfg.qty_note.same_words` 였다.

**완주하지 못했다.**  그러므로 "유도만으로 AL NOUF1 을 재현한다" 는 **이 회차의 방법으로는
성립하지 않는다** — 23개(3+20)를 되살려도 아직 멈춘다.  남은 묶음은 [E] 에서
"묶음 하나만 지우기" 로 갈랐다 (`groups.json`).
