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

setlocal enabledelayedexpansion
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set PY=.venv\Scripts\python.exe
) else (
  set PY=python
)

set CLEAN=
for %%a in (%*) do if "%%a"=="--clean" set CLEAN=--clean

echo [1/4] 의존성 확인
%PY% -c "import importlib.util,sys; m=[x for x in ('fastapi','uvicorn','multipart','pymupdf','openpyxl','yaml','numpy') if not importlib.util.find_spec(x)]; sys.exit('missing: '+', '.join(m) if m else 0)"
if errorlevel 1 (
  echo.
  echo 의존성이 없습니다:  %PY% -m pip install -r requirements.txt
  pause
  exit /b 1
)
%PY% -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)"
if errorlevel 1 (
  echo     PyInstaller 설치
  %PY% -m pip install pyinstaller
  if errorlevel 1 ( echo PyInstaller 설치 실패 & pause & exit /b 1 )
)

echo [2/4] 빌드 정보 기록  app\_build.json
%PY% -c "import json,datetime,sys;sys.path.insert(0,'.');from app.version import VERSION;json.dump({'version':VERSION,'built_at':datetime.date.today().isoformat()},open('app/_build.json','w'),indent=1)"
if errorlevel 1 ( echo 빌드 정보 기록 실패 & pause & exit /b 1 )
%PY% -c "import json;d=json.load(open('app/_build.json'));print('    v'+d['version'],d['built_at'])"

echo [3/4] 빠른 회귀 테스트
%PY% -m pytest -q -m "not slow and not ui"
if errorlevel 1 (
  echo.
  echo 테스트가 실패했습니다. 이 상태로는 exe 를 만들지 않습니다.
  pause
  exit /b 1
)

echo [4/4] PyInstaller
%PY% -m PyInstaller %CLEAN% --noconfirm pid_extract.spec
if errorlevel 1 ( echo 빌드 실패 & pause & exit /b 1 )

echo.
for %%f in (dist\PID_Extract.exe) do echo 완료:  %%~ff  (%%~zf bytes)
echo.
echo 이 exe 를 아무 폴더에나 두고 더블클릭하면 됩니다.
echo 분석 결과는 exe 옆의 pid_data 폴더에 남고, 그 PC 밖으로 나가지 않습니다.
pause
endlocal
