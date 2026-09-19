# [E] 차이 분류 — 상수 하나하나 (35회차)

판정: ㉠ 영향 없음 · ㉡ 유도가 대신하고 지문 같음 · ㉢ 유도가 대신하고 지문 다름 · ㉣ 유도 없음 → 멈춤 · ㉤ None 이 조용히 흘러 틀린 값 ·
**시험불가**(이 방법이 닿지 않는 자리) · **미실측**(상한 안에 개별로 못 잼).  뒤의 둘은 프롬프트의 다섯 판정 밖이고 **숨기지 않고 따로 센다**.

탐침(p1~p10) 기준 199행 · `0087c236` · Q'ty 398.  `_fit_layout` 이 얹는 키(㉡ 근거): `regions.drawing_area`, `regions.notes_area`, `regions.notes_text_x_max`, `title_block.project_name_region`, `title_block.project_name_min_height`, `title_block.title_region`, `title_block.title_min_height`, `title_block.dwg_no_region`, `title_block.rev_box`, `title_block.sheet_box`, `title_block.hist_rule_y`, `title_block.hist_rule_x0_max`, `title_block.hist_rule_x1_min`, `title_block.hist_rev_col`, `title_block.hist_date_col`, `formats.revision`, `text.dedup_exact_duplicates`, `vendor_marks.glyph_sizes`, `review_markup.requires_fill`, `sct_scope.box_from_both_edges`

## 0. 개수

| 판정 | 개수 |
|---|---:|
| ㉠ | 18 |
| ㉡ | 20 |
| ㉢ | 0 |
| ㉣ | 26 |
| ㉣-D | 91 |
| ㉤ | 0 |
| 시험불가 | 25 |
| 미실측 | 19 |
| — | 1 |
| 합 | 200 (199 + project.code) |

## 0-1. 전량 58장 확인 실행 (worktree · 낯선 프로필 경로)

| 실행 | 지운 상수 | 결과 | 본선 |
|---|---:|---|---|
| ㉠/㉡ 묶음만 지움 (유도가 답한 키는 안 지움) | 61 | {"ok": true, "rows": 1037, "fingerprint": "fb85b039", "qty": 1931, "missing": null} · 542.5초 | `fb85b039` · 1037 · 1931 |
| (첫 시도 — 유도값=설정값이면 지우던 훅) | 61 | {"ok": false, "rows": null, "fingerprint": null, "qty": null, "missing": "cfg.vendor_marks.glyph_sizes"} · 377.3초 | 방법 결함 (D-0 4) |
| 아무것도 안 지움 (유도 overlay 만) | 0 | {"ok": true, "rows": 1037, "fingerprint": "fb85b039", "qty": 1931, "missing": null} | `fb85b039` · 1037 · 1931 |

**두 실행 다 본선과 같다.**  즉 (가) 낯선 프로필 경로가 얹는 19칸(`moved58.json` — `regions.*`·`title_block.*` 15 · `formats.revision` `^[A-Z][0-9]?$→^[A-Z]$` · `sct_scope.box_from_both_edges None→True` 등)은 58장 지문을 한 칸도 안 옮기고, (나) ㉠/㉡ 61개를 지운 것도 안 옮긴다.  ⚠ 지문 밖 열(REV — `A1` 장 · Description)은 이 실행이 기록하지 않았다 → 조사 목록.

## 1. 표

