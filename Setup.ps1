param([string]$Python='python', [switch]$InstallAddin)
$ErrorActionPreference='Stop'
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
& (Join-Path $base 'rockpro_cad\addin\Build.ps1') -OutputFolder bin-v03-final
if ($InstallAddin) {
    & (Join-Path $base 'rockpro_cad\addin\Install-User.ps1') -BinaryFolder bin-v03-final
}
Write-Output 'Ready. See HANDOVER.md. Save documents and restart IronCAD if the add-in was installed.'
