param([string]$BinaryFolder='bin-counts-2027')
$ErrorActionPreference='Stop'
# A separate per-user component; never replaces the running RockPro CAD DLL.
$dll=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "$BinaryFolder/RockPro.MountCounts.dll")).Path
$manifest=Get-Content -LiteralPath (Join-Path (Split-Path $dll) 'build-target.json') -Raw | ConvertFrom-Json
if($manifest.host_year -ne 2027 -or $manifest.dll_sha256 -ne (Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash){throw 'Quantity controller target/hash mismatch; no registration changed.'}
$assemblyName=[Reflection.AssemblyName]::GetAssemblyName($dll)
$identity=$assemblyName.FullName
$version=$assemblyName.Version.ToString()
$guid='{93C43C38-9891-44D5-85A9-A07D513C3C21}'
$prog='RockPro.CAD.MountCounts2027'
$className='RockPro.CAD.MountCountsAddin'
$root=[Microsoft.Win32.Registry]::CurrentUser
$path="Software\Classes\CLSID\$guid"
$prior=$root.OpenSubKey("$path\InprocServer32")
if($null -ne $prior -and $prior.GetValue('Class') -ne $className){throw 'GUID already belongs to another class; no registration changed.'}
$cls=$root.CreateSubKey($path)
$cls.SetValue('','RockPro — Ilość okuć')
$inproc=$cls.CreateSubKey('InprocServer32')
$inproc.SetValue('','mscoree.dll');$inproc.SetValue('ThreadingModel','Both')
foreach($key in @($inproc,$inproc.CreateSubKey($version))){
    $key.SetValue('Class',$className);$key.SetValue('Assembly',$identity)
    $key.SetValue('RuntimeVersion','v4.0.30319');$key.SetValue('CodeBase',([Uri]$dll).AbsoluteUri)
}
$cls.CreateSubKey('ProgId').SetValue('',$prog)
$cls.CreateSubKey('Implemented Categories\{62C8FE65-4EBB-45E7-B440-6E39B2CDBF29}').Close()
$cls.CreateSubKey('Implemented Categories\{6CA5004A-8CD0-454D-88BA-E9700C9789A6}').Close()
$cls.CreateSubKey('Required Categories\{2D652377-6B3B-450E-840A-5DE09A48B464}').Close()
$cls.CreateSubKey('Name').SetValue('','RockPro — Ilość okuć')
$cls.CreateSubKey('Description').SetValue('','Liczba okuć i powiązanych wycięć w oznaczonych modelach RockPro. IronCAD 2027.')
$cls.CreateSubKey('AddIn Version Compatibility\GreaterThanAndEqualTo').SetValue('','29..')
$root.CreateSubKey("Software\Classes\$prog\CLSID").SetValue('',$guid)
$app=$root.CreateSubKey('Software\IronCAD\IRONCAD 29.0\Applications\RockPro Ilość okuć')
$app.SetValue('',$guid);$app.SetValue('LoadOnStartup',1,[Microsoft.Win32.RegistryValueKind]::DWord)
$app.SetValue('ShowInList',1,[Microsoft.Win32.RegistryValueKind]::DWord)
Write-Output "Registered separate quantity controller for IronCAD 2027: $dll"
