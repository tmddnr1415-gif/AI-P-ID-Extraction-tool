@echo off
rem hotfix50/51 - start the P&ID server (company network, port 8000) at logon.
rem Registers a Task Scheduler entry for THIS user; no administrator needed.
rem The server window starts minimised.  Undo with uninstall_autostart_lan.bat.
rem ASCII only and CRLF on purpose (see run_lan_service.bat).
setlocal
cd /d "%~dp0"
set TASK=PID_Extract_LAN
schtasks /Create /F /SC ONLOGON /RL LIMITED /TN "%TASK%" /TR "cmd.exe /c start \"PID\" /min \"%~dp0run_lan_service.bat\""
if errorlevel 1 (
  echo.
  echo Could not register the task.  See the message above.
  pause
  exit /b 1
)
echo.
echo Registered: the P^&ID server starts on LAN port 8000 at every logon.
echo Starting it now ...
schtasks /Run /TN "%TASK%" >nul
echo.
echo Check in a browser:  http://localhost:8000/
echo Other PCs also need the firewall opened once - open_firewall_8000.bat (administrator).
pause
