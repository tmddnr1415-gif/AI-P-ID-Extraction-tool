@echo off
rem One command to bring the app up on Windows - the same thing run.sh does.
rem
rem   start.bat            start on 8000, reload on code change
rem   start.bat 9000       another port
rem   start.bat --verify   verification mode: attribute drawings against
rem                        data\CZE_Field_Instrument.xlsx (a *finished* list).
rem                        Off by default; normal use has no such file.
rem
rem Analyses already in app\_data\app.db are kept, so an earlier result opens
rem immediately. Delete the app\_data folder to start clean.

setlocal enabledelayedexpansion
cd /d "%~dp0"

set PORT=8000
set RELOAD=--reload
for %%a in (%*) do (
  if "%%a"=="--no-reload" (set RELOAD=) else (
  if "%%a"=="--verify" (set PID_VERIFY_EXCEL=data\CZE_Field_Instrument.xlsx) else (
  set PORT=%%a))
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
  echo 의존성이 없습니다:  %PY% -m pip install -r requirements.txt
  exit /b 1
)

if not exist logs mkdir logs
if defined PID_VERIFY_EXCEL echo 검증 모드: %PID_VERIFY_EXCEL% 로 귀속을 판정합니다.
echo -^> http://127.0.0.1:%PORT%
echo -^> 로그: logs\server.log
echo.

rem cmd.exe has no `tee`, so the log is written by uvicorn's own stream and
rem echoed back as it goes.
%PY% -m uvicorn app.main:app --host 127.0.0.1 --port %PORT% %RELOAD% 2>&1 | %PY% -c "import sys;f=open('logs/server.log','a',encoding='utf-8',buffering=1);[ (sys.stdout.write(l), f.write(l)) for l in sys.stdin ]"
endlocal
