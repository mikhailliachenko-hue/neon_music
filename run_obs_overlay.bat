@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "GODOT_GUI=C:\Users\BAZA\Documents\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe"

if not exist "%GODOT_GUI%" (
    where godot.exe >nul 2>nul
    if errorlevel 1 (
        echo Godot GUI not found.
        echo Expected: %GODOT_GUI%
        echo Install Godot or add godot.exe to PATH, then run this file again.
        pause
        exit /b 1
    )
    set "GODOT_GUI=godot.exe"
)

start "Neon Music OBS Overlay" "%GODOT_GUI%" --path "%PROJECT_DIR%." --resolution 2560x1440 -- --obs-overlay --render-clock=audio --no-tuning-gui

endlocal
