param([string]$Trace='', [string]$Database='', [string]$Model='')
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$integration=Join-Path $repo 'Integracja'
if (-not $Trace) {
    $latest=Get-ChildItem -LiteralPath (Join-Path $repo 'artifacts') -Filter '*.jsonl' -File -Recurse |
        Where-Object { $_.Directory.Name -eq 'trace' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) { $Trace=$latest.FullName }
}
if (-not $Database) { $Database=Join-Path $integration 'rockpro_cad\data\projects.sqlite3' }
$observerArgs=@('-m','rockpro_cad.process_observer')
if ($Trace) { $observerArgs+=@('--trace',(Resolve-Path -LiteralPath $Trace).Path) }
if (Test-Path -LiteralPath $Database) { $observerArgs+=@('--database',(Resolve-Path -LiteralPath $Database).Path) }
if ($Model) { $observerArgs+=@('--model',(Resolve-Path -LiteralPath $Model).Path) }
Push-Location $integration
try { & (Join-Path $integration '.venv\Scripts\python.exe') @observerArgs; if ($LASTEXITCODE -ne 0) { throw 'Observer failed to start or exited with an error' } }
finally { Pop-Location }
