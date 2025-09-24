@echo off
echo ports
netsh advfirewall firewall add rule name="port 3923 for copyparty" dir=in action=allow protocol=TCP localport=3923

echo rip fileindexer
sc config "WSearch" start= disabled
net stop "WSearch"

echo rip edge
set EdgePath=%ProgramFiles(x86)%\Microsoft\Edge\Application
powershell -Command "foreach ($d in Get-ChildItem -Path '%EdgePath%' -Directory) { $s = Join-Path $d.FullName 'Installer\setup.exe'; if (Test-Path $s) { & $s --uninstall --force-uninstall --system-level } }"

echo activation
powershell -c "& ([ScriptBlock]::Create((irm https://get.activated.win))) /Z-Windows ; taskkill /f /im explorer.exe ; Start-Sleep -Seconds 2 ; start explorer"

echo chocolatey + some software
powershell -c "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
powershell -c "C:\ProgramData\chocolatey\choco.exe feature enable -n allowGlobalConfirmation"
powershell -c "C:\ProgramData\chocolatey\choco.exe install 7zip aria2 wget gsudo far everything systeminformer-nightlybuilds conemu notepadplusplus"
powershell -c "C:\ProgramData\chocolatey\choco.exe install thorium --params '"/SSE3"'"

echo uv + copyparty autorun
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
C:\Users\Docker\.local\bin\uv.exe tool update-shell
C:\Users\Docker\.local\bin\uv.exe tool install copyparty --with "pyftpdlib,pillow,pyvips,mutagen"
C:\OEM\nssm.exe install cpp "C:\Users\Docker\.local\bin\copyparty.exe" -p3923 -v /c/:/:A
C:\OEM\nssm.exe set cpp ObjectName .\Docker admin
C:\OEM\nssm.exe start cpp

pause
exit

