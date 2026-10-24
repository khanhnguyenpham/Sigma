$ErrorActionPreference='Stop'
$m3ProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
& (Join-Path $m3ProjectRoot '.venv-m3/Scripts/python.exe') (Join-Path $PSScriptRoot 'local_stack.py') stop
exit $LASTEXITCODE
