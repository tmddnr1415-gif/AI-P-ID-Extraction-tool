# 44회차 [B] — 있는 것 조사 (새로 만들기 전에 답한다)

HEAD `e95bc85` (43회차 마감).  조사 방법: 코드를 읽었다 — `app/main.py` ·
`app/db.py` · `app/static/app.js` · `app/excel_out.py` · `app/revisions.py` ·
`app/pipeline.py`.  **실행한 것 없음, 고친 것 없음.**

## 0. 결론 먼저 — 요구 여섯 중 넷은 이미 서버에 있다 (열일곱 번째)

| 요구 | 있는가 | 어디 | 없는 것 |
| --- | --- | --- | --- |
| 도면 위 클릭 → PDF pt | **있다** | `app.js sheetPoint()` — 화면 분율 × `S.page.width/height` | 드래그 **사각형** (두 점) |
| 편집값 층에 새 행 | **있다** | `POST /jobs/{id}/rows` → `db.add_row` (`added=1` · 키 `u`+uuid · `ai_json` 전부 None · `user_json` = 값) · `＋행` 버튼 + 픽 모드 | 사각형 저장(`rect_json='[]'`) · 제안값(type/scope/qty) · 작성자 · `scope_source`/`qty_source` · 오버레이 표시 |
| 오검출 표시 (행 삭제 없이) | **있다** | `DELETE /jobs/{id}/rows/{key}` → `db.remove_row` — 검출 행은 **지우지 않고 `removed=1`** · 스냅샷·Excel 에서 빠짐 · `feedback(REMOVED, rules_hit)` 기록 · 복원 `POST …/restore` | 사유 분류 · 오버레이에 표시 · 복원 **버튼** (API 만 있음) |
| 미검출 지점 + 주변 기하 기록 | **있다** | `pipeline.probe_point` (반경 60pt 의 path·선분·낱말) · 우클릭 `MISSED` 신고 · `_capture_point` | — |
| 피드백 이력 | **있다** | `feedback` 표 (ADDED/REMOVED/EDITED · rect · ai/user · basis · geometry · author) · `GET /jobs/{id}/feedback` · `report` 표 (`_capture_row`/`_capture_context` = 지문·pdf sha256·빌드) | zip 으로 **꺼내는 길** (json + md + 조각 그림) |
| 개정 표기 Excel 행 칠하기 | **있다** | `excel_out._mark_revision` (ADDED 노랑 · MODIFIED 연녹 · DELETED 붉은+취소선) · `_remark` 가 REMARK 열을 채움 | 사용자 추가 행의 표기 — 단 **Rev.A 산출물에는 음영이 없어야 한다**(§7.1)는 제약이 있어 칠하기는 못 쓴다 |

13·15·16·18·22·24·25·27·28·31·36·38·40·41·43회차와 같은 모양이다 — 도면이
아니라 **코드가** 이미 갖고 있었고, 없던 것은 그것을 잇는 길이다.

## 1. 오버레이 클릭·드래그와 좌표 변환

* **화면 → PDF pt**: `sheetPoint(ev)` (app.js 3643) — `#sheet` 이미지의
  경계 사각형 안 분율 `(fx, fy)` 에 `S.page.width/height` 를 곱한다.  확대(`S.zoom`
  CSS 배율)와 서버 렌더 배율(`zoom=1.6`)이 둘 다 분율에서 빠진다.
* **PDF pt → 화면**: `drawOverlay()` 가 `scale = S.natural.w / S.page.width`
  로 `it.rect` 를 SVG 좌표로 옮기고 `viewBox` 는 이미지 픽셀 크기다.
* **회전**: `S.page.width/height` 는 `pidcache.load_pages` 의 `page.rect`
  (회전 적용된 표시 크기)이고, PNG 는 `page.get_pixmap` (회전 적용)이며,
  `pc.words`·`pc.drawings()` 는 `rotation_matrix` 로 표시 좌표로 옮겨져 있다
  (pidcache 88·121).  즉 **화면 분율 × 표시 크기 = 표시 좌표** 이고 검출 rect
  와 같은 좌표계다.  33·41회차의 함정(`d["rect"]` 회전 전 좌표)은 **화면 쪽에는
  없다** — 화면은 회전 전 좌표를 한 번도 만지지 않는다.  다만 [F] 의 조각
  그림은 `get_pixmap(clip=)` 대신 **전체 장을 렌더한 뒤 표시 좌표로 자른다**
  (43회차 `crop43b.py` 의 방법) — clip 의 좌표계를 가정하지 않는다.
