param([string]$Python='python', [switch]$InstallAddin, [ValidateSet(2023,2027)][int]$IronCADYear=2023)
$ErrorActionPreference='Stop'
if ($InstallAddin -and (Get-Process -Name IRONCAD -ErrorAction SilentlyContinue)) {
    throw 'Save documents and close IronCAD before Setup -InstallAddin. Setup made no changes.'
}
Set-Location -LiteralPath $PSScriptRoot
$base=Join-Path $PSScriptRoot 'Integracja'
$py=Join-Path $base '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $py)) {
    & $Python -m venv (Join-Path $base '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python venv failed' }
}
& $py -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependencies failed' }
& $py (Join-Path $PSScriptRoot 'configure.py')
if ($LASTEXITCODE -ne 0) { throw 'Configuration failed' }
& (Join-Path $base 'rockpro_cad\addin\Build.ps1') -OutputFolder "bin-ic$IronCADYear" -IronCADYear $IronCADYear
if ($InstallAddin) {
    & (Join-Path $base 'rockpro_cad\addin\Install-User.ps1') -BinaryFolder "bin-ic$IronCADYear" -IronCADYear $IronCADYear
}
Write-Output 'Ready. See HANDOVER.md. Save documents and restart IronCAD if the add-in was installed.'
