@echo off
rem hotfix50/51 - remove the logon entry made by install_autostart_lan.bat.
rem It does NOT kill python processes: the department dashboard server runs on
rem python too.  Close the minimised "PID server - LAN port 8000" window instead.
rem ASCII only and CRLF on purpose (see run_lan_service.bat).
schtasks /Delete /F /TN "PID_Extract_LAN"
echo.
echo Logon entry removed.  To stop the running server, close the window
echo "PID server - LAN port 8000" on the taskbar.
echo (python is not killed here - the dashboard server is python too.)
pause
