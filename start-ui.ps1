$ErrorActionPreference = "Stop"

param(
    [switch]$Demo
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".venv\\Scripts\\python.exe")) {
    Write-Host "Virtual environment not found. Run setup.ps1 first."
    exit 1
}

if ($Demo) {
    $env:DEMO_MODE = "1"
}

& ".venv\\Scripts\\python.exe" -m streamlit run streamlit_app.py
