param([ValidatePattern('^\d{2}:\d{2}$')][string]$At = '07:00')
$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'
$taskScript = Join-Path $PSScriptRoot 'refresh_delivery_job.py'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Install the project environment first.' }
$taskTime = [datetime]::ParseExact($At, 'HH:mm', [System.Globalization.CultureInfo]::InvariantCulture)
$taskName = 'SIGMA-Customer-Delivery-Refresh'
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.State -eq 'Running') { throw 'SIGMA refresh is running. Retry after it finishes.' }
    if (@($existing.Actions).Count -ne 1 -or $existing.Actions[0].WorkingDirectory -ne $PSScriptRoot -or $existing.Actions[0].Arguments -notlike ('*' + $taskScript + '*')) {
        throw 'The existing task belongs to another checkout. It was not replaced.'
    }
}
$taskAction = New-ScheduledTaskAction -Execute $taskPython -Argument ('"' + $taskScript + '" --delivery-config config.delivery.json') -WorkingDirectory $PSScriptRoot
$taskTrigger = New-ScheduledTaskTrigger -Daily -At $taskTime
$taskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $taskTrigger -Settings $taskSettings -Description 'Local SIGMA customer D+7 refresh; skips unchanged inputs; preserves last good run on failure.' -Force | Out-Null
Write-Output ('Registered daily local refresh at ' + $At + ' in the Windows time zone. No data are uploaded.')
