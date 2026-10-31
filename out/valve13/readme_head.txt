valve13 — 설계사용 출력 때 넣을 Issue Type 고르기 (+ valve12 까지 전부)

무엇이 달라지나
  1. Issue List Excel 이나 Mark-up PDF 를 만들 때 먼저 'Issue Type 선택' 창이 뜹니다.
     종류마다 건수가 보이고, 넣을 것만 체크합니다 (전체 · 모두 끄기 · 설계사용 기본 단추).
     예) 재질 · 설계 검토만 보내기 → Material Review + Valve Review 만 체크.
  2. 고른 종류는 다음 출력 때도 그대로 기억합니다.
  3. 어디서 만들든 같습니다: Reports & Export · Issue List 화면 · Datasheet Review(한 Tag PDF) · 분석 끝 Mark-up PDF 단추.
  4. Dismissed 처리한 지적은 언제나 빠집니다.

적용 순서
  1) apply_to_PID_dev.bat → 확인 → 2) apply_to_PID_ops.bat → 8000 서버 재시작
  valve01~12 를 적용하지 않았어도 이것 하나로 됩니다. 대시보드는 바꿀 것 없음.
