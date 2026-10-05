param([ValidatePattern('^\d{2}:\d{2}$')][string]$At = '07:00')
$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$taskScript = Join-Path $PSScriptRoot 'refresh_delivery_job.py'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Install the project environment first.' }
$taskTime = [datetime]::ParseExact($At, 'HH:mm', [System.Globalization.CultureInfo]::InvariantCulture)
$taskAction = New-ScheduledTaskAction -Execute $taskPython -Argument ('"' + $taskScript + '"') -WorkingDirectory $PSScriptRoot
$taskTrigger = New-ScheduledTaskTrigger -Daily -At $taskTime
$taskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName 'SIGMA-Customer-Delivery-Refresh' -Action $taskAction -Trigger $taskTrigger -Settings $taskSettings -Description 'Local SIGMA customer D+7 refresh; skips unchanged inputs; preserves last good run on failure.' -Force | Out-Null
Write-Output ('Registered daily local refresh at ' + $At + ' in the Windows time zone. No data are uploaded.')
