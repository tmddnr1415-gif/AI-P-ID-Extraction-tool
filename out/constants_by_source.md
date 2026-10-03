# 상수 재분류 — 도면의 어디에서 말하는가 (§9 [A])

**코드 0줄.  분류만 한다.**  대상은 23회차 상수표 — dataclass 기본값 71개 + config 잎 210개.
등급: **A** 인쇄돼 있고 코드가 이미 찾는데 안 쓴다 → 즉시 · **B** 인쇄돼 있는데 코드가 안 찾는다 → 읽기 추가 ·
**C** 범례에 없고 본문 실물에서 잰다 · **D** 도면 어디에도 없다 → 사람 지정 · **E** 도면과 무관 · **✔** 이미 도면에서 유도한다.

## 0. 등급별 개수

| 등급 | 개수 | 뜻 |
| --- | ---: | --- |
| A | 38 | 찾는데 안 쓴다 — 가장 값싸다 |
| A/C | 3 | 정의줄이 획이면 A · 텍스트면 C (25회차 별표) |
| A/D | 25 | 범례 ISA 표는 A · 발주처 접기는 D |
| B | 5 | 인쇄돼 있는데 안 찾는다 |
| C | 30 | 본문 실물에서 잰다 |
| D | 92 | 도면에 없다 — 사람·발주처 |
| E | 48 | 도면과 무관 |
| ✔ | 37 | 이미 유도 |
| 합 | 278 | (묶음 단위로 세어 71+210=281 과 3 차이) |

**★ A 는 38개(+ A/C 3 · A/D 25)** — 코드가 이미 찾아 둔 것을 쓰기만 하면 된다.  
**B 는 5개**뿐이다 — "안 찾는" 것은 적다.  **C 30 · D 92** 가 범용성의 실제 한계이고, D 의 대부분(발주처 표기 49 · 양식 23 · 실무 판단 15)은 **도면이 아니라 발주처가 말하는 것**이라 프로필이 맞는 자리다.  
E 를 뺀 **외워둔 값의 진짜 수 = 193** (A·B·C·D 합, 이미 유도한 ✔ 제외).

## 1. 표

