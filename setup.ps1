$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "Video Creator Agent setup"

$pythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py -3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
}

if (-not $pythonCmd) {
    Write-Host "Python not found. Install Python 3.10+ and re-run."
    Write-Host "Suggested: winget install Python.Python.3"
    exit 1
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "ffmpeg not found. Install ffmpeg and re-run."
    Write-Host "Suggested: winget install Gyan.FFmpeg"
    exit 1
}

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    & $pythonCmd -m venv .venv
}

Write-Host "Installing requirements..."
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "Running setup wizard..."
& ".venv\Scripts\python.exe" "scripts\setup_wizard.py"

Write-Host "Setup complete."
Write-Host "Run: .\\start-ui.ps1"
