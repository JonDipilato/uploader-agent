$ErrorActionPreference = "Stop"

param(
    [int]$Minutes = 0
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".venv\\Scripts\\python.exe")) {
    Write-Host "Virtual environment not found. Run setup.ps1 first."
    exit 1
}

$ArgsList = @("-m", "src.agent", "--config", "config.yaml", "--once", "--test")
if ($Minutes -gt 0) {
    $ArgsList += @("--test-minutes", $Minutes)
}

& ".venv\\Scripts\\python.exe" @ArgsList
