hotfix51 — 자동 시작 창에서 P&ID 서버가 뜨지 않던 것 (배치 파일 한글 문제) · hotfix50 누적

이 꾸러미는 hotfix50 위에 hotfix51 을 얹은 것입니다.  푸는 법은 이전과 같습니다
(프로그램 폴더에 그대로 덮어쓰기 · app/_data/ 와 data/ 는 들어 있지 않습니다).

1. 원인: 서버 창에 'twork' · 'loopback' · 'uble-click' 같은 글자가 찍히고 서버가 안 뜬 것은, Windows 명령 창이
   한글이 든 bat 파일을 UTF-8 모드에서 줄 가운데부터 읽었기 때문입니다.  분석 엔진·화면은 바뀌지 않았습니다.
2. 고친 것: bat 파일 여섯(start · build · run_lan_service · install/uninstall_autostart_lan · open_firewall_8000)을
   영어·ASCII 로 바꿨고, 자동 시작은 start.bat 을 거치지 않고 서버를 직접 띄웁니다.
3. 회사 PC 에서:
   ① 오류가 찍힌 "P&ID 분석 서버" 창을 닫습니다
   ② 이 꾸러미를 덮어씁니다
   ③ install_autostart_lan.bat 를 다시 더블클릭합니다 (방화벽은 다시 열 필요 없습니다)
   ④ 작업 표시줄의 "PID server - LAN port 8000" 창 안에 "Uvicorn running on http://0.0.0.0:8000" 이 보이면 됩니다
   ⑤ http://localhost:8000/?embed=1&mode=bid 를 다시 엽니다
4. 앞으로 서버 창 이름은 "PID server - LAN port 8000" 입니다.  끌 때는 그 창을 닫습니다.
5. ⚠ bat 파일은 이 개발 환경(Linux)에서 실행해 볼 수 없습니다.  그래도 안 뜨면 그 창의 마지막 몇 줄을 사진으로 보내 주세요.

