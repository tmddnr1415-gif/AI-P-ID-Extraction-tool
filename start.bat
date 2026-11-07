@echo off
rem One command to bring the app up on Windows - the same thing run.sh does.
rem
rem   start.bat            start on 8000 (no file watching)
rem   start.bat 9000       another port
rem   start.bat --reload   restart on code change (development only)
rem   start.bat --lan      hotfix50: open on the company network (0.0.0.0) so the
rem                        department dashboard can show it in an iframe.  Only
rem                        loopback / private / this PC's /16 / PID_ALLOW get in.
rem   start.bat --verify   verification mode: attribute drawings against
rem                        data\CZE_Field_Instrument.xlsx (a *finished* list).
rem                        Off by default; normal use has no such file.
rem
rem hotfix51: this file is ASCII only with CRLF line ends on purpose.  cmd.exe
rem misreads a batch file holding UTF-8 text (after chcp 65001 it runs pieces of
rem comments as commands), which is how hotfix50's LAN service never started.
rem
rem app\_data holds ALL screens' data (analyses, uploads, LOGIC, panel, DCS,
rem books ...).  Back it up (backup_pid_data.bat) before deleting anything there.
rem Do not move the data folder - keep backups on another drive instead.

setlocal enabledelayedexpansion
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set PORT=8000
set RELOAD=
set HOST=127.0.0.1
for %%a in (%*) do (
  if "%%a"=="--lan" (set HOST=0.0.0.0& set PID_LAN=1) else (
  if "%%a"=="--reload" (set RELOAD=--reload) else (
  if "%%a"=="--no-reload" (set RELOAD=) else (
  if "%%a"=="--verify" (set PID_VERIFY_EXCEL=data\CZE_Field_Instrument.xlsx) else (
  set PORT=%%a))))
)

rem Use the project's virtual environment when there is one, so a plain
rem double-click works without activating anything by hand.
if exist ".venv\Scripts\python.exe" (
  set PY=.venv\Scripts\python.exe
) else (
  set PY=python
)

%PY% -c "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python 3.11 is not installed or not on PATH - see docs\offline_setup_windows.md
  echo   expected: .venv\Scripts\python.exe  ^(run setup.bat once^)
  exit /b 1
)
%PY% -c "import importlib.util,sys; m=[x for x in ('fastapi','uvicorn','multipart','pymupdf','openpyxl','yaml','numpy') if not importlib.util.find_spec(x)]; sys.exit('missing: '+', '.join(m) if m else 0)"
if errorlevel 1 (
  echo.
  echo Missing packages. Run setup.bat once, or:  %PY% -m pip install -r requirements.txt
  exit /b 1
)

if not exist logs mkdir logs
if defined PID_DATA_DIR echo data folder: %PID_DATA_DIR%
if defined PID_VERIFY_EXCEL echo Verify mode: attributing drawings against %PID_VERIFY_EXCEL%

rem Already running?  preflight: 0 free, 3 this server answers, 4 taken by something else.
%PY% -c "import sys;from app import lan_check;sys.exit(lan_check.preflight(%PORT%))"
if errorlevel 4 (
  echo Port %PORT% is held by another program - run check_pid_server.bat to see which.
  exit /b 4
)
if errorlevel 3 (
  echo Already running at http://127.0.0.1:%PORT% - opening the browser.
  start http://127.0.0.1:%PORT%
  exit /b 0
)

echo -^> http://127.0.0.1:%PORT%
if defined PID_LAN (
  echo LAN mode: other PCs connect with these addresses ^(private ranges and this PC's /16 only^)
  %PY% -c "from app import lan; print('\n'.join('   -> ' + u for u in lan.urls(%PORT%)))"
)
echo -^> log: logs\server.log
echo.

rem cmd.exe has no `tee`, so the log is written by uvicorn's own stream and
rem echoed back as it goes.  Access log (holds user names) and server header are off.
%PY% -m uvicorn app.main:app --host %HOST% --port %PORT% %RELOAD% --no-access-log --no-server-header 2>&1 | %PY% -c "import sys;f=open('logs/server.log','a',encoding='utf-8',buffering=1);[ (sys.stdout.write(l), f.write(l)) for l in sys.stdin ]"
endlocal
