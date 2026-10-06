param([ValidatePattern('^\d{2}:\d{2}$')][string]$At = '07:00')
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $taskProjectRoot '.venv\Scripts\pythonw.exe'
$taskArguments = '-m sigma refresh --delivery-config data/configs/config.delivery.json'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Install the project environment first.' }
$taskTime = [datetime]::ParseExact($At, 'HH:mm', [System.Globalization.CultureInfo]::InvariantCulture)
$taskName = 'SIGMA-Customer-Delivery-Refresh'
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.State -eq 'Running') { throw 'SIGMA refresh is running. Retry after it finishes.' }
    if (@($existing.Actions).Count -ne 1 -or $existing.Actions[0].WorkingDirectory -ne $taskProjectRoot -or ($existing.Actions[0].Arguments -ne $taskArguments -and $existing.Actions[0].Arguments -notlike '*refresh_delivery_job.py*')) {
        throw 'The existing task belongs to another checkout. It was not replaced.'
    }
}
$taskAction = New-ScheduledTaskAction -Execute $taskPython -Argument $taskArguments -WorkingDirectory $taskProjectRoot
$taskTrigger = New-ScheduledTaskTrigger -Daily -At $taskTime
$taskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $taskTrigger -Settings $taskSettings -Description 'Local SIGMA customer D+7 refresh; skips unchanged inputs; preserves last good run on failure.' -Force | Out-Null
Write-Output ('Registered daily local refresh at ' + $At + ' in the Windows time zone. No data are uploaded.')