| 파라미터 | 값/개수 | 도면의 어디에 있는가 | 코드가 이미 찾는가 | 쓰고 있는가 | 등급 | 비고 |
| --- | --- | --- | --- | --- | --- | --- |
| `ds.drawing_area/notes_area/notes_text_x_max` | 3 | 도면틀 괘선 (본문) | 찾는다(derive_layout) | 쓴다 | **✔** | 22회차부터 유도 |
| `ds.cap_span` | (7,50)pt | 범례 계기 버블 그림 | 찾는다(legend_rules circle_diameter) | 안 쓴다 | **A** | 버블 크기는 범례가 그린다 · 실제로는 모양 규칙이라 A3 도 통과 |
| `ds.cap_ratio` | (1.6,2.4) | —(비율) | — | — | **E** | 비율 — 축척을 넘는다 (23회차 확인) |
| `ds.brk_corner_tol/side_tol/side_slack/anchor_slack` | 4 | 본문 선의 정밀도 | 안 찾는다 | — | **C** | 콜리니어 간격 분포로 잴 수 있다 (5회차 표준 끊김과 같은 방법) |
| `ds.mark_blob/mark_glyph_span/mark_cluster_gap` | 3 | NOTES 정의줄의 별표 (AL NOUF1 획 · TC2 텍스트) | 찾는다(read_mark_dictionary glyph_size) | 안 쓴다 — path 마다 상수를 먼저 건다 | **A/C** | ★ 25회차 뿌리.  정의줄이 텍스트면 본문 실물(C) |
| `ds.box_edge_cover` | 0.35 | —(비율) | — | — | **E** |  |
| `ds.box_mark_margin` | 20.0pt | 본문 상자 테두리 띠 | 안 찾는다 | — | **C** | 상자 선 두께·별표 크기 비례로 |
| `ds.note_line_gap` | 20.0pt | NOTES 줄 간격 | 찾는다(_notes_lines 가 줄을 세운다) | 안 쓴다 | **A** | 줄 간격 분포가 이미 손에 있다 |
| `ds.mark_above/mark_side/note_mark_row_tol` | 3 | 본문 — 버블 크기에 비례 | 안 찾는다 | — | **C** | 19회차 실측은 AL NOUF1 한 문서 |
| `ds.brk_max_mark/brk_max_gap/brk_bridge/brk_min_marks/brk_min_span` | 5 | 범례 p2 선 종류 표 (체인 파선) | 찾는다(derive_line_styles · _fit_layout brk_*) | 일부 — brk_* 는 UNAVAILABLE 로 버린다 | **A** | line_styles 는 범례에서 읽어 쓴다.  같은 표의 파선 주기를 brk_* 에 안 쓴다 |
| `ds.scope_text_tol/drop_x_tol/drop_end_tol` | 3 | 본문 | 안 찾는다 | — | **C** |  |
| `ds.scope_box_both_edges` | False | 도면에 없다 (판정 방식) | — | — | **D** | 실무 판단 · sct_scope 와 같은 항목 |
| `dv.drawing_area` | 1 | 도면틀 | 찾는다 | 쓴다 | **✔** |  |
| `dv.body_ratio/waist_ratio/disc_aspect/dome_aspect/cyl_aspect` | 5 | —(비율) | — | — | **E** | 비율 — TC2 몸체 389개가 이것으로 잡혔다 |
| `dv.seg_span/body_short/arc_above/tick_span/tick_reach/bar_reach/bar_min/act_box` | 8 | 범례 p2·p3 밸브 몸체·액추에이터 그림 | 찾는다(legend_rules butterfly/actuator_stem/pneumatic) | 일부 — 세 항목만 쓴다 | **A** | 범례가 몸체를 그린다.  TC2 범례는 액추에이터를 몸체 없이 그려 스템이 없다(23회차 ㉣) |
| `dv.bar_axis_tol/bar_cover/centre_tol/stem_slack` | 4 | 본문 선의 정밀도 | 안 찾는다 | — | **C** |  |
| `dv.dome_flat/cyl_side/cyl_divider` | 3 | 범례 p3 | 찾는다(legend_rules) | 쓴다 | **✔** | 범례 유도 |
| `dv.act_reach/act_offaxis/tag_reach` | 3 | 본문 — 버블·몸체 크기 비례 | 안 찾는다 | — | **C** |  |
| `tb.dwg_no/title/rev/sheet/project_name 칸 + *_min_height + hist_* 5` | 12 | 타이틀블록 캡션 · 이력 표 괘선 | 찾는다 | 쓴다 | **✔** | 22·24회차 |
| `tb.hist_row_inset` | 1.2 | 그리지 않는 값 (여백) | — | — | **E** | 24회차 |
| `tb.title_line_tol` | 6.0 | 제목 칸 글줄 간격 | 찾는다(캡션·글자 높이) | 안 쓴다 | **A** |  |
| `tb.zoom` | 24.0 | 본문 글자 높이에 비례해야 함 | 찾는다(title_min_height 를 잰다) | 안 쓴다 | **A** | A3 에서 글자가 절반 픽셀 |
| `tb.grid/ink_frac/blank_above/min_ink_px/char_gap_px/ratio_high/ratio_medium` | 7 | —(판독 알고리즘) | — | — | **E** | char_gap_px 는 글자 높이 비례가 맞다 → 후보 C |
| `cfg.anchors.type_map + anchors` | 25 | 범례 p3 ISA 문자표 (+ 발주처 TYPE 표기) | 찾는다(isa_table.py 런타임 파싱) | 일부 — 앵커 사전은 config | **A/D** | TT→TIT 같은 접기는 발주처 표기(D) |
| `cfg.description.* (llm 4 제외)` | 49 | 도면에 없다 — 발주처 557행에서 센 값 | — | — | **D** | 발주처 리스트 · 프로젝트 프로필 자리가 맞다 |
| `cfg.description.llm` | 4 | — | — | — | **E** | 기본 꺼짐 |
| `cfg.review_axes.* · review_markup · matching · project` | 28 | —(UI·운영) | — | — | **E** |  |
| `cfg.valves.legend_fallback` | 15 | 범례 p2·p3 | 찾는다(legend_rules) | 쓴다 — 못 읽으면 조용히 이 값 | **A** | ★ 범례 값과 같은 숫자라 폴백이 조용하다 (15회차) |
| `cfg.title_block (13)` | 13 | 타이틀블록 캡션 · 이력 표 | 찾는다 | 쓴다 | **✔** |  |
| `cfg.title_block.hist_row_inset` | 1 | 그리지 않는 값 | — | — | **E** |  |
| `cfg.valves.excel · excel.columns · excel` | 23 | 발주처 양식 xlsx | 찾는다(양식 파일을 연다) | 일부 | **D** | 양식이 말한다 — 도면이 아니라 |
| `cfg.vendor_marks.glyph_sizes` | 1 | NOTES 정의줄 별표 | 찾는다(_vendor_notation) | 쓴다 — 빈 값도 덮는다 | **A** | ★ 25회차 ① |
| `cfg.vendor_marks 나머지 + package_box` | 9 | 본문 — 버블·상자 크기 비례 | 안 찾는다 | — | **C** |  |
| `cfg.valves.actuator_reach/offaxis/tag_reach` | 3 | 본문 | 안 찾는다 | — | **C** |  |
| `cfg.valves.valve_type_actuator` | 4 | 도면에 없다 — 발주처 VALVE TYPE 표기 | — | — | **D** |  |
| `cfg.formats.drawing_no` | 1 | 타이틀블록 도면번호 칸의 낱말 | 찾는다(칸은 유도) | 안 쓴다 — 형식은 config | **A** | 23회차 ㉡ · TC2 56/60 |
| `cfg.formats 나머지 (date · revision · unit_code_*)` | 5 | 타이틀블록 이력 표 · 도면번호 | 일부 | 안 쓴다 | **B** |  |
| `cfg.regions · sheet` | 5 | 도면틀 | 찾는다 | 쓴다 | **✔** |  |
| `cfg.scope · sct_scope · supplier_interface_span · multi_signal_bundle · revision · client_form · qty_scope_overrides` | 15 | 도면에 없다 — 발주처·실무 판단 | — | — | **D** |  |
| `cfg.unit_multiplier_fallback` | 3 | 범례 p5 승수표 | 찾는다(projectconfig 승수표 파싱) | 쓴다 — 못 읽으면 조용히 이 값 | **A** | ★ 23회차 ㉢ · TC2 262/607 Q'ty 못 셈 · SADARA 82행 전부 None |
| `cfg.broken_line.brk_max_mark` | 1 | 범례 p2 선 종류 표 | 찾는다(_fit_layout · UNAVAILABLE) | 안 쓴다 | **A** | 23회차 ㉤ |

