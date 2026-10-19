param([int]$Port=8000)
$ErrorActionPreference='Stop'
$m3ProjectRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location -LiteralPath $m3ProjectRoot
. (Join-Path $PSScriptRoot 'load_env.ps1')
& (Join-Path $m3ProjectRoot '.venv-m3/Scripts/python.exe') (Join-Path $PSScriptRoot 'local_stack.py') start --port $Port
exit $LASTEXITCODE
