# JARVIS Background Service Launcher
$ProjectRoot = "C:\Users\karth\OneDrive\Desktop\sanju"
Set-Location -Path $ProjectRoot

# Ensure logs directory exists
if (-not (Test-Path "$ProjectRoot\storage\logs")) {
    New-Item -ItemType Directory -Path "$ProjectRoot\storage\logs" -Force | Out-Null
}

$LogFile = "$ProjectRoot\storage\logs\jarvis_service.log"
$ErrorLog = "$ProjectRoot\storage\logs\jarvis_error.log"

# Check if already running on port 8000
$portCheck = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($portCheck) {
    Add-Content -Path $LogFile -Value "JARVIS is already running on port 8000 (PID: $($portCheck[0].OwningProcess))."
    exit 0
}

Add-Content -Path $LogFile -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting JARVIS AI Operating System Background Service..."

# Launch Uvicorn silently with Voice Listener active
Start-Process -FilePath "python" `
    -ArgumentList "-m uvicorn api.main:app --host 127.0.0.1 --port 8000" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError $ErrorLog

Add-Content -Path $LogFile -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] JARVIS Background Service launched successfully."
