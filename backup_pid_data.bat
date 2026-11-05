@echo off
rem hotfix132 - back up ALL screens' data (app\_data and the feedback folder voc\).
rem   backup_pid_data.bat                      -> PID_BACKUP_DIR, else app\_data\backups
rem   backup_pid_data.bat D:\pid_backup        -> that folder (another drive is safer)
rem   backup_pid_data.bat D:\pid_backup --keep 14
rem   backup_pid_data.bat --list               -> the backups there
rem   backup_pid_data.bat --restore D:\pid_backup\pid_backup_20261105_0930
rem                                            -> restore (stop the server first)
rem The server keeps a daily copy of app.db by itself; this keeps everything else too.
rem Steps in docs\user_manual.md, section "backup".  ASCII only and CRLF on purpose.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if exist ".venv\Scripts\python.exe" (set PY=.venv\Scripts\python.exe) else (set PY=python)
%PY% -c "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python 3.11 is not installed or not on PATH - see docs\offline_setup_windows.md
  echo   expected: .venv\Scripts\python.exe  ^(run setup.bat once^)
  pause
  exit /b 1
)

if not "%~1"=="" goto given
if defined PID_BACKUP_DIR goto envdest
echo No destination given and PID_BACKUP_DIR is not set.
echo Backing up next to the data (app\_data\backups) - that is the same disk.
echo For a safer copy give another drive:  backup_pid_data.bat D:\pid_backup
echo.
%PY% spike\backup_data.py
goto done

:envdest
%PY% spike\backup_data.py "%PID_BACKUP_DIR%"
goto done

:given
%PY% spike\backup_data.py %*

:done
set RC=%errorlevel%
echo.
pause
exit /b %RC%
