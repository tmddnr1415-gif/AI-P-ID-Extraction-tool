@echo off
rem hotfix50 - remove the logon entry made by install_autostart_lan.bat.
rem It does NOT kill python processes: the department dashboard server runs on
rem python too.  Close the minimised "P&ID 분석 서버" window to stop the server.
chcp 65001 >nul
schtasks /Delete /F /TN "PID_Extract_LAN"
echo.
echo 자동 시작을 지웠습니다.  지금 켜져 있는 서버는 작업 표시줄의 "P^&ID 분석 서버" 창을 닫아 끄세요.
echo (대시보드 서버도 python 이라 여기서 python 을 일괄 종료하지 않습니다.)
pause
