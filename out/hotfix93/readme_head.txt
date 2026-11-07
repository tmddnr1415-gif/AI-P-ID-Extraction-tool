hotfix93 — PID_dev + 운영(PID) 꾸러미  (97a8732 기준 누적 · hotfix56 ~ 93 + LOGIC L1 ~ L19 포함)

LOGIC 검토 (L15 ~ L19 · 이번에 새로 들어간 것)
  · 출력을 켜면 그 출력에 필요한 입력들이 주황색으로 세 번 깜박여 알려 줍니다
  · 매크로 블록이 시간에 맞춰 안에서 같이 돕니다 · 타이머 시간을 고칠 수 있고(기본 10초) 남은 시간을 셉니다
  · 게이트 출력은 언제나 게이트 논리대로 — 입력 조건이 안 맞으면 출력이 서지 않습니다 (OR · NOR · 투표 ·
    메모리 · 타이머 · STEP 까지) · 시트를 넘어 이어서 켜집니다 · 준 신호를 한 번에 모두 풀기
  · 켜진 신호선을 가늘게 그립니다
  · 신호 현황 창 (옮길 수 있음): 내가 준 신호 · 나간 출력 · 멈춘 곳 — 다른 시트에서도 끌 수 있고, 누르면 그 시트로

P&ID 서버 (hotfix93)
  · 서버가 멈춘 뒤 다시 띄울 때 "다른 프로세스가 파일을 사용 중" 이 나오며 다시 안 뜨던 것을 고쳤습니다.
    서버 기록 파일(logs\server.log)을 다른 프로그램이 쥐고 있어도 서버는 뜹니다 (그때는 새 이름의 기록 파일에 씁니다).
  · 서버 창에서 Ctrl+C 를 눌러도 서버가 꺼지지 않습니다.  끄려면 창을 닫으세요.
  ※ 이 고침은 서버 창 파일(run_lan_service.bat)도 바뀌어야 완성됩니다 — 아래 4) 를 한 번 해 주세요.

순서 (zip 을 아무 폴더에 풀고):
  1) apply_to_PID_dev.bat 더블클릭
  2) 분석이 돌고 있지 않을 때  apply_to_PID_ops.bat 더블클릭
       → "포트 8000 서버를 다시 띄울까요? [Y/n]" 에서 Enter
       → "[완료] 서버가 다시 떴습니다 — 업데이트 hotfix93" 이 나오면 됩니다
  3) 대시보드에서 P&ID 분석 · LOGIC 을 다시 열고 Ctrl+F5
  4) 서버 창 파일 바꾸기 (한 번만)
       ① 작업 표시줄에서 "PID server" 창을 모두 닫습니다 (여러 개면 전부)
       ② C:\Claude\PID\run_lan_service.bat 의 이름을 run_lan_service.bat.old 로 바꿉니다
       ③ zip 의 service 폴더에 있는 run_lan_service.bat 을 C:\Claude\PID 에 복사합니다
       ④ C:\Claude\PID\run_lan_service.bat 을 더블클릭 — 창에
          "Ctrl+C does not stop the server - close the window." 가 보이면 끝
       ※ 서버 창이 켜져 있는 동안에는 이 파일을 덮어쓰지 마세요 (돌던 창이 엉뚱하게 움직입니다).

문제가 생기면:  rollback_PID_ops.bat 더블클릭.  서버 창 파일은 .old 를 원래 이름으로 되돌리면 됩니다.
