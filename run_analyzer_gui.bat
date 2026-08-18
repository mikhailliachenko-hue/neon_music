@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "LOCAL_VENV=%~dp0.venv\Scripts\python.exe"
set "PARENT_VENV=%~dp0..\.venv\Scripts\python.exe"
set "POV_NEON_VENV=%~dp0..\pov_neon\.venv\Scripts\python.exe"
set "BUNDLED_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

set "ANALYZER_PY="
call :select_python "%LOCAL_VENV%"
if defined ANALYZER_PY goto launch
call :select_python "%PARENT_VENV%"
if defined ANALYZER_PY goto launch
call :select_python "%POV_NEON_VENV%"
if defined ANALYZER_PY goto launch
call :select_python "%BUNDLED_PY%"
if defined ANALYZER_PY goto launch

where python >nul 2>nul
if not errorlevel 1 call :select_python "python"
if defined ANALYZER_PY goto launch

echo.
echo ERROR: A compatible analyzer Python environment was not found.
echo Required modules: tkinter, librosa, numpy and scipy.
echo Checked the local project, parent folder, pov_neon and bundled Python.
echo See requirements.txt or create .venv inside this project.
pause
exit /b 1

:launch
echo Using Python: %ANALYZER_PY%
echo Checking NVIDIA GPU support...
"%ANALYZER_PY%" -c "import torch; assert torch.cuda.is_available(); x=torch.ones(1,device='cuda'); torch.cuda.synchronize()" >nul 2>nul
if not errorlevel 1 goto open_gui

where nvidia-smi >nul 2>nul
if errorlevel 1 goto cpu_fallback
nvidia-smi -L >nul 2>nul
if errorlevel 1 goto cpu_fallback

echo NVIDIA GPU found. Installing PyTorch CUDA automatically.
echo This is a one-time large download; the analyzer will open when it finishes.
"%ANALYZER_PY%" -m pip install --upgrade --force-reinstall --no-deps "torch==2.12.1" --index-url https://download.pytorch.org/whl/cu130
if errorlevel 1 goto cpu_fallback
"%ANALYZER_PY%" -c "import torch; assert torch.cuda.is_available(), 'CUDA is not available'; x=torch.randn((1024,1024),device='cuda'); y=x@x; torch.cuda.synchronize(); print('GPU READY:',torch.cuda.get_device_name(0),'| torch',torch.__version__,'| CUDA',torch.version.cuda,'| check',float(y[0,0]))"
if errorlevel 1 goto cpu_fallback
goto open_gui

:cpu_fallback
echo GPU is unavailable. Starting the analyzer in CPU mode.

:open_gui
"%ANALYZER_PY%" "%~dp0scripts\python\analyzer_gui.py" %*
set "ANALYZER_EXIT=%errorlevel%"
if not "%ANALYZER_EXIT%"=="0" (
  echo.
  echo ERROR: Analyzer GUI exited with code %ANALYZER_EXIT%.
  pause
)
exit /b %ANALYZER_EXIT%

:select_python
set "PYTHON_CANDIDATE=%~1"
if /i not "%PYTHON_CANDIDATE%"=="python" if not exist "%PYTHON_CANDIDATE%" exit /b 0
"%PYTHON_CANDIDATE%" -c "import tkinter, librosa, numpy, scipy" >nul 2>nul
if errorlevel 1 exit /b 0
set "ANALYZER_PY=%PYTHON_CANDIDATE%"
exit /b 0
