# Phase 1 (valve29) — 분석 결과와 구현 계획

기준 버전: **valve28** (커밋 `d1c3618`). 지시서 "Engineering Intelligence Upgrade" §13 의 Phase 1 = 운영 신뢰성.

## 0. 시작 전에 한 것

| 항목 | 결과 |
|---|---|
| Git | 브랜치 `ccr-efbe7e75-n915ze`, origin 과 같음, 작업 트리 깨끗 |
| 문서 | DESIGN §1~§33 · USER_GUIDE · handoff/valve.md 검토 (특히 §5 데이터, §11 VOC 경로와 "판정 코드는 정답지를 읽지 않는다", §32 Revision 이어받기, §33 검증 엔진) |
| 기준 저장 (저장소 밖 `out/valve29/`, 고객 값) | `baseline_valve28_vt_shot.json` = 실자료 사본의 지적 2,889건(ikey · check · type · severity · description · expected · status) + KPI · 검증 7,872(✓6,806 ✗426 –640) · `baseline_pytest.txt` · `eval_valve28/` (칸 지문 포함) |
| 시험 | 전체 pytest · valve_eval --check · diff_sim · sim 3000 · mutate · sim_pdf · rev_sim · ui_audit (valve28 회차 끝에 모두 통과, 다시 돌려 저장) |

## 1. 지금 구조 — Phase 1 이 건드리는 곳

| 부분 | 지금 | 영향 |
|---|---|---|
| 지적 상태 | `issue_state(datasheet_id, ikey, status, note, by, at, since)` — status ∈ Open · Confirmed · Dismissed · Resolved | **Excel/PDF 에서 Dismissed 제외, Rev 이어받기, 대시보드 수가 모두 이 status 를 씀** → 바꾸지 않는다 |
| 피드백 | Reports › Review Feedback json (`/feedback.json`) + `spike/valve_voc.py`. 판정 모듈이 이 파일을 읽지 않는 것을 시험이 지킴 | 새 피드백도 같은 원칙: 기록·통계만, 규칙은 읽지 않음 |
| 규칙 번호 | valve28 에서 모든 지적에 `check`(DE-01 · PMS-trim · PD-design_pressure · MR-01 …) · `checks.REGISTRY` 48 항목 | Rule Performance 의 묶음 기준으로 그대로 씀 |
| 근거 | 지적마다 evidence · basis (valve28) | 결정 시점 스냅샷에 함께 저장 |
| 추출 출처 | field: document · page · bbox · key · 읽은 값 · 고친 값 | parser version · 추출 방법이 없음 |
| PDF ↔ 지적 | 지적 상자 · 칸 상자를 누르면 그 지적/칸 | 빈 PDF 자리를 누르면 아무 일도 없음 |
| 성능 | 164 DS 실측 · 990 DS 사본(`/tmp/vt_big`) Tag 이동만 실측 | 500 DS 없음 · 첫 계산(cold) · 화면 완료 시간 미측정 |

## 2. 구현 계획

### 2.1 Engineering Feedback Loop (지시서 §1)

- **status 는 그대로 두고 그 옆에 결정을 기록**한다. `issue_state` 에 열 추가: `decision` · `reason_cat` · `conclusion` · `modified_text` · `modified_severity` · `rule_ver`.
  결정 → 기존 status 대응(기존 출력이 그대로 맞게):

  | Engineer Decision | status | 출력 |
  |---|---|---|
  | Confirmed | Confirmed | 그대로 |
  | Modified | Confirmed | 설명 · Severity 를 엔지니어가 고친 것으로 (원문은 기록) |
  | Dismissed | Dismissed | 빠짐 (지금과 같음) |
  | Not Applicable | Dismissed | 빠짐 |
  | Deferred | Open | 남음 (보류 표시) |

  기존 'Resolved'(설계사가 고침)는 상태로 그대로 둔다 — 규칙 정확도 통계에서는 'Confirmed 계열'로 센다(valve_voc 와 같은 해석).
- **결정 기록표 `decision_log`** (덧붙이기만, 지우지 않음): Rule ID · Rule 버전 · Tag · Rev · 원래 지적 · 원래 Severity · 결정 · 사유 분류 · 사유 · 최종 결론 · 검토자 · 시각 · 근거 문서 · evidence(JSON).
  지시서 1.2 의 항목 전부. 3개월 추세는 이 표에서.
- **사유 분류 7종**: Project Specification Exception · Vendor Clarification · Incorrect Rule Logic · Incorrect Data Extraction · Not Applicable · Duplicate Finding · Other.
  Dismissed · Not Applicable · Modified 는 분류를 반드시 고르게 한다.
