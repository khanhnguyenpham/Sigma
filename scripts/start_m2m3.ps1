param([ValidateRange(1024, 65535)][int]$Port = 8504, [string]$DeliveryConfig = 'outputs/sigma_m2m3_checkpoint_v3/delivery.json')
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
$ErrorActionPreference = 'Stop'
$presentationPath = [System.IO.Path]::GetFullPath((Join-Path $taskProjectRoot $DeliveryConfig))
$presentationRoot = [System.IO.Path]::GetFullPath($taskProjectRoot).TrimEnd('\') + '\'
if (-not $presentationPath.StartsWith($presentationRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Presentation config must be inside this project.'
}
if (-not (Test-Path -LiteralPath $presentationPath)) {
    throw 'Build a frozen release with python -m sigma release-check first; see docs/m2m3-demo.md.'
}
$presentationBundle = Get-Content -LiteralPath $presentationPath -Raw | ConvertFrom-Json
if (-not $presentationBundle.product_runs -or -not $presentationBundle.release_checkpoint) {
    throw 'Use a frozen release-check config for the M2/M3 presentation.'
}
& (Join-Path $taskProjectRoot 'scripts/start_product.ps1') -Port $Port -DeliveryConfig $DeliveryConfig
