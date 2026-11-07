valve16 — Excel 목록 앞에 No. · Summary 시트 (+ valve15 까지 전부)

무엇이 달라지나
  1. 두 Excel 의 모든 목록 시트 첫 열이 No. 입니다 (Issue List · Summary by Tag · All Valves · Datasheet Notes).
  2. Issue List Excel 'Summary' 시트: Area · Site · Unit 별 Issue Type 건수 · Major · Minor · Tag 수 · 합계, 아래에 Area 별 합계 표.
  3. Valve List Excel 'Summary' 시트: Area · Site · Unit 별 Valve Type(ESDV · SDV · BDV · XV · MOV) 수 · 열린 지적 · 조치 필요 Tag · 새/바뀐 Tag, 아래에 Area 별 합계 표.
  4. 두 Summary 모두 Excel 필터가 걸려 있습니다.

적용 순서
  1) apply_to_PID_dev.bat → 확인 → 2) apply_to_PID_ops.bat → 8000 서버 재시작
  valve01~15 를 적용하지 않았어도 이것 하나로 됩니다. 대시보드는 바꿀 것 없음.
