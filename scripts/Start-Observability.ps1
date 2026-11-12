# RockPro observability in one command: Phoenix dashboard + automatic export.
#
#   .\scripts\Start-Observability.ps1                  start both in the background (no windows), print the URL
#   .\scripts\Start-Observability.ps1 -Status          show what is running and the last export lines
#   .\scripts\Start-Observability.ps1 -Stop            stop what this script started (for your Windows user)
#   .\scripts\Start-Observability.ps1 -EnableAtLogon   start it automatically when you log in to Windows
#   .\scripts\Start-Observability.ps1 -DisableAtLogon  undo -EnableAtLogon
#
# Phoenix listens only on 127.0.0.1. On a shared (RDP) computer there is one
# Phoenix for everybody; each Windows user runs their own exporter for their
# own RockPro folder. Logs: artifacts\phoenix\logs. Guide: docs\PHOENIX_DASHBOARD.md
param(
    [switch]$Status,
    [switch]$Stop,
    [switch]$EnableAtLogon,
    [switch]$DisableAtLogon,
    [int]$Port = 6006,
    [string]$Database = '',
    [double]$Every = 30,
    [string]$StartupFolder = [Environment]::GetFolderPath('Startup')
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$phoenixPython = Join-Path $root 'tools\phoenix\.venv\Scripts\python.exe'
$exporter = Join-Path $root 'scripts\export_to_phoenix.py'
$logs = Join-Path $root 'artifacts\phoenix\logs'
$shortcut = Join-Path $StartupFolder 'RockPro observability.lnk'
if (-not $Database) {
    $Database = if ($env:ROCKPRO_STUDIO_DATABASE) { $env:ROCKPRO_STUDIO_DATABASE } else { Join-Path $root 'artifacts\studio.sqlite' }
}
$url = "http://127.0.0.1:$Port"

function Get-PhoenixListener {
    @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Get-OwnExporter {
    # The exporter of *this* RockPro folder, for the current Windows user.
    $me = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and $_.CommandLine -like "*export_to_phoenix.py*--watch*" -and $_.CommandLine -like "*$exporter*" -and
        ((Invoke-CimMethod -InputObject $_ -MethodName GetOwnerSid -ErrorAction SilentlyContinue).Sid -eq $me)
    })
}

function Test-PhoenixUp {
    try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 -Uri "$url/healthz").StatusCode -eq 200 } catch { $false }
}

function Show-Tail($name) {
    $path = Join-Path $logs $name
    if ((Test-Path -LiteralPath $path) -and (Get-Item -LiteralPath $path).Length -gt 0) {
        Write-Output "--- last lines of $path"
        Get-Content -LiteralPath $path -Tail 8 -Encoding UTF8
    }
}

if ($EnableAtLogon) {
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($shortcut)
    $link.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $link.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Port $Port -Every $Every -Database `"$Database`""
    $link.WorkingDirectory = $root
    $link.WindowStyle = 7   # minimized; the script itself starts everything hidden
    $link.Description = 'Start the RockPro Phoenix dashboard and exporter'
    $link.Save()
    Write-Output "Added to your Windows startup: $shortcut"
    Write-Output 'From your next login, Phoenix and the exporter start automatically. Undo with -DisableAtLogon.'
    return
}
if ($DisableAtLogon) {
    if (Test-Path -LiteralPath $shortcut) { Remove-Item -LiteralPath $shortcut; Write-Output "Removed $shortcut" }
    else { Write-Output 'Not enabled at logon; nothing to remove.' }
    return
}

