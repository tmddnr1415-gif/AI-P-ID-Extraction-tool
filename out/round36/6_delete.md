# [E] 삭제 목록 38 → 본선에 적용할 수 있는 것과 없는 것

35회차 삭제 목록 38 = ㉠ 18 + ㉡ 20.  **적용 전에 "누가 그 값을 읽는가" 를 네 프로젝트 저장 결과로 다시 셌다.**
35회차의 ㉡ 판정은 **AL NOUF1 한 문서**의 실측이었고, [E] 게이트는 **네 프로젝트** 지문·행·Q'ty 불변이다.

## E-0 적용할 수 없는 것 — 14 (다른 프로젝트가 그 값으로 돌고 있다)

| 항목 | 개수 | 누가 읽나 (저장 결과 `legend.*.source` / `multipliers.source`) | 지우면 |
| --- | ---: | --- | --- |
| `valves.legend_fallback.actuator_stem.*` | 4 | **SADARA · TC2 · UAD** 전부 `CONFIG_FALLBACK` (범례가 스템을 안 그린다 — 23회차 ㉣) | 세 프로젝트의 액추에이터 판정이 멈춘다 |
| `valves.legend_fallback.pneumatic.*` | 6 | **SADARA** `CONFIG_FALLBACK` | SADARA 공압 판정이 멈춘다 |
| `unit_multiplier_fallback.00/10/11` | 3 | **TC2 203행 · UAD 149행** `MULTIPLIER_FROM_CONFIG` | TC2 Q'ty 3047 → 2844 · UAD 149 → 0 (전부 빈칸) |
| `project.code` | 1 | 프로필 열쇠 — 35회차가 "실험 장치, 본선에서는 남긴다" 고 적었다 | — |

**35회차 [F] 의 "삭제" 판정 중 13개는 틀렸다** — "유도가 이미 이기고 있던 죽은 코드" 는 AL NOUF1 에서만 참이고,
그 값들은 세 프로젝트의 **3급 폴백**이다.  §9 4(못 읽으면 멈춘다)로 가려면 그 세 프로젝트에 **사람 지정 자리**(31회차
승수 화면과 같은 것)가 먼저 있어야 한다 — 다음 회차 후보.  이 회차에서는 게이트가 막는다.

## E-0′ 적용할 수 없는 것 — 1 (㉡ 가 낯선 프로필 경로에서만 참이다)

`vendor_marks.glyph_sizes` — 35회차는 "58장 유도값 = 설정값" 으로 ㉡·삭제로 뒀다.  그런데 그 유도값이 **얹히는** 것은
낯선 프로필 경로뿐이다: `_fit_layout` 은 프로필이 그 문서의 것이고 기하를 적고 있으면 `values = {}` 로 **아무것도 얹지
않는다**(24회차 [6]).  AL NOUF1 에서 이 잎을 지우면 유도값이 들어오는 길이 없고 `KNOWN_GLYPH_SIZES` 가 `()` 가 된다.
35회차 묶음 토글이 "지워도 같다" 고 본 것은 그 실험이 `project.code` 를 표식으로 바꿔 **낯선 경로를 강제**했기 때문이다.
→ **스스로 뒤집은 판단** — 이 회차에서 지우지 않는다.  지우려면 `_fit_layout` 이 "설정에 없는 키" 는 자기 문서에서도
얹게 바뀌어야 하고, 그것은 AL NOUF1 판정을 유도값에 맡기는 별도 회차다.

## E-1 dataclass 기본값 — 14 (한 커밋)

| 필드 | 현재 | 한 것 | 근거 |
| --- | --- | --- | --- |
| `ds.side_tol` | 0.8 | **필드째 삭제** | 코드 참조 0 (정의뿐) |
| `ds.note_mark_row_tol` | 6.0 | **필드째 삭제** + `_layout_from_config` 의 대입 삭제 | 정의·대입 외 참조 0 |
| `ds.mark_blob` · `mark_glyph_span` · `mark_cluster_gap` · `mark_above` · `note_line_gap` · `box_mark_margin` · `scope_text_tol` · `drop_x_tol` · `drop_end_tol` · `brk_max_mark` | 각 수 | 기본값 `None` · config 를 **`cfg.get` 필수**로 | config 잎이 언제나 덮었다 — 같은 수가 두 곳.  두 프로필(`alnouf1`·`sadara`) 모두 열 키를 전부 갖는다(실측).  없으면 시작 때 `ConfigError: required setting … is missing` 으로 멈춘다 (§9 4) |
| `ds.scope_box_both_edges` | False | 기본값 `None` | `bool(config)` 로 언제나 덮인다 |
| `tb.title_line_tol` | 6.0 | 기본값 `None` · `cfg.get` 필수 | 두 프로필 다 `title_block.title_line_tol` 을 갖는다 |

**죽은 참조 확인**: `side_tol`·`note_mark_row_tol`·`x_slack` 을 읽는 코드 0 (grep · 아래 [E-2] 의 config 잎과 짝).

## E-2 config 잎 — 9 (한 커밋)

| 잎 | 근거 |
| --- | --- |
| `vendor_marks.x_slack` (alnouf1 · sadara) | 코드 참조 0 — 19회차가 창을 `mark_side` 로 바꾼 뒤 남은 고아 |
| `vendor_marks.note_row_tol` (alnouf1 · sadara) | 읽던 필드(`note_mark_row_tol`)를 [E-1] 에서 지웠다 |
| `qty_note.unit_words` · `qty_note.range_words` | 코드 기본값(`_DEFAULT_UNIT`·`_DEFAULT_RANGE`)과 같은 값 — 프로젝트가 늘릴 때만 적는 자리 |
| `valves.legend_fallback.butterfly.*` 5 | 네 프로젝트 전부 `LEGEND` — 폴백을 읽은 적이 없다.  없으면 `legend_rules` 가 `UNAVAILABLE` 로 사유를 남긴다 |

## E-3 합계 — 외워둔 값

| | 개수 |
| ---: | ---: |
| 35회차 목록 | 199 |
| [C] 낱말 4 (`_DEFAULT_SAME`) + 잎 1 (`qty_note.same_words`) | −5 |
| [E-1] dataclass 14 | −14 |
| [E-2] config 잎 8 (`same_words` 는 위에서 셌다) | −8 |
| [B] 로 재분류된 25 | (아래 `3_type_map.md` B-2) |
| **남은 외워둔 값** | **__REMAIN__** |
