# [F] 사람이 답할 것과 규칙이 답할 것 — ㉮㉯㉰ (35회차)

대상은 **삭제 목록을 뺀 나머지 162개**.  ㉮ 어휘·문형(발주처가 쓰는 낱말 — LLM 또는 규칙, **이 회차에 구현하지 않는다**) · ㉯ 범례·구조(기하 · 유도 구현 대상) · ㉰ 도면에 없음(양식 · 실무 판단 · 사람 지정).

| 갈래 | 개수 | 어디서 답이 오나 |
|---|---:|---|
| ㉮ 어휘·문형 | 84 | 발주처 리스트(557행)에서 센 값 · 프로젝트 프로필 · 다음 회차의 LLM/규칙 후보 |
| ㉯ 범례·구조 | 45 | 그 도면의 범례·본문 실물 — 유도 구현 |
| ㉰ 도면에 없음 | 33 | 발주처 양식 · 실무 판단 · 사람 지정 화면 |
| 합 | 162 | |

## ㉮ (84)

| 상수 | 등급 | 목록 |
|---|---|---|
| `cfg.anchors.type_map.TT` | A/D | 결함 |
| `cfg.anchors.type_map.PT` | A/D | 결함 |
| `cfg.anchors.type_map.LT` | A/D | 결함 |
| `cfg.anchors.type_map.PDT` | A/D | 결함 |
| `cfg.anchors.type_map.DPIT` | A/D | 결함 |
| `cfg.anchors.type_map.FT` | A/D | 결함 |
| `cfg.anchors.type_map.LG` | A/D | 결함 |
| `cfg.anchors.type_map.TI` | A/D | 결함 |
| `cfg.anchors.type_map.PI` | A/D | 결함 |
| `cfg.anchors.type_map.LI` | A/D | 결함 |
| `cfg.anchors.type_map.FI` | A/D | 결함 |
| `cfg.anchors.type_map.TIT` | A/D | 결함 |
| `cfg.anchors.type_map.PIT` | A/D | 결함 |
| `cfg.anchors.type_map.LIT` | A/D | 결함 |
| `cfg.anchors.type_map.PDIT` | A/D | 결함 |
| `cfg.anchors.type_map.FIT` | A/D | 결함 |
| `cfg.anchors.type_map.LS` | A/D | 결함 |
| `cfg.anchors.type_map.LSH` | A/D | 결함 |
| `cfg.anchors.type_map.LSHH` | A/D | 결함 |
| `cfg.anchors.type_map.LSL` | A/D | 결함 |
| `cfg.anchors.type_map.FS` | A/D | 결함 |
| `cfg.anchors.type_map.RO` | A/D | 결함 |
| `cfg.anchors.type_map.FE` | A/D | 결함 |
| `cfg.anchors.type_map.TW` | A/D | 결함 |
| `cfg.anchors.not_field` | A/D | 결함 |
| `cfg.scope.vendor_description` | D | 사람 지정 |
| `cfg.multi_signal_bundle.merged_type` | D | 사람 지정 |
| `cfg.multi_signal_bundle.description_signal` | D | 사람 지정 |
| `cfg.description.axis_mode` | D | 사람 지정 |
| `cfg.description.prefix` | D | 사람 지정 |
| `cfg.description.unit_mark` | D | 사람 지정 |
| `cfg.description.title_open` | D | 사람 지정 |
| `cfg.description.title_close` | D | 사람 지정 |
| `cfg.description.template` | D | 사람 지정 |
| `cfg.description.measured_on` | D | 사람 지정 |
| `cfg.description.note` | D | 사람 지정 |
| `cfg.description.equipment_words` | D | 사람 지정 |
| `cfg.description.position_words.pump.left` | D | 사람 지정 |
| `cfg.description.position_words.pump.right` | D | 사람 지정 |
| `cfg.description.position_words.other.left` | D | 사람 지정 |
| `cfg.description.position_words.other.right` | D | 사람 지정 |
| `cfg.description.position_words.pump_nouns` | D | 사람 지정 |
| `cfg.description.unit_prefix_skip_codes` | D | 사람 지정 |
| `cfg.description.variable_words.PD` | D | 사람 지정 |
| `cfg.description.variable_words.RO` | D | 사람 지정 |
| `cfg.description.variable_words.FE` | D | 사람 지정 |
| `cfg.description.position_word_types` | D | 사람 지정 |
| `cfg.description.end_ordinal_types` | D | 사람 지정 |
| `cfg.description.system_abbreviations.CLOSED COOLING WATER` | D | 사람 지정 |
| `cfg.description.system_abbreviations.AUX. COOLING WATER` | D | 사람 지정 |
| `cfg.description.position_by_system.CCW TI` | D | 사람 지정 |
| `cfg.description.sole_equipment_sheet_max` | D | 사람 지정 |
| `cfg.description.equipment_alias_choice.boiler_feedwater_pump` | D | 사람 지정 |
| `cfg.description.equipment_alias_choice.condensate_extraction_pump` | D | 사람 지정 |
| `cfg.description.project_abbreviations.clean_drain` | D | 사람 지정 |
| `cfg.description.project_abbreviations.restriction_orifice` | D | 사람 지정 |
| `cfg.description.equipment_modifiers.VALVE` | D | 사람 지정 |
| `cfg.description.equipment_modifiers.HEADER` | D | 사람 지정 |
| `cfg.description.equipment_modifiers.BOX` | D | 사람 지정 |
| `cfg.description.user_input_reasons` | D | 사람 지정 |
| `cfg.description.position_by_noun.TANK` | D | 사람 지정 |
| `cfg.description.position_by_noun.VALVE` | D | 사람 지정 |
| `cfg.description.position_by_noun.HEADER` | D | 사람 지정 |
| `cfg.description.position_pair_words` | D | 사람 지정 |
| `cfg.description.type_display_names.AT` | D | 사람 지정 |
| `cfg.description.type_display_names.AIT` | D | 사람 지정 |
| `cfg.description.duplicate_suffix_types` | D | 사람 지정 |
| `cfg.description.line_phrase_types` | D | 사람 지정 |
| `cfg.description.position_by_side.PIT ABOVE` | D | 사람 지정 |
| `cfg.description.position_by_side.PDIT ABOVE` | D | 사람 지정 |
| `cfg.description.position_by_side.PDIT LEFT` | D | 사람 지정 |
| `cfg.description.between_symbol_types` | D | 사람 지정 |
| `cfg.description.alarm_suffix.HH` | D | 사람 지정 |
| `cfg.description.alarm_suffix.H` | D | 사람 지정 |
| `cfg.description.alarm_suffix.LL` | D | 사람 지정 |
| `cfg.description.alarm_suffix.L` | D | 사람 지정 |
| `cfg.description.examples` | D | 사람 지정 |
| `cfg.qty_note.same_words` | ? | 유도 구현 |
| `cfg.valves.valve_type_actuator.MOV` | D | 사람 지정 |
| `cfg.valves.valve_type_actuator.MOV_I` | D | 사람 지정 |
| `cfg.valves.valve_type_actuator.HOV` | D | 사람 지정 |
| `cfg.valves.valve_type_actuator.CV` | D | 사람 지정 |
| `cfg.valves.cv_tags` | D | 사람 지정 |
| `cfg.valves.xv_tags` | D | 사람 지정 |

