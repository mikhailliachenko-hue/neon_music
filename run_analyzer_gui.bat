@echo off
setlocal
cd /d "%~dp0"
set "PROJECT_VENV=%~dp0..\.venv\Scripts\python.exe"
if exist "%PROJECT_VENV%" (
  "%PROJECT_VENV%" "%~dp0scripts\python\analyzer_gui.py" %*
  exit /b %errorlevel%
)
set "LOCAL_VENV=%~dp0.venv\Scripts\python.exe"
if exist "%LOCAL_VENV%" (
  "%LOCAL_VENV%" "%~dp0scripts\python\analyzer_gui.py" %*
  exit /b %errorlevel%
)
set "BUNDLED_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED_PY%" (
  "%BUNDLED_PY%" "%~dp0scripts\python\analyzer_gui.py" %*
  exit /b %errorlevel%
)
where python >nul 2>nul
if %errorlevel%==0 (
  python "%~dp0scripts\python\analyzer_gui.py" %*
  exit /b %errorlevel%
)
echo Python was not found. Install Python 3.10+ and librosa, then run this file again.
pause