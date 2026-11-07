valve11 — Ball Valve 엔지니어로서 검토 (+ valve10 까지 전부)

무엇이 달라지나
  1. 작업대 오른쪽 'Expert' 탭: 한 데이터시트를 Ball Valve 엔지니어처럼 봅니다.
     - 재질 (valve10 의 MR 규칙)
     - 설계 (새 VR 규칙 15개): PMS 플랜지 면 RF/RTJ · 크기에 맞는 플랜지 규격(B16.5 / B16.47) · Floating/Trunnion 이 크기·Class·PMS 품목에 맞는지 ·
       Fail 위치와 스프링 · SIL(Fail-last · Partial stroke) · 누설 등급과 시트 · Anti-static / Blow-out · 가연·독성 유체의 Fire-safe ·
       Trunnion 시트 구성과 캐비티 릴리프(액상 · Dense CO2) · Cold 보온의 확장 Stem · Piggable Full bore · 밸브 크기와 배관 크기 · Erosive 연질 시트
     - 다른 데이터시트 대비: 같은 Piping Class 데이터시트 대부분과 다른 값을 찾아 줍니다 (올린 데이터시트 전체에서 배움).
     의견마다 근거 규격과 '지식' 설명을 펼쳐 볼 수 있습니다.
  2. Settings › 'Ball Valve 지식': 도구가 기준으로 쓰는 표준 · 설계 · 재질 지식 28항목.
  3. Issue List 에 'Valve Review'(조치 필요 = Major, 확인 필요 = Minor). Valve List 의 열 이름은 'Expert Review (Tool)'.

적용 순서
  1) apply_to_PID_dev.bat → 확인 → 2) apply_to_PID_ops.bat → 8000 서버 재시작
  valve01~10 을 적용하지 않았어도 이것 하나로 됩니다. 대시보드는 바꿀 것 없음.
