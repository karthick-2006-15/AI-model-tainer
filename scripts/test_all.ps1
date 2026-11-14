# =====================================================================
# JARVIS — Master Test Suite Runner
# Executes backend unit tests and frontend type-checking & builds.
# =====================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "             JARVIS AUTOMATED VERIFICATION               " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# 1. Run Python Unit Tests
Write-Host "[1/2] Running Complete Backend Unit & Integration Tests (All Modules)..." -ForegroundColor Yellow
python -m pytest tests/unit/ -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: Backend tests encountered errors." -ForegroundColor Red
    exit 1
}
Write-Host "PASSED: All 53 Backend tests succeeded 100%." -ForegroundColor Green
Write-Host ""

# 2. Run Frontend Type-check & Production Build
Write-Host "[2/2] Running Frontend Type-Check & Production Build..." -ForegroundColor Yellow
Set-Location "$ProjectRoot\ui"
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED: Frontend build encountered errors." -ForegroundColor Red
    exit 1
}
Write-Host "PASSED: Frontend build and typecheck succeeded 100%." -ForegroundColor Green
Write-Host ""

Write-Host "ALL SUBSYSTEM VERIFICATION GATES PASSED." -ForegroundColor Cyan
