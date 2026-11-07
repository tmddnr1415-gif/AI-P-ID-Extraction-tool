# REGRESSION_REPORT — valve29 (Phase 1)

기준: valve28 (`d1c3618`, 시험 1,888 통과). 원칙: **기존에 정확하게 동작하는 기능을 훼손하지 않는다** — 그래서 판정 · 출력이 그대로인지를 기계로 비교했다.

## 1. 판정이 그대로인가

| 점검 | 방법 | 결과 |
|---|---|---|
| 실자료 지적 전부 | `spike/valve_snapshot_diff.py check` — valve28 실자료 사본(164 DS)의 지적 2,887건을 ikey · check · type · severity · description · expected · status 칸 단위 비교 | **추가 0 · 삭제 0 · 변경 0** |
| 읽기(추출) 지문 | `spike/valve_eval.py --check` (456쪽 · 17,471칸 · PMS · Process · 규칙 개수) | **baseline unchanged** |
| 차등 시뮬레이션 | `spike/valve_diff_sim.py` (읽은 값을 다시 그려 다시 읽기) | 140 DS · 12,470칸 **불일치 0** |
| 규칙 시뮬레이션 | `spike/valve_sim.py --n 3000` (엔지니어 기대 vs 규칙, 퍼즈 500) | recall · precision **1.000** · 예외 0 |
| 실자료 변이 재생 | `spike/valve_mutate.py` (164 × 14 변이) | 전부 **100 %** |
| 다른 양식 읽기 | `spike/valve_sim_pdf.py --n 190` | **0.992** (valve28 과 같음) · 예외 0 |
| Revision 사슬 | `spike/valve_rev_sim.py --n 300` (A → B → C, 엔지니어 결정 · 이어받기 · 해결/미반영/새 지적) | 7,175 점검 **1.000** · 예외 0 (Phase 1 중 1,500건 × 3판 = 55,223 점검도 1.000) |

## 2. 출력이 그대로인가 (성능 수정의 안전 확인)

| 출력 | 비교 | 결과 |
|---|---|---|
| Issue List Excel | 고치기 전 코드 vs 후, 164 · 500 DS — 모든 시트의 모든 셀 값 + 앞 60행의 채움 · 테두리 · 굵기 · 글자색 | **동일** (Info 시트의 생성 시각만 다름). 열 3개(Rule ID · Engineer Decision · Decision Reason)는 끝에 추가 |
| Valve List Excel | 같은 방법, 164 · 500 DS, 링크 포함 | **동일** |
| Mark-up PDF (164 DS 전체, 561쪽) | 쪽마다 크기 · 글자(해시) · 그림 수 · 주석 수 · 책갈피, 마크업 고정 ON / OFF 둘 다 | **동일** (OFF 의 표지 생성 시각만 다름) |

## 3. 자동 시험

| 묶음 | valve28 | valve29 |
|---|---|---|
| 전체 `pytest -q` | 1,888 통과 · 42 건너뜀 | **1,897 통과** · 42 건너뜀 · 실패 0 |
| 밸브 시험 `-k valve` | 89 | **99** (+ `tests/test_valve_feedback.py` 9 · + 1 compact) |
| 화면 자기점검 `valve_ui_audit.cjs` | 25/25 | **25/25** |

새 시험(`tests/test_valve_feedback.py`):
결정 → status 대응 · 잘못된 결정/사유 분류 거절 · 옛 status 호출 호환 · Modified 원문 보관 · 결정 기록 스냅샷 · Rule Performance 수 · 3개월 추세 · 검토 권고 기준 ·
설정 값 검증 · 다음 Revision 으로 결정 · 사유 이어받기 · 변경 절차 단계 조건(시험 없이 승인 불가 · 코드 버전 없이 적용 불가) · **판정 코드가 결정/변경 기록/설정/feedback 을 읽지 않음(AST)** ·
읽기 엔진 버전 · op/tol/result · Excel 스타일(빠른 경로 후에도 같음 · 임시 시트 안 남음) · compact 목록이 같은 정보.

## 4. 고친 결함 (기존 기능의 숨은 결함 — 측정 중 발견)

| 결함 | 영향 | 조치 |
|---|---|---|
| 화면 Issue List 가 최대 6,000행, PMS 3,000행, Process 4,000행만 표시 | 500 DS 에서 지적 8,795 중 2,795 건이 화면에 안 보임(Excel · PDF 에는 있음) | 전부 표시(나눠 그림), 행 클릭 위임 |
| Mark-up PDF 가 Tag 수의 제곱으로 느려짐 | 500 DS 182 s, 990 DS 는 10분 이상 예상 | 선형(42 s) |
| Excel 두 개가 Tag 수에 비해 지나치게 느림 | 500 DS Issue List 105 s | 6 s |

## 5. 바뀐 동작 (의도한 것)

- 지적 상태 선택이 **결정 창**으로 바뀜 — Dismissed · Not Applicable · Modified 는 사유 분류가 있어야 저장. 옛 API 호출(`{status, note}`)은 그대로 받음.
- Modified 결정이 있으면 Excel/PDF 에 엔지니어 문구 · Severity 가 나감.
- 기존 status 로 바꾸던 화면 기록은 결정 기록에도 남음(사유 분류 없음).
