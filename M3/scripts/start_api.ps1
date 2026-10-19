param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$m3ProjectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location -LiteralPath $m3ProjectRoot
. (Join-Path $PSScriptRoot 'load_env.ps1')
& (Join-Path $m3ProjectRoot '.venv-m3/Scripts/python.exe') -m uvicorn sigma_m3.main:create_app --factory --host 127.0.0.1 --port $Port
exit $LASTEXITCODE
