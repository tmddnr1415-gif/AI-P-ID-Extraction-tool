@echo off
rem hotfix50 - keep the P&ID server up on the company network for the department
rem dashboard.  Started at logon by install_autostart_lan.bat (or by hand).
rem If the server stops it is started again after 10 seconds.  Close this
rem window to stop it for good (or run uninstall_autostart_lan.bat).
rem
rem Uses PID_Extract.exe when it sits next to this file, otherwise start.bat
rem (Python install).  Port 8000 - the address the dashboard has written down.
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PID_NO_HOLD=1
if not exist logs mkdir logs
title P^&ID 분석 서버 (사내망 · 포트 8000)
:loop
echo [%date% %time%] P^&ID 분석 서버를 켭니다 (사내망 · 포트 8000)>> logs\lan_service.log
if exist "PID_Extract.exe" (
  "PID_Extract.exe" --lan --no-browser 8000
) else (
  call start.bat --lan --no-reload 8000
)
echo [%date% %time%] 서버가 멈췄습니다 - 10초 뒤 다시 켭니다>> logs\lan_service.log
timeout /t 10 /nobreak >nul
goto loop
