# [B] 지울 목록 — 35회차

기준: `out/constants_by_source.md`(25회차 분류 · **34회차 갱신본은 이 저장소에 없다** — 27·31회차가 더한 `qty_note` 등은 "애매하면 지우는 쪽" 규칙으로 넣었다).
지운다 = 등급 **A · B · C · D**.  남긴다 = **E**(알고리즘·UI) · **✔**(이미 유도).

## 합계 — dataclass 39 + config 160 = **199**

25회차의 193 과 다른 이유: config 잎이 210 → 216 으로 늘었고(`qty_note` 3 · `cv_tags`·`xv_tags` 등), 
그 표는 묶음 단위로 세어 71+210=281 과 3 차이가 있었다.  이 목록은 **항목 단위**다.

## 1. dataclass 기본값 (코드 고정분 포함) — 지우는 법: 기본값을 `MISSING` sentinel 로

| 파일:줄 | 필드 | 현재 값 | 등급 |
|---|---|---|---|
| `app/engine/detect_symbols.py:187` | `cap_span` | `(7.0, 50.0)` | A |
| `app/engine/detect_symbols.py:189` | `brk_corner_tol` | `3.0` | C |
| `app/engine/detect_symbols.py:190` | `side_tol` | `0.8` | C |
| `app/engine/detect_symbols.py:191` | `side_slack` | `1.5` | C |
| `app/engine/detect_symbols.py:192` | `anchor_slack` | `3.0` | C |
| `app/engine/detect_symbols.py:195` | `mark_blob` | `(1.5, 8.0)` | A/C |
| `app/engine/detect_symbols.py:196` | `mark_glyph_span` | `(3.0, 8.0)` | A/C |
| `app/engine/detect_symbols.py:197` | `mark_cluster_gap` | `2.0` | A/C |
| `app/engine/detect_symbols.py:200` | `box_mark_margin` | `20.0` | C |
| `app/engine/detect_symbols.py:201` | `note_line_gap` | `20.0` | A |
| `app/engine/detect_symbols.py:202` | `mark_above` | `25.0` | C |
| `app/engine/detect_symbols.py:213` | `mark_side` | `10.0` | C |
| `app/engine/detect_symbols.py:214` | `note_mark_row_tol` | `6.0` | C |
| `app/engine/detect_symbols.py:217` | `brk_max_mark` | `20.0` | A |
| `app/engine/detect_symbols.py:218` | `brk_max_gap` | `6.0` | A |
| `app/engine/detect_symbols.py:219` | `brk_bridge` | `26.0` | A |
| `app/engine/detect_symbols.py:220` | `brk_min_marks` | `6` | A |
| `app/engine/detect_symbols.py:221` | `brk_min_span` | `40.0` | A |
| `app/engine/detect_symbols.py:224` | `scope_text_tol` | `30.0` | C |
| `app/engine/detect_symbols.py:225` | `drop_x_tol` | `2.0` | C |
| `app/engine/detect_symbols.py:226` | `drop_end_tol` | `1.5` | C |
| `app/engine/detect_symbols.py:230` | `scope_box_both_edges` | `False` | D |
| `app/engine/detect_valves.py:183` | `seg_span` | `(1.0, 60.0)` | A |
| `app/engine/detect_valves.py:184` | `body_short` | `(5.0, 30.0)` | A |
| `app/engine/detect_valves.py:192` | `arc_above` | `6.0` | A |
| `app/engine/detect_valves.py:195` | `tick_span` | `(1.5, 6.0)` | A |
| `app/engine/detect_valves.py:196` | `tick_reach` | `1.3` | A |
| `app/engine/detect_valves.py:199` | `bar_reach` | `3.4` | A |
| `app/engine/detect_valves.py:200` | `bar_min` | `1.1` | A |
| `app/engine/detect_valves.py:229` | `act_box` | `(9.0, 34.0)` | A |
| `app/engine/detect_valves.py:186` | `bar_axis_tol` | `0.8` | C |
| `app/engine/detect_valves.py:187` | `bar_cover` | `1.2` | C |
| `app/engine/detect_valves.py:189` | `centre_tol` | `2.0` | C |
| `app/engine/detect_valves.py:207` | `stem_slack` | `-1.0` | C |
| `app/engine/detect_valves.py:223` | `act_reach` | `90.0` | C |
| `app/engine/detect_valves.py:224` | `act_offaxis` | `12.0` | C |
| `app/engine/detect_valves.py:232` | `tag_reach` | `190.0` | C |
| `app/engine/extract_titleblocks.py:106` | `title_line_tol` | `6.0` | A |
| `app/engine/extract_titleblocks.py:122` | `zoom` | `24.0` | A |

