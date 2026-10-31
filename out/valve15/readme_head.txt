valve15 — Area · Unit 별 Tag 번호 규칙을 배우고 검사 (+ valve14 까지 전부)

무엇이 달라지나
  1. 올린 데이터시트의 Tag 를 Area · Site · Unit 별로 묶어 번호 규칙을 스스로 배웁니다 (Tag 절차서 문서 없이):
     접두가 무엇인지(Unit · 제목의 SYSTEM · P&ID 의 System) · 기능 코드 · 번호 자릿수와 앞자리 · 구분(공백 / '-') · A/B · 번호 계열이 어느 P&ID 장에 있는지.
     예) North Unit 98 = 98 + ESDV/BDV/MOV/XV + 980nnn (A/B) · South Unit 98 = 98 + 기능 + '-' + nnn · W15 = 315 + 기능 + 980nnn
         Brownfield North = 제목의 SYSTEM 번호가 앞에 (00XV · 08SDV …) · Brownfield South = 제목의 UNIT 번호가 앞에 (19XV · 84XV …)
  2. Settings › 'Tag Numbering' 표에서 배운 규칙을 봅니다.
  3. 규칙을 벗어난 Tag · 두 문서에 같은 Tag · 기능 코드와 Fail 동작이 안 맞는 것(ESDV/SDV 는 보통 Fail Close, BDV 는 Fail Open)을
     Expert 탭 'Tag 번호' 의견과 Issue List 'Valve Review' 로 알려 줍니다.
  4. Valve List Excel 'All Valves' 시트에 Tag Prefix · Function · Loop No. 열 (필터).

적용 순서
  1) apply_to_PID_dev.bat → 확인 → 2) apply_to_PID_ops.bat → 8000 서버 재시작
  valve01~14 를 적용하지 않았어도 이것 하나로 됩니다. 대시보드는 바꿀 것 없음.