if ($Stop) {
    $own = Get-OwnExporter   # venv launcher + the Python it starts
    foreach ($p in $own) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    if ($own) { Write-Output "Stopped exporter (process $($own[0].ProcessId))." } else { Write-Output 'Exporter was not running.' }
    $pidFile = Join-Path $logs 'phoenix.pid'
    if (Test-Path -LiteralPath $pidFile) {
        $id = [int](Get-Content -LiteralPath $pidFile -Raw)
        # Stop Phoenix only if this script started it as you; on a shared computer
        # someone else may be using it.
        $owned = Get-CimInstance Win32_Process -Filter "ProcessId = $id" -ErrorAction SilentlyContinue
        if ($owned) {
            # The whole tree: PowerShell -> venv launcher -> Python running Phoenix.
            & taskkill.exe /PID $id /T /F | Out-Null
            Write-Output "Stopped Phoenix (process $id and its children)."
        }
        Remove-Item -LiteralPath $pidFile
    }
    if (Get-PhoenixListener) { Write-Output "Phoenix on port $Port is still running; it was started by someone else or another way." }
    return
}

if ($Status) {
    if (Test-PhoenixUp) { Write-Output "Phoenix:  running at $url" } else { Write-Output "Phoenix:  NOT running (start: .\scripts\Start-Observability.ps1)" }
    $own = Get-OwnExporter
    if ($own) { Write-Output "Exporter: running (process $($own[0].ProcessId)), every $Every s, database $Database" }
    else { Write-Output 'Exporter: NOT running for your user and this folder' }
    if (Test-Path -LiteralPath $shortcut) { Write-Output 'At logon: enabled' } else { Write-Output 'At logon: not enabled (-EnableAtLogon)' }
    Show-Tail 'exporter.log'
    Show-Tail 'exporter.err.log'
    return
}

# --- start ---
New-Item -ItemType Directory -Force $logs | Out-Null
if (-not (Test-Path -LiteralPath $phoenixPython)) {
    Write-Output 'Phoenix is not installed yet; installing it once (needs internet)...'
    & (Join-Path $PSScriptRoot 'Start-Phoenix.ps1') -InstallOnly
}

if (Get-PhoenixListener) {
    Write-Output "Phoenix:  already running at $url"
} else {
    $p = Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') `
        -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PSScriptRoot 'Start-Phoenix.ps1'), '-Port', $Port) `
        -WorkingDirectory $root -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logs 'phoenix.log') -RedirectStandardError (Join-Path $logs 'phoenix.err.log')
    Set-Content -LiteralPath (Join-Path $logs 'phoenix.pid') -Value $p.Id -Encoding ascii
    Write-Output "Phoenix:  starting (process $($p.Id)) ..."
    $deadline = (Get-Date).AddSeconds(90)
    while (-not (Test-PhoenixUp)) {
        if ($p.HasExited) { Show-Tail 'phoenix.log'; Show-Tail 'phoenix.err.log'; throw 'Phoenix stopped while starting; see the log lines above.' }
        if ((Get-Date) -gt $deadline) { Show-Tail 'phoenix.err.log'; throw "Phoenix did not answer at $url within 90 s." }
        Start-Sleep -Seconds 2
    }
    Write-Output "Phoenix:  running at $url"
}

$own = Get-OwnExporter
if ($own) {
    Write-Output "Exporter: already running (process $($own[0].ProcessId))"
} else {
    $e = Start-Process -FilePath $phoenixPython `
        -ArgumentList @('-X', 'utf8', '-u', "`"$exporter`"", '--watch', $Every, '--database', "`"$Database`"", '--endpoint', "$url/v1/traces") `
        -WorkingDirectory $root -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logs 'exporter.log') -RedirectStandardError (Join-Path $logs 'exporter.err.log')
    Write-Output "Exporter: running (process $($e.Id)), every $Every s, database $Database"
}
if (-not (Test-Path -LiteralPath $Database)) {
    Write-Output "Note: $Database does not exist yet. Start Studio with --database pointing to it and save a draft."
}
Write-Output ''
Write-Output "Open $url  ->  project 'rockpro'  ->  Traces."
Write-Output 'Status: .\scripts\Start-Observability.ps1 -Status    Stop: -Stop    Start at login: -EnableAtLogon'