## 2. config 잎 (`config/project_alnouf1.yaml`) — 지우는 법: 키 제거 (+ 그 키가 채우는 dataclass 필드도 sentinel)

| 키 | 현재 값 | 등급 |
|---|---|---|
| `formats.drawing_no` | `"^[A-Z0-9]{4}-[A-Z0-9]{7}-[A-Z0-9]{3}-\\d{4}$"` | A |
| `formats.date` | `"^\\d{1,2}\\.\\s?[A-Z]{3}\\.\\d{4}$"` | B |
| `formats.revision` | `"^[A-Z][0-9]?$"` | B |
| `formats.unit_code_segment` | `1` | B |
| `formats.unit_code_chars` | `[0, 2]` | B |
| `formats.system_code_chars` | `[2, 5]` | B |
| `excel.sheet` | `"2.0_Instrument List"` | D |
| `excel.first_data_row` | `8` | D |
| `excel.columns.no` | `1` | D |
| `excel.columns.system` | `6` | D |
| `excel.columns.pid_no` | `7` | D |
| `excel.columns.type` | `8` | D |
| `excel.columns.qty` | `9` | D |
| `excel.columns.description` | `10` | D |
| `excel.columns.tag_no` | `5` | D |
| `excel.columns.scope` | `37` | D |
| `excel.columns.remark` | `41` | D |
| `anchors.type_map.TT` | `"TIT"` | A/D |
| `anchors.type_map.PT` | `"PIT"` | A/D |
| `anchors.type_map.LT` | `"LIT"` | A/D |
| `anchors.type_map.PDT` | `"PDIT"` | A/D |
| `anchors.type_map.DPIT` | `"PDIT"` | A/D |
| `anchors.type_map.FT` | `"FIT"` | A/D |
| `anchors.type_map.LG` | `"LI"` | A/D |
| `anchors.type_map.TI` | `"TI"` | A/D |
| `anchors.type_map.PI` | `"PI"` | A/D |
| `anchors.type_map.LI` | `"LI"` | A/D |
| `anchors.type_map.FI` | `"FI"` | A/D |
| `anchors.type_map.TIT` | `"TIT"` | A/D |
| `anchors.type_map.PIT` | `"PIT"` | A/D |
| `anchors.type_map.LIT` | `"LIT"` | A/D |
| `anchors.type_map.PDIT` | `"PDIT"` | A/D |
| `anchors.type_map.FIT` | `"FIT"` | A/D |
| `anchors.type_map.LS` | `"LS"` | A/D |
| `anchors.type_map.LSH` | `"LS"` | A/D |
| `anchors.type_map.LSHH` | `"LS"` | A/D |
| `anchors.type_map.LSL` | `"LS"` | A/D |
| `anchors.type_map.FS` | `"FS"` | A/D |
| `anchors.type_map.RO` | `"RO"` | A/D |
| `anchors.type_map.FE` | `"FE"` | A/D |
| `anchors.type_map.TW` | `"TW"` | A/D |
| `anchors.not_field` | `[]` | A/D |
| `revision.document_rule` | `"max"` | D |
| `client_form.scope_filter` | `"all"` | D |
| `scope.exclusion_rules` | `"none"` | D |
| `scope.supplier_from_notes` | `"\\bBY\\s+(?P<name>[^.]+?)\\s*\\.?\\s*$"` | D |
| `scope.vendor_description` | `"skip"` | D |
| `vendor_marks.glyph_sizes` | `[[4.0, 4.0], [5.2, 5.2]]` | A |
| `vendor_marks.blob_span` | `[1.5, 8.0]` | C |
| `vendor_marks.glyph_span` | `[3.0, 8.0]` | C |
| `vendor_marks.cluster_gap` | `2.0` | C |
| `vendor_marks.above` | `25.0` | C |
| `vendor_marks.x_slack` | `6.0` | C |
| `vendor_marks.note_row_tol` | `6.0` | C |
| `vendor_marks.note_line_gap` | `20.0` | C |
| `vendor_marks.package_box.edge_cover` | `0.35` | C |
| `vendor_marks.package_box.mark_margin` | `20.0` | C |
| `broken_line.brk_max_mark` | `28.3` | A |
| `sct_scope.text_tol` | `30.0` | C |
| `sct_scope.drop_x_tol` | `2.0` | C |
| `sct_scope.drop_end_tol` | `1.5` | C |
| `supplier_interface_span.label` | `"공급자 인터페이스 구간 — 배관 및 기기 공급자 범위"` | D |
| `supplier_interface_span.supplied_by` | `""` | D |
| `supplier_interface_span.description` | `"keep"` | D |
| `multi_signal_bundle.merge_quantity` | `true` | D |
| `multi_signal_bundle.merged_type` | `"LS"` | D |
| `multi_signal_bundle.description_signal` | `"representative"` | D |
| `description.axis_mode` | `"mixed"` | D |
| `description.prefix` | `"UNIT"` | D |
| `description.unit_mark` | `"#"` | D |
| `description.title_open` | `["FOR"]` | D |
| `description.title_close` | `["SYSTEM"]` | D |
| `description.template` | `"UNIT #{unit} {system} {variable}"` | D |
| `description.measured_on` | `"발주처 계기 리스트 557행 (data/CZE_Field_Instrument.xlsx)"` | D |
| `description.note` | `"접미(A/B/C, HIGH HIGH)와 중간 서술은 도면에 없어 템플릿에 넣지 않았습니다"` | D |
| `description.equipment_words` | `["PUMP", "COOLER", "TANK", "HEATER", "HEX", "EXCHANGER", "SKID", "CEP"` | D |
| `description.position_words.pump.left` | `"SUCTION"` | D |
| `description.position_words.pump.right` | `"DISCHARGE"` | D |
| `description.position_words.other.left` | `"INLET"` | D |
| `description.position_words.other.right` | `"OUTLET"` | D |
| `description.position_words.pump_nouns` | `["PUMP", "CEP", "BFP"]` | D |
| `description.unit_prefix_skip_codes` | `["00"]` | D |
| `description.variable_words.PD` | `["DIFFERENTIAL", "PRESSURE"]` | D |
| `description.variable_words.RO` | `["RESTRICTION", "ORIFICE"]` | D |
| `description.variable_words.FE` | `["FLOW", "ELEMENT"]` | D |
| `description.position_word_types` | `["PIT", "PDIT", "FS", "FIT", "FE"]` | D |
| `description.end_ordinal_types` | `["PIT", "TIT", "FIT", "PDIT"]` | D |
| `description.system_abbreviations.CLOSED COOLING WATER` | `"CCW"` | D |
| `description.system_abbreviations.AUX. COOLING WATER` | `"ACW"` | D |
| `description.position_by_system.CCW TI` | `"RETURN"` | D |
| `description.sole_equipment_sheet_max` | `2` | D |
| `description.equipment_alias_choice.boiler_feedwater_pump` | `"BOILER FEED WATER PUMP"` | D |
| `description.equipment_alias_choice.condensate_extraction_pump` | `"CEP"` | D |
| `description.project_abbreviations.clean_drain` | `["CD", "CLEAN DRAIN"]` | D |
| `description.project_abbreviations.restriction_orifice` | `["RO", "RESTRICTION ORIFICE"]` | D |
| `description.equipment_modifiers.VALVE` | `["BYPASS", "LETDOWN", "CONTROL", "MODULATING", "SHOTDOWN", "SHUTDOWN",` | D |
| `description.equipment_modifiers.HEADER` | `["DISCHARGE", "STEAM", "SEAL", "RING", "OUTLET", "SUCTION"]` | D |
| `description.equipment_modifiers.BOX` | `["WATER", "FLASH"]` | D |
| `description.user_input_reasons` | `[{"types": ["PDIT"], "noun": "PUMP", "needs_subject": true, "code": "D` | D |
| `description.position_by_noun.TANK` | `""` | D |
| `description.position_by_noun.VALVE` | `"DOWNSTREAM"` | D |
| `description.position_by_noun.HEADER` | `"DISCHARGE"` | D |
| `description.position_pair_words` | `["DISCHARGE", "SUCTION", "RETURN", "SUPPLY", "OUTLET", "INLET", "DOWNS` | D |
| `description.type_display_names.AT` | `"Analyzer"` | D |
| `description.type_display_names.AIT` | `"Analyzer"` | D |
| `description.duplicate_suffix_types` | `[]` | D |
| `description.line_phrase_types` | `["LS"]` | D |
| `description.position_by_side.PIT ABOVE` | `"DISCHARGE"` | D |
| `description.position_by_side.PDIT ABOVE` | `"SUCTION"` | D |
| `description.position_by_side.PDIT LEFT` | `"SUCTION"` | D |
| `description.between_symbol_types` | `["PDIT"]` | D |
| `description.alarm_suffix.HH` | `["HIGH", "HIGH"]` | D |
| `description.alarm_suffix.H` | `["HIGH"]` | D |
| `description.alarm_suffix.LL` | `["LOW", "LOW"]` | D |
| `description.alarm_suffix.L` | `["LOW"]` | D |
| `description.examples` | `[]` | D |
| `unit_multiplier_fallback.00` | `1` | A |
| `unit_multiplier_fallback.10` | `2` | A |
| `unit_multiplier_fallback.11` | `4` | A |
| `qty_note.same_words` | `["IDENTICAL", "SIMILAR", "SAME", "TYPICAL"]` | ?(27회차 신설 · 애매→지움) |
| `qty_note.unit_words` | `["GROUP", "UNIT", "TRAIN"]` | ?(27회차 신설 · 애매→지움) |
| `qty_note.range_words` | `["THRU", "THROUGH", "~"]` | ?(27회차 신설 · 애매→지움) |
| `qty_scope_overrides` | `[{"keyword": "PLANT COMMON", "multiplier": 1}]` | D |
| `valves.actuator_reach` | `90.0` | C |
| `valves.actuator_offaxis` | `12.0` | C |
| `valves.tag_reach` | `190.0` | C |
| `valves.excel.sheet` | `"3.0_Valve List"` | D |
| `valves.excel.first_data_row` | `8` | D |
| `valves.excel.columns.no` | `1` | D |
| `valves.excel.columns.pid_no` | `2` | D |
| `valves.excel.columns.valve_type` | `3` | D |
| `valves.excel.columns.qty` | `4` | D |
| `valves.excel.columns.system` | `5` | D |
| `valves.excel.columns.description` | `12` | D |
| `valves.excel.columns.remark` | `39` | D |
| `valves.excel.columns.tag_no` | `11` | D |
| `valves.excel.columns.actuator` | `25` | D |
| `valves.excel.columns.body` | `27` | D |
| `valves.deliverables` | `[{"tag": "CZI", "path": "data/CZI_Butterfly_Valve.xlsx", "bodies": ["B` | D |
| `valves.valve_type_actuator.MOV` | `"MOTOR"` | D |
| `valves.valve_type_actuator.MOV_I` | `"MOTOR"` | D |
| `valves.valve_type_actuator.HOV` | `"HYDRAULIC"` | D |
| `valves.valve_type_actuator.CV` | `"PNEUMATIC"` | D |
| `valves.cv_tags` | `["FCV", "LCV", "PCV", "TCV", "CV"]` | D |
| `valves.xv_tags` | `["XV", "HV"]` | D |
| `valves.legend_fallback.butterfly.tick_length` | `3.0` | A |
| `valves.legend_fallback.butterfly.tick_reach_radii` | `1.498` | A |
| `valves.legend_fallback.butterfly.bar_reach_radii` | `2.822` | A |
| `valves.legend_fallback.butterfly.bar_min_radii` | `2.378` | A |
| `valves.legend_fallback.butterfly.circle_diameter` | `6.06` | A |
| `valves.legend_fallback.actuator_stem.stem_gap` | `0.0` | A |
| `valves.legend_fallback.actuator_stem.stem_offaxis` | `0.03` | A |
| `valves.legend_fallback.actuator_stem.stem_length` | `19.86` | A |
| `valves.legend_fallback.actuator_stem.centre_to_body` | `26.97` | A |
| `valves.legend_fallback.pneumatic.dome_flat` | `14.22` | A |
| `valves.legend_fallback.pneumatic.dome_depth` | `7.11` | A |
| `valves.legend_fallback.pneumatic.dome_aspect` | `0.5` | A |
| `valves.legend_fallback.pneumatic.cylinder_side` | `14.16` | A |
| `valves.legend_fallback.pneumatic.cylinder_aspect` | `1.003` | A |
| `valves.legend_fallback.pneumatic.cylinder_divider` | `0.5` | A |