## ㉯ (45)

| 상수 | 등급 | 목록 |
|---|---|---|
| `ds.cap_span` | A | 유도 구현 |
| `ds.brk_corner_tol` | C | 유도 구현 |
| `ds.side_slack` | C | 유도 구현 |
| `ds.anchor_slack` | C | 유도 구현 |
| `ds.mark_side` | C | 유도 구현 |
| `ds.brk_max_gap` | A | 유도 구현 |
| `ds.brk_bridge` | A | 유도 구현 |
| `ds.brk_min_marks` | A | 유도 구현 |
| `ds.brk_min_span` | A | 유도 구현 |
| `dv.seg_span` | A | 유도 구현 |
| `dv.body_short` | A | 조사 |
| `dv.arc_above` | A | 조사 |
| `dv.tick_span` | A | 조사 |
| `dv.tick_reach` | A | 조사 |
| `dv.bar_reach` | A | 조사 |
| `dv.bar_min` | A | 조사 |
| `dv.act_box` | A | 조사 |
| `dv.bar_axis_tol` | C | 조사 |
| `dv.bar_cover` | C | 조사 |
| `dv.centre_tol` | C | 조사 |
| `dv.stem_slack` | C | 조사 |
| `dv.act_reach` | C | 조사 |
| `dv.act_offaxis` | C | 조사 |
| `dv.tag_reach` | C | 조사 |
| `tb.zoom` | A | 유도 구현 |
| `cfg.formats.drawing_no` | A | 유도 구현 |
| `cfg.formats.date` | B | 유도 구현 |
| `cfg.formats.revision` | B | 조사 |
| `cfg.formats.unit_code_segment` | B | 조사 |
| `cfg.formats.unit_code_chars` | B | 조사 |
| `cfg.formats.system_code_chars` | B | 조사 |
| `cfg.vendor_marks.blob_span` | C | 유도 구현 |
| `cfg.vendor_marks.glyph_span` | C | 유도 구현 |
| `cfg.vendor_marks.cluster_gap` | C | 유도 구현 |
| `cfg.vendor_marks.above` | C | 유도 구현 |
| `cfg.vendor_marks.note_line_gap` | C | 유도 구현 |
| `cfg.vendor_marks.package_box.edge_cover` | C | 유도 구현 |
| `cfg.vendor_marks.package_box.mark_margin` | C | 유도 구현 |
| `cfg.broken_line.brk_max_mark` | A | 유도 구현 |
| `cfg.sct_scope.text_tol` | C | 유도 구현 |
| `cfg.sct_scope.drop_x_tol` | C | 유도 구현 |
| `cfg.sct_scope.drop_end_tol` | C | 유도 구현 |
| `cfg.valves.actuator_reach` | C | 조사 |
| `cfg.valves.actuator_offaxis` | C | 조사 |
| `cfg.valves.tag_reach` | C | 유도 구현 |

