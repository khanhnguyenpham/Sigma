param([string]$EnvFile = (Join-Path $PSScriptRoot '../.env'))
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $EnvFile)) { throw 'Create the ignored web/backend/.env from web/backend/configs/.env.example first.' }
foreach ($line in Get-Content -LiteralPath $EnvFile) {
    if ($line -match '^\s*(#|$)') { continue }
    $parts = $line.Split('=', 2)
    if ($parts.Length -ne 2 -or $parts[0] -notmatch '^M3_[A-Z_]+$') { throw 'Invalid M3 environment field' }
    [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
}
