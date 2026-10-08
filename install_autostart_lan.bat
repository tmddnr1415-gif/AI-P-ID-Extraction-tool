@echo off
rem hotfix50 - start the P&ID server (company network, port 8000) at logon.
rem Registers a Task Scheduler entry for THIS user; no administrator needed.
rem The window starts minimised.  Undo with uninstall_autostart_lan.bat.
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set TASK=PID_Extract_LAN
schtasks /Create /F /SC ONLOGON /RL LIMITED /TN "%TASK%" /TR "cmd.exe /c start \"PID\" /min \"%~dp0run_lan_service.bat\""
if errorlevel 1 (
  echo.
  echo 작업 스케줄러에 등록하지 못했습니다.  위 메시지를 확인하세요.
  pause
  exit /b 1
)
echo.
echo 등록했습니다: 로그온할 때 P^&ID 분석 서버가 사내망 포트 8000 으로 켜집니다.
echo 지금 한 번 켭니다.
schtasks /Run /TN "%TASK%" >nul
echo.
echo 다른 PC 에서 들어오려면 방화벽도 열어야 합니다 - open_firewall_8000.bat (관리자 권한).
pause
