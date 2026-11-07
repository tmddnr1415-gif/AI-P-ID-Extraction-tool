valve18 — Issue List Excel 에 'Summary by Area' 시트 (+ valve17 까지 전부)

무엇이 달라지나
  1. Issue List Excel 세 번째 시트 'Summary by Area': North · South · Brownfield · W15 마다 한 줄 —
     Unit · Tag 수 · 지적 합계 · Major · Minor · Issue Type 별 건수 · 검토 상태(Open · Confirmed · Resolved) 별 건수, 맨 아래 Total.
  2. 그 아래 'By Area × Issue Type × Severity' 표: Area 마다 종류별 Major / Minor 와 Tag 수.
  3. 시트 순서: Issue List · Summary (Area · Site · Unit 세부) · Summary by Area · Summary by Tag · Info.

적용 순서
  1) apply_to_PID_dev.bat → 확인 → 2) apply_to_PID_ops.bat → 8000 서버 재시작
  valve01~17 을 적용하지 않았어도 이것 하나로 됩니다. 대시보드는 바꿀 것 없음.
