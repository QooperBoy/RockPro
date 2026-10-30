param([string]$EvidenceFolder='')
$ErrorActionPreference='Stop'
if (-not $EvidenceFolder) {
    $EvidenceFolder=Join-Path $PSScriptRoot ('../../../artifacts/quantity-layout-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ'))
}
if(Test-Path -LiteralPath $EvidenceFolder){throw 'Use a new evidence folder.'}
$out=New-Item -ItemType Directory -Path $EvidenceFolder
$exe=Join-Path $out.FullName 'MountRowLayoutChecks.exe'
& 'C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe' /nologo /codepage:65001 "/out:$exe" (Join-Path $PSScriptRoot 'MountRowLayout.cs') (Join-Path $PSScriptRoot 'tests/MountRowLayoutChecks.cs')
if($LASTEXITCODE -ne 0){throw 'Layout checks compilation failed.'}
& $exe | Tee-Object -FilePath (Join-Path $out.FullName 'checks.txt')
if($LASTEXITCODE -ne 0){throw 'Layout checks failed.'}
