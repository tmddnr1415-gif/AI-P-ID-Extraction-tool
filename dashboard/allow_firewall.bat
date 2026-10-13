@echo off
rem ============================================================
rem  Allow members to reach this dashboard server on Wi-Fi.
rem  Right-click this file -> "Run as administrator".
rem  1) adds an inbound allow rule for TCP 8080 on every network
rem     type (Domain / Private / Public - Wi-Fi is often Public)
rem  2) turns off inbound BLOCK rules for python (block beats allow)
rem  Uses python + netsh only (no PowerShell).
rem  No admin rights? Ask IT: "allow inbound TCP 8080 to this PC
rem  on every network type (company Wi-Fi included)".
rem ============================================================
cd /d "%~dp0"
set "PORT=8080"
if not "%~1"=="" set "PORT=%~1"
net session >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Not running as administrator.
  echo         Right-click allow_firewall.bat and choose "Run as administrator".
  echo         If you cannot, ask IT to allow inbound TCP %PORT% to this PC.
  pause
  exit /b 1
)
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python not found in PATH.
  pause
  exit /b 1
)
python "%~dp0net_check.py" --port %PORT% --fix
echo.
pause
