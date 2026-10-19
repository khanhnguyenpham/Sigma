$ErrorActionPreference = 'Stop'
$m3ProjectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location -LiteralPath $m3ProjectRoot
. (Join-Path $PSScriptRoot 'load_env.ps1')
& (Join-Path $m3ProjectRoot '.venv-m3/Scripts/python.exe') -m sigma_m3.worker
exit $LASTEXITCODE
