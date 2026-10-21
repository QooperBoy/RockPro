param([string]$OutputFolder='bin')
$ErrorActionPreference='Stop'
$sdk='C:\Program Files\IronCAD\2027\ICAPI\Samples\C#\References'
$out=Join-Path $PSScriptRoot $OutputFolder
New-Item -ItemType Directory -Force $out | Out-Null
$compiler='C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
& $compiler /nologo /target:library /platform:x64 "/out:$out\RockPro.CAD.dll" "/reference:$sdk\interop.ICApiIronCAD.dll" '/reference:C:\Program Files (x86)\Microsoft.NET\Primary Interop Assemblies\stdole.dll' /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll (Join-Path $PSScriptRoot 'RockProAddin.cs') (Join-Path $PSScriptRoot 'RockProPanel.cs') (Join-Path $PSScriptRoot 'LayoutForm.cs') (Join-Path $PSScriptRoot 'UiText.cs')
if($LASTEXITCODE -ne 0) {throw 'C# build failed'}
Copy-Item -LiteralPath "$sdk\interop.ICApiIronCAD.dll" -Destination $out -Force
Write-Output "Built $out\RockPro.CAD.dll"



