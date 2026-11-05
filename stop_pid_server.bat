@echo off
rem hotfix132 - stop the P&ID server (it does not start it again).
rem   stop_pid_server.bat          -> the server on port 8000 (the operations server)
rem   stop_pid_server.bat 9000     -> the server on another port
rem It finds the server by its port, so run it from the development folder
rem (PID_dev): it uses PID_dev's own spike\restart_pid_server.py, which knows
rem --stop.  The operations folder only gets app\ and config\ in an update, so
rem an older copy there may not know --stop (it would restart instead).
rem If the service window (run_lan_service.bat) is open, close it too, or it
rem starts the server again in 10 seconds.  Start again: run_lan_service.bat.
rem ASCII only and CRLF on purpose.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set "TOOL=%~dp0spike\restart_pid_server.py"
set PORT=8000
if not "%~1"=="" set PORT=%~1
if exist ".venv\Scripts\python.exe" (set PY=.venv\Scripts\python.exe) else (set PY=python)
%PY% -c "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python 3.11 is not installed or not on PATH - see docs\offline_setup_windows.md
  echo   expected: .venv\Scripts\python.exe  ^(run setup.bat once^)
  pause
  exit /b 1
)
findstr /c:"--stop" "%TOOL%" >nul 2>&1
if errorlevel 1 (
  echo.
  echo This folder's spike\restart_pid_server.py is missing or too old to stop the server.
  echo Run stop_pid_server.bat from the development folder ^(PID_dev^) instead -
  echo it stops the server on port %PORT% whichever folder that server runs from.
  pause
  exit /b 1
)

echo Stopping the server on port %PORT% ...
%PY% "%TOOL%" %PORT% --stop
echo.
echo If the service window (run_lan_service.bat) is open, close it too,
echo or the server restarts in 10 s.
pause