* **드래그**: `#stage` 의 pointerdown/move/up 이 왼쪽 버튼 드래그를 **스크롤**
  로 쓴다 (`PAN_SLOP` 4px).  `S.picking` 이면 팬을 끄고 클릭 한 점을
  `createRow(point)` 로 보낸다.  → 마크업 모드는 **픽 모드와 같은 자리**에
  "두 점(드래그 사각형)" 을 더하는 것이다.  `#stage.picking #ov { pointer-events:
  none }` 이 이미 상자 클릭을 막으므로 빈 자리 드래그가 성립한다.

## 2. 편집값 층 — "새 행" 이 되는가

된다.  `db.add_row` 는 `added=1` 로 넣고 `store_result` 는 재분석 때 `added`
행을 **건너뛴다**(지우지도 `deleted` 로 만들지도 않는다).  `_merged` 가 `added`
·`removed` 를 행에 싣고 그리드는 `＋`·`✕` 플래그와 `tr.added`/`tr.deleted` 를
붙인다.  값은 `user_json` 만 있고 `ai_json` 은 전부 None 이라 **모든 칸이 "사람
값"** 이다 — 편집 연필(`r.user` 에 있으면 `.edited`)이 자동으로 붙는다.

없는 것 다섯:
1. `rect_json='[]'` — 지점은 `feedback.rect_json` 에만 남는다.  오버레이는
   `pid_page.layers_json`(분석 때 `pipeline._layers`)만 읽으므로 **추가 행은
   도면에 안 보인다** (아래 4 의 등식이 여기서 깨진다).
2. 제안값 없음 — `values: {}` 로 만든다.
3. 작성자 없음 — `add_row` 경로만 `author` 를 안 받는다 (PATCH 는 받는다).
4. `scope_source`/`qty_source` 자리 없음 — `EDITABLE` 10열에 없고 `feedback`
   에도 없다.  → `evidence_json` 에 둔다 (행의 `evidence` 는 지문 밖이고 근거
   패널이 읽는 자리다).  `EDITABLE` 은 늘리지 않는다.
5. 오버레이 층의 `scope` 갈래는 `pipeline._layers` 가 분석 때 적는다 — 사용자
   추가 행은 화면이 `S.rows` 의 `rect`+`scope` 로 **그때 만든다** (`itemScope`
   가 이미 그리드 `cellValue(row,"scope")` 로 되찾는 길을 갖고 있다).

## 3. 안정 ID — §7.3 을 깨지 않고 마크업 행에 주는 법

* 부여는 `revisions.Registry.assign` **하나**이고, 부르는 곳은
  `revisions.compare` ← `main._run_comparison` ← 분석 직후 뿐이다.
  `next_seq` 는 그 계통의 **모든** 기록(삭제 포함)의 최대 + 1 — 회수가 없다.
* 지금 추가 행은 분석 뒤에 생기므로 **ID 도 `excel_no` 도 못 받는다**.  Excel
  에서는 번호 없는 갈래(system·page·key 순)로 뒤에 붙는다.  다음 리비전으로
  **넘어가지도 않는다** — Rev.B 의 `_run_comparison` 은 Rev.B job 의 행만 본다.
* 프로젝트에 안 묶인 분석(`job.project` 빈 값)은 장부 자체가 없다.
* **방법 (새 개념 없음)**: 마크업 행을 만들 때 그 프로젝트 장부에서
  `registry.assign(row, revision)` 을 한 번 부르고 기록에 `origin: "user"` 를
  적는다.  같은 장부·같은 `next_seq` 이므로 단조 증가·회수 없음이 그대로다.
  Rev.B 에서 엔진이 그 자리를 찾으면 반경 매칭으로 **같은 ID** 를 잇고(history
  에 첫 row_key 가 `u…` 로 남아 "사람이 먼저 봤다" 가 읽힌다), 못 찾으면
  DELETED_CANDIDATE 로 사람이 확정한다 — 지금 규칙 그대로다.  프로젝트가 없으면
  ID 없이 키만 갖고 화면이 그렇게 말한다 (31회차 `bound`·`keyed` 와 같은 규율).
  ⚠ `id_registry.json` 은 `_run_comparison` 이 `Registry.load` 로 다시 읽으므로
  마크업이 쓴 항목이 분석 때 **덮이지 않는다** (load → assign → save).

