@echo off
setlocal

rem The live preview must fit on the desktop. Final export resolution is chosen
rem separately inside the tuning panel (Full HD / 2K / 4K).
set "PREVIEW_WIDTH=1280"
set "PREVIEW_HEIGHT=720"

set "PROJECT_DIR=%~dp0"
set "GODOT_GUI=C:\Users\BAZA\Documents\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe"

if not exist "%GODOT_GUI%" (
    where godot.exe >nul 2>nul
    if errorlevel 1 (
        echo Godot GUI not found.
        echo Expected: %GODOT_GUI%
        pause
        exit /b 1
    )
    set "GODOT_GUI=godot.exe"
)

start "Neon Music Visual Tuning" "%GODOT_GUI%" --path "%PROJECT_DIR%." --resolution %PREVIEW_WIDTH%x%PREVIEW_HEIGHT% -- --render-clock=audio

endlocal
