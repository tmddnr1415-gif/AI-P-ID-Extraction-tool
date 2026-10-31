@echo off
rem ============================================================
rem  Remove the auto-start task and stop the watchdog + server
rem ============================================================
chcp 65001 >nul
schtasks /End /TN "DeptDashboardServer" >nul 2>nul
schtasks /Delete /F /TN "DeptDashboardServer"
rem stop pythonw processes running watchdog.py / server.py from this folder
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | Where-Object { $_.CommandLine -match 'watchdog\.py|server\.py' -and $_.CommandLine -match [regex]::Escape('%~dp0'.TrimEnd('\')) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('stopped PID ' + $_.ProcessId) }"
echo Auto-start removed.
pause
