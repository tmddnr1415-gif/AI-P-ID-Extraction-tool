@echo off
rem hotfix132 - restart the P&ID server on port 8000 (for example after an update).
rem Stops only the program that listens on port 8000; the service window
rem (run_lan_service.bat) brings it back with the new code in about 10 seconds.
rem It asks first if an analysis is running.  ASCII only and CRLF on purpose.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if exist ".venv\Scripts\python.exe" (set PY=.venv\Scripts\python.exe) else (set PY=python)
%PY% -c "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python 3.11 is not installed or not on PATH - see docs\offline_setup_windows.md
  echo   expected: .venv\Scripts\python.exe  ^(run setup.bat once^)
  pause
  exit /b 1
)

%PY% spike\restart_pid_server.py 8000
echo.
pause
