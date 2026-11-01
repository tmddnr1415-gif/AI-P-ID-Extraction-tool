# Ball Valve Datasheet Review — 사용 설명서 (검토 엔지니어용)

대시보드 › 실행 프로젝트 › CO2 PJT › Datasheet › **Ball Valve** 에서 엽니다. (P&ID 서버 8000 의 `/valve/`)
이 도구는 PDF 글자층만 읽고, 규칙으로 검토합니다 — OCR · AI 추정 없음. 판정과 승인은 사람이 합니다.

## 1. 5분 안에 처음 쓰기

1. **Document Management** — Datasheet PDF(수십~수백 장 한 파일도 됨)를 끌어 넣습니다. Valve List(TBE .xlsx) · Process Data PDF · PMS PDF 는 있으면 같이.
2. 분석이 끝나면(쪽 수에 따라 수십 초) Valve List Excel 과 Issue List Excel 이 자동으로 만들어져 내려옵니다.
3. **Dashboard** 에서 전체 수(Tag · 오류 · 누락 · PMS · Process)와 Area 별 현황을 봅니다. 타일을 누르면 그 종류의 목록으로 갑니다.
4. **Datasheet Review** 에서 Tag 를 하나씩 봅니다 (↓/J 다음 Tag, ↑/K 이전 Tag). 왼쪽 PDF 에 지적 상자가 번호와 함께 보이고, 오른쪽 탭에 설명이 있습니다.
5. **Reports & Export** 에서 설계사에게 보낼 Issue List Excel · Mark-up PDF 를 만듭니다 (넣을 Issue Type 을 고를 수 있음).

## 2. 화면

| 화면 | 무엇을 하나 |
|---|---|
| Dashboard | 전체 현황 · Area 별 · 검토 진행 · 최근 활동 |
| Document Management | 파일 올리기 · 다시 읽기 · 처리 상태 |
| Valve List | 모든 Tag 를 Excel 처럼 한 표에 (열 필터 · 정렬 · 열 숨기기) · 셀을 누르면 오른쪽에 그 PDF 자리 · Issue List 보기로 전환 |
| Datasheet Review | 한 Tag 작업대: PDF + 지적 · 요약 · 칸 값 · Process · PMS · Expert(재질·설계·Tag) · Revision · Notes · 의견 · 이력 |
| Revision Comparison | 같은 Tag 의 이전 판과 칸별 비교 |
| Process Data Verification | 데이터시트 공정 값 ↔ Process Data 표 |
| PMS Compliance | 데이터시트 ↔ Piping Material Spec(Class 머리 · Ball Valve 품목) |
| Reports & Export | Valve List · Issue List · Mark-up PDF · CSV · Revision 비교 · Review Feedback |
| Settings | 이름 · 단축키 · Tag Numbering(배운 규칙) · Ball Valve 지식 · 버전 |

머리의 **?** 를 누르면 화면마다 한 줄 설명이 보입니다. 평소에는 숨겨져 있습니다.

## 3. 지적(Issue)의 종류와 색

| 종류 | 색 | 뜻 | 설계사 전달 |
|---|---|---|---|
| Data Error | 빨강 | 데이터시트 안에서 서로 맞지 않음 (Line No. 의 Class ≠ Piping Class, 없는 Note 참조 …) | ○ |
| Data Missing | 주황 | 값이 비어 있음 (PROCESS DATA 빈칸 전부 포함 — Process DS 를 참조해도) | ○ |
| Open Item | 주황 | HOLD · TBC · TBA — 풀고 값을 넣어야 함 | ○ |
| PMS Non-Compliance / Review | 빨강 | PMS 와 다름 / PMS 로 확인 못 함 | ○ |
| Process Mismatch | 주황 | Process Data 표와 다름 | ○ |
| Material Review / Valve Review | 청록 | 재질 · 설계 · Tag 번호 · 다른 데이터시트 대비 의견 (Action = Major · Confirm = Minor) | ○ |
| Revision Change | 노랑 | 이전 판과 다름 | ○ |
| Reviewer Correction / Comment | 파랑 | 내가 고친 값 · 남긴 의견 · Mark-up | ○ |
| Extraction Review | 보라 | 도구가 짝을 못 정한 칸 — 내부용 | × |

- 같은 이유의 지적(예: Process Data 빈칸 13개)은 작업대에서 **한 카드**로 묶입니다. 카드의 '상태 일괄…' 로 한 번에 바꿉니다.
- 상태: Open → Confirmed(설계사에게 보낼 것) · Dismissed(지적 아님 — 전달본에서 빠짐) · Resolved. 바꿀 때 이유를 적으면 감사 기록에 남습니다.
- 설계사에게 가는 문장은 한 줄입니다: *무엇이 문제 · 값 · 할 일*. 긴 근거는 Expert 탭에만 있습니다.

## 4. 작업대 요령

