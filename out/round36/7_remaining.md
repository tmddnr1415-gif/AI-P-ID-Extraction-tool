# [F] 남은 일 목록 — 36회차 갱신 (35회차 다섯 목록 · ㉮㉯㉰)

| 목록 | 35회차 | 36회차 | 무엇이 움직였나 |
|---|---:|---:|---|
| 삭제 | 38 | 24(적용) + 1(열쇠) | 적용 24 = dataclass 14 + config 잎 10.  폴백 13 은 사람 지정으로, `glyph_sizes` 는 조사로 |
| 조사 | 20 | 21 | + `glyph_sizes` |
| 유도 구현 | 26 | 25 | 그대로 |
| 사람 지정 | 91 | 129 | + anchors 25 ([B]: 시험불가 → ㉣ · 발주처 표기) + 폴백 13 |
| 결함 | 25 | 0 | [B] 가 풀었다 |
| 합 | 200 | 200 | |

**외워둔 값** — 35회차 199 → **175** (목록에서 24 지움) · 목록 밖 코드 낱말 `_DEFAULT_SAME` 4 도 지웠다.  [B] 는 값을 더하지 않았다(재분류만).

㉮㉯㉰ (삭제를 뺀 나머지 175):

| 갈래 | 35회차 | 36회차 |
|---|---:|---:|
| ㉮ 어휘·문형 | 84 | 83 |
| ㉯ 범례·구조 | 45 | 59 |
| ㉰ 도면에 없음 | 33 | 33 |

## 항목별

| 상수 | 35회차 | 36회차 | 왜 |
|---|---|---|---|
| `ds.side_tol` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `ds.mark_blob` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `ds.mark_glyph_span` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `ds.mark_cluster_gap` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `ds.box_mark_margin` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `ds.note_line_gap` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `ds.mark_above` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `ds.note_mark_row_tol` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `ds.brk_max_mark` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `ds.scope_text_tol` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `ds.drop_x_tol` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `ds.drop_end_tol` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `ds.scope_box_both_edges` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `tb.title_line_tol` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `cfg.anchors.type_map.TT` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.PT` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.LT` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.PDT` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.DPIT` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.FT` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.LG` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.TI` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.PI` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.LI` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.FI` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.TIT` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.PIT` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.LIT` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.PDIT` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.FIT` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.LS` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.LSH` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.LSHH` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.LSL` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.FS` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.RO` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.FE` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.type_map.TW` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.anchors.not_field` | 결함 | **사람 지정** | [B] 재바인딩 뒤 ㉣ — 유도 없음.  `TT→TIT` 접기는 발주처 표기(D).  키 집합은 범례 ISA 표가 감사할 수 있다 |
| `cfg.vendor_marks.glyph_sizes` | 삭제 | **조사** | ㉡ 는 낯선 프로필 경로에서만 참 — 자기 프로필 문서는 `_fit_layout` 이 아무것도 얹지 않는다.  지우려면 그 경로를 바꿔야 한다 |
| `cfg.vendor_marks.x_slack` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `cfg.vendor_marks.note_row_tol` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `cfg.unit_multiplier_fallback.00` | 삭제 | **사람 지정** | 3급 폴백 — SADARA·TC2·UAD 가 읽는다.  §9 4 로 가려면 사람 지정 자리(31회차 승수 화면 같은 것)가 먼저 |
| `cfg.unit_multiplier_fallback.10` | 삭제 | **사람 지정** | 3급 폴백 — SADARA·TC2·UAD 가 읽는다.  §9 4 로 가려면 사람 지정 자리(31회차 승수 화면 같은 것)가 먼저 |
| `cfg.unit_multiplier_fallback.11` | 삭제 | **사람 지정** | 3급 폴백 — SADARA·TC2·UAD 가 읽는다.  §9 4 로 가려면 사람 지정 자리(31회차 승수 화면 같은 것)가 먼저 |
| `cfg.qty_note.same_words` | 유도 구현 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `cfg.qty_note.unit_words` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `cfg.qty_note.range_words` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `cfg.valves.legend_fallback.butterfly.tick_length` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `cfg.valves.legend_fallback.butterfly.tick_reach_radii` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `cfg.valves.legend_fallback.butterfly.bar_reach_radii` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `cfg.valves.legend_fallback.butterfly.bar_min_radii` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `cfg.valves.legend_fallback.butterfly.circle_diameter` | 삭제 | **삭제(적용)** | 36회차 [E]/[C] 에서 본선에 적용 — 회귀 넷 불변 |
| `cfg.valves.legend_fallback.actuator_stem.stem_gap` | 삭제 | **사람 지정** | 3급 폴백 — SADARA·TC2·UAD 가 읽는다.  §9 4 로 가려면 사람 지정 자리(31회차 승수 화면 같은 것)가 먼저 |
| `cfg.valves.legend_fallback.actuator_stem.stem_offaxis` | 삭제 | **사람 지정** | 3급 폴백 — SADARA·TC2·UAD 가 읽는다.  §9 4 로 가려면 사람 지정 자리(31회차 승수 화면 같은 것)가 먼저 |
| `cfg.valves.legend_fallback.actuator_stem.stem_length` | 삭제 | **사람 지정** | 3급 폴백 — SADARA·TC2·UAD 가 읽는다.  §9 4 로 가려면 사람 지정 자리(31회차 승수 화면 같은 것)가 먼저 |
| `cfg.valves.legend_fallback.actuator_stem.centre_to_body` | 삭제 | **사람 지정** | 3급 폴백 — SADARA·TC2·UAD 가 읽는다.  §9 4 로 가려면 사람 지정 자리(31회차 승수 화면 같은 것)가 먼저 |
| `cfg.valves.legend_fallback.pneumatic.dome_flat` | 삭제 | **사람 지정** | 3급 폴백 — SADARA·TC2·UAD 가 읽는다.  §9 4 로 가려면 사람 지정 자리(31회차 승수 화면 같은 것)가 먼저 |
| `cfg.valves.legend_fallback.pneumatic.dome_depth` | 삭제 | **사람 지정** | 3급 폴백 — SADARA·TC2·UAD 가 읽는다.  §9 4 로 가려면 사람 지정 자리(31회차 승수 화면 같은 것)가 먼저 |
| `cfg.valves.legend_fallback.pneumatic.dome_aspect` | 삭제 | **사람 지정** | 3급 폴백 — SADARA·TC2·UAD 가 읽는다.  §9 4 로 가려면 사람 지정 자리(31회차 승수 화면 같은 것)가 먼저 |
| `cfg.valves.legend_fallback.pneumatic.cylinder_side` | 삭제 | **사람 지정** | 3급 폴백 — SADARA·TC2·UAD 가 읽는다.  §9 4 로 가려면 사람 지정 자리(31회차 승수 화면 같은 것)가 먼저 |
| `cfg.valves.legend_fallback.pneumatic.cylinder_aspect` | 삭제 | **사람 지정** | 3급 폴백 — SADARA·TC2·UAD 가 읽는다.  §9 4 로 가려면 사람 지정 자리(31회차 승수 화면 같은 것)가 먼저 |
| `cfg.valves.legend_fallback.pneumatic.cylinder_divider` | 삭제 | **사람 지정** | 3급 폴백 — SADARA·TC2·UAD 가 읽는다.  §9 4 로 가려면 사람 지정 자리(31회차 승수 화면 같은 것)가 먼저 |
| `cfg.project.code` | 삭제 | **삭제(열쇠·본선 유지)** | 실험 장치였다.  외워둔 값이 아니다 |

(움직이지 않은 항목은 `out/round35_remaining.md` 그대로)
