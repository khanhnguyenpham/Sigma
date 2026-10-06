param([ValidateRange(1024, 65535)][int]$Port = 8505)
$ErrorActionPreference = 'Stop'
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskProjectRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    throw 'Create .venv and install requirements.txt first; see README.md.'
}
& '.\.venv\Scripts\python.exe' -m streamlit run M2/report_app.py --server.headless true --server.address 127.0.0.1 --server.port $Port --browser.gatherUsageStats false
