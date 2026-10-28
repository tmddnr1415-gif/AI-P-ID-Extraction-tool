@echo off
rem hotfix50/51/52 - keep the P&ID server up on the company network (port 8000)
rem for the department dashboard.  Started at logon by install_autostart_lan.bat
rem or by double-click.  If the server stops it is started again after 10 s.
rem Close this window to stop it (uninstall_autostart_lan.bat removes the logon entry).
rem
rem ASCII only and CRLF line ends on purpose: cmd.exe misreads batch files that
rem hold UTF-8 text.  hotfix50 called start.bat after chcp 65001 and cmd ran
rem fragments of its comments as commands ('twork', 'loopback', ...), so the
rem server never came up.  This file starts the server itself.
rem
rem hotfix52: the server writes to logs\server.log, never to this window.  A
rem console window that is clicked goes into "Select" mode and every program
rem writing to it stops - uvicorn writes one line per request, so the whole
rem server froze on the first page load (browser kept loading forever).
rem Before starting, it checks that port 8000 is free (app\lan_check.py):
rem   0 free -> start   3 this server already answers -> wait
rem   4 taken but silent -> say so and wait (check_pid_server.bat tells more)
rem   anything else (python itself failed) -> start anyway; the error lands in the log
rem
rem hotfix54: PYTHONUTF8=1.  Python writes a redirected log in the Windows code
rem page (cp949) and cp949 has no em dash; the start-up audit line holds one when
rem the database has hand-added rows, so the server died while starting and this
rem window restarted it every 10 s.  When it stops, the end of the log is shown.
setlocal
cd /d "%~dp0"
set PID_LAN=1
set PID_NO_HOLD=1
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist logs mkdir logs
title PID server - LAN port 8000
if exist ".venv\Scripts\python.exe" (set PY=.venv\Scripts\python.exe) else (set PY=python)

:loop
if exist "PID_Extract.exe" goto run_exe
%PY% -m app.lan_check --preflight
if errorlevel 4 goto busy
if errorlevel 3 goto already
echo [%date% %time%] starting PID server, LAN port 8000>> logs\lan_service.log
echo.
echo PID server - LAN mode, port 8000.  Other PCs connect with:
%PY% -c "from app import lan; print(chr(10).join('   ' + u for u in lan.urls(8000)))"
echo.
echo Server messages go to logs\server.log (not to this window).
echo Keep this window open; minimise it.  Problems: run check_pid_server.bat
%PY% -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> logs\server.log 2>&1
goto stopped

:run_exe
echo [%date% %time%] starting PID_Extract.exe, LAN port 8000>> logs\lan_service.log
echo PID server (exe) - LAN mode, port 8000.  Messages go to logs\server.log
"PID_Extract.exe" --lan --no-browser 8000 >> logs\server.log 2>&1
goto stopped

:already
echo [%date% %time%] port 8000 already served by a P^&ID server - waiting>> logs\lan_service.log
echo A P^&ID server is already answering on port 8000 (another window).  Checking again in 60 seconds.
timeout /t 60 /nobreak >nul
goto loop

:busy
echo [%date% %time%] port 8000 taken but not answering - waiting>> logs\lan_service.log
echo.
echo Port 8000 is held by a program that does not answer.
echo If another P^&ID server window exists, click it and press Esc, or close it.
echo Run check_pid_server.bat to see which program holds the port.
echo Checking again in 30 seconds.
timeout /t 30 /nobreak >nul
goto loop

:stopped
echo [%date% %time%] server stopped - restarting in 10 seconds>> logs\lan_service.log
echo.
echo Server stopped.  End of logs\server.log:
if exist "PID_Extract.exe" (echo   see logs\server.log) else (%PY% -m app.lan_check --tail)
echo Restarting in 10 seconds.
timeout /t 10 /nobreak >nul
goto loop