## 4. 범례 카운팅과 등식

`buildOverlayLegend()` 가 `overlayItems(S.page)`(= `page.layers` 전부)를
`itemScope(it)` 로 세 칸에 세고, `needs_review` 는 **그중** 으로 따로 센다
(33회차).  `page.layers` 는 분석 때 행과 1:1 이라 **세 칸 합 = 상자 수 =
그리드 행 수**가 성립한다.  `EXCLUDED` 층(행 없는 심볼)은 `it.row===false` 로
갈라 그리지만 `counts` 에 **같이 세어진다** — 즉 등식은 정확히는 "layers 항목
수" 이고, 그 장에 EXCLUDED 마크가 있으면 상자 수 > 행 수다 (오늘도 그렇다).
→ 44회차는 이 사실을 바꾸지 않고, **사용자 추가 행을 layers 와 같은 얼굴로
화면에서 합친 뒤** "(그중) 사용자 추가 N" 을 검토 필요와 같은 방식(**그중**)
으로 센다 — 후보 A.  후보 B(다섯째 색 칸)는 색이 SCOPE 를 잃으므로 안 쓴다.
오검출(`removed`) 행은 layers 항목이 그대로 있으므로 상자도 그리드 행도 남는다
— 등식 불변 · 상자에 취소 표식만 더한다.

## 5. Excel — 어느 행이 나가고 표시는 어디에

* `db.snapshot` 이 `removed` 행을 **이미 뺀다** · `added` 행은 **넣는다**.
  `write_all` 은 `deleted` 를 빼고 `in_client_scope(row)` 로 거른다 — 전량
  모드면 전부, `sct` 모드면 SCOPE 값이 SCT 이거나 빈 행.  → 마크업 행의
  `scope` 가 `USER` 값이든 `DRAWING` 값이든 **그 값으로 판정된다** (요구 그대로,
  코드 0줄).
* 표시 자리 후보 셋 중 **REMARK 열** 하나만 남는다:
  - 행 칠하기(`_mark_revision` 재사용) — §7.1 "Rev.A 산출물에 음영·취소선이
    하나도 없어야 한다" 와 충돌.  버린다.
  - 별도 시트 — 발주처 양식(5개 부속 시트)을 그대로 두는 것이 `blank_form`
    의 약속이라 시트를 더하면 양식이 바뀐다.  버린다.
  - REMARK — 발주처 자기 열이고 `_remark` 가 이미 검토 사유·접힌 신호를 쓴다.
    `사용자 추가 · <작성자>` 를 **앞에** 붙인다.  **시각은 안 쓴다**(결정성).
* 결정성: `_remark` 는 순수 함수, 정렬은 `excel_no`/(system,page,key).  마크업
  행에 `excel_no` 가 있으면(3) 그 자리에 선다.

## 6. 기존 상자 클릭 → 오검출

있다 — `삭제` 버튼(`#row-delete`)이 그리드 선택 행에 대해 `DELETE …/rows/{key}`
를 부르고 `db.remove_row` 는 검출 행을 **지우지 않고 `removed=1`** 로 둔다
(사유 `window.prompt` 한 줄).  근거 패널은 "이 행은 결과에서 빠졌습니다 / 양식
빠집니다" 라고 말한다(14회차 `scopeFacts`).  복원은 `POST …/restore` 만 있고
버튼이 없다.  오버레이 상자에는 아무 표시도 없다.
→ 44회차 [D-3] 은 **이 경로에 사유 분류(㉢ 오검출 등)와 복원 버튼과 상자
표식을 더하는 것**이지 새 경로가 아니다.  마크업 모드에서 상자를 클릭하면
같은 DELETE 를 사유와 함께 부른다.

