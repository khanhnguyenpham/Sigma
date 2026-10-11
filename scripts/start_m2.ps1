param([ValidateRange(1024, 65535)][int]$Port = 8505, [string]$RunId = '')
$ErrorActionPreference = 'Stop'
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskProjectRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    throw 'Create .venv and install requirements.txt first; see README.md.'
}
$env:SIGMA_M2_RUN_ID = $RunId
$taskM2App = if ($RunId) { 'M2/report_app.py' } else { 'M2/final_app.py' }
& '.\.venv\Scripts\python.exe' -m streamlit run $taskM2App --server.headless true --server.address 127.0.0.1 --server.port $Port --browser.gatherUsageStats false
