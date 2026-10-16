# [F] 피드백 내보내기 — 명세

`GET /jobs/{id}/feedback_export?by=<이름>` → `{data}/feedback/feedback_<프로젝트>_<YYYY-MM-DD>.zip`
(프로젝트가 없으면 PDF 이름).  `app/markup.py::export_zip`.  **새 사실을 만들지 않는다** — 있는 표
(`item` 의 추가·오검출 · `feedback` 의 편집 · `report`)를 꺼낸다.  마크업은 내보낸 뒤에도 남는다.

## feedback.json

| 키 | 뜻 |
| --- | --- |
| `project` · `job_id` · `pdf_name` · `pdf_sha256` · `revision` | 어느 분석인가 |
| `fingerprint` | 그 분석의 판정 지문 (마크업이 못 건드리는 값) |
| `rows_total` | 살아 있는 행 수 (`removed=0`) |
| `exported_at` · `by` · `authors` | 언제 · 누가 · 항목에 적힌 이름들 |
| `counts` | 종류별 수 · `summary` = `GET /jobs/{id}/markup` |
| `legend_source` | 범례 유도/재사용 (15회차) |
| `items[]` | 아래 |

`items[].kind`:
* `missing` — 추가 행: `row_key` `page` `pid_no` `rect` `tab` `type` `scope` `scope_source` `qty`
  `qty_source` `description` `class` `note` `by` `at` `stable_id` `proposal`(제안 때 도면이 말한 것) `clip`
* `false_positive` — 오검출 표시 또는 삭제 표시: `class` `note` `by` `at` `excluded_from_excel` `rules_hit` `clip`
* `wrong_value` — 편집 이력(기존 행 · (행,칸) 마지막 것): `column` `current`(엔진) `should_be`(사람) `note` `by` `at`
* `report` — 오류 신고(12회차 표): `what` `note` `report_kind`

## feedback.md — 한 표 (번호 · 종류 · 장 · P&ID No. · Type · 내용 · 작성자 · 조각)

## 조각/ · 장/

사각형이 있는 항목마다 `조각/NNN_pP_<kind>.png` (여백 60pt · 표시 좌표 · 전체 장을 렌더한 뒤
자른다 — clip 좌표계를 가정하지 않는다 · 43회차 `crop43b` 방법) · 장마다 `장/pP.png` (1/3 축소
· 표시 상자 색: 누락 초록 · 오검출 빨강 · 값 틀림 주황 · 신고 보라).  PDF 가 없으면 둘 다 없다.

## 저장소

`.gitignore`: `out/feedback_*.zip` · `out/round44/feedback_*.zip` · `out/round44/verify/feedback_*.zip`.
서버 쪽 `{data}/feedback/` 은 `app/_data/` 아래라 이미 막혀 있다.
