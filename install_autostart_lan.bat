@echo off
rem hotfix50/51 - start the P&ID server (company network, port 8000) at logon.
rem Registers a Task Scheduler entry for THIS user; no administrator needed.
rem The server window starts minimised.  Undo with uninstall_autostart_lan.bat.
rem ASCII only and CRLF on purpose (see run_lan_service.bat).
rem hotfix132: python and packages are checked first - a task that registers but
rem never comes up is worse than a message here.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set TASK=PID_Extract_LAN
if exist ".venv\Scripts\python.exe" (set PY=.venv\Scripts\python.exe) else (set PY=python)
%PY% -c "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python 3.11 is not installed or not on PATH - see docs\offline_setup_windows.md
  echo   expected: .venv\Scripts\python.exe  ^(run setup.bat once^)
  pause
  exit /b 1
)
%PY% -c "import importlib.util,sys; m=[x for x in ('fastapi','uvicorn','multipart','pymupdf','openpyxl','yaml','numpy') if not importlib.util.find_spec(x)]; sys.exit('missing: '+', '.join(m) if m else 0)"
if errorlevel 1 (
  echo.
  echo Missing packages. Run setup.bat once, or:  %PY% -m pip install -r requirements.txt
  pause
  exit /b 1
)
schtasks /Create /F /SC ONLOGON /RL LIMITED /TN "%TASK%" /TR "cmd.exe /c start \"PID\" /min \"%~dp0run_lan_service.bat\""
if errorlevel 1 (
  echo.
  echo Could not register the task.  See the message above.
  pause
  exit /b 1
)
echo.
echo Registered: the P^&ID server starts on LAN port 8000 at every logon of THIS user (not at boot).
echo The PC must be logged on as this user for other PCs to reach the server - use
echo automatic logon + screen lock, and turn sleep off (config\user_manual.md, section "autostart").
echo Starting it now ...
schtasks /Run /TN "%TASK%" >nul
echo.
echo Check in a browser:  http://localhost:8000/
echo Check the task:      schtasks /Query /TN %TASK%
echo Other PCs also need the firewall opened once - open_firewall_8000.bat (administrator).
pause
