param([string]$OutputFolder='bin-counts-2027')
$ErrorActionPreference='Stop'
$sdk=Join-Path $env:ProgramFiles 'IronCAD/2027/ICAPI/Samples/C#/References/interop.ICApiIronCAD.dll'
$out=Join-Path $PSScriptRoot $OutputFolder
New-Item -ItemType Directory -Force $out | Out-Null
$sourceTag=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'MountCountController.cs') -Algorithm SHA256).Hash.Substring(0,12)
$compiled=Join-Path $out "RockPro.MountCounts_$sourceTag.dll"
& 'C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe' /nologo /codepage:65001 /target:library /platform:x64 "/out:$compiled" "/reference:$sdk" /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll (Join-Path $PSScriptRoot 'MountCountController.cs')
if($LASTEXITCODE -ne 0){throw 'Quantity controller build failed. Do not replace a DLL loaded in IronCAD.'}
Copy-Item -LiteralPath $compiled -Destination (Join-Path $out "RockPro.MountCounts.dll") -Force
Copy-Item -LiteralPath $sdk -Destination $out -Force
@{host_year=2027;dll_sha256=(Get-FileHash -LiteralPath "$out/RockPro.MountCounts.dll" -Algorithm SHA256).Hash;source_sha256=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'MountCountController.cs') -Algorithm SHA256).Hash} | ConvertTo-Json | Set-Content -LiteralPath "$out/build-target.json" -Encoding utf8
Write-Output "Built separate quantity controller: $out/RockPro.MountCounts.dll"
