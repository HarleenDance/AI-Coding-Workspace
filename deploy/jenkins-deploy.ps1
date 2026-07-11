param(
  [switch]$NoCache,
  [string]$BackendImage = "app-backend:latest",
  [string]$FrontendImage = "app-frontend:latest"
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
  Write-Host ""
  Write-Host "==== $Message ====" -ForegroundColor Cyan
}

function Test-CommandExists([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Command '$Name' not found. Please install it and make sure it is in PATH."
  }
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

Write-Step "Checking required commands"
Test-CommandExists "docker"
docker --version
docker compose version

Write-Step "Preparing .env"
$EnvFile = Join-Path $RepoRoot ".env"
$EnvExample = Join-Path $RepoRoot ".env.example"
if (-not (Test-Path $EnvFile)) {
  if (Test-Path $EnvExample) {
    Copy-Item $EnvExample $EnvFile
    Write-Host "Created .env from .env.example. Please fill API keys in Jenkins credentials or .env for real AI calls." -ForegroundColor Yellow
  } else {
    @"
DB_PASSWORD=change_this_password
DEEPSEEK_API_KEY=
DASHSCOPE_API_KEY=
"@ | Set-Content -Path $EnvFile -Encoding UTF8
    Write-Host "Created default .env." -ForegroundColor Yellow
  }
}

if ($env:DB_PASSWORD) {
  "DB_PASSWORD=$env:DB_PASSWORD" | Set-Content -Path $EnvFile -Encoding UTF8
  "DEEPSEEK_API_KEY=$env:DEEPSEEK_API_KEY" | Add-Content -Path $EnvFile -Encoding UTF8
  "DASHSCOPE_API_KEY=$env:DASHSCOPE_API_KEY" | Add-Content -Path $EnvFile -Encoding UTF8
  Write-Host "Wrote .env from Jenkins environment variables."
}

$BuildArgs = @()
if ($NoCache) {
  $BuildArgs += "--no-cache"
}

Write-Step "Building backend image"
docker build @BuildArgs -f deploy/backend.Dockerfile -t $BackendImage aI-coding-workspace-backend

Write-Step "Building frontend image"
docker build @BuildArgs -t $FrontendImage aI-coding-workspace-frontend

Write-Step "Cleaning up old containers"
docker rm -f ai-ide-db ai-ide-backend ai-ide-frontend 2>$null | Out-Null

Write-Step "Starting services"
docker compose up -d db
docker compose up -d backend frontend

Write-Step "Service status"
docker compose ps

Write-Step "Backend health check"
# Jenkins runs inside Docker; use host.docker.internal to reach host-mapped ports
$HealthUrl = "http://host.docker.internal:8000/api/health/db"
if (-not (Test-Connection -ComputerName "host.docker.internal" -Count 1 -Quiet -ErrorAction SilentlyContinue)) {
  $HealthUrl = "http://localhost:8000/api/health/db"
}
$Healthy = $false
for ($i = 1; $i -le 30; $i++) {
  try {
    $Response = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 5
    if ($Response.StatusCode -eq 200) {
      $Healthy = $true
      Write-Host "Backend is healthy: $HealthUrl" -ForegroundColor Green
      break
    }
  } catch {
    Start-Sleep -Seconds 3
  }
}

if (-not $Healthy) {
  Write-Host "Backend health check failed. Recent backend logs:" -ForegroundColor Yellow
  docker compose logs --tail=120 backend
  throw "Backend did not become healthy in time."
}

Write-Step "Deployment finished"
Write-Host "Frontend: http://localhost/" -ForegroundColor Green
Write-Host "Backend API: http://localhost:8000/api" -ForegroundColor Green
Write-Host "Database: internal (db:5432)" -ForegroundColor Green
