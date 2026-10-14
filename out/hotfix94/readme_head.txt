hotfix94 — PID_dev + 운영(PID) 꾸러미  (97a8732 기준 누적 · hotfix56 ~ 94 + LOGIC L1 ~ L19 포함)

P&ID 분석 (hotfix94 · 이번에 새로 들어간 것)
  · 도면에서 Shift 를 누른 채 끌어 계기 여러 개를 고른 뒤, Shift 를 누른 채 그중 하나를 왼쪽 클릭하면
    "SCT 공급 · VENDOR · 둘 다 아님" 판이 뜹니다.  고른 것이 묶음 전체에 한 번에 들어가고
    오른쪽 목록에도 바로 반영됩니다.  (Ctrl+Z 로 되돌리기 가능)
  · 묶음에서 하나를 빼려면 Ctrl 을 누른 채 그 상자를 클릭하세요.
  · 묶음 밖 상자를 Shift+클릭하면 예전처럼 묶음에 더해집니다.

이전 꾸러미(hotfix93)의 내용도 모두 들어 있습니다
  (LOGIC L15~L19 · 서버가 "다른 프로세스가 파일을 사용 중" 으로 다시 안 뜨던 것 고침).

순서 (zip 을 아무 폴더에 풀고):
  1) apply_to_PID_dev.bat 더블클릭
  2) 분석이 돌고 있지 않을 때  apply_to_PID_ops.bat 더블클릭
       → "포트 8000 서버를 다시 띄울까요? [Y/n]" 에서 Enter
       → "[완료] 서버가 다시 떴습니다 — 업데이트 hotfix94" 가 나오면 됩니다
  3) 대시보드에서 P&ID 분석을 다시 열고 Ctrl+F5
  4) (hotfix93 때 아직 안 했다면 한 번만) 서버 창 파일 바꾸기
       ① 작업 표시줄에서 "PID server" 창을 모두 닫습니다
       ② C:\Claude\PID\run_lan_service.bat 의 이름을 run_lan_service.bat.old 로 바꿉니다
       ③ zip 의 service 폴더에 있는 run_lan_service.bat 을 C:\Claude\PID 에 복사합니다
       ④ C:\Claude\PID\run_lan_service.bat 을 더블클릭 — 창에
          "Ctrl+C does not stop the server - close the window." 가 보이면 끝
       ※ hotfix93 때 이미 했으면 건너뛰세요.

문제가 생기면:  rollback_PID_ops.bat 더블클릭.
