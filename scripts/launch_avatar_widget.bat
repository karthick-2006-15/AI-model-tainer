@echo off
set SCRIPT_DIR=%~dp0
set USER_DATA=c:\Users\karth\OneDrive\Desktop\sanju\.avatar_chrome_data
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app="http://localhost:5173/?mode=widget" --user-data-dir="%USER_DATA%" --window-size=370,470 --window-position=1140,340 --disable-features=Translate,OptimizationHints --no-first-run
exit /b 0
