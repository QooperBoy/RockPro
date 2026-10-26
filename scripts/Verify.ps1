param([string]$Python='', [switch]$WithAddinBuild, [switch]$WithUiChecks, [ValidateSet(2023,2027)][int]$IronCADYear=2023)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
if (-not $Python) { $Python=Join-Path $repo 'Integracja\.venv\Scripts\python.exe' }
$pythonCommand=Get-Command $Python -ErrorAction SilentlyContinue
if (-not $pythonCommand) { throw 'Python not found. Pass -Python with an existing interpreter; verification does not install dependencies.' }
$runnerArgs=@((Join-Path $PSScriptRoot 'verify.py'),'--year',$IronCADYear)
if ($WithAddinBuild) { $runnerArgs+='--build' }
if ($WithUiChecks) { $runnerArgs+='--ui' }
& $pythonCommand.Source @runnerArgs
if ($LASTEXITCODE -ne 0) { throw 'Verification failed. See the evidence path reported above.' }
