@echo off
rem Valve (company PC): put back the last backup of app\valve + app\static\valve in C:\Claude\PID and restart port 8000.
cd /d "%~dp0.."
set PYTHONUTF8=1
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" spike\valve_deploy_to_ops.py --rollback %*
pause
