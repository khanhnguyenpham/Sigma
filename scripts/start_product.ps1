param([ValidateRange(1024, 65535)][int]$Port = 8503, [string]$DeliveryConfig = 'data/configs/config.delivery.json')
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $taskProjectRoot
$env:SIGMA_DELIVERY_CONFIG = $DeliveryConfig
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    throw 'Create .venv and install requirements.txt first; see README.md.'
}
& '.\.venv\Scripts\python.exe' -m streamlit run sigma/ui/product.py --server.headless true --server.address 127.0.0.1 --server.port $Port --browser.gatherUsageStats false
