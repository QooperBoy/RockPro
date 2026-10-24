param([Parameter(Mandatory=$true)][string]$Dataset)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$integration=Join-Path $repo 'Integracja'
$resolved=(Resolve-Path -LiteralPath $Dataset).Path
Push-Location $integration
try { & (Join-Path $integration '.venv\Scripts\python.exe') -m rockpro_cad.layer_viewer --dataset $resolved }
finally { Pop-Location }
