param(
    [Parameter(Mandatory=$true)][string]$Bundle,
    [Parameter(Mandatory=$true)][string]$Database,
    [Parameter(Mandatory=$true)][string]$CadAssets,
    [string]$Python='', [string]$Previews='', [string]$PartImages='',
    [string]$SourceParts='', [int]$Port=0
)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
if(-not $Python){$Python=Join-Path $repo 'Integracja/.venv/Scripts/python.exe'}
if(-not (Test-Path -LiteralPath $Python)){throw 'Podaj -Python ze ścieżką istniejącego środowiska RockPro.'}
$arguments=@('-m','rockpro_cad.reference_studio','--bundle',(Resolve-Path -LiteralPath $Bundle).Path,
    '--database',(Resolve-Path -LiteralPath $Database).Path,
    '--cad-assets',(Resolve-Path -LiteralPath $CadAssets).Path,'--port',"$Port")
foreach($pair in @(@('--previews',$Previews),@('--part-images',$PartImages),@('--source-parts',$SourceParts))){
    if($pair[1]){$arguments+=@($pair[0],(Resolve-Path -LiteralPath $pair[1]).Path)}
}
$previousPythonPath=$env:PYTHONPATH;$previousCadYear=$env:ROCKPRO_IRONCAD_YEAR
try {
    $env:PYTHONPATH=Join-Path $repo 'Integracja';$env:ROCKPRO_IRONCAD_YEAR='2027'
    Push-Location $repo
    try {& $Python @arguments;if($LASTEXITCODE -ne 0){throw 'Studio zakończyło pracę z błędem.'}}
    finally {Pop-Location}
} finally {$env:PYTHONPATH=$previousPythonPath;$env:ROCKPRO_IRONCAD_YEAR=$previousCadYear}
