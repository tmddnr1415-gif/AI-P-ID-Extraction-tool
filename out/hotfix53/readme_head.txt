hotfix53 — .venv 설치가 cp949 오류로 멈추던 것 · hotfix52 누적

이 꾸러미는 hotfix52 위에 hotfix53 을 얹은 것입니다.  hotfix52 를 따로 적용할 필요 없이 이것 하나만
C:\Claude\PID 에 덮어쓰세요 (app/_data/ 와 data/ 는 들어 있지 않습니다).  분석 엔진은 바뀌지 않았습니다.

1. 원인: pip 은 requirements 파일을 Windows 코드페이지(cp949)로 읽는데 파일 주석이 UTF-8 한글이었습니다.
   requirements*.txt 다섯을 영어 주석(ASCII)으로 바꿨습니다.  고정 버전은 그대로입니다.
2. 덮어쓴 뒤 같은 명령을 다시 실행하면 됩니다:
     cd /d C:\Claude\PID
     .venv\Scripts\python -m pip install --no-index --find-links wheels -r requirements-win.txt
     .venv\Scripts\python -m pip install --no-index --find-links wheels_r55 -r requirements-win-dxf.txt
3. 그다음 install_autostart_lan.bat → check_pid_server.bat ("서버는 정상입니다").
   바닥줄 "업데이트 hotfix53" 으로 적용 여부를 확인할 수 있습니다.