| 상수 | 현재 값 | 등급(25회차) | 판정 | 근거 |
|---|---|---|---|---|
| `ds.cap_span` | `(7.0, 50.0)` | A | **㉣** | 재현 루프 멈춤 #4 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `ds.brk_corner_tol` | `3.0` | C | **㉣** | 재현 루프 멈춤 #19 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `ds.side_tol` | `0.8` | C | **㉠** | 묶음 `ds dataclass 나머지` 지워도 199/`0087c236` — 탐침 10장 경로에서 읽히지 않는다 |
| `ds.side_slack` | `1.5` | C | **㉣** | 재현 루프 멈춤 #5 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `ds.anchor_slack` | `3.0` | C | **㉣** | 재현 루프 멈춤 #21 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `ds.mark_blob` | `(1.5, 8.0)` | A/C | **㉠** | 묶음 `ds dataclass 나머지` 지워도 199/`0087c236` — dataclass 기본값을 **config 잎(`vendor_marks.blob_span`)이 덮는다**. 죽은 기본값(같은 수가 두 곳에 있다) |
| `ds.mark_glyph_span` | `(3.0, 8.0)` | A/C | **㉠** | 묶음 `ds dataclass 나머지` 지워도 199/`0087c236` — dataclass 기본값을 **config 잎(`vendor_marks.glyph_span`)이 덮는다**. 죽은 기본값(같은 수가 두 곳에 있다) |
| `ds.mark_cluster_gap` | `2.0` | A/C | **㉠** | 묶음 `ds dataclass 나머지` 지워도 199/`0087c236` — dataclass 기본값을 **config 잎(`vendor_marks.cluster_gap`)이 덮는다**. 죽은 기본값(같은 수가 두 곳에 있다) |
| `ds.box_mark_margin` | `20.0` | C | **㉠** | 묶음 `ds dataclass 나머지` 지워도 199/`0087c236` — dataclass 기본값을 **config 잎(`vendor_marks.package_box.mark_margin`)이 덮는다**. 죽은 기본값(같은 수가 두 곳에 있다) |
| `ds.note_line_gap` | `20.0` | A | **㉠** | 묶음 `ds dataclass 나머지` 지워도 199/`0087c236` — dataclass 기본값을 **config 잎(`vendor_marks.note_line_gap`)이 덮는다**. 죽은 기본값(같은 수가 두 곳에 있다) |
| `ds.mark_above` | `25.0` | C | **㉠** | 묶음 `ds dataclass 나머지` 지워도 199/`0087c236` — dataclass 기본값을 **config 잎(`vendor_marks.above`)이 덮는다**. 죽은 기본값(같은 수가 두 곳에 있다) |
| `ds.mark_side` | `10.0` | C | **㉣** | 재현 루프 멈춤 #10 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `ds.note_mark_row_tol` | `6.0` | C | **㉠** | 묶음 `ds dataclass 나머지` 지워도 199/`0087c236` — dataclass 기본값을 **config 잎(`vendor_marks.note_row_tol`)이 덮는다**. 죽은 기본값(같은 수가 두 곳에 있다) |
| `ds.brk_max_mark` | `20.0` | A | **㉠** | 묶음 `ds dataclass 나머지` 지워도 199/`0087c236` — dataclass 기본값을 **config 잎(`broken_line.brk_max_mark`)이 덮는다**. 죽은 기본값(같은 수가 두 곳에 있다) |
| `ds.brk_max_gap` | `6.0` | A | **㉣** | 재현 루프 멈춤 #14 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `ds.brk_bridge` | `26.0` | A | **㉣** | 재현 루프 멈춤 #15 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `ds.brk_min_marks` | `6` | A | **㉣** | 재현 루프 멈춤 #13 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `ds.brk_min_span` | `40.0` | A | **㉣** | 재현 루프 멈춤 #16 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `ds.scope_text_tol` | `30.0` | C | **㉠** | 묶음 `ds dataclass 나머지` 지워도 199/`0087c236` — dataclass 기본값을 **config 잎(`sct_scope.text_tol`)이 덮는다**. 죽은 기본값(같은 수가 두 곳에 있다) |
| `ds.drop_x_tol` | `2.0` | C | **㉠** | 묶음 `ds dataclass 나머지` 지워도 199/`0087c236` — dataclass 기본값을 **config 잎(`sct_scope.drop_x_tol`)이 덮는다**. 죽은 기본값(같은 수가 두 곳에 있다) |
| `ds.drop_end_tol` | `1.5` | C | **㉠** | 묶음 `ds dataclass 나머지` 지워도 199/`0087c236` — dataclass 기본값을 **config 잎(`sct_scope.drop_end_tol`)이 덮는다**. 죽은 기본값(같은 수가 두 곳에 있다) |
| `ds.scope_box_both_edges` | `False` | D | **㉠** | 묶음 `ds dataclass 나머지` 지워도 199/`0087c236` — 탐침 10장 경로에서 읽히지 않는다 |
| `dv.seg_span` | `(1.0, 60.0)` | A | **㉣** | 묶음 `dv dataclass(15)` 이 이 상수에서 멈춤 — 유도 없음 |
| `dv.body_short` | `(5.0, 30.0)` | A | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `dv.arc_above` | `6.0` | A | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `dv.tick_span` | `(1.5, 6.0)` | A | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `dv.tick_reach` | `1.3` | A | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `dv.bar_reach` | `3.4` | A | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `dv.bar_min` | `1.1` | A | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `dv.act_box` | `(9.0, 34.0)` | A | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `dv.bar_axis_tol` | `0.8` | C | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `dv.bar_cover` | `1.2` | C | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `dv.centre_tol` | `2.0` | C | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `dv.stem_slack` | `-1.0` | C | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `dv.act_reach` | `90.0` | C | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `dv.act_offaxis` | `12.0` | C | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `dv.tag_reach` | `190.0` | C | **미실측** | 묶음 `dv dataclass(15)` 이 `dv.seg_span` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `tb.title_line_tol` | `6.0` | A | **㉠** | 묶음 `tb.title_line_tol` 지워도 199/`0087c236` — 탐침 10장 경로에서 읽히지 않는다 |
| `tb.zoom` | `24.0` | A | **㉣** | 재현 루프 멈춤 #1 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.formats.drawing_no` | `"^[A-Z0-9]{4}-[A-Z0-9]{7}-[A-Z0-9]{3}…` | A | **㉣** | 재현 루프 멈춤 #2 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.formats.date` | `"^\\d{1,2}\\.\\s?[A-Z]{3}\\.\\d{4}$"` | B | **㉣** | 재현 루프 멈춤 #3 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.formats.revision` | `"^[A-Z][0-9]?$"` | B | **㉡** | `_fit_layout` 이 얹는다 (`^[A-Z][0-9]?$` → `^[A-Z]$`) — strip 훅이 건너뛰어 **지운 적이 없다**. 유도가 이미 덮는 값인데 목록은 A/B 로 적었다. 탐침 지문은 같고, 58장은 §0-1 |
| `cfg.formats.unit_code_segment` | `1` | B | **미실측** | 어느 묶음에도 들지 않았고 되살리기 사슬에도 닿지 않았다 |
| `cfg.formats.unit_code_chars` | `[0, 2]` | B | **미실측** | 어느 묶음에도 들지 않았고 되살리기 사슬에도 닿지 않았다 |
| `cfg.formats.system_code_chars` | `[2, 5]` | B | **미실측** | 어느 묶음에도 들지 않았고 되살리기 사슬에도 닿지 않았다 |
| `cfg.excel.sheet` | `"2.0_Instrument List"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.excel.first_data_row` | `8` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.excel.columns.no` | `1` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.excel.columns.system` | `6` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.excel.columns.pid_no` | `7` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.excel.columns.type` | `8` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.excel.columns.qty` | `9` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.excel.columns.description` | `10` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.excel.columns.tag_no` | `5` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.excel.columns.scope` | `37` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.excel.columns.remark` | `41` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.anchors.type_map.TT` | `"TIT"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.PT` | `"PIT"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.LT` | `"LIT"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.PDT` | `"PDIT"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.DPIT` | `"PDIT"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.FT` | `"FIT"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.LG` | `"LI"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.TI` | `"TI"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.PI` | `"PI"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.LI` | `"LI"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.FI` | `"FI"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.TIT` | `"TIT"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.PIT` | `"PIT"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.LIT` | `"LIT"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.PDIT` | `"PDIT"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.FIT` | `"FIT"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.LS` | `"LS"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.LSH` | `"LS"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.LSHH` | `"LS"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.LSL` | `"LS"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.FS` | `"FS"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.RO` | `"RO"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.FE` | `"FE"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.type_map.TW` | `"TW"` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.anchors.not_field` | `[]` | A/D | **시험불가** | 묶음 `anchors(25)` 지워도 199/`0087c236` — 그러나 `anchors.type_map` 은 import 때 `_V3_FIELD_TYPE_MAP` 으로 굳어 유도 뒤 지우기가 닿지 않는다. **이 방법으로는 판정할 수 없다** |
| `cfg.revision.document_rule` | `"max"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.client_form.scope_filter` | `"all"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.scope.exclusion_rules` | `"none"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.scope.supplier_from_notes` | `"\\bBY\\s+(?P<name>[^.]+?)\\s*\\.?\\s*$"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.scope.vendor_description` | `"skip"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.vendor_marks.glyph_sizes` | `[[4.0, 4.0], [5.2, 5.2]]` | A | **㉡** | `_fit_layout` 이 얹는다 (`[[4.0, 4.0], [5.2, 5.2]]` → `[[4.0, 4.0]]`) — strip 훅이 건너뛰어 **지운 적이 없다**. 유도가 이미 덮는 값인데 목록은 A/B 로 적었다. 탐침 지문은 같고, 58장은 §0-1 |
| `cfg.vendor_marks.blob_span` | `[1.5, 8.0]` | C | **㉣** | 재현 루프 멈춤 #6 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.vendor_marks.glyph_span` | `[3.0, 8.0]` | C | **㉣** | 재현 루프 멈춤 #8 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.vendor_marks.cluster_gap` | `2.0` | C | **㉣** | 재현 루프 멈춤 #7 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.vendor_marks.above` | `25.0` | C | **㉣** | 재현 루프 멈춤 #11 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.vendor_marks.x_slack` | `6.0` | C | **㉠** | 묶음 `vendor_marks.x_slack+note_row_tol` 지워도 199/`0087c236` — 탐침 10장 경로에서 읽히지 않는다 |
| `cfg.vendor_marks.note_row_tol` | `6.0` | C | **㉠** | 묶음 `vendor_marks.x_slack+note_row_tol` 지워도 199/`0087c236` — 탐침 10장 경로에서 읽히지 않는다 |
| `cfg.vendor_marks.note_line_gap` | `20.0` | C | **㉣** | 재현 루프 멈춤 #9 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.vendor_marks.package_box.edge_cover` | `0.35` | C | **㉣** | 재현 루프 멈춤 #17 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.vendor_marks.package_box.mark_margin` | `20.0` | C | **㉣** | 재현 루프 멈춤 #20 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.broken_line.brk_max_mark` | `28.3` | A | **㉣** | 재현 루프 멈춤 #12 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.sct_scope.text_tol` | `30.0` | C | **㉣** | 재현 루프 멈춤 #18 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.sct_scope.drop_x_tol` | `2.0` | C | **㉣** | 재현 루프 멈춤 #22 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.sct_scope.drop_end_tol` | `1.5` | C | **㉣** | 재현 루프 멈춤 #23 — 유도가 얹힌 뒤에도 이 값을 읽는다. 되살려야 진행 |
| `cfg.supplier_interface_span.label` | `"공급자 인터페이스 구간 — 배관 및 기기 공급자 범위"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.supplier_interface_span.supplied_by` | `""` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.supplier_interface_span.description` | `"keep"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.multi_signal_bundle.merge_quantity` | `true` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.multi_signal_bundle.merged_type` | `"LS"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.multi_signal_bundle.description_signal` | `"representative"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.axis_mode` | `"mixed"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.prefix` | `"UNIT"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.unit_mark` | `"#"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.title_open` | `["FOR"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.title_close` | `["SYSTEM"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.template` | `"UNIT #{unit} {system} {variable}"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.measured_on` | `"발주처 계기 리스트 557행 (data/CZE_Field_Inst…` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.note` | `"접미(A/B/C, HIGH HIGH)와 중간 서술은 도면에 없어 …` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.equipment_words` | `["PUMP", "COOLER", "TANK", "HEATER", …` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_words.pump.left` | `"SUCTION"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_words.pump.right` | `"DISCHARGE"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_words.other.left` | `"INLET"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_words.other.right` | `"OUTLET"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_words.pump_nouns` | `["PUMP", "CEP", "BFP"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.unit_prefix_skip_codes` | `["00"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.variable_words.PD` | `["DIFFERENTIAL", "PRESSURE"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.variable_words.RO` | `["RESTRICTION", "ORIFICE"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.variable_words.FE` | `["FLOW", "ELEMENT"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_word_types` | `["PIT", "PDIT", "FS", "FIT", "FE"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.end_ordinal_types` | `["PIT", "TIT", "FIT", "PDIT"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.system_abbreviations.CLOSED COOLING WATER` | `"CCW"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.system_abbreviations.AUX. COOLING WATER` | `"ACW"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_by_system.CCW TI` | `"RETURN"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.sole_equipment_sheet_max` | `2` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.equipment_alias_choice.boiler_feedwater_pump` | `"BOILER FEED WATER PUMP"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.equipment_alias_choice.condensate_extraction_pump` | `"CEP"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.project_abbreviations.clean_drain` | `["CD", "CLEAN DRAIN"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.project_abbreviations.restriction_orifice` | `["RO", "RESTRICTION ORIFICE"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.equipment_modifiers.VALVE` | `["BYPASS", "LETDOWN", "CONTROL", "MOD…` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.equipment_modifiers.HEADER` | `["DISCHARGE", "STEAM", "SEAL", "RING"…` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.equipment_modifiers.BOX` | `["WATER", "FLASH"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.user_input_reasons` | `[{"types": ["PDIT"], "noun": "PUMP", …` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_by_noun.TANK` | `""` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_by_noun.VALVE` | `"DOWNSTREAM"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_by_noun.HEADER` | `"DISCHARGE"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_pair_words` | `["DISCHARGE", "SUCTION", "RETURN", "S…` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.type_display_names.AT` | `"Analyzer"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.type_display_names.AIT` | `"Analyzer"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.duplicate_suffix_types` | `[]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.line_phrase_types` | `["LS"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_by_side.PIT ABOVE` | `"DISCHARGE"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_by_side.PDIT ABOVE` | `"SUCTION"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.position_by_side.PDIT LEFT` | `"SUCTION"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.between_symbol_types` | `["PDIT"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.alarm_suffix.HH` | `["HIGH", "HIGH"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.alarm_suffix.H` | `["HIGH"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.alarm_suffix.LL` | `["LOW", "LOW"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.alarm_suffix.L` | `["LOW"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.description.examples` | `[]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.unit_multiplier_fallback.00` | `1` | A | **㉡** | 묶음 `unit_multiplier_fallback(3)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.unit_multiplier_fallback.10` | `2` | A | **㉡** | 묶음 `unit_multiplier_fallback(3)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.unit_multiplier_fallback.11` | `4` | A | **㉡** | 묶음 `unit_multiplier_fallback(3)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.qty_note.same_words` | `["IDENTICAL", "SIMILAR", "SAME", "TYP…` | ? | **㉣** | 상한 20 에서 멈춘 뒤 다음 차례(24번째) — 되살리지 못했다 |
| `cfg.qty_note.unit_words` | `["GROUP", "UNIT", "TRAIN"]` | ? | **㉠** | config 값 = 코드 기본값 (`projectconfig._DEFAULT_*`). 묶음 토글은 sentinel 의 `if got` 에서 멈췄지만 **키를 실제로 빼면** 코드가 같은 낱말을 쓴다 — 코드 대조로 판정 |
| `cfg.qty_note.range_words` | `["THRU", "THROUGH", "~"]` | ? | **㉠** | config 값 = 코드 기본값 (`projectconfig._DEFAULT_*`). 묶음 토글은 sentinel 의 `if got` 에서 멈췄지만 **키를 실제로 빼면** 코드가 같은 낱말을 쓴다 — 코드 대조로 판정 |
| `cfg.qty_scope_overrides` | `[{"keyword": "PLANT COMMON", "multipl…` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.actuator_reach` | `90.0` | C | **미실측** | 묶음 `valves.actuator_reach/offaxis/tag_reach(3)` 이 `cfg.valves.tag_reach` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `cfg.valves.actuator_offaxis` | `12.0` | C | **미실측** | 묶음 `valves.actuator_reach/offaxis/tag_reach(3)` 이 `cfg.valves.tag_reach` 에서 먼저 멈춰 이 상수까지 닿지 않았다 (상한 20 · 4시간 안에 개별 실측 못 함) |
| `cfg.valves.tag_reach` | `190.0` | C | **㉣** | 묶음 `valves.actuator_reach/offaxis/tag_reach(3)` 이 이 상수에서 멈춤 — 유도 없음 |
| `cfg.valves.excel.sheet` | `"3.0_Valve List"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.excel.first_data_row` | `8` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.excel.columns.no` | `1` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.excel.columns.pid_no` | `2` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.excel.columns.valve_type` | `3` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.excel.columns.qty` | `4` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.excel.columns.system` | `5` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.excel.columns.description` | `12` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.excel.columns.remark` | `39` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.excel.columns.tag_no` | `11` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.excel.columns.actuator` | `25` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.excel.columns.body` | `27` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.deliverables` | `[{"tag": "CZI", "path": "data/CZI_But…` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.valve_type_actuator.MOV` | `"MOTOR"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.valve_type_actuator.MOV_I` | `"MOTOR"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.valve_type_actuator.HOV` | `"HYDRAULIC"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.valve_type_actuator.CV` | `"PNEUMATIC"` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.cv_tags` | `["FCV", "LCV", "PCV", "TCV", "CV"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.xv_tags` | `["XV", "HV"]` | D | **㉣-D** | 런타임 D 표 — 덩이로 미리 되살렸다(개별 실측은 `description.unit_prefix_skip_codes` 1개 · 1차 4번째 멈춤). 도면에 없는 값이라 유도가 있을 수 없다 — 사람·발주처 |
| `cfg.valves.legend_fallback.butterfly.tick_length` | `3.0` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.butterfly.tick_reach_radii` | `1.498` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.butterfly.bar_reach_radii` | `2.822` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.butterfly.bar_min_radii` | `2.378` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.butterfly.circle_diameter` | `6.06` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.actuator_stem.stem_gap` | `0.0` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.actuator_stem.stem_offaxis` | `0.03` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.actuator_stem.stem_length` | `19.86` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.actuator_stem.centre_to_body` | `26.97` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.pneumatic.dome_flat` | `14.22` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.pneumatic.dome_depth` | `7.11` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.pneumatic.dome_aspect` | `0.5` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.pneumatic.cylinder_side` | `14.16` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.pneumatic.cylinder_aspect` | `1.003` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.valves.legend_fallback.pneumatic.cylinder_divider` | `0.5` | A | **㉡** | 묶음 `valves.legend_fallback(15)` 지워도 199/`0087c236` — 범례(p2·p3·p5)가 답하므로 폴백은 읽히지 않는다 |
| `cfg.project.code` | `"ALNOUF1"` | E→지움 | **—** | 프로필 열쇠. 표식 문자열로 바꿔 낯선 프로필 경로를 강제했다 (판정 대상 아님) |
