param(
    [Parameter(Mandatory=$true)][string]$File,
    [switch]$Apply,
    [string]$ProjectId='',
    [int]$ExpectedRevision=-1,
    [string]$ExpectedSourceSha256=''
)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$integration=Join-Path $repo 'Integracja'
$source=(Resolve-Path -LiteralPath $File).Path
if ([IO.Path]::GetExtension($source) -ine '.xlsx') { throw 'Wymagany plik XLSX' }
if ((Get-Item -LiteralPath $source).Length -gt 2MB) { throw 'Maksymalny rozmiar arkusza: 2 MB' }
$bytes=[IO.File]::ReadAllBytes($source)
$hasher=[Security.Cryptography.SHA256]::Create()
try { $digest=([BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace('-','').ToLowerInvariant() }
finally { $hasher.Dispose() }
$imports=Join-Path $integration 'imports'
[IO.Directory]::CreateDirectory($imports) | Out-Null
$staged=Join-Path $imports ($digest+'.xlsx')
if (-not (Test-Path -LiteralPath $staged)) { [IO.File]::WriteAllBytes($staged,$bytes) }
if ($Apply) {
    if (-not $ProjectId -or $ExpectedRevision -lt 0 -or $ExpectedSourceSha256 -notmatch '^[0-9a-f]{64}$') {
        throw 'Zapis wymaga ProjectId, ExpectedRevision i ExpectedSourceSha256 odczytanych w podglądzie'
    }
    $request=@{name='import_excel_configuration';arguments=@{project_id=$ProjectId;path=$staged;expected_revision=$ExpectedRevision;expected_source_sha256=$ExpectedSourceSha256}}
} else { $request=@{name='preview_excel_configuration';arguments=@{path=$staged}} }
$requestPath=Join-Path $imports ('request-'+[guid]::NewGuid().ToString('N')+'.json')
$json=$request | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText($requestPath,$json,[Text.UTF8Encoding]::new($false))
& (Join-Path $integration '.venv\Scripts\python.exe') (Join-Path $integration 'rockpro_cad\mcp\worker.py') $requestPath
if ($LASTEXITCODE -ne 0) { throw 'Operacja Excel nie powiodła się; szczegóły powyżej' }
