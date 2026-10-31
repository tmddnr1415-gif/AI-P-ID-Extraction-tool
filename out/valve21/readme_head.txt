valve21 — 실자료로 1,839번 변이 검증 · Valve List 멈춤 결함 수정 · Area/Unit 화면 (+ valve20 까지 전부)

무엇이 달라지나
  1. 결함 수정: Valve List 가 두 번째 열 때 '불러오는 중…' 에서 멈추던 문제(서버 캐시가 압축 헤더를 재사용). 실패하면 '다시 시도' 단추가 나옵니다.
  2. 검토 보완(실자료 164 Tag 에 변이 14가지를 넣어 1,839번 대조, 100 % 일치):
     - Fire Safe 칸이 'HOLD (API 607 …)' 인데 PMS 품목이 Fire tested 면 Compliant 가 아니라 '확인 필요'(10건).
     - 같은 Piping Class 다수 재질이 표기만 달라('CF8M/CF3M' · 'CF8M') 갈리던 것을 합쳐, 다른 재질(예: WCB)을 제대로 잡습니다.
     - NACE 칸 'NA' 인데 Class 가 NACE 요구면 Non-Compliant 대신 '확인 필요'.
  3. Area · Unit 을 화면에서: Valve List 열(필터) · Issue List 의 Area 선택 · 작업대 머리 · 대시보드 'By Area' 카드.
  4. Expert 탭의 '참고' 의견은 접힌 채 시작합니다 (제목을 누르면 펼침).

적용 순서
  1) apply_to_PID_dev.bat → 확인 → 2) apply_to_PID_ops.bat → 8000 서버 재시작
  valve01~20 을 적용하지 않았어도 이것 하나로 됩니다. 대시보드는 바꿀 것 없음.
