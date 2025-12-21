$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".venv\\Scripts\\python.exe")) {
    Write-Host "Virtual environment not found. Run setup.ps1 first."
    exit 1
}

& ".venv\\Scripts\\python.exe" -m src.agent --config config.yaml
