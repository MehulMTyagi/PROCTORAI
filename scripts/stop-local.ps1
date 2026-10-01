param(
  [int[]]$Ports = @(8010, 8765, 5173, 5174)
)

$ErrorActionPreference = "Stop"

foreach ($port in $Ports) {
  $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  foreach ($connection in $connections) {
    $processId = $connection.OwningProcess
    if ($processId -gt 0) {
      Write-Host "Stopping process $processId on port $port"
      Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
  }
}

Write-Host "Local ProctorAI ports are clear."
