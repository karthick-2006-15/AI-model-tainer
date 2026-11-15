' JARVIS Silent Background Launcher
' Executes PowerShell script with completely hidden window
Set WshShell = CreateObject("WScript.Shell")
strCommand = "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File ""C:\Users\karth\OneDrive\Desktop\sanju\scripts\start_jarvis_background.ps1"""
WshShell.Run strCommand, 0, False
Set WshShell = Nothing
