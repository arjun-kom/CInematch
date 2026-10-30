# Starts CineMatch with Docker and opens the dashboard.
# Usage (PowerShell, in this folder):   .\run.ps1          start
#                                       .\run.ps1 -Stop    stop
#                                       .\run.ps1 -Reset   stop and delete all stored data
param([switch]$Stop, [switch]$Reset)

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker is not installed or not running. Install Docker Desktop first." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path .env)) { Copy-Item .env.example .env }

if ($Reset) { docker compose down -v; exit }
if ($Stop)  { docker compose down; exit }

$port = 8090
$line = Select-String -Path .env -Pattern '^WEB_PORT=(\d+)' | Select-Object -First 1
if ($line) { $port = $line.Matches[0].Groups[1].Value }

docker compose up --build -d
if ($LASTEXITCODE -ne 0) { Write-Host "docker compose failed. See the messages above." -ForegroundColor Red; exit 1 }

Write-Host "Waiting for the API to be ready..."
for ($i = 0; $i -lt 60; $i++) {
    try {
        $r = Invoke-RestMethod "http://localhost:$port/api/health" -TimeoutSec 2
        if ($r.database -eq "up") { break }
    } catch { }
    Start-Sleep -Seconds 2
}
Write-Host "Dashboard: http://localhost:$port" -ForegroundColor Green
Write-Host "API docs : http://localhost:8010/docs"
Start-Process "http://localhost:$port"
