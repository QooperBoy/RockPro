param(
    [string]$Python = (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
)
$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$repo = Join-Path $workspace 'Transfer_RockPro_20261024\RockPro\rockpro-cad'
if (Get-Process -Name IRONCAD -ErrorAction SilentlyContinue) {
    throw 'Close IronCAD before installing. No installation was performed.'
}
if (-not (Test-Path -LiteralPath $Python)) { throw 'Pass -Python with an existing Python x64 executable.' }
# RegisterTypeLib must honor the installer's existing HKCR -> HKCU override.
# Microsoft: https://learn.microsoft.com/windows/win32/api/oleauto/nf-oleauto-oaenableperusertlibregistration
# This process-only setting does not change UAC or machine-wide configuration.
$previous = [Environment]::GetEnvironmentVariable('OAPERUSERTLIBREG', 'Process')
try {
    $env:OAPERUSERTLIBREG = '1'
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'Setup.ps1') -Python $Python -InstallAddin
    if ($LASTEXITCODE -ne 0) { throw 'RockPro installation failed. Review the installer output.' }
} finally {
    [Environment]::SetEnvironmentVariable('OAPERUSERTLIBREG', $previous, 'Process')
}

# Generate the legacy Automation wrapper from the local vendor type library.
# Generating it from live COM type information was too slow on this host.
$localPython = Join-Path $repo 'Integracja\.venv\Scripts\python.exe'
& $localPython -c "import comtypes.client; comtypes.client.GetModule(r'C:\Program Files\IronCAD\2027\bin\IronCad.tlb')"
if ($LASTEXITCODE -ne 0) { throw 'Legacy Automation wrapper preparation failed.' }
