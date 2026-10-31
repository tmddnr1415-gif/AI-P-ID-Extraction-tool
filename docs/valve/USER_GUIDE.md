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
- PDF 위 **Mark-up** 줄: 사각형 · 구름 · 화살표 · 펜 · 글상자 … 분류(Comment / Question / Error / Missing)에 따라 Issue 종류가 됩니다.
- Expert 탭: Action(조치) · Confirm(확인) · Note(참고, 접힘). 의견마다 근거 규격과 '지식' 설명, 근거 위치(칸 · Note · PMS 쪽 · Process Data 쪽) 링크.
- `[` `]` 로 왼쪽 Tag 목록 · 오른쪽 패널을 접습니다. `M` 으로 Mark-up 줄, `F` 로 PDF 검색.

## 5. Excel 두 가지

- **Valve List Excel**: 회사 TBE 양식 그대로(바뀐 칸 노랑 + 'Previous:' 메모 · Vendor 행 삭제) + **Summary · Summary by Area · All Valves**(Tag 한 줄씩 — Area · Site · Unit · Tag 구조 · 재질 · PFP · Fugitive · Fire Safe · NACE · SIL … 열, Excel 필터) + Datasheet Notes.
- **Issue List Excel**: 설계사 전달용. 맨 앞 No. · Area · Site · Unit, Area 순 정렬, Summary · Summary by Area · Summary by Tag 시트. 만들 때 **Issue Type 선택 창**이 뜹니다(선택은 기억됨).
- Mark-up PDF: 지적이 있는 쪽만 번호 붙은 색 상자 + Tag 별 Issue Summary 쪽. 인쇄하면 표시가 같이 나옵니다.

## 6. 자주 묻는 것

- **Area · Unit 은 어디서 오나?** 데이터시트 제목(QELNG NORTH / SOUTH / W15)과 P&ID 번호에서. 제목에 '(SYSTEM xx – UNIT yy)' 가 있으면 기존 플랜트 = Brownfield.
- **왜 Process Data 빈칸을 다 지적하나?** 요청에 따라 Process DS 를 참조해도 전부 표기합니다. 한 카드로 묶여 있으니 일괄 Dismissed/Confirmed 로 처리하세요.
- **PMS 가 틀린 것 같다.** 판정마다 PMS 쪽 번호가 있습니다. 누르면 그 자리를 엽니다. 도구는 어느 쪽이 옳은지 정하지 않습니다.
- **다시 읽기.** Document Management 에서 '다시 읽기' — 검토 상태 · 의견 · 고친 값은 유지됩니다.
- **느리다.** 처음 켠 뒤 한 번은 뒤에서 계산합니다(수십 초). 그 뒤로는 바로 뜹니다. 서버를 다시 켜도 계산 결과는 `pid_data/valve/cache/review/` 에 남아 있습니다.
- **백업.** 매일 처음 켤 때 `pid_data/valve/backups/valve.db.<날짜>.bak` (7개 보관). 원본 파일은 덮어쓰지 않습니다.
- **규칙의 근거.** Settings › Ball Valve 지식 · Tag Numbering. 회사 사양 값(Floating 한계 · 시트 온도 한계 · PST 정책)이 다르면 개발 쪽에 알려 주세요 — 규칙표를 맞춥니다.
