hotfix96 — PID_dev + 운영(PID) 꾸러미  (97a8732 기준 누적 · hotfix56 ~ 95 + LOGIC L1 ~ L22 포함)

LOGIC 검토 (이번에 새로 들어간 것)
  · L21: 앞으로의 Logic 양식(19VA · Control Logic & Loop Diagram)을 읽습니다.
         예전에는 그 PDF 에서 1장만 Logic 시트로 읽었고, 이제 827장을 읽습니다.
  · L22: 게이트 종류를 못 읽은 블록은 사람이 눌러 고릅니다 (AND · OR · 메모리 등).
         FM/TO 칸을 못 읽었으면 그 칸에 값을 적어 잇습니다.
         시간 블록(PD · GT 등)의 기본 시간이 5초이고, 게이트마다 바꿀 수 있습니다.
         첫 화면에서 분석 기록을 지울 수 있습니다.
  · 고친 값은 분석 결과와 따로 저장되어 다시 열어도 남습니다.
  · 새 양식 PDF 는 업데이트 뒤 다시 분석해 주세요.

서버 점검 도구 (check_pid_server.bat)
  · 한국어 Windows 에서 "'NoneType' object has no attribute 'splitlines'" 로 죽던 것을 고쳤습니다.
    이제 포트 8000 을 어느 프로그램이 잡고 있는지 제대로 보여 줍니다.

이전 꾸러미 내용도 모두 들어 있습니다 (hotfix95: Logic 분석이 WinError 5 로 멈추던 것 등).

순서 (zip 을 아무 폴더에 풀고):
  1) apply_to_PID_dev.bat 더블클릭
  2) 분석이 돌고 있지 않을 때  apply_to_PID_ops.bat 더블클릭
       → "포트 8000 서버를 다시 띄울까요? [Y/n]" 에서 Enter
       → "[완료] 서버가 다시 떴습니다 — 업데이트 hotfix96" 가 나오면 됩니다
  3) 대시보드에서 P&ID 분석 · LOGIC 을 다시 열고 Ctrl+F5
  4) 서버 창 파일(run_lan_service.bat)을 이미 새 것으로 바꿨으면 건너뛰세요.
     아직이면 zip 의 service 폴더의 run_lan_service.bat 을 C:\Claude\PID 에 넣습니다
     (서버 창을 모두 닫은 뒤, 옛 파일은 .old 로).

문제가 생기면:  rollback_PID_ops.bat 더블클릭.
