# [F] 남은 일 목록 — 다섯으로 가른다 (35회차)

이 회차의 산출물이다.  **어느 목록도 이 회차에 본선에 적용하지 않는다** — 다음 회차다.

| 목록 | 개수 | 뜻 |
|---|---:|---|
| 삭제 | 38 | 지워도 지문이 안 움직인다 — 설정이 코드·범례·유도의 사본이다 |
| 조사 | 20 | 이 회차 방법으로 판정이 안 섰다 — 개별 실측 · 지문 밖 열 대조 |
| 유도 구현 | 26 | 유도가 없어 멈춘다 — 도면(범례·본문)에 근거가 있다 |
| 사람 지정 | 91 | 도면에 없다 — 프로필·사람 지정 화면 |
| 결함 | 25 | 코드 구조가 유도를 막는다 |
| 합 | 200 | = 지운 목록 199 + project.code |

## 삭제 (38)

| 상수 | 등급 | 판정 | 왜 이 목록인가 |
|---|---|---|---|
| `ds.side_tol` | C | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `ds.mark_blob` | A/C | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `ds.mark_glyph_span` | A/C | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `ds.mark_cluster_gap` | A/C | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `ds.box_mark_margin` | C | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `ds.note_line_gap` | A | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `ds.mark_above` | C | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `ds.note_mark_row_tol` | C | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `ds.brk_max_mark` | A | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `ds.scope_text_tol` | C | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `ds.drop_x_tol` | C | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `ds.drop_end_tol` | C | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `ds.scope_box_both_edges` | D | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `tb.title_line_tol` | A | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `cfg.vendor_marks.glyph_sizes` | A | ㉡ | 58장 유도값 = 설정값 ([[4.0, 4.0], [5.2, 5.2]]) — 설정은 유도의 사본이다 (10장 탐침에서는 `[[4.0, 4.0]]` 로 달랐다 — 정의줄이 두 크기를 다 주는 장이 p10 뒤에 있다) |
| `cfg.vendor_marks.x_slack` | C | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `cfg.vendor_marks.note_row_tol` | C | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `cfg.unit_multiplier_fallback.00` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.unit_multiplier_fallback.10` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.unit_multiplier_fallback.11` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.qty_note.unit_words` | ? | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `cfg.qty_note.range_words` | ? | ㉠ | 지워도 지문 불변 · 코드 기본값과 같다 |
| `cfg.valves.legend_fallback.butterfly.tick_length` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.butterfly.tick_reach_radii` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.butterfly.bar_reach_radii` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.butterfly.bar_min_radii` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.butterfly.circle_diameter` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.actuator_stem.stem_gap` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.actuator_stem.stem_offaxis` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.actuator_stem.stem_length` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.actuator_stem.centre_to_body` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.pneumatic.dome_flat` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.pneumatic.dome_depth` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.pneumatic.dome_aspect` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.pneumatic.cylinder_side` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.pneumatic.cylinder_aspect` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.valves.legend_fallback.pneumatic.cylinder_divider` | A | ㉡ | 범례가 답한다 — 비우면 범례 없는 개정본이 **시끄럽게** 멈춘다 (§9 4 · 15회차 보류 항목의 답). 적용은 실무 판단 |
| `cfg.project.code` | E→지움 | — | 프로필 열쇠 — 지운 것은 실험 장치였다. 본선에서는 남긴다(E). 합계를 맞추려 여기 둔다 |

## 조사 (20)

| 상수 | 등급 | 판정 | 왜 이 목록인가 |
|---|---|---|---|
| `dv.body_short` | A | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `dv.arc_above` | A | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `dv.tick_span` | A | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `dv.tick_reach` | A | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `dv.bar_reach` | A | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `dv.bar_min` | A | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `dv.act_box` | A | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `dv.bar_axis_tol` | C | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `dv.bar_cover` | C | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `dv.centre_tol` | C | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `dv.stem_slack` | C | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `dv.act_reach` | C | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `dv.act_offaxis` | C | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `dv.tag_reach` | C | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `cfg.formats.revision` | B | ㉡ | 유도값 ≠ 설정값 (^[A-Z][0-9]?$ → ^[A-Z]$) — 지문은 같지만 지문 밖 열(REV·Description)을 58장에서 대조해야 한다 |
| `cfg.formats.unit_code_segment` | B | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `cfg.formats.unit_code_chars` | B | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `cfg.formats.system_code_chars` | B | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `cfg.valves.actuator_reach` | C | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |
| `cfg.valves.actuator_offaxis` | C | 미실측 | 개별 실측이 안 됐다 — 다음 회차가 묶음을 쪼개 잰다 (회당 약 2.5분) |

## 유도 구현 (26)

| 상수 | 등급 | 판정 | 왜 이 목록인가 |
|---|---|---|---|
| `ds.cap_span` | A | ㉣ | 찾는데 안 쓴다 — 코드가 이미 잰 값을 잇는다 |
| `ds.brk_corner_tol` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `ds.side_slack` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `ds.anchor_slack` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `ds.mark_side` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `ds.brk_max_gap` | A | ㉣ | 찾는데 안 쓴다 — 코드가 이미 잰 값을 잇는다 |
| `ds.brk_bridge` | A | ㉣ | 찾는데 안 쓴다 — 코드가 이미 잰 값을 잇는다 |
| `ds.brk_min_marks` | A | ㉣ | 찾는데 안 쓴다 — 코드가 이미 잰 값을 잇는다 |
| `ds.brk_min_span` | A | ㉣ | 찾는데 안 쓴다 — 코드가 이미 잰 값을 잇는다 |
| `dv.seg_span` | A | ㉣ | 찾는데 안 쓴다 — 코드가 이미 잰 값을 잇는다 |
| `tb.zoom` | A | ㉣ | 찾는데 안 쓴다 — 코드가 이미 잰 값을 잇는다 |
| `cfg.formats.drawing_no` | A | ㉣ | 찾는데 안 쓴다 — 코드가 이미 잰 값을 잇는다 |
| `cfg.formats.date` | B | ㉣ | 인쇄돼 있는데 안 찾는다 — 읽기 추가 |
| `cfg.vendor_marks.blob_span` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `cfg.vendor_marks.glyph_span` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `cfg.vendor_marks.cluster_gap` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `cfg.vendor_marks.above` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `cfg.vendor_marks.note_line_gap` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `cfg.vendor_marks.package_box.edge_cover` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `cfg.vendor_marks.package_box.mark_margin` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `cfg.broken_line.brk_max_mark` | A | ㉣ | 찾는데 안 쓴다 — 코드가 이미 잰 값을 잇는다 |
| `cfg.sct_scope.text_tol` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `cfg.sct_scope.drop_x_tol` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `cfg.sct_scope.drop_end_tol` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |
| `cfg.qty_note.same_words` | ? | ㉣ | ? |
| `cfg.valves.tag_reach` | C | ㉣ | 본문 실물에서 잰다 (분포 · 비율) |

## 사람 지정 (91)

| 상수 | 등급 | 판정 | 왜 이 목록인가 |
|---|---|---|---|
| `cfg.excel.sheet` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.excel.first_data_row` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.excel.columns.no` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.excel.columns.system` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.excel.columns.pid_no` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.excel.columns.type` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.excel.columns.qty` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.excel.columns.description` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.excel.columns.tag_no` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.excel.columns.scope` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.excel.columns.remark` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.revision.document_rule` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.client_form.scope_filter` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.scope.exclusion_rules` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.scope.supplier_from_notes` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.scope.vendor_description` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.supplier_interface_span.label` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.supplier_interface_span.supplied_by` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.supplier_interface_span.description` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.multi_signal_bundle.merge_quantity` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.multi_signal_bundle.merged_type` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.multi_signal_bundle.description_signal` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.axis_mode` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.prefix` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.unit_mark` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.title_open` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.title_close` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.template` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.measured_on` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.note` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.equipment_words` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_words.pump.left` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_words.pump.right` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_words.other.left` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_words.other.right` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_words.pump_nouns` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.unit_prefix_skip_codes` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.variable_words.PD` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.variable_words.RO` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.variable_words.FE` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_word_types` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.end_ordinal_types` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.system_abbreviations.CLOSED COOLING WATER` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.system_abbreviations.AUX. COOLING WATER` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_by_system.CCW TI` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.sole_equipment_sheet_max` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.equipment_alias_choice.boiler_feedwater_pump` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.equipment_alias_choice.condensate_extraction_pump` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.project_abbreviations.clean_drain` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.project_abbreviations.restriction_orifice` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.equipment_modifiers.VALVE` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.equipment_modifiers.HEADER` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.equipment_modifiers.BOX` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.user_input_reasons` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_by_noun.TANK` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_by_noun.VALVE` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_by_noun.HEADER` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_pair_words` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.type_display_names.AT` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.type_display_names.AIT` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.duplicate_suffix_types` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.line_phrase_types` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_by_side.PIT ABOVE` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_by_side.PDIT ABOVE` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.position_by_side.PDIT LEFT` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.between_symbol_types` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.alarm_suffix.HH` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.alarm_suffix.H` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.alarm_suffix.LL` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.alarm_suffix.L` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.description.examples` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.qty_scope_overrides` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.excel.sheet` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.excel.first_data_row` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.excel.columns.no` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.excel.columns.pid_no` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.excel.columns.valve_type` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.excel.columns.qty` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.excel.columns.system` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.excel.columns.description` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.excel.columns.remark` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.excel.columns.tag_no` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.excel.columns.actuator` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.excel.columns.body` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.deliverables` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.valve_type_actuator.MOV` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.valve_type_actuator.MOV_I` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.valve_type_actuator.HOV` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.valve_type_actuator.CV` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.cv_tags` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |
| `cfg.valves.xv_tags` | D | ㉣-D | 도면에 없다 — 프로필·사람 지정 화면(15·18·31회차 구조) |

## 결함 (25)

| 상수 | 등급 | 판정 | 왜 이 목록인가 |
|---|---|---|---|
| `cfg.anchors.type_map.TT` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.PT` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.LT` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.PDT` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.DPIT` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.FT` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.LG` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.TI` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.PI` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.LI` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.FI` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.TIT` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.PIT` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.LIT` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.PDIT` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.FIT` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.LS` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.LSH` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.LSHH` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.LSL` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.FS` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.RO` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.FE` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.type_map.TW` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |
| `cfg.anchors.not_field` | A/D | 시험불가 | `anchors.*` 는 import 때 `_V3_FIELD_TYPE_MAP`/`RULESET_V3` 로 굳고 `_rebind_config` 이 다시 만들지 않는다 — 유도든 overlay 든 이 표에는 **닿을 수 없다** (22회차 격리의 빈 자리) |

