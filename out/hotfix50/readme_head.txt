hotfix50 — 부서 대시보드(입찰 / 실행 프로젝트 > P&ID 분석)에 이 프로그램을 넣기 · hotfix49 누적

이 꾸러미는 hotfix49 위에 hotfix50 을 얹은 것입니다.  푸는 법은 이전과 같습니다
(프로그램 폴더에 그대로 덮어쓰기 · app/_data/ 와 data/ 는 들어 있지 않습니다).

1. 분석 엔진은 바뀌지 않았습니다.  결과 · Excel 은 그대로이고 다시 분석할 필요가 없습니다.
2. 대시보드 폴더에는 아무것도 넣지 않습니다.  이 프로그램은 부서장 PC 에서 포트 8000 으로 따로 돌고,
   대시보드가 그 화면을 iframe 으로 보여 줍니다.  절차 전문은 docs/dashboard_embed.md 입니다.
3. 부서장 PC 에서 한 번:
   ① open_firewall_8000.bat 를 오른쪽 클릭 → 관리자 권한으로 실행
      (대시보드 대역도 열려면 명령 창에서  open_firewall_8000.bat 65.3.0.0/16 )
   ② install_autostart_lan.bat 더블클릭 — 로그온 때 자동으로 켜지고 지금 한 번 켜집니다
   ③ 다른 PC 의 Edge 에서 http://ASEUNGWOOK-B01:8000/ 이 열리는지 확인
   손으로 켜려면  start.bat --lan --no-reload  또는  PID_Extract.exe --lan
4. 사내망 모드에서는 루프백 · 사설망 · 이 PC 의 /16 대역만 들어옵니다 (대시보드 서버와 같은 규칙).
   다른 대역을 더하려면 환경 변수 PID_ALLOW=65.4.0.0/16 .
5. 대시보드를 만든 Claude 에게 줄 프롬프트는 docs/dashboard_embed.md 3절에 그대로 있습니다.
   주소는  http://<서버>:8000/?embed=1&mode=bid(입찰) 또는 epc(실행)&user=<이름>  입니다.
   embed=1 이면 이 화면의 왼쪽 메뉴가 숨고 결과 탭이 결과 머리 아래 줄로 옵니다.
6. 끄기: 작업 표시줄의 "P&ID 분석 서버" 창을 닫습니다.  자동 시작 해제는 uninstall_autostart_lan.bat
   (대시보드 서버도 python 이라 python 을 일괄 종료하지 않습니다).
7. ⚠ bat 파일은 이 개발 환경(Linux)에서 실행해 보지 못했습니다.  처음 한 번은 창의 메시지를 확인해 주세요.
   화면이 예전 모양이면 Ctrl+F5.  바닥줄 "업데이트 hotfix50" 으로 적용 여부를 확인할 수 있습니다.

