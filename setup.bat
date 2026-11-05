@echo off
rem hotfix132 - first-time setup on a Windows PC.  Double-click once.
rem   1. finds Python 3.11 (the wheels are cp311)
rem   2. makes .venv (the project's own Python folder)
rem   3. installs the packages: offline from wheels\ when that folder is there
rem      (requirements-win.txt, and requirements-win-dxf.txt from wheels_r55\),
rem      otherwise from the internet (requirements.txt)
rem   4. makes logs\ and runs the server check (check_pid_server.bat does the same)
rem Then start the server with run_lan_service.bat (or start.bat on this PC only).
rem Background: docs\offline_setup_windows.md.  ASCII only and CRLF on purpose.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if exist ".venv\Scripts\python.exe" goto have_venv
set BASE=
py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 set BASE=py -3.11
if not defined BASE set BASE=python
%BASE% -c "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python 3.11 is required ^(the wheels are cp311^) - see docs\offline_setup_windows.md
  echo Install Python 3.11 for this user, tick "Add python.exe to PATH", then run setup.bat again.
  pause
  exit /b 1
)
echo [1/3] making .venv with %BASE%
%BASE% -m venv .venv
if errorlevel 1 ( echo making .venv failed & pause & exit /b 1 )

:have_venv
set PY=.venv\Scripts\python.exe
%PY% -c "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo .venv is not Python 3.11 - rename the .venv folder and run setup.bat again.
  pause
  exit /b 1
)

echo [2/3] installing packages
if exist "wheels\" (
  %PY% -m pip install --no-index --find-links wheels -r requirements-win.txt
) else (
  %PY% -m pip install -r requirements.txt
)
if errorlevel 1 (
  echo.
  echo Installing packages failed - see the lines above and docs\offline_setup_windows.md
  pause
  exit /b 1
)
if exist "wheels_r55\" %PY% -m pip install --no-index --find-links wheels_r55 -r requirements-win-dxf.txt

echo [3/3] checking
if not exist logs mkdir logs
%PY% -m app.lan_check
echo.
echo Setup done.  Start the server:  run_lan_service.bat  (company network)
echo                             or:  start.bat            (this PC only)
echo Automatic start at logon:        install_autostart_lan.bat
echo Manual:                          docs\user_manual.md  (or the ? button on any screen)
pause
