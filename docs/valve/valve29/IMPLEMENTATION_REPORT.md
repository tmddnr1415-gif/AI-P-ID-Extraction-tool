# IMPLEMENTATION_REPORT — valve29 (Phase 1: 운영 신뢰성)

기준: valve28 (`d1c3618`). 지시서 "Engineering Intelligence Upgrade" §13 Phase 1 = Engineering Feedback Loop · Rule Performance · Source Traceability · 990 DS 성능 측정.
분석 · 계획: `docs/valve/PHASE1_PLAN.md`. 회귀: `REGRESSION_REPORT.md`. 성능: `PERFORMANCE_REPORT.md`. 규칙: `RULE_CHANGELOG.md`. 사용법: `USER_GUIDE_UPDATE.md`.

## 1. 신규 기능

### 1.1 Engineering Feedback Loop (지시서 §1)
- **Engineer Decision 5종** — Confirmed · Modified · Dismissed · Deferred · Not Applicable (+ 기존 Resolved · Open).
  **기존 status(Open/Confirmed/Dismissed/Resolved)는 바꾸지 않고 그 옆에 기록**한다. 결정 → status 대응: Confirmed·Modified → Confirmed, Dismissed·Not Applicable → Dismissed, Deferred → Open.
  그래서 Excel/PDF 에서 빠지는 것, Rev 이어받기, 대시보드 수가 valve28 과 같은 규칙으로 움직인다.
- **사유 분류 7종** (Dismissed · Not Applicable · Modified 는 필수): Project Specification Exception · Vendor Clarification · Incorrect Rule Logic · Incorrect Data Extraction · Not Applicable · Duplicate Finding · Other.
- **Modified**: 엔지니어가 고친 문구 · Severity 가 출력에 나가고, 도구 원문은 `original_description` · `original_severity` 로 보관.
- **결정 기록(`decision_log`, 덧붙이기만)**: Rule ID · Rule 버전 · Tag · Rev · 원래 지적 · 원래 Severity · Actual · Reference · Source Document · Evidence(JSON) · 결정 · 사유 분류 · 사유 · 최종 결론 · Modified 문구 · 검토자 · 시각 — 지시서 1.2 항목 전부.
- **Rule Performance** 화면(새 메뉴) · API: Rule 별 Total · Confirmed · Modified · Resolved · Dismissed · N/A · Deferred · 미결정 · Confirmation/Dismissal Rate · 사유 분포 · 최근 3개월 추세.
  Dismissal Rate 를 오탐률이라 부르지 않고, '도구 원인'(Incorrect Rule Logic + Incorrect Data Extraction)을 따로 센다.
- **검토 권고** 표시: 결정 ≥ N 건 · Dismissal ≥ R. N · R 은 프로젝트 설정(도구 기본값 10 · 30 % 를 화면에 밝힘).
- **Rule 변경 절차**(지시서 1.4): `rule_change` 기록 — ① 기존/변경안 ② 이유 → Proposed · ③ Regression ④ Simulation → Tested · ⑤ 승인(Tested 뒤에만) → Approved · ⑥ Applied(코드의 `RULE_VERSION` 이 제안 버전과 같을 때만).
  **기록은 규칙을 바꾸지 않는다.** 판정 코드가 결정 · 변경 기록을 읽지 않는 것을 AST 시험이 지킨다.
- **Rule 버전 · 출처**: 48 규칙 모두 v1(= valve28 논리) · 출처 'General Engineering Check'(프로젝트 기준 문서 없음 — §5.3).
- 새 Revision 이어받기(valve27)에 결정 · 사유 분류 · 결론도 함께 넘어감.
- Review Feedback json v2 · `spike/valve_voc.py` 가 v2 를 읽어 Rule 별 결정 · 사유 분류를 보고하고, 규칙 탓이 아닌 사유(프로젝트 예외 · Vendor 회신 · 중복 · N/A)는 '오탐' 에서 뺀다.

### 1.2 Source Traceability (지시서 §7)
- 데이터시트마다 **읽기 엔진 버전**(`datasheet.parser_version` = `extract.PARSER_VERSION` "extract-v22"). valve28 이전에 읽은 것은 비어 있고 화면에 'valve28 이전' 으로 표시(지어내지 않음). 다시 읽기(refresh) 때 갱신.
- 칸의 **추출 방법** 표시: text layer · ruled table / note reference / pairing unsure (Review) / engineer correction(누가 · 언제).
- 지적마다 **op**(비교 연산) · **tol**(허용오차) · **result**(규칙의 판정 문구). Actual = value, Reference = expected(기존). 규칙에 이미 있는 것만 적음(Process Data 수치 1 %).
- 작업대: Data 탭 위에 칸 출처(파일 · Doc · Rev · 쪽 · 행 · 위치 · 방법 · 엔진 버전 · **그 칸의 지적 링크**). **PDF 의 빈 자리를 누르면 그 자리의 칸** → 출처 · 지적. 지적 카드에 비교 한 줄.
- Issue List Excel 끝에 Rule ID · Engineer Decision · Decision Reason 열(앞의 27열은 이름 · 순서 그대로).

