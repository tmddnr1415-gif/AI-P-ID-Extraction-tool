@echo off
rem One command to bring the app up on Windows - the same thing run.sh does.
rem
rem   start.bat            start on 8000, reload on code change
rem   start.bat 9000       another port
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
rem Analyses already in app\_data\app.db are kept, so an earlier result opens
rem immediately. Delete the app\_data folder to start clean.

setlocal enabledelayedexpansion
cd /d "%~dp0"

set PORT=8000
set RELOAD=--reload
set HOST=127.0.0.1
for %%a in (%*) do (
  if "%%a"=="--lan" (set HOST=0.0.0.0& set PID_LAN=1) else (
  if "%%a"=="--no-reload" (set RELOAD=) else (
  if "%%a"=="--verify" (set PID_VERIFY_EXCEL=data\CZE_Field_Instrument.xlsx) else (
  set PORT=%%a)))
)

rem Use the project's virtual environment when there is one, so a plain
rem double-click works without activating anything by hand.
if exist ".venv\Scripts\python.exe" (
  set PY=.venv\Scripts\python.exe
) else (
  set PY=python
)

%PY% -c "import importlib.util,sys; m=[x for x in ('fastapi','uvicorn','multipart','pymupdf','openpyxl','yaml','numpy') if not importlib.util.find_spec(x)]; sys.exit('missing: '+', '.join(m) if m else 0)"
if errorlevel 1 (
  echo.
  echo Missing packages. Run:  %PY% -m pip install -r requirements.txt
  exit /b 1
)

if not exist logs mkdir logs
if defined PID_VERIFY_EXCEL echo Verify mode: attributing drawings against %PID_VERIFY_EXCEL%
echo -^> http://127.0.0.1:%PORT%
if defined PID_LAN (
  echo LAN mode: other PCs connect with these addresses ^(private ranges and this PC's /16 only^)
  %PY% -c "from app import lan; print('\n'.join('   -> ' + u for u in lan.urls(%PORT%)))"
)
echo -^> log: logs\server.log
echo.

rem cmd.exe has no `tee`, so the log is written by uvicorn's own stream and
rem echoed back as it goes.
%PY% -m uvicorn app.main:app --host %HOST% --port %PORT% %RELOAD% 2>&1 | %PY% -c "import sys;f=open('logs/server.log','a',encoding='utf-8',buffering=1);[ (sys.stdout.write(l), f.write(l)) for l in sys.stdin ]"
endlocal
