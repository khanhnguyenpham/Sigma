param(
    [ValidatePattern('^[A-Za-z0-9_-]*$')][string]$RunId = '',
    [ValidateRange(1024, 65535)][int]$Port = 8502
)
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $taskProjectRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    throw 'Create .venv and install requirements.txt first; see README.md.'
}
$taskPreviousWeeklyRun = $env:SIGMA_WEEKLY_RUN_ID
try {
    if ($RunId) { $env:SIGMA_WEEKLY_RUN_ID = $RunId }
    & '.\.venv\Scripts\python.exe' -m streamlit run sigma/ui/weekly.py --server.headless true --server.address 127.0.0.1 --server.port $Port --browser.gatherUsageStats false
} finally {
    $env:SIGMA_WEEKLY_RUN_ID = $taskPreviousWeeklyRun
}
