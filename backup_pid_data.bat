@echo off
rem hotfix132 - back up ALL screens' data (app\_data and the feedback folder voc\).
rem Which data folder: C:\Claude\PID\app\_data (the operations server) when it
rem exists, else this folder's app\_data.  --data FOLDER chooses another one.
rem The folder is printed first - check it before going on.
rem   backup_pid_data.bat                      -> PID_BACKUP_DIR, else DATA\backups
rem   backup_pid_data.bat D:\pid_backup        -> that folder (another drive is safer)
rem   backup_pid_data.bat D:\pid_backup --keep 14
rem   backup_pid_data.bat --list D:\pid_backup -> the backups there
rem   backup_pid_data.bat --restore D:\pid_backup\pid_backup_20261105_0930
rem                                            -> restore into the same data folder
rem                                               (stop the server first)
rem   backup_pid_data.bat --data D:\other\app\_data ...   -> another data folder
rem Run it from the development folder (PID_dev): an update brings only app\ and
rem config\ to the operations folder, so spike\backup_data.py may not be there.
rem The server keeps a daily copy of app.db by itself; this keeps everything else too.
rem Steps in config\user_manual.md, section "backup".  ASCII only and CRLF on purpose.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set "TOOL=%~dp0spike\backup_data.py"
set "DATA=%~dp0app\_data"
if exist "C:\Claude\PID\app\_data\*" set "DATA=C:\Claude\PID\app\_data"
if exist ".venv\Scripts\python.exe" (set PY=.venv\Scripts\python.exe) else (set PY=python)
%PY% -c "import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python 3.11 is not installed or not on PATH - see docs\offline_setup_windows.md
  echo   expected: .venv\Scripts\python.exe  ^(run setup.bat once^)
  pause
  exit /b 1
)
if not exist "%TOOL%" (
  echo.
  echo spike\backup_data.py is not in this folder.
  echo Run backup_pid_data.bat from the development folder ^(PID_dev^) instead.
  pause
  exit /b 1
)
echo Data folder (default): %DATA%
echo   ^(--data FOLDER on the command line chooses another one^)
echo.

if not "%~1"=="" goto given
if defined PID_BACKUP_DIR goto envdest
echo No destination given and PID_BACKUP_DIR is not set.
echo Backing up into the data folder's own backups folder - that is the same disk.
echo For a safer copy give another drive:  backup_pid_data.bat D:\pid_backup
echo.
%PY% "%TOOL%" --data "%DATA%"
goto done

:envdest
%PY% "%TOOL%" --data "%DATA%" "%PID_BACKUP_DIR%"
goto done

:given
%PY% "%TOOL%" --data "%DATA%" %*

:done
set RC=%errorlevel%
echo.
pause
exit /b %RC%
