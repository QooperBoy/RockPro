$ErrorActionPreference = 'Stop'
& "$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\parameter_panel.py"
exit $LASTEXITCODE