- **Rule Performance** (새 화면 + `GET /projects/{pid}/rules/performance`): Rule 별 Total Findings · Confirmed · Dismissed · Modified · Deferred · N/A · 미결정 · Confirmation Rate · Dismissal Rate · 사유 분류 분포 · 최근 3개월 월별 추세.
  **Dismissal Rate 를 False Positive Rate 라고 부르지 않는다** — 사유 분류 중 'Incorrect Rule Logic' · 'Incorrect Data Extraction' 만 따로 "도구 쪽 원인" 으로 보인다.
- **검토 권고**: 결정 수 ≥ N 이고 Dismissal Rate ≥ R 인 규칙을 표시. N · R 은 프로젝트 설정(기본값 10건 · 30 % — **도구 기본값이라고 화면에 밝히고 바꿀 수 있게**). 규칙은 바꾸지 않는다.
- **Rule 버전 · 변경 절차**: `checks.REGISTRY` 각 규칙에 `version`(valve28 기준 전부 1) · `source`(지금은 전부 "General Engineering Check" — 프로젝트 문서 근거가 없으므로, 지시서 §5.3).
  `rule_change` 표 + 화면: 변경 제안 → ① 기존/변경안 비교 ② 이유 ③ 실자료 Regression 결과 ④ Simulation 결과 ⑤ Engineer 승인 ⑥ 적용 버전. ③④⑤ 가 채워지지 않으면 '승인' 으로 넘어가지 않음.
  **규칙 코드는 이 표를 읽지 않는다**(기존 AST 시험을 새 모듈까지 넓힘). 실제 코드 변경은 개발 쪽이 하고, 적용되면 REGISTRY 버전을 올린다.
- 새 판(Rev B)에 이어받을 때(valve27) 결정 · 사유 분류도 같이 넘긴다 — 기존 이어받기 규칙(같은 칸 · 같은 값)은 그대로.
- Review Feedback json: version 2 — 기존 필드 유지 + decision · reason_cat · conclusion · rule · rule_ver · evidence. `valve_voc.py` 는 두 판 모두 읽음.
- Issue List Excel: 'Rule ID' · 'Engineer Decision' · 'Decision Reason' 열 추가(기존 열은 이름 · 순서 유지, 뒤에 붙임).

### 2.2 Source Traceability (지시서 §7)

- `datasheet.parser_version` (새로 읽는 것부터 `extract.PARSER_VERSION`; 예전 행은 "valve28 이전" 으로 표시 — 지어내지 않음).
- 칸마다 추출 방법을 계산해 보임: `text-layer · ruled table` / `note reference` (Note 값을 해석) / `engineer correction`.
- 지적마다 `op`(비교 연산 — =, ≤, ≡ 재질 동치, present, released …) · `tol`(허용오차 — Process Data 수치 1 % 등 규칙에 이미 있는 것만) · `result`(규칙이 낸 판정 문구: Non-Compliant / Review Required / Mismatch / Action / Confirm / Note / Finding).
  Actual = value, Reference = expected(기존). 새 값을 만들지 않고 규칙이 이미 쓰는 것만 적는다.
- PDF 의 빈 자리를 누르면(선택 도구) 그 자리의 칸을 찾아 선택 + 그 칸의 지적 수를 알림. 지적 상자 → 근거 영역은 이미 됨.

### 2.3 성능 측정 (지시서 §8 의 Phase 1 부분)

- 164 DS(실자료 사본) · 500 DS(990 사본에서 잘라 만듦) · 990 DS. Cold(서버 새로 켬 · 디스크 캐시 지움) / Warm.
- API 시간 + **화면 표시 완료 시간**(Playwright: 메뉴 누름 → 표/목록이 그려지고 network idle): 첫 로딩 · Summary · Tag 이동 · Issue List · Revision · Process · PMS · Excel · Mark-up PDF.
- 회귀가 보이면 고친다 — 단, 캐시 키에 Revision(감사 id) · 규칙 버전(VERSION)이 들어가 있는지 확인(이미 있음, 새 결정 표도 키에 포함).

### 2.4 기존 기능 보호 장치

- 판정 결과가 바뀌지 않음을 기계로 확인: valve28 기준 스냅샷(지적 2,889건의 ikey · check · type · severity · description · expected)과 valve29 결과를 **칸 단위 비교**하는 스크립트(`spike/valve_snapshot_diff.py`). Phase 1 의 기대값은 "차이 0" — 새 필드(op · tol · result · decision)만 늘어남.
- 기존 시험 전부 + valve_eval --check(지문) + 시뮬레이션 5종 + ui_audit.

## 3. Phase 1 에서 하지 않는 것 (이유)

- 규칙 자동 변경 · 학습 — 지시서 금지.
- 프로젝트 기준 문서 연결(§5) · Document Hierarchy(§4.3) — Phase 2. 지금은 모든 규칙의 출처를 "General Engineering Check" 로 정직하게 표시만 한다.
- Dashboard 전면 개편(§9) · Workflow 8단계(§10) — Phase 2~4. Phase 1 은 Rule Performance 화면과 대시보드의 결정 수만.