## ㉰ (33)

| 상수 | 등급 | 목록 |
|---|---|---|
| `cfg.excel.sheet` | D | 사람 지정 |
| `cfg.excel.first_data_row` | D | 사람 지정 |
| `cfg.excel.columns.no` | D | 사람 지정 |
| `cfg.excel.columns.system` | D | 사람 지정 |
| `cfg.excel.columns.pid_no` | D | 사람 지정 |
| `cfg.excel.columns.type` | D | 사람 지정 |
| `cfg.excel.columns.qty` | D | 사람 지정 |
| `cfg.excel.columns.description` | D | 사람 지정 |
| `cfg.excel.columns.tag_no` | D | 사람 지정 |
| `cfg.excel.columns.scope` | D | 사람 지정 |
| `cfg.excel.columns.remark` | D | 사람 지정 |
| `cfg.revision.document_rule` | D | 사람 지정 |
| `cfg.client_form.scope_filter` | D | 사람 지정 |
| `cfg.scope.exclusion_rules` | D | 사람 지정 |
| `cfg.scope.supplier_from_notes` | D | 사람 지정 |
| `cfg.supplier_interface_span.label` | D | 사람 지정 |
| `cfg.supplier_interface_span.supplied_by` | D | 사람 지정 |
| `cfg.supplier_interface_span.description` | D | 사람 지정 |
| `cfg.multi_signal_bundle.merge_quantity` | D | 사람 지정 |
| `cfg.qty_scope_overrides` | D | 사람 지정 |
| `cfg.valves.excel.sheet` | D | 사람 지정 |
| `cfg.valves.excel.first_data_row` | D | 사람 지정 |
| `cfg.valves.excel.columns.no` | D | 사람 지정 |
| `cfg.valves.excel.columns.pid_no` | D | 사람 지정 |
| `cfg.valves.excel.columns.valve_type` | D | 사람 지정 |
| `cfg.valves.excel.columns.qty` | D | 사람 지정 |
| `cfg.valves.excel.columns.system` | D | 사람 지정 |
| `cfg.valves.excel.columns.description` | D | 사람 지정 |
| `cfg.valves.excel.columns.remark` | D | 사람 지정 |
| `cfg.valves.excel.columns.tag_no` | D | 사람 지정 |
| `cfg.valves.excel.columns.actuator` | D | 사람 지정 |
| `cfg.valves.excel.columns.body` | D | 사람 지정 |
| `cfg.valves.deliverables` | D | 사람 지정 |

