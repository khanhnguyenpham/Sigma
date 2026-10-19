$ErrorActionPreference='Stop'
$m3ProjectRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
& (Join-Path $m3ProjectRoot '.venv-m3/Scripts/python.exe') (Join-Path $PSScriptRoot 'local_stack.py') stop
exit $LASTEXITCODE