- 칸을 누르면 PDF 의 그 자리와 밸브 그림의 부위가 함께 표시됩니다. 값이 틀리면 ✎ 로 고칩니다(원본은 그대로, 누가 언제 고쳤는지 남음).
- PDF 위 **Mark-up** 줄: 스탬프 · 메모 · 타자기 · 글상자 · 말풍선 · 형광펜 · 취소선 · 밑줄 · 물결 밑줄 · 화살표 · 선 · 사각형 · 원 · 꺾은선 · 다각형 · 구름 · 펜 · 지우개.
  말풍선은 가리킬 곳에서 끌어 상자 자리에서 놓고, 꺾은선 · 다각형은 점마다 누른 뒤 두 번 누르거나 Enter.
  분류(Comment / Question / Error / Missing)에 따라 Issue 종류가 되고, 색 팔레트 · 굵기로 모양을 바꿀 수 있습니다(선택한 표시에도 적용).
  ★ 는 지금 도구·색·굵기를 즐겨찾기로 저장합니다. '바로' 를 켜면 의견 창 없이 바로 그려지고 의견은 나중에 Enter 로 답니다.
  스탬프(I)는 APPROVED · HOLD · ✓ · ✗ 등 종류를 고르고 누르는 자리에 놓습니다. 지우개(X)는 표시를 누르면 지웁니다(Ctrl+Z 되돌리기).
- Expert 탭: Action(조치) · Confirm(확인) · Note(참고, 접힘). 의견마다 근거 규격과 '지식' 설명, 근거 위치(칸 · Note · PMS 쪽 · Process Data 쪽) 링크.
- `[` `]` 로 왼쪽 Tag 목록 · 오른쪽 패널을 접습니다. `M` 으로 Mark-up 줄, `F` 로 PDF 검색.

## 5. Excel 두 가지

- **Valve List Excel**: 회사 TBE 양식 그대로(바뀐 칸 노랑 + 'Previous:' 메모 · Vendor 행 삭제) + **Summary · Summary by Area · All Valves**(Tag 한 줄씩 — Area · Site · Unit · Tag 구조 · 재질 · PFP · Fugitive · Fire Safe · NACE · SIL … 열, Excel 필터) + Datasheet Notes.
- **Issue List Excel**: 설계사 전달용. 맨 앞 No. · Area · Site · Unit, Area 순 정렬, Summary · Summary by Area · Summary by Tag 시트. 만들 때 **Issue Type 선택 창**이 뜹니다(선택은 기억됨).
- Mark-up PDF: 지적이 있는 쪽만 번호 붙은 색 상자 + **그 쪽 오른쪽 여백에 번호별 코멘트**(프로그램 지적 · 내 의견) + Tag 별 Issue Summary 쪽.
  마크업은 PDF 에 고정되어 어느 뷰어 · 인쇄에서도 화면 그대로 나옵니다. 선택 창에서 '마크업 고정' 을 끄면 Acrobat 에서 고칠 수 있는 주석으로 나옵니다.
- 공정 값(설계 온도 · 압력 · 유체 · 상)에 기댄 의견은 어느 문서 값인지 먼저 씁니다:
  *Based on Ref. Process Data CO2S-SSG-IN-REQ-00009 (p.54) design temp. 260 °C, seat RTFE exceeds its 230 °C limit …* /
  Process Data 에 값이 없으면 *Based on Datasheet design temp. …*.

## 6. 새 Revision(B · C · D)이 오면

- 그냥 Document Management 에 올리면 됩니다. 같은 Tag 의 새 판으로 묶이고, 규칙 검토는 자동으로 다시 됩니다.
- 이전 판의 검토는 이어받습니다: **Dismissed** 한 지적은 같은 칸이 그대로면 그대로 Dismissed · **Confirmed**(설계사에게 보낸) 지적이 그대로 남아 있으면 **"Not addressed since Rev A"** 로 표시(Major).
  칸에 단 의견도 그 칸이 안 바뀌었으면 새 판에 복사됩니다('Rev A' 표). 직접 그린 표시는 옛 쪽 것이라 복사되지 않습니다.
- 작업대 머리의 `Rev A→B ✓5 ✗0 +3` 칩 = 해결 · 미반영 · 새 지적. Tag 목록의 ✗N, 대시보드 Revision Changes 타일의 '미반영 N' 도 같은 수입니다.

## 7. 지적의 근거와 검증 보고

- 지적마다 **근거**가 붙습니다: 맞대어 본 쪽(PMS p.12 · Process Data p.54 · 이전 판 값 · 같은 데이터시트의 다른 칸)과 실제 값, 그리고 규칙 번호. 작업대 Issues 카드의 '근거:' 링크를 누르면 그 쪽이 열립니다.
  Issue List Excel 의 'Evidence' · 'Basis' 열, Mark-up PDF 의 쪽 옆 코멘트에도 같은 내용이 있습니다.