## 7. 제안값을 읽는 길 (§9 ①②)

* **SCOPE**: 파이프라인이 밸브 행에 쓰는 11회차 순서가 그대로 함수로 있다 —
  `ds.read_mark_dictionary(pc)` → `ds.find_marks(pc, …, allow_sizes)` →
  `ds.find_package_boxes` → `ds.package_box_marks` → `ds.read_vendor_mark(rect,
  marks, box_marks, mark_dict)` → `pipeline._scope_of`.  사각형만 사용자
  것으로 바꾸면 된다.  ⚠ 이 함수들은 `ds.LAYOUT`(config) 을 읽고, 22회차부터
  분석이 끝나면 config 가 되돌아간다.  그래서 요청 시점에 **그 job 의
  프로젝트 config 로 잠시 묶고**(`analyse` 가 `_own_config` 로 하는 것과 같은
  감싸기 — `snapshot = deepcopy(CFG.data)` … `finally` 되돌림) 읽는다.  이
  헬퍼는 `pipeline.py` 에 두어야 하므로 **기준선 체인이 끝난 뒤** 건드린다.
  결과에는 `scope_source: DRAWING`(별표를 읽음) / `USER`(못 읽어 사람이 적음)
  와 읽은 별표 개수·정의줄 원문을 `evidence` 에 남긴다.
* **수량**: 승수는 `engine_json.multipliers`(범례 표) · `unit_notes`(그 장
  NOTES) · `unit_multipliers.json`(사람) · 설정 폴백 순이고 그 순서는
  `pipeline._note_factor` 하나다.  마크업 행은 **같은 장의 기존 행이 받은
  `qty`** 를 그대로 제안한다 — 그 장의 배수는 장 단위 사실이고 이미 행에
  찍혀 있다(수량 근거 `qty_basis` 도 함께).  같은 장에 행이 없으면 빈칸 +
  `qty_source: USER`.  ⚠ Typical(38회차) 배수는 상자 안 행에만 곱하므로
  "같은 장" 이 아니라 **같은 장에서 그 사각형과 같은 Typical 상자 안 행** 을
  본다 — 그런 행이 없으면 장의 최빈 qty.
* **TYPE**: `probe_point` 가 반경 안 낱말을 이미 돌려준다.  사각형 **안**
  낱말 중 이 프로젝트 앵커 사전(`ds` 룰셋의 `type_map` 키·값 — 36회차
  `ruleset_v3(cfg)`)에 있는 것 하나면 제안, 아니면 빈칸.
* **P&ID No.**: `S.page.drawing_no`(pid_page) — 이미 `createRow` 가 넣는다.

## 8. 범위 합의안 (사용자가 실시간이 아니므로 이 가정으로 진행한다)

새로 만드는 것은 다음 여섯뿐이고 전부 **잇는 코드**다:
1. `POST /jobs/{id}/rows` 에 `rect`·`author`·제안값 채우기·`scope_source`
   ·`qty_source`·`MANUAL_ADD` 사유·안정 ID 부여(프로젝트가 있을 때).
2. `pipeline.propose_at(pdf, page_no, rect, project)` — §7 의 세 제안
   (체인 종료 뒤 작성).
3. `DELETE …/rows/{key}` 에 사유 분류(`MANUAL_REJECT` + ㉡㉢㉣/미지정) ·
   복원 버튼 · 오버레이 취소 표식.
4. 화면: 마크업 모드 토글 · 드래그 사각형 · 추가 행을 오버레이에 (파선 테두리
   + ✚ 아이콘, 색은 SCOPE 그대로 — E-1 (b)) · 범례 "(그중) 사용자 추가 N" ·
   "같은 자리 다른 장에도" 제안(31회차 방식 — 제안만, 행마다 누른다).
5. Excel REMARK 앞머리 `사용자 추가 · <작성자>` (`_remark` 한 줄).
6. `GET /jobs/{id}/feedback_export` → zip (feedback.json · feedback.md ·
   조각/ · 장/) + `.gitignore` `out/feedback_*.zip`.

건드리지 않는 것: 검출·`pipeline._layers`·`store_result`·지문·축·`EDITABLE`
·발주처 양식 열·43회차 보류·42회차 설계.