## 3. 등급별

| 등급 | 개수 |
|---|---:|
| ?(27회차 신설 · 애매→지움) | 3 |
| A | 38 |
| A/C | 3 |
| A/D | 25 |
| B | 5 |
| C | 33 |
| D | 92 |

## 4. 남기는 것 (지우지 않는다)

* E — `ds.cap_ratio` · `ds.box_edge_cover` · `dv.body_ratio/waist_ratio/disc_aspect/dome_aspect/cyl_aspect` · `tb.hist_row_inset/grid/ink_frac/blank_above/min_ink_px/char_gap_px/ratio_high/ratio_medium` · config `project.* sheet.* matching.* review_markup.* review_axes.* description.llm.* valves.disabled_rules`
* ✔ — `ds.drawing_area/notes_area/notes_text_x_max` · `dv.drawing_area/dome_flat/cyl_side/cyl_divider` · `tb` 칸 12 · config `regions.* title_block.*`

⚠ `sheet.width_pt/height_pt` 는 ✔(유도)로 두었다 — `_fit_layout` 이 그 문서에서 잰다.  `project.code/name` 은 프로필 열쇠라 E 로 두었다;
다만 **이 둘이 남아 있으면 `_fit_layout` 이 "프로필이 그 문서의 것" 이라 판단해 유도값을 안 얹는다** (24회차 [6]).
그러면 지운 자리에 유도값이 들어올 길이 없으므로, [C] 에서는 `project.code` 도 비운다 (경계가 애매하면 지우는 쪽).  → 실제 지우는 수 +1 = **200**.