- **Checks 탭** = 이 Tag 에 대해 도구가 본 48 항목: ✓ 이상 없음 · ✗ 지적(누르면 그 지적) · – 자료가 없어 판단하지 않음(이유 표시: PMS 없음 · Process Data 에 없는 Tag · 설계 온도 없음 · 첫 판 …).
  – 는 통과가 아닙니다. 대시보드 'Verification Coverage' 와 Issue List Excel 'Verification' 시트(Tag × 항목)에서 전체를 봅니다.

## 8. 지적에 대한 결정 · Rule Performance (valve29)

- 지적마다 **결정**: Open · Confirmed · Modified(문구 · Severity 고쳐 보냄) · Dismissed · Deferred(보류) · Not Applicable · Resolved. Dismissed · Not Applicable · Modified 는 사유 분류를 고릅니다.
  Dismissed · Not Applicable 은 설계사 전달본에서 빠지고, 새 Revision 에도 같은 칸 · 같은 값이면 이어받습니다.
- 메뉴 **Rule Performance**: 규칙마다 지적 수와 결정 · 사유 · 3개월 추세. Dismiss % 는 오탐률이 아닙니다 — '도구 원인' 열을 보세요. 규칙 변경은 '변경 제안' 절차로만(규칙이 저절로 바뀌지 않음).
- 작업대 Data 탭 · PDF 의 빈 곳을 누르면 그 칸의 출처(파일 · Rev · 쪽 · 위치 · 읽은 방법)와 그 칸의 지적이 나옵니다. 자세한 것은 `docs/valve/valve29/USER_GUIDE_UPDATE.md`.

## 9. 새 창 · 실시간 연동

- 작업대 PDF 도구줄의 **⧉** = PDF 만 새 창으로(두 번째 모니터). 메인 창에서 Tag · 칸 · 지적을 고르면 새 창이 따라가고, 새 창에서 지적 상자나 칸을 누르면 메인 창이 그것을 엽니다.
- 머리의 **⧉ 새 창** = 지금 화면을 새 창으로. 예) 한 창은 Issue List, 다른 창은 작업대 — 목록에서 누르면 작업대가 그 Tag · 지적으로 갑니다. 한 창에서 결정을 바꾸면 다른 창에도 바로 반영됩니다.
- **⧉ PDF (화면 위쪽)** = 어느 화면에서나 PDF 창을 엽니다. **왼쪽 모니터에 Valve List / Issue List / PMS / Process, 오른쪽 모니터에 PDF 창** —
  줄을 누르면 오른쪽 창이 그 Tag · 칸 · 지적을 바로 보여 줍니다(다음 줄들은 미리 받아 둠, 보통 0.1 초대). **PDF 창에서도 Mark-up 도구 전부**(스탬프 · 말풍선 · 지우개 · Ctrl+Z …)를 쓰고,
  그 표시는 바로 메인 창 · Issue List 에 반영됩니다. PDF 창에서 J / K(▲ ▼)를 누르면 왼쪽 목록이 다음 / 이전 줄로 갑니다.
- **🔗 연동** 을 끄면 그 창은 따라가지 않습니다. 팝업이 막히면 브라우저 주소창의 팝업 허용을 켜 주세요.

## 10. 자주 묻는 것

- **Area · Unit 은 어디서 오나?** 데이터시트 제목(QELNG NORTH / SOUTH / W15)과 P&ID 번호에서. 제목에 '(SYSTEM xx – UNIT yy)' 가 있으면 기존 플랜트 = Brownfield.
- **왜 Process Data 빈칸을 다 지적하나?** 요청에 따라 Process DS 를 참조해도 전부 표기합니다. 한 카드로 묶여 있으니 일괄 Dismissed/Confirmed 로 처리하세요.
- **PMS 가 틀린 것 같다.** 판정마다 PMS 쪽 번호가 있습니다. 누르면 그 자리를 엽니다. 도구는 어느 쪽이 옳은지 정하지 않습니다.
- **다시 읽기.** Document Management 에서 '다시 읽기' — 검토 상태 · 의견 · 고친 값은 유지됩니다.
- **느리다.** 처음 켠 뒤 한 번은 뒤에서 계산합니다(수십 초). 그 뒤로는 바로 뜹니다. 서버를 다시 켜도 계산 결과는 `pid_data/valve/cache/review/` 에 남아 있습니다.
- **백업.** 매일 처음 켤 때 `pid_data/valve/backups/valve.db.<날짜>.bak` (7개 보관). 원본 파일은 덮어쓰지 않습니다.
- **규칙의 근거.** Settings › Ball Valve 지식 · Tag Numbering. 회사 사양 값(Floating 한계 · 시트 온도 한계 · PST 정책)이 다르면 개발 쪽에 알려 주세요 — 규칙표를 맞춥니다.
