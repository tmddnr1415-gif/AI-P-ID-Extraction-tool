valve14 — Issue List · 전체 Valve List 를 Area · Unit 별로 걸러 보기 (+ valve13 까지 전부)

무엇이 달라지나
  1. Issue List Excel (설계사 전달용): 맨 앞에 Area · Site · Unit 열. Excel 필터로 North / South / Brownfield / W15, Unit 별로 고릅니다.
     Summary by Tag 시트도 같은 열이 있고, Material Review · Valve Review 건수 열이 더해졌습니다.
  2. Valve List Excel: 'All Valves' 시트 — 전체 Valve 를 한 줄씩 (Area · Site · Unit · Tag · 종류 · Doc · Rev · Service · P&ID · Line ·
     Class · Size · Rating · 재질 · Fail · 누설 · NACE · 특수 요구사항 · Expert Review · 열린 지적 수 …), 필터 · 틀 고정.
     밸브 종류 시트(ESDV · BDV · XV · MOV …)에도 Area · Site · Unit 열과 필터.
  3. Area · Unit 은 문서에서 읽습니다: 데이터시트 제목의 QELNG NORTH / SOUTH / W15,
     제목에 '(SYSTEM xx – UNIT yy)' 가 있으면 기존 플랜트 = Brownfield (Site 열에 North/South 는 그대로).
     Unit 은 제목의 UNIT → 없으면 P&ID 번호(98-98-PR-PID → 98).
  4. 두 Excel 모두 Reports & Export 화면에서 만듭니다 (Issue List 는 Issue Type 선택 창을 거칩니다).

적용 순서
  1) apply_to_PID_dev.bat → 확인 → 2) apply_to_PID_ops.bat → 8000 서버 재시작
  valve01~13 을 적용하지 않았어도 이것 하나로 됩니다. 대시보드는 바꿀 것 없음.
