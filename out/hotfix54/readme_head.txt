hotfix54 — 서버가 켜지다 죽고 10초마다 다시 켜지던 것 · hotfix52·53 누적

이 꾸러미 하나만 C:\Claude\PID 에 덮어쓰세요 (app/_data/ 와 data/ 는 들어 있지 않습니다).
분석 엔진은 바뀌지 않았습니다.  ★ 덮어쓰기 전에 "PID server - LAN port 8000" 창을 먼저 닫으세요
(실행 중인 bat 파일을 바꾸면 cmd 가 엉뚱한 줄부터 읽습니다).

1. 원인: hotfix52 부터 서버 출력을 logs\server.log 로 보내는데, 한국어 Windows 의 파이썬은 그 파일을
   cp949 로 씁니다.  cp949 에는 '—' 가 없고, 사람이 손으로 더한 행이 있는 DB 에서는 서버가 켜질 때
   '—' 가 든 점검 문장을 한 줄 출력합니다 → UnicodeEncodeError → 켜지는 도중에 죽음.
2. 고친 것:
   - run_lan_service.bat · check_pid_server.bat 에 set PYTHONUTF8=1 (로그를 UTF-8 로)
     메모장으로 직접 넣은 한 줄이 있었다면 이 파일이 같은 내용을 담고 있으니 그대로 덮어쓰면 됩니다.
   - 그래도 cp949 로 쓰게 되면 못 쓰는 글자를 '?' 로 바꿔 쓰고 서버는 산다 (app/console.py · exe 도 같음)
   - 서버가 멈추면 창에 logs\server.log 끝(마지막 오류)을 보여 줍니다
3. 확인: run_lan_service.bat 다시 실행(또는 PC 재시작) → check_pid_server.bat → "서버는 정상입니다" ·
   [2] 줄 끝이 hotfix54.

