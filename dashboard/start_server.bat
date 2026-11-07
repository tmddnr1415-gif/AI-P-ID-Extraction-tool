@echo off
rem ============================================================
rem  Dept Weekly Dashboard server  (double-click to start)
rem  - Uses this folder as the operating folder (data, history, archive, trash)
rem  - Admin URL on this PC : http://localhost:8080/  (opens automatically)
rem  - Members              : http://<this PC IP>:8080/
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"
title Dept Weekly Dashboard Server (port 8080)
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python not found in PATH.
  pause
  exit /b 1
)
rem --open : browser opens http://localhost:8080/ after the server starts
rem          (if the port is busy, the server prints a message and exits without opening)
python server.py --root "%~dp0." --port 8080 --open
echo.
echo Server stopped.
pause