### 1.3 성능 (지시서 §8 Phase 1 부분)
- 측정 도구 `spike/valve_perf.py` + `spike/valve_perf_screen.cjs`: Cold(디스크 캐시 삭제) · Restart · Warm × API 시간 + **화면 표시 완료 시간**, 164 / 500 / 990 DS.
- 측정에서 찾은 병목 2개를 고침 (내용 동일 — 셀 값 · 스타일 비교로 확인):
  Issue List Excel 15.6 s → 1.9 s, Valve List Excel 6.5 s → 3.3 s (164 DS). 원인: openpyxl 이 셀마다 새 Border/Alignment 를 해시 · `ws.max_row`/`ws[r]` 가 행마다 시트 전체를 다시 훑음 · Valve List 가 이미 계산된 특수 요구사항을 Tag 마다 두 번 다시 계산.
  자세한 수치는 `PERFORMANCE_REPORT.md`.

### 1.4 보호 장치
- `spike/valve_snapshot_diff.py`: valve28 실자료 지적 2,887건(ikey · check · type · severity · description · expected · status)을 저장해 두고 칸 단위로 비교. valve29 결과 **차이 0**.

## 2. 수정된 파일

| 파일 | 변경 |
|---|---|
| `app/valve/store.py` | 표 `decision_log` · `rule_change` · `project_setting` · 열 `issue_state.decision/reason_cat/conclusion/modified_text/modified_severity/rule_ver` · `datasheet.parser_version` (기존 DB 자동 추가) · DECISIONS · DECISION_STATUS · REASON_CATS |
| `app/valve/api.py` | 결정 API(기존 status 호출 호환) · 결정 기록 · Rule Performance · 설정 · 변경 기록 API · 이어받기에 결정 포함 · feedback v2 · Issue Excel 에 결정 · VERSION valve29 |
| `app/valve/ruleperf.py` (새) | 규칙 통계 · 변경 절차 상태 검사 |
| `app/valve/checks.py` | RULE_VERSION · RULE_SOURCE · OPS · rule_of |
| `app/valve/issues.py` | 지적에 op · tol · result · decision · reason_cat · conclusion · (Modified) 원문 보관 |
| `app/valve/revisions.py` | 이어받을 때 결정 필드도 |
| `app/valve/extract.py` | PARSER_VERSION |
| `app/valve/exports.py` | Excel 3열 추가 · 스타일 한 번 만들어 복사(`_proto`) · 행 번호 직접 계산 |
| `app/valve/tbe.py` | 같은 스타일 복사 · 이미 계산된 requirements 재사용 |
| `app/static/valve/*` | 결정 창 · 일괄 결정 · Rule Performance 화면 · 칸 출처 · PDF 빈 곳 → 칸 · 지적 카드 비교 줄 · 새 메뉴 |
| `spike/valve_snapshot_diff.py` · `valve_perf.py` · `valve_perf_screen.cjs` (새) · `valve_voc.py` | 보호 · 측정 · v2 읽기 |
| `tests/test_valve_feedback.py` (새) | 결정 · 기록 · 통계 · 변경 절차 · 이어받기 · 설정 · AST 가드 · 추적 · Excel 스타일 (9개) |

## 3. 신규 API

| 메서드 · 경로 | 내용 |
|---|---|
| `PUT /api/valve/datasheets/{id}/issues/{ikey}` | (확장) `{decision, reason_cat, note, conclusion, modified_text, modified_severity}` — 기존 `{status, note}` 도 그대로 받음 |
| `GET /api/valve/projects/{pid}/rules/performance` | Rule 별 통계 · 3개월 추세 · 설정 |
| `GET /api/valve/projects/{pid}/rules/decisions?rule=&limit=` | 결정 기록 |
| `PUT /api/valve/projects/{pid}/settings` | 검토 권고 기준(rp_min_n · rp_dismiss_rate) — 값 검증 |
| `GET/POST /api/valve/projects/{pid}/rule-changes` · `PUT /api/valve/rule-changes/{id}` | 규칙 변경 기록 · 단계 이동(조건 미충족이면 거절, 입력한 글은 저장) |

## 4. 신규 DB 항목
위 표의 store.py 줄 참조. 기존 DB 는 서버가 켜질 때 열 · 표를 추가한다(지우지 않음).

## 5. 신규 Rule ID · 기존 Rule 변경
- 신규 규칙 **없음**. 기존 48 규칙 **판정 변경 없음**(버전 1 로 고정). → `RULE_CHANGELOG.md`.

## 6. 미완료 (Phase 1 범위 안)
- 결정 통계의 실제 의미는 **실사용 결정이 쌓여야** 나온다 — 지금 실자료 사본에는 결정이 없다.
- 지적 → PDF 근거 자동 표시는 데이터시트 쪽 상자 · PMS/Process Data 쪽 링크까지. PMS · Process Data PDF 안의 '표 칸' 단위 상자는 그 문서 리더가 bbox 를 줄 때만(지금 Process Data 는 칸 단위, PMS 는 품목 줄 단위).

## 7. 운영 시 주의
- 결정 창이 새로 뜬다 — Dismissed · N/A · Modified 는 사유 분류를 골라야 저장된다. 예전 '상태' 와 같은 자리.
- Rule Performance 의 '검토 권고' 는 **규칙을 바꾸라는 뜻이 아니라 살펴보라는 표시**. 변경은 반드시 변경 기록 절차로.
- 업데이트 후 첫 실행은 검토 캐시를 다시 계산한다(164 DS 약 7 s, 990 DS 는 `PERFORMANCE_REPORT.md`).
