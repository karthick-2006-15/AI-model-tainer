@echo off
title JARVIS Floating Desktop Avatar
echo [JARVIS] Launching Floating Desktop Avatar Widget...
cd /d "%~dp0\.."
start "" python scripts\run_floating_avatar.py
exit
