@echo off
rem Valve (company PC): test in C:\Claude\PID_dev, back up, copy app\valve + app\static\valve to C:\Claude\PID, restart port 8000.
cd /d "%~dp0.."
set PYTHONUTF8=1
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" spike\valve_deploy_to_ops.py %*
pause
