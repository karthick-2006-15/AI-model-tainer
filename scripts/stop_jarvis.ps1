# Stop JARVIS Background Processes
Write-Host "Stopping JARVIS AI Operating System services..." -ForegroundColor Yellow

# Find process listening on port 8000
$portConnections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($portConnections) {
    foreach ($conn in $portConnections) {
        $procId = $conn.OwningProcess
        try {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Write-Host "Terminated process $procId on port 8000." -ForegroundColor Green
        } catch {}
    }
} else {
    Write-Host "No active JARVIS server detected on port 8000." -ForegroundColor Gray
}

Write-Host "JARVIS services stopped." -ForegroundColor White
