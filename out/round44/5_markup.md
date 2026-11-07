# [D] 마크업 UI — 무엇을 어떻게 만들었나

## 1. 흐름 (요구 [D-1]~[D-4])

| 단계 | 화면 | 서버 | 저장 |
| --- | --- | --- | --- |
| 모드 켜기 | `[마크업]` (`#markup-toggle`) — `#stage.markup` · 팬 꺼짐 · 커서 십자 | — | — |
| 빈 자리 드래그 | `pointerdown/move/up` (capture) 로 고무줄 사각형 · `sheetPoint` 두 번 → 표시 좌표 pt (검출 rect 와 같은 좌표계 · 회전 장도 같음) | — | — |
| 제안 | `markupDialog(rect)` | `POST /jobs/{id}/markup/propose` → `markup.propose` → `pipeline.propose_at` (별표·NOTES·낱말) + 같은 장 행의 수량 + 앵커 사전 TYPE | **없음** |
| 확정 | 대화상자: 산출물 탭 · Type · SCOPE(+공급자 이름) · Q'ty · Description · 사유(㉡ 기본) · 메모 · 작성자.  제안값 옆에 **도면에서 읽음 / 못 읽음** 문장 | `POST /jobs/{id}/rows` (`rect` · `values` · `author` · `scope_source` · `qty_source` · `reason_class` · `note` · `proposal`) | `item`: `added=1` · `rect_json` · `ai_json` 전부 None · `user_json` = 값 · `evidence_json.markup{…}` · `needs_review=''` · `feedback(ADDED, geometry=probe_point)` · 프로젝트가 있으면 `revision_state` + 장부 `id_registry.json` |
| 목록 | `tr.added` + ＋ 플래그 (기존) · 근거 패널: 작성자·시각·사유 · **SCOPE 출처 · 수량 출처** · 안정 ID · Type 제안 | `GET /jobs/{id}/rows` (`reject`·`added`·`rect` 실림) | — |
| 도면 | `overlayItems` 가 `S.rows` 의 추가 행을 층 항목과 **같은 얼굴**로 합침 → 점선 테두리 + 왼쪽 위 ✚ · 색은 SCOPE | — | — |
| 오검출 | 마크업 모드에서 상자 클릭 → `rejectDialog` (㉢/㉣/미지정/기타 · Excel 제외 체크 · 메모 · 작성자) | `DELETE /jobs/{id}/rows/{key}?reason_class&author&exclude&reason` → `db.remove_row(reject=…, exclude=…)` | `item.removed`(제외일 때만) · `item.reject_json` · `feedback(REMOVED)` |
| 값 틀림 | 같은 대화상자에서 ㉣ → 칸·값 입력 | `PATCH …/rows/{key}` (`reason: WRONG_VALUE: …`) | `user_json` · `feedback(EDITED)` — 기존 경로 |
| 되돌리기 | 목록 `[되돌리기]` · 대화상자 `[되돌리기]` | `POST …/rows/{key}/restore` (있던 API · 버튼만 새로) | `removed=0` · `reject_json='{}'` |
| 같이 적용 | 근거 패널 `[다른 장에도…]` → 장 체크 → 장마다 다시 제안 → 고른 장에만 행 | `propose` + `rows` 반복 | 장마다 `markup.note = "pN 마크업에서 같이 적용"` |

## 2. 제안값 — 읽는 순서와 못 읽었을 때

* **SCOPE**: `pipeline.propose_at` — `ds.detect` 앞부분과 **같은 함수·같은 인자**
  (`bubble_outlines` + `dashed_bubble_outlines` → `read_mark_dictionary` → `find_marks` →
  `find_package_boxes` → `package_box_marks` → `read_vendor_mark(others=이웃 버블)`) →
  `_scope_of`.  config 는 그 분석이 얹었던 좌표(`applied_rules.layout.moved`)를 같은
  `CFG.overlay` 로 얹고 끝나면 되돌린다 (`_own_config` 한 벌).
  **별표가 없으면 SCT 가 아니라 빈칸이다** — 검출 행의 "별표 없음 = SCT" 는 그 심볼의 별표
  자리를 다 본 뒤의 규칙이지, 사람이 그린 사각형에서는 못 찾은 것과 없는 것을 가를 수
  없기 때문이다.  실측(AL NOUF1 p6): VENDOR(HRSG) FIT 자리 → `VENDOR(HRSG)` · `DRAWING` ·
  별표 1 / SCT PIT 자리 → `""` · `USER`.
* **Q'ty**: 같은 장의 추출 행이 받은 `qty` 를 옮긴다 (그 장의 배수는 장 단위 사실이고
  `_note_factor` 의 순서가 이미 찍혀 있다).  값이 갈리면(Typical 상자 안·밖) 고르지 않고
  빈칸 + 사유 `같은 장의 수량이 갈립니다 (2 (30행) · 8 (4행))`.  행이 없으면 빈칸.
* **TYPE**: 사각형과 겹치는 낱말(`pidcache.tokens` — SHX 어구도) 중 **이 프로젝트 앵커
  사전**(`RULESET_V3.anchors`)에 있는 것이 하나면 그것 (`field_type_map` 으로 `PT → PIT`).
  둘 이상이면 고르지 않고 후보만 낸다.  밸브 태그면 탭만 제안한다.
* 출처 규칙: 제안값을 그대로 두면 `DRAWING`, 바꾸거나 빈칸을 채우면 `USER`.  화면이
  계산해 보내고 서버는 받은 것을 적는다 — 사람이 바꾼 것을 도면 값이라 적을 길이 없다.

## 3. 안정 ID (§7.3)

`markup.assign_stable_id` — 그 프로젝트 장부에서 `Registry.assign` 을 부른다 (`next_seq` =
계통 최대 + 1 · 회수 없음).  기록에 `origin: user`.  상태는 `compare()` 규칙 그대로
(`compared_with` 없으면 BASELINE, 있으면 ADDED).  `excel_no` 는 `assign_excel_numbers` 로
그 탭의 다음 번호.  프로젝트가 없으면 ID 없이 `why` 문장만 (`bound`·`keyed` 규율).
시험: 두 행 연속 → seq 연속 · `next_seq` 가 그 다음 · 프로젝트 없으면 빈 ID.

## 4. 이 회차가 만들지 않은 것 / 한계

* `EDITABLE` 은 늘리지 않았다 — `scope_source`·`qty_source` 는 `evidence_json.markup` 이다.
  그리드에서 SCOPE 를 나중에 고치면 `user_json.scope` 는 바뀌지만 `scope_source` 는 그대로
  `DRAWING` 일 수 있다 → 근거 패널은 `✎ 사람이 고침` 연필로 그 사실을 따로 말한다 (기존
  `mark()`).  둘을 합치는 것은 다음 회차 후보.
* 제안은 **그 분석의 `layout.moved` 만** 되살린다.  범례 유도값은 `ds.LAYOUT` 에 안
  들어가므로(인자로만 흐른다) 되살릴 것이 없고, 별표 크기는 `find_marks` 가 그 장에서
  런타임에 잰다.  다만 `KNOWN_GLYPH_SIZES` 는 config 값이다 — 검출 때와 같다.
* 오검출 표시의 사각형 표식은 `page.layers` 의 항목에 걸린다.  층에 없는 행(옛 `＋행`
  으로 만든 rect 없는 행)은 도면에 표시가 없다 — 목록의 플래그만.
* "같이 적용" 은 같은 **좌표**를 다른 장에 쓴다.  장마다 도면이 다르므로 자동이 아니라
  사람이 고른 장에만, 장마다 다시 읽어 제안한다.
