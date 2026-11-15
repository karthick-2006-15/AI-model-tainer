@echo off
title PROJECT JARVIS // MARK VII
cls
echo ==========================================================
echo                PROJECT JARVIS // MARK VII                
echo      Personal AI Operating System - Subsystems Boot       
echo ==========================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_jarvis.ps1"
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] JARVIS failed to launch or exited with an error.
    pause
)
