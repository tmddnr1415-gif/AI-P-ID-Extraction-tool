@echo off
rem ============================================================
rem  Check why members cannot reach the dashboard server.
rem  Run on the SERVER PC (no admin rights needed). Take a photo
rem  of the window or save network_check.txt and send it.
rem ============================================================
cd /d "%~dp0"
set "PORT=8080"
if not "%~1"=="" set "PORT=%~1"
set "OUT=%~dp0network_check.txt"
echo Dashboard network check  %DATE% %TIME%  PC=%COMPUTERNAME%  port=%PORT% > "%OUT%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=%PORT%; '--- 1. Network type (Public = firewall often blocks members) ---'; Get-NetConnectionProfile | Format-Table InterfaceAlias,Name,NetworkCategory -AutoSize | Out-String; '--- 2. IPv4 addresses (members use http://IP:' + $p + '/) ---'; Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | Format-Table InterfaceAlias,IPAddress,PrefixLength -AutoSize | Out-String; '--- 3. Is the server listening? ---'; try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 ('http://localhost:' + $p + '/api/info'); 'OK: server answers on localhost:' + $p } catch { 'NO: server not running on port ' + $p + ' (start_server.bat)' }; Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue | Format-Table LocalAddress,LocalPort,OwningProcess -AutoSize | Out-String; '--- 4. Firewall rules for this port / python (Block beats Allow) ---'; Get-NetFirewallPortFilter -Protocol TCP | Where-Object { $_.LocalPort -eq [string]$p } | Get-NetFirewallRule | Where-Object Direction -eq 'Inbound' | Format-Table DisplayName,Enabled,Action,Profile -AutoSize | Out-String; Get-NetFirewallApplicationFilter | Where-Object { $_.Program -match 'python(w)?\.exe$' } | Get-NetFirewallRule | Where-Object Direction -eq 'Inbound' | Format-Table DisplayName,Enabled,Action,Profile -AutoSize | Out-String; '--- 5. Firewall on/off per network type ---'; Get-NetFirewallProfile | Format-Table Name,Enabled,DefaultInboundAction -AutoSize | Out-String" >> "%OUT%" 2>&1
type "%OUT%"
echo.
echo Saved: %OUT%
echo  - Network type "Public" or a python "Block" rule  : run allow_firewall.bat as administrator
echo  - Server answers here but members still fail       : company Wi-Fi may be separated from wired LAN - ask IT
pause
