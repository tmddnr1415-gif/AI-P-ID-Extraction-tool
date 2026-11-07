hotfix105 — PID_dev + 운영(PID) 꾸러미  (97a8732 기준 누적 · hotfix101~104 내용 전부 포함)

이번에 들어간 것 — LOGIC
  (L46) 선이 연결 안 된 입력(예: 매크로의 O_OPN 단자)은 비활성(0)으로 보고
        게이트가 그 값대로 동작합니다.
        · 입력이 0 인 NOT 은 이제 출력 1 을 냅니다
        · 출력이 안 나오면 "입력선 N개가 연결 안 됨 (0 으로 봄)" 이라고 알려 줍니다
        · 그룹 시험 · 검토 결과는 다시 배우면 일부 바뀔 수 있습니다
  (이전 hotfix103~104 의 L43 · L44 · L45 도 그대로 들어 있습니다)

순서 (zip 을 아무 폴더에 풀고):
  1) apply_to_PID_dev.bat 더블클릭
  2) 분석이 돌고 있지 않을 때  apply_to_PID_ops.bat 더블클릭
       → "포트 8000 서버를 다시 띄울까요? [Y/n]" 에서 Enter
       → "[완료] 서버가 다시 떴습니다 — 업데이트 hotfix105" 가 나오면 됩니다
  3) 대시보드에서 LOGIC 을 다시 열고 Ctrl+F5
  4) 서버 창 파일(run_lan_service.bat)을 이미 새 것으로 바꿨으면 건너뛰세요.
     아직이면 zip 의 files 폴더에 있는 run_lan_service.bat 을 C:\Claude\PID 에 넣습니다
     (서버 창을 모두 닫은 뒤, 옛 파일은 .old 로).

문제가 생기면:  rollback_PID_ops.bat 더블클릭.
