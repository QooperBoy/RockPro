# Start the local Arize Phoenix dashboard for RockPro observability.
# Listens only on this computer (127.0.0.1). Data: artifacts\phoenix (git-ignored).
# First run installs Phoenix into tools\phoenix\.venv (needs internet once).
param(
    [int]$Port = 6006,
    [string]$Python = 'py',
    [switch]$InstallOnly
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root 'tools\phoenix\.venv'
$exe = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $exe)) {
    Write-Output "Installing Phoenix into $venv ..."
    if ($Python -eq 'py') { & py -3 -m venv $venv } else { & $Python -m venv $venv }
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Phoenix venv' }
    & $exe -m pip install --upgrade pip
    & $exe -m pip install -r (Join-Path $root 'tools\phoenix\requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Phoenix installation failed' }
}
if ($InstallOnly) { return }
$data = Join-Path $root 'artifacts\phoenix'
New-Item -ItemType Directory -Force $data | Out-Null
$env:PHOENIX_HOST = '127.0.0.1'
$env:PHOENIX_PORT = "$Port"
$env:PHOENIX_GRPC_PORT = '4317'
$env:PHOENIX_WORKING_DIR = $data
$env:PHOENIX_TELEMETRY_ENABLED = 'false'
$env:PHOENIX_PROJECT_NAME = 'rockpro'
$env:PHOENIX_DB_LOGGING_LEVEL = 'warning'   # otherwise every SQL statement is printed
Write-Output "Phoenix: http://127.0.0.1:$Port  (Ctrl+C stops it; data in $data)"
& $exe -m phoenix.server.main serve
