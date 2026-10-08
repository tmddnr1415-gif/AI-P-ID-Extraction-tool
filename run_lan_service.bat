@echo off
rem hotfix50/51 - keep the P&ID server up on the company network (port 8000)
rem for the department dashboard.  Started at logon by install_autostart_lan.bat
rem or by double-click.  If the server stops it is started again after 10 s.
rem Close this window to stop it (uninstall_autostart_lan.bat removes the logon entry).
rem
rem ASCII only and CRLF line ends on purpose: cmd.exe misreads batch files that
rem hold UTF-8 text.  hotfix50 called start.bat after chcp 65001 and cmd ran
rem fragments of its comments as commands ('twork', 'loopback', ...), so the
rem server never came up.  This file now starts the server itself.
setlocal
cd /d "%~dp0"
set PID_LAN=1
set PID_NO_HOLD=1
if not exist logs mkdir logs
title PID server - LAN port 8000
if exist ".venv\Scripts\python.exe" (set PY=.venv\Scripts\python.exe) else (set PY=python)

:loop
echo [%date% %time%] starting PID server, LAN port 8000>> logs\lan_service.log
if exist "PID_Extract.exe" goto run_exe
echo PID server - LAN mode, port 8000.  Other PCs connect with:
%PY% -c "from app import lan; print(chr(10).join('   ' + u for u in lan.urls(8000)))"
%PY% -m uvicorn app.main:app --host 0.0.0.0 --port 8000
goto stopped

:run_exe
"PID_Extract.exe" --lan --no-browser 8000

:stopped
echo [%date% %time%] server stopped - restarting in 10 seconds>> logs\lan_service.log
echo Server stopped.  Restarting in 10 seconds (close this window to stop for good).
timeout /t 10 /nobreak >nul
goto loop
