param([string]$Config = 'data/configs/product30.json', [string]$TaskName = 'SigmaM3Refresh', [string]$At = '07:00')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$pythonWindowless = Join-Path $projectRoot '.venv/Scripts/pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonWindowless)) { throw 'Project pythonw.exe is missing.' }
$configFile = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $Config))
if (-not (Test-Path -LiteralPath $configFile)) { throw 'Product configuration is missing.' }
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) { throw 'Task name already exists. Inspect it before choosing a new name.' }
$arguments = '-m sigma refresh-m3 --config "' + $configFile + '"'
$action = New-ScheduledTaskAction -Execute $pythonWindowless -Argument $arguments -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$options = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $options -Description 'Local SIGMA M3 refresh. Validates source; skips unchanged inputs; preserves last good run.' | Select-Object TaskName, State