## 2. 이 표가 정하는 순서 (후보 — 결정하지 않는다)

A 부터.  한 회차에 여럿 해도 된다 — 코드가 이미 찾아 둔 값을 쓰는 것이라 위험이 낮다.

| 후보 | 등급 | 무엇 | 왜 이 순서인가 |
| --- | --- | --- | --- |
| 1 | A | **별표** — 정의줄·본문의 별표를 획의 관계로 읽는다 (25회차 진행 중) | 현장 보고 · TC2 SCOPE 전체가 걸려 있다 |
| 2 | A | **승수표** `unit_multiplier_fallback` — 머리말 철자 허용 · 2행 허용 · 못 읽으면 멈춤 | TC2 Q'ty 262/607 · SADARA 82행 전부 None · 축3 예측 +7.2 |
| 3 | A | **`vendor_marks.glyph_sizes` 빈 값 덮기** · `valves.legend_fallback` 조용한 폴백 → 시끄럽게 | 한 줄짜리 · 15회차부터 적혀 있던 것 |
| 4 | A | **`formats.drawing_no`** — 도면번호 칸의 낱말에서 자릿수를 센다 | TC2 56/60 · 축3 예측 +1.1 |
| 5 | A | **`brk_max_mark`** — 범례 선 종류 표의 파선 주기를 쓴다 | TC2 가 AL NOUF1 값 28.3 으로 판정 중 |
| 6 | C | 마크 창 `mark_above/side` · `act_box` — 버블·몸체 크기 **비례**로 | 23회차 §6 절대 pt 목록 |
| 7 | B | `formats.date/revision/unit_code_*` | 작다 |
| — | D | 발주처 표기 49 · 양식 23 · 실무 판단 15 | **프로필·사람 지정 화면**(15·18회차 재사용) — 도면에서 읽을 것이 아니다 |
