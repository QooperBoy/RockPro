param([string]$OutputFolder='bin', [ValidateSet(2023,2027)][int]$IronCADYear=2023)
$ErrorActionPreference='Stop'
function Get-RockProSha256([string]$Path) {
    $stream=[IO.File]::OpenRead($Path); $hash=[Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($hash.ComputeHash($stream)).Replace('-','') }
    finally { $stream.Dispose(); $hash.Dispose() }
}

$sdk=Join-Path $env:ProgramFiles "IronCAD\$IronCADYear\ICAPI\Samples\C#\References"
if (-not (Test-Path -LiteralPath "$sdk\interop.ICApiIronCAD.dll")) { throw "Missing SDK for IronCAD $IronCADYear" }
$out=Join-Path $PSScriptRoot $OutputFolder
New-Item -ItemType Directory -Force $out | Out-Null
$compiler='C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
& $compiler /nologo /target:library /platform:x64 "/define:IRONCAD$IronCADYear" "/out:$out\RockPro.CAD.dll" "/reference:$sdk\interop.ICApiIronCAD.dll" '/reference:C:\Program Files (x86)\Microsoft.NET\Primary Interop Assemblies\stdole.dll' /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll (Join-Path $PSScriptRoot 'RockProAddin.cs') (Join-Path $PSScriptRoot 'RockProPanel.cs') (Join-Path $PSScriptRoot 'RpcProcessSession.cs') (Join-Path $PSScriptRoot 'LayoutForm.cs') (Join-Path $PSScriptRoot 'CasePlanForm.cs') (Join-Path $PSScriptRoot 'HandleDecisionForm.cs') (Join-Path $PSScriptRoot 'DeviceVariantsForm.cs') (Join-Path $PSScriptRoot 'InventoryForm.cs') (Join-Path $PSScriptRoot 'InventoryCommandForm.cs') (Join-Path $PSScriptRoot 'PurchaseProposalForm.cs') (Join-Path $PSScriptRoot 'MaterialPlanForm.cs') (Join-Path $PSScriptRoot 'UiText.cs')
if($LASTEXITCODE -ne 0) {throw 'C# build failed'}
Copy-Item -LiteralPath "$sdk\interop.ICApiIronCAD.dll" -Destination $out -Force
@{host_year=$IronCADYear;host_major=($IronCADYear-1998);dll_sha256=(Get-RockProSha256 "$out\RockPro.CAD.dll");sdk_sha256=(Get-RockProSha256 "$sdk\interop.ICApiIronCAD.dll")} | ConvertTo-Json | Set-Content -LiteralPath "$out\build-target.json" -Encoding UTF8
Write-Output "Built $out\RockPro.CAD.dll"



