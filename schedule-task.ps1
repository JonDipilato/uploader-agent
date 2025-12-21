$ErrorActionPreference = "Stop"

param(
    [string]$Time,
    [switch]$Remove
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$TaskName = "VideoCreatorAgentDaily"

if ($Remove) {
    schtasks /Delete /TN $TaskName /F | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path ".venv\\Scripts\\python.exe")) {
    Write-Host "Virtual environment not found. Run setup.ps1 first."
    exit 1
}

if (-not $Time) {
    $Time = & ".venv\\Scripts\\python.exe" -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c.get('schedule', {}).get('daily_time', '03:00'))"
}

if (-not $Time) {
    Write-Host "Schedule time not found. Provide -Time HH:MM or set schedule.daily_time in config.yaml."
    exit 1
}

$PyPath = Join-Path $Root ".venv\\Scripts\\python.exe"
$Cmd = "cmd /c `"cd /d `"$Root`" && `"$PyPath`" -m src.agent --config config.yaml --once`""

schtasks /Create /TN $TaskName /SC DAILY /ST $Time /TR $Cmd /F | Out-Null
Write-Host "Created scheduled task: $TaskName at $Time daily."
