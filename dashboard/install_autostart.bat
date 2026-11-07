@echo off
rem ============================================================
rem  Register the dashboard server to start automatically at logon
rem  (Task Scheduler task "DeptDashboardServer").
rem  The task runs watchdog.py with pythonw (no window), which
rem  starts server.py on port 8080 and restarts it if it crashes
rem  or stops responding. Logs: watchdog.log, server.log
rem  Double-click to install. No admin rights needed (runs as you).
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"
set "PYW="
for /f "delims=" %%i in ('where pythonw 2^>nul') do if not defined PYW set "PYW=%%i"
if not defined PYW (
  echo [ERROR] pythonw.exe not found in PATH.
  pause
  exit /b 1
)
echo pythonw : %PYW%
echo folder  : %~dp0
schtasks /Create /F /TN "DeptDashboardServer" /SC ONLOGON /RL LIMITED /TR "\"%PYW%\" \"%~dp0watchdog.py\""
if errorlevel 1 (
  echo [ERROR] Failed to register the task. Ask IT if Task Scheduler is restricted.
  pause
  exit /b 1
)
echo.
echo Registered. Starting now...
schtasks /Run /TN "DeptDashboardServer"
timeout /t 6 >nul
start "" "http://localhost:8080/"
echo Done. The server will start automatically every time you log on.
echo To remove: uninstall_autostart.bat
pause
