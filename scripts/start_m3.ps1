param([string]$Config = 'data/configs/product30.json')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$pythonExe = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Create the project .venv and install requirements.txt first.' }
$env:SIGMA_M3_CONFIG = $Config
$productSettings = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
& $pythonExe -m streamlit run sigma/ui/product30.py --server.address 127.0.0.1 --server.port $productSettings.port --server.headless true
exit $LASTEXITCODE
