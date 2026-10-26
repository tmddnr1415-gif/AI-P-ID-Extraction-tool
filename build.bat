@echo off
rem Build the single-file exe.  Run this and nothing else - the same command
rem produces the same build, and it stamps the date it was made into the file
rem that the screen and the diagnostic export read back.
rem
rem   build.bat                 build with the bundled default profile
rem   build.bat --clean         throw away PyInstaller's cache first
rem
rem Output:  dist\PID_Extract.exe
rem
rem The client's drawings and workbooks are NOT packaged - see pid_extract.spec.
rem Nothing here reaches the network except pip, and only if PyInstaller is
rem missing.
rem ASCII only and CRLF on purpose (see run_lan_service.bat - cmd.exe misreads
rem batch files that hold UTF-8 text).

setlocal enabledelayedexpansion
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set PY=.venv\Scripts\python.exe
) else (
  set PY=python
)

set CLEAN=
for %%a in (%*) do if "%%a"=="--clean" set CLEAN=--clean

echo [1/4] checking packages
%PY% -c "import importlib.util,sys; m=[x for x in ('fastapi','uvicorn','multipart','pymupdf','openpyxl','yaml','numpy') if not importlib.util.find_spec(x)]; sys.exit('missing: '+', '.join(m) if m else 0)"
if errorlevel 1 (
  echo.
  echo Missing packages. Run:  %PY% -m pip install -r requirements.txt
  pause
  exit /b 1
)
%PY% -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)"
if errorlevel 1 (
  echo     installing PyInstaller
  %PY% -m pip install pyinstaller
  if errorlevel 1 ( echo PyInstaller install failed & pause & exit /b 1 )
)

echo [2/4] writing build info  app\_build.json
%PY% -c "import json,datetime,sys;sys.path.insert(0,'.');from app.version import VERSION;json.dump({'version':VERSION,'built_at':datetime.date.today().isoformat()},open('app/_build.json','w'),indent=1)"
if errorlevel 1 ( echo writing build info failed & pause & exit /b 1 )
%PY% -c "import json;d=json.load(open('app/_build.json'));print('    v'+d['version'],d['built_at'])"

echo [3/4] fast regression tests
%PY% -m pytest -q -m "not slow and not ui"
if errorlevel 1 (
  echo.
  echo Tests failed.  No exe is built in this state.
  pause
  exit /b 1
)

echo [4/4] PyInstaller
%PY% -m PyInstaller %CLEAN% --noconfirm pid_extract.spec
if errorlevel 1 ( echo build failed & pause & exit /b 1 )

echo.
for %%f in (dist\PID_Extract.exe) do echo done:  %%~ff  (%%~zf bytes)
echo.
echo Put this exe in any folder and double-click it.
echo Results stay in the pid_data folder next to the exe and never leave that PC.
pause
endlocal
