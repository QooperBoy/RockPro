param([string]$EvidenceFolder='')
$ErrorActionPreference='Stop'
if(-not $EvidenceFolder){$EvidenceFolder=Join-Path $PSScriptRoot ('../../../artifacts/wall-math-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ'))}
if(Test-Path -LiteralPath $EvidenceFolder){throw 'Use a new evidence folder.'}
$out=New-Item -ItemType Directory -Path $EvidenceFolder
$sdk=Join-Path $env:ProgramFiles 'IronCAD/2027/ICAPI/Samples/C#/References/interop.ICApiIronCAD.dll'
$exe=Join-Path $out.FullName 'WallMountMathChecks.exe'
$sources=@('MountCountController.cs','MountRowLayout.cs','WallMountMapper.cs','tests/WallMountMathChecks.cs') | ForEach-Object {Join-Path $PSScriptRoot $_}
& 'C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe' /nologo /target:exe /platform:x64 /codepage:65001 /main:WallMountMathChecks "/out:$exe" "/reference:$sdk" /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll @sources
if($LASTEXITCODE -ne 0){throw 'Wall-mapping checks compilation failed.'}
Copy-Item -LiteralPath $sdk -Destination $out.FullName
& $exe | Tee-Object -FilePath (Join-Path $out.FullName 'checks.txt')
if($LASTEXITCODE -ne 0){throw 'Wall-mapping checks failed.'}
