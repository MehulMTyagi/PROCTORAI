param(
  [switch]$SkipSeed,
  [switch]$KeepExisting,
  [string]$DatabaseUrl = "sqlite+pysqlite:///C:/git/PROCTORAI/services/api/data/proctorai-local.db"
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ApiDir = Join-Path $RepoRoot "services\api"
$AiDir = Join-Path $RepoRoot "services\ai-engine"
$DataDir = Join-Path $ApiDir "data"
$LogDir = Join-Path $RepoRoot "data\logs"
$ApiBase = "http://127.0.0.1:8010"
$AiBase = "http://127.0.0.1:8765"
$WebBase = "http://127.0.0.1:5173"
$CandidateBase = "http://127.0.0.1:5174"

function Stop-LocalPorts {
  foreach ($port in @(8010, 8765, 5173, 5174)) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
      $processId = $connection.OwningProcess
      if ($processId -gt 0) {
        Write-Host "Stopping process $processId on port $port"
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
      }
    }
  }
}

function Wait-ForUrl {
  param(
    [string]$Url,
    [int]$TimeoutSeconds = 45
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    try {
      $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
        return
      }
    } catch {
      Start-Sleep -Milliseconds 750
    }
  } while ((Get-Date) -lt $deadline)

  throw "Timed out waiting for $Url"
}

function Start-LocalProcess {
  param(
    [string]$Name,
    [string]$FilePath,
    [string[]]$ArgumentList,
    [string]$WorkingDirectory,
    [hashtable]$Environment = @{}
  )

  $previousEnvironment = @{}
  foreach ($key in $Environment.Keys) {
    $previousEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
    [Environment]::SetEnvironmentVariable($key, [string]$Environment[$key], "Process")
  }

  $safeName = ($Name.ToLowerInvariant() -replace "[^a-z0-9]+", "-").Trim("-")
  $stdout = Join-Path $LogDir "$safeName.out.log"
  $stderr = Join-Path $LogDir "$safeName.err.log"

  Write-Host "Starting $Name"
  try {
    Start-Process -FilePath $FilePath `
      -ArgumentList $ArgumentList `
      -WorkingDirectory $WorkingDirectory `
      -WindowStyle Hidden `
      -RedirectStandardOutput $stdout `
      -RedirectStandardError $stderr | Out-Null
  } finally {
    foreach ($key in $Environment.Keys) {
      [Environment]::SetEnvironmentVariable($key, $previousEnvironment[$key], "Process")
    }
  }
}

New-Item -ItemType Directory -Force -Path $DataDir, $LogDir | Out-Null

if (-not $KeepExisting) {
  Stop-LocalPorts
}

$env:PYTHONPATH = $ApiDir
$env:DATABASE_URL = $DatabaseUrl

Push-Location $ApiDir
try {
  Write-Host "Migrating local SQLite database"
  python -m alembic upgrade head
  if (-not $SkipSeed) {
    Write-Host "Seeding development users and assessment"
    python -m app.db.seed
  }
} finally {
  Pop-Location
}

Start-LocalProcess `
  -Name "API" `
  -FilePath "python" `
  -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8010") `
  -WorkingDirectory $ApiDir `
  -Environment @{ PYTHONPATH = $ApiDir; DATABASE_URL = $DatabaseUrl }

Start-LocalProcess `
  -Name "AI sidecar" `
  -FilePath "python" `
  -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8765") `
  -WorkingDirectory $AiDir `
  -Environment @{ PYTHONPATH = $AiDir }

Start-LocalProcess `
  -Name "Web portal" `
  -FilePath "npm.cmd" `
  -ArgumentList @("--workspace", "@proctorai/web-portal", "run", "dev") `
  -WorkingDirectory $RepoRoot `
  -Environment @{ VITE_API_BASE_URL = $ApiBase }

Start-LocalProcess `
  -Name "Candidate portal" `
  -FilePath "npm.cmd" `
  -ArgumentList @("--workspace", "@proctorai/candidate-desktop", "run", "dev") `
  -WorkingDirectory $RepoRoot `
  -Environment @{ VITE_API_BASE_URL = $ApiBase; VITE_AI_ENGINE_URL = $AiBase }

Wait-ForUrl "$ApiBase/health" 90
Wait-ForUrl "$AiBase/health" 90
Wait-ForUrl $WebBase 90
Wait-ForUrl $CandidateBase 90

Write-Host ""
Write-Host "ProctorAI local stack is ready:"
Write-Host "  API:       $ApiBase"
Write-Host "  AI:        $AiBase"
Write-Host "  Proctor:   $WebBase"
Write-Host "  Candidate: $CandidateBase/#/assessments"
Write-Host "  Logs:      $LogDir"

& (Join-Path $PSScriptRoot "check-local.ps1")
if ($LASTEXITCODE -ne 0) {
  throw "Local ProctorAI stack started, but smoke checks failed. See $LogDir."
}
