param(
  [string]$ApiBase = "http://127.0.0.1:8010",
  [string]$AiBase = "http://127.0.0.1:8765",
  [string]$WebBase = "http://127.0.0.1:5173",
  [string]$CandidateBase = "http://127.0.0.1:5174"
)

$ErrorActionPreference = "Stop"

function Test-Url {
  param([string]$Url)

  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 15
    [pscustomobject]@{ Url = $Url; Status = $response.StatusCode; Ok = $true }
  } catch {
    [pscustomobject]@{ Url = $Url; Status = $_.Exception.Message; Ok = $false }
  }
}

$checks = @(
  Test-Url "$ApiBase/health"
  Test-Url "$AiBase/health"
  Test-Url $WebBase
  Test-Url $CandidateBase
)

$loginOk = $false
$assessmentCount = 0
$firstAssessment = $null
try {
  $loginBody = @{ email = "candidate@example.com"; password = "password123" } | ConvertTo-Json
  $login = Invoke-RestMethod "$ApiBase/auth/login" -Method Post -ContentType "application/json" -TimeoutSec 15 -Body $loginBody
  $assessments = Invoke-RestMethod "$ApiBase/assessments" -TimeoutSec 15 -Headers @{ Authorization = "Bearer $($login.access_token)" }
  $assessmentList = @($assessments)
  $loginOk = $true
  $assessmentCount = $assessmentList.Count
  if ($assessmentCount -gt 0) {
    $firstAssessment = $assessmentList[0].title
  }
} catch {
  $firstAssessment = $_.Exception.Message
}

$result = [pscustomobject]@{
  Services = $checks
  CandidateLoginOk = $loginOk
  AssessmentCount = $assessmentCount
  FirstAssessment = $firstAssessment
}

$result | ConvertTo-Json -Depth 5

if (($checks | Where-Object { -not $_.Ok }).Count -gt 0 -or -not $loginOk -or $assessmentCount -lt 1) {
  exit 1
}
