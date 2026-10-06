$taskProjectRoot = Split-Path -Parent $PSScriptRoot
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $taskProjectRoot
if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    throw "Create .venv and install requirements.txt first; see README.md."
}
$taskPreviousRunId = $env:SIGMA_RUN_ID
try {
    if (-not $taskPreviousRunId -and (Test-Path -LiteralPath "outputs")) {
        $taskCompletedRuns = foreach ($taskFolder in Get-ChildItem -LiteralPath "outputs" -Directory) {
            $taskManifestPath = Join-Path $taskFolder.FullName "manifest.json"
            if (Test-Path -LiteralPath $taskManifestPath) {
                try {
                    $taskManifest = Get-Content -LiteralPath $taskManifestPath -Raw | ConvertFrom-Json
                    if ($taskManifest.status -eq "complete") {
                        [PSCustomObject]@{ Id = $taskFolder.Name; Created = $taskManifest.created_at_utc; Source = $taskManifest.source_kind }
                    }
                } catch { Write-Warning "Skipped an unreadable local run manifest." }
            }
        }
        $taskPrivateRuns = @($taskCompletedRuns | Where-Object Source -eq "private_order_snapshot")
        $taskRunsForDefault = if ($taskPrivateRuns.Count) { $taskPrivateRuns } else { $taskCompletedRuns }
        $taskLatestRun = $taskRunsForDefault | Sort-Object Created -Descending | Select-Object -First 1
        if ($taskLatestRun) { $env:SIGMA_RUN_ID = $taskLatestRun.Id }
    }
    & ".\.venv\Scripts\python.exe" -m streamlit run sigma/ui/daily.py --server.headless true --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
} finally {
    $env:SIGMA_RUN_ID = $taskPreviousRunId
}
