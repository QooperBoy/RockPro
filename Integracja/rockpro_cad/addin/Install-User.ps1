param([string]$BinaryFolder='bin')
$ErrorActionPreference='Stop'
$dll=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "$BinaryFolder\RockPro.CAD.dll")).Path
$assembly=[Reflection.AssemblyName]::GetAssemblyName($dll).FullName
# The host needs native ICAPI COM metadata in addition to the managed add-in class.
$python=Join-Path $PSScriptRoot '..\..\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Missing integration venv. Run Setup.ps1 first.' }
& $python (Join-Path $PSScriptRoot 'Repair-IcApi.py')
if ($LASTEXITCODE -ne 0) { throw 'ICAPI registration failed; add-in installation stopped.' }
$guid='{B7659903-7C95-4E26-923F-DB5119AD1460}'
$prog='RockPro.CAD.Addin'
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
$compat.CreateSubKey('GreaterThanAndEqualTo').SetValue('', '29..')
$compat.Close()

$root.CreateSubKey("Software\Classes\$prog\CLSID").SetValue('',$guid)
$app=$root.CreateSubKey('Software\IronCAD\IRONCAD 29.0\Applications\RockPro CAD')
$app.SetValue('',$guid)
$app.SetValue('LoadOnStartup',1,[Microsoft.Win32.RegistryValueKind]::DWord)
$app.SetValue('ShowInList',1,[Microsoft.Win32.RegistryValueKind]::DWord)
Write-Output 'Registered RockPro CAD for current user, IronCAD 29.0. No machine-wide settings changed.'
