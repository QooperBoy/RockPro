param([string]$BinaryFolder='bin', [ValidateSet(2023,2027)][int]$IronCADYear=2023)
$ErrorActionPreference='Stop'
function Get-RockProSha256([string]$Path) {
    $stream=[IO.File]::OpenRead($Path); $hash=[Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($hash.ComputeHash($stream)).Replace('-','') }
    finally { $stream.Dispose(); $hash.Dispose() }
}

if (Get-Process -Name IRONCAD -ErrorAction SilentlyContinue) {
    throw 'Close IronCAD after saving documents before registering the add-in. No registration was changed.'
}
$dll=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "$BinaryFolder\RockPro.CAD.dll")).Path
$manifest=Get-Content -LiteralPath (Join-Path (Split-Path $dll) 'build-target.json') -Raw | ConvertFrom-Json
if ($manifest.host_year -ne $IronCADYear -or $manifest.dll_sha256 -ne (Get-RockProSha256 $dll)) { throw 'Build target/hash mismatch; no registration changed.' }
$major=$IronCADYear-1998
$assembly=[Reflection.AssemblyName]::GetAssemblyName($dll).FullName
# The host needs native ICAPI COM metadata in addition to the managed add-in class.
$python=Join-Path $PSScriptRoot '..\..\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Missing integration venv. Run Setup.ps1 first.' }
# Scope per-user type-library registration to this installer process.
$oldPerUserTypeLib=$env:OAPERUSERTLIBREG
try {
    $env:OAPERUSERTLIBREG='1'
    & $python (Join-Path $PSScriptRoot 'Repair-IcApi.py') --year $IronCADYear
    if ($LASTEXITCODE -ne 0) { throw 'ICAPI registration failed; add-in installation stopped.' }
} finally { $env:OAPERUSERTLIBREG=$oldPerUserTypeLib }
$guid='{B7659903-7C95-4E26-923F-DB5119AD1460}'
$prog='RockPro.CAD.Addin'
if ($IronCADYear -eq 2023) { $guid='{BEC3F005-C8B6-4A90-97CC-841324F7A635}'; $prog='RockPro.CAD.Addin2023' }
$codebase=[Uri]::UnescapeDataString(([Uri]$dll).AbsoluteUri)
$root=[Microsoft.Win32.Registry]::CurrentUser
$cls=$root.CreateSubKey("Software\Classes\CLSID\$guid")
$cls.SetValue('', 'RockPro CAD')
$inproc=$cls.CreateSubKey('InprocServer32')
$inproc.SetValue('','mscoree.dll')
$inproc.SetValue('ThreadingModel','Both')
foreach($key in @($inproc,$inproc.CreateSubKey('0.1.0.0'))) {
    $key.SetValue('Class','RockPro.CAD.Addin')
    $key.SetValue('Assembly',$assembly)
    $key.SetValue('RuntimeVersion','v4.0.30319')
    $key.SetValue('CodeBase',$codebase)
}
$cls.CreateSubKey('ProgId').SetValue('',$prog)
$cls.CreateSubKey('Implemented Categories\{62C8FE65-4EBB-45E7-B440-6E39B2CDBF29}').Close()
$cls.CreateSubKey('Implemented Categories\{6CA5004A-8CD0-454D-88BA-E9700C9789A6}').Close()
$cls.CreateSubKey('Required Categories\{2D652377-6B3B-450E-840A-5DE09A48B464}').Close()
$cls.CreateSubKey('Name').SetValue('', 'RockPro CAD')
$cls.CreateSubKey('Description').SetValue('', 'RockPro CAD: parametry szkieletu i lokalny MCP.')
# SDK MyRegistration.rgs: declare host-version compatibility for discovery.
$compat=$cls.CreateSubKey('AddIn Version Compatibility')
$compat.CreateSubKey('GreaterThanAndEqualTo').SetValue('', "$major..")
$compat.Close()

$root.CreateSubKey("Software\Classes\$prog\CLSID").SetValue('',$guid)
$app=$root.CreateSubKey("Software\IronCAD\IRONCAD $major.0\Applications\RockPro CAD")
$app.SetValue('',$guid)
$app.SetValue('LoadOnStartup',1,[Microsoft.Win32.RegistryValueKind]::DWord)
$app.SetValue('ShowInList',1,[Microsoft.Win32.RegistryValueKind]::DWord)
Write-Output "Registered RockPro CAD for current user, IronCAD $major.0. No machine-wide settings changed."
