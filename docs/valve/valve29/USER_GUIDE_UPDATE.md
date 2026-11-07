# USER_GUIDE_UPDATE — valve29 에서 달라진 사용법 (계장 엔지니어용)

## 1. 지적에 대한 결정 — 상태 대신 "Engineer Decision"

작업대 Issues 탭 · Issue List 표에서 지적마다 고르던 상태(Open / Confirmed / Dismissed / Resolved)가 **결정**으로 바뀌었습니다.

| 고르는 것 | 뜻 | 설계사 전달본(Excel · PDF) |
|---|---|---|
| Open | 아직 결정 전 | 들어감 |
| **Confirmed** | 지적이 맞음 — 설계사에게 보냄 | 들어감 |
| **Modified** | 지적은 맞지만 문구 · Severity 를 고쳐서 보냄 | 고친 문구로 들어감 (도구 원문은 기록에 남음) |
| **Dismissed** | 지적이 아님 | 빠짐 |
| **Deferred** | 보류 — 나중에 결정 | 들어감 (Open 과 같음) |
| **Not Applicable** | 이 밸브에는 해당 없음 | 빠짐 |
| Resolved | 설계사가 고침 | 들어감 (지금과 같음) |

- 결정을 고르면 창이 뜹니다: **사유 분류**(Dismissed · Not Applicable · Modified 는 꼭) · 사유 · 최종 결론.
  사유 분류: Project Specification Exception · Vendor Clarification · Incorrect Rule Logic · Incorrect Data Extraction · Not Applicable · Duplicate Finding · Other.
- 같은 이유의 지적 묶음(예: Process Data 빈칸 13개)은 '일괄 결정…' 으로 한 번에.
- 모든 결정은 그때의 지적 문구 · 값 · 근거와 함께 기록됩니다(지워지지 않음).
- 새 Revision 이 오면 Dismissed / Not Applicable / Confirmed 결정과 **사유 분류도 같이** 이어받습니다(같은 칸 · 같은 값일 때 — valve27 과 같은 규칙).

## 2. Rule Performance (새 메뉴)

- 규칙(Rule ID)마다: 지적 수 · Confirmed · Modified · Resolved · Dismissed · N/A · Deferred · 미결정 · Confirm % · Dismiss % · **도구 원인** · 최근 3개월.
- **Dismiss % 는 오탐률이 아닙니다.** 프로젝트 예외나 Vendor 회신으로도 Dismiss 합니다. 규칙 자체가 틀렸다는 신호는 '도구 원인'(사유 분류가 Incorrect Rule Logic / Incorrect Data Extraction 인 건수)입니다.
- '검토 권고' 표시: 결정 수 ≥ N 이고 Dismiss % ≥ R 인 규칙. N · R 은 화면 위에서 프로젝트에 맞게 바꿉니다(도구 기본값 10건 · 30 %).
- 규칙을 누르면 그 규칙의 결정 기록(누가 · 언제 · 왜)이 나옵니다.
- **변경 제안**: 규칙을 바꿔야 한다고 보면 '변경 제안' — ① 기존 규칙 · 변경안 ② 이유 ③ 실자료 Regression 결과 ④ Simulation 결과 → 승인. 승인해도 규칙은 저절로 바뀌지 않습니다. 개발 쪽이 코드를 고치고 버전을 올린 뒤에만 '적용' 표시가 됩니다.
- 모든 규칙의 출처는 지금 **General Engineering Check** 입니다(회사 · 프로젝트 기준 문서가 아직 연결되지 않았기 때문 — Phase 2).

## 3. 근거 추적

- 작업대 Data 탭에서 칸을 누르거나, **PDF 의 빈 곳(선택 도구)을 누르면** 그 자리 칸이 선택되고 위에 출처가 보입니다:
  파일 · Doc. No. · Rev · 쪽 · 행 · 위치 · 읽은 방법(글자층 표 / Note 참조 / 엔지니어 수정) · 읽기 엔진 버전 · **그 칸의 지적**(누르면 그 지적으로).
- 지적 카드에 비교 한 줄: *실제 값 · 비교(=, ≤, ≡ 재질 동치, present …) · 기준 값 (±허용오차) → 결과*.
- Issue List Excel 끝에 **Rule ID · Engineer Decision · Decision Reason** 열이 붙었습니다(앞의 열은 그대로).

## 4. 그대로인 것

판정 규칙 · 지적 개수 · Excel/PDF 형식(열 추가 외) · Revision 이어받기 · Mark-up 은 valve28 과 같습니다.
