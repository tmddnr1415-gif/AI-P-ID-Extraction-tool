@echo off
rem hotfix50/51 - let other PCs on the company network reach port 8000.
rem Run as administrator.
rem
rem   open_firewall_8000.bat                 local subnet + private ranges
rem   open_firewall_8000.bat 65.3.0.0/16     ... plus this range (the dashboard's /16)
rem
rem The server itself also refuses anything outside loopback / private / this
rem PC's /16 / PID_ALLOW (app/lan.py) - this rule is the outer fence.
rem ASCII only and CRLF on purpose (see run_lan_service.bat).
net session >nul 2>&1
if errorlevel 1 (
  echo Administrator rights are needed.  Right-click this file - Run as administrator,
  echo or run it from an administrator terminal.
  pause
  exit /b 1
)
set REMOTE=localsubnet,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
if not "%~1"=="" set REMOTE=%REMOTE%,%~1
netsh advfirewall firewall delete rule name="PID Extract 8000" >nul 2>&1
netsh advfirewall firewall add rule name="PID Extract 8000" dir=in action=allow protocol=TCP localport=8000 remoteip=%REMOTE%
if errorlevel 1 (
  echo Could not create the firewall rule.
  pause
  exit /b 1
)
echo.
echo Opened: TCP 8000 for %REMOTE%
pause
