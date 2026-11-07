@echo off
rem ============================================================
rem  Allow members to reach this dashboard server on Wi-Fi.
rem  Use when members can connect while this PC is on wired LAN
rem  but NOT when it is on company Wi-Fi.
rem  Right-click this file -> "Run as administrator".
rem  It does 2 things (Windows Firewall, this PC only):
rem   1) allows inbound TCP 8080 (dashboard) and 8100 (virtual plaza)
rem      on every network type
rem      (Domain / Private / Public - Wi-Fi is often "Public")
rem   2) turns off inbound BLOCK rules for python.exe / pythonw.exe
rem      (made when "Public networks" was unchecked in the
rem       first "Allow access?" pop-up; block beats allow)
rem  No admin rights? Ask IT: "allow inbound TCP 8080 to this PC
rem  on the company Wi-Fi network".
rem ============================================================
cd /d "%~dp0"
set "PORT=8080"
if not "%~1"=="" set "PORT=%~1"
net session >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Not running as administrator.
  echo         Right-click allow_firewall.bat and choose "Run as administrator".
  echo         If you cannot, ask IT to allow inbound TCP %PORT% to this PC on Wi-Fi.
  pause
  exit /b 1
)
echo [1/3] Allow inbound TCP %PORT% on all network types ...
netsh advfirewall firewall delete rule name="DeptDashboard %PORT%" >nul 2>&1
netsh advfirewall firewall add rule name="DeptDashboard %PORT%" dir=in action=allow protocol=TCP localport=%PORT% profile=any
netsh advfirewall firewall delete rule name="DeptDashboard Plaza 8100" >nul 2>&1
netsh advfirewall firewall add rule name="DeptDashboard Plaza 8100" dir=in action=allow protocol=TCP localport=8100 profile=any
if errorlevel 1 (
  echo [ERROR] Could not add the firewall rule. Company policy may manage the firewall - ask IT.
  pause
  exit /b 1
)
echo.
echo [2/3] Inbound BLOCK rules for python (turned off if found) ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$r = Get-NetFirewallApplicationFilter | Where-Object { $_.Program -match 'python(w)?\.exe$' } | Get-NetFirewallRule | Where-Object { $_.Direction -eq 'Inbound' -and $_.Action -eq 'Block' -and $_.Enabled -eq 'True' }; if ($r) { $r | ForEach-Object { Write-Host ('  disabled: ' + $_.DisplayName + ' [' + $_.Profile + ']'); $_ | Disable-NetFirewallRule } } else { Write-Host '  none' }"
echo.
echo [3/3] Network type and addresses of this PC
powershell -NoProfile -Command "Get-NetConnectionProfile | Format-Table InterfaceAlias,Name,NetworkCategory -AutoSize; Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | Format-Table InterfaceAlias,IPAddress -AutoSize"
echo Members can open:  http://%COMPUTERNAME%:%PORT%/   or  http://(IPAddress above):%PORT%/
echo If members still cannot connect on Wi-Fi, the company network may block
echo Wi-Fi to/from wired PCs. Ask IT, or keep the server PC on wired LAN.
pause
