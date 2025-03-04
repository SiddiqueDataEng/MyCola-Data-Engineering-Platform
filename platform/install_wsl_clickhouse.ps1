# MyCola Platform - WSL2 + ClickHouse Installer
# Run as Administrator in PowerShell

# Must be run as admin
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")) {
    Write-Host "ERROR: Run this script as Administrator (right-click PowerShell > Run as Administrator)" -ForegroundColor Red
    exit 1
}

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "MyCola - WSL2 + ClickHouse Installer"    -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""
Write-Host "This will:" -ForegroundColor White
Write-Host "  1. Enable WSL2 (Windows Subsystem for Linux 2)"
Write-Host "  2. Install Ubuntu 22.04 LTS"
Write-Host "  3. After reboot: install ClickHouse inside Ubuntu"
Write-Host ""
Write-Host "Your machine WILL need to reboot once." -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "Proceed? (y/n)"
if ($confirm -ne "y") { Write-Host "Cancelled."; exit 0 }

Write-Host ""
Write-Host "[Step 1] Enabling WSL features..." -ForegroundColor Yellow
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

Write-Host ""
Write-Host "[Step 2] Setting WSL default version to 2..." -ForegroundColor Yellow
# Download and install WSL2 kernel update
$kernelUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
$kernelMsi = "$env:TEMP\wsl_update_x64.msi"
Write-Host "  Downloading WSL2 kernel update..."
Invoke-WebRequest -Uri $kernelUrl -OutFile $kernelMsi -UseBasicParsing
Start-Process msiexec.exe -ArgumentList "/i `"$kernelMsi`" /quiet" -Wait
Write-Host "  WSL2 kernel installed."

wsl --set-default-version 2

Write-Host ""
Write-Host "[Step 3] Installing Ubuntu 22.04..." -ForegroundColor Yellow
wsl --install -d Ubuntu-22.04 --no-launch

Write-Host ""
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "REBOOT REQUIRED"                          -ForegroundColor Yellow
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""
Write-Host "After rebooting:"
Write-Host "  1. Ubuntu will finish installing (set username/password)"
Write-Host "  2. Then run this command INSIDE Ubuntu:" -ForegroundColor White
Write-Host ""
Write-Host "     curl https://clickhouse.com/install.sh | sudo bash" -ForegroundColor Green
Write-Host "     sudo clickhouse start" -ForegroundColor Green
Write-Host "     clickhouse-client  # verify" -ForegroundColor Green
Write-Host ""
Write-Host "  3. From Windows PowerShell, run:" -ForegroundColor White
Write-Host "     pip install clickhouse-driver pandas pyarrow" -ForegroundColor Green
Write-Host "     python F:\siddi\clickstream_sales_analytics\platform\apply_schema.py" -ForegroundColor Green
Write-Host "     python F:\siddi\clickstream_sales_analytics\platform\load_data.py" -ForegroundColor Green
Write-Host ""

$reboot = Read-Host "Reboot now? (y/n)"
if ($reboot -eq "y") {
    Restart-Computer -Force
}
