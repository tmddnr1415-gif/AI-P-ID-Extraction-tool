@echo off
rem hotfix52 - is the P&ID server on port 8000 answering?  Double-click it.
rem Shows which programs hold port 8000, whether /version and the first-screen
rem data answer, and what to do.  Writes the same text to logs\lan_check.txt.
rem It only looks; it stops nothing.  ASCII only and CRLF (see run_lan_service.bat).
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (set PY=.venv\Scripts\python.exe) else (set PY=python)
%PY% -m app.lan_check
echo.
pause
