# =====================================================================
# JARVIS — Single Command Startup Script for Windows
# Launches both the FastAPI Backend and the React Holographic HUD.
# =====================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "               PROJECT JARVIS // MARK VII                " -ForegroundColor Cyan
Write-Host "     Personal AI Operating System - Subsystems Boot       " -ForegroundColor DarkCyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Set working directory to project root
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# Verify Python
Write-Host "[1/3] Verifying Python Runtime..." -ForegroundColor Yellow
$py = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python 3.10+ is required." -ForegroundColor Red
    exit 1
}
Write-Host "      Detected: $py" -ForegroundColor Green

# Verify Database
Write-Host "[2/3] Checking Database Integrity..." -ForegroundColor Yellow
python -c "from storage.db.connection import init_db; init_db(); print('      Database tables verified.')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to initialize SQLite database." -ForegroundColor Red
    exit 1
}

# Launching Services
Write-Host "[3/3] Launching Subsystems..." -ForegroundColor Yellow
Write-Host "      FastAPI Core:  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "      Interactive Docs: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "      Holographic HUD: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to shutdown all subsystems." -ForegroundColor DarkGray

# Start Backend in Background Process
$BackendJob = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload" -PassThru

# Start UI in Foreground
Set-Location "$ProjectRoot\ui"
try {
    npm run dev
} finally {
    Write-Host ""
    Write-Host "Shutting down JARVIS subsystems..." -ForegroundColor Yellow
    if ($BackendJob -and -not $BackendJob.HasExited) {
        Stop-Process -Id $BackendJob.Id -Force
        Write-Host "JARVIS Core stopped cleanly." -ForegroundColor Green
    }
}
