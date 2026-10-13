@echo off
rem ============================================================
rem  Check why members cannot reach the dashboard server.
rem  Run on the SERVER PC (no admin rights needed).
rem  Uses python + netsh/ipconfig only (no PowerShell - it may be
rem  blocked by company policy). Result: network_check.txt
rem  Optional: check_network.bat 8081   (other port)
rem ============================================================
cd /d "%~dp0"
set "PORT=8080"
if not "%~1"=="" set "PORT=%~1"
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python not found in PATH.
  pause
  exit /b 1
)
python "%~dp0net_check.py" --port %PORT%
echo.
pause
