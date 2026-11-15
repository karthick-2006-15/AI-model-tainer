# Setup JARVIS Always-On Windows Auto-Start
$StartupFolder = [Environment]::GetFolderPath('Startup')
$VbsScriptPath = "C:\Users\karth\OneDrive\Desktop\sanju\scripts\run_jarvis_silent.vbs"
$ShortcutPath = Join-Path -Path $StartupFolder -ChildPath "JARVIS_Always_On.lnk"

Write-Host "Configuring JARVIS to launch automatically on Windows boot..." -ForegroundColor Cyan
Write-Host "Target Startup Folder: $StartupFolder" -ForegroundColor Gray

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = "`"$VbsScriptPath`""
$Shortcut.WorkingDirectory = "C:\Users\karth\OneDrive\Desktop\sanju"
$Shortcut.Description = "JARVIS Personal AI Operating System Always-On Voice Service"
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll, 15"
$Shortcut.Save()

if (Test-Path $ShortcutPath) {
    Write-Host "[SUCCESS] JARVIS Auto-Start configured successfully!" -ForegroundColor Green
    Write-Host "Whenever you turn on or log in to your laptop, JARVIS will start automatically in the background." -ForegroundColor White
    Write-Host "Say 'Hey Jarvis' at any time to communicate via voice!" -ForegroundColor Yellow
} else {
    Write-Error "Failed to create startup shortcut."
}
