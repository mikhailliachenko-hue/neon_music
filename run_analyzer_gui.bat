@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "PROJECT_VENV=%~dp0..\.venv\Scripts\python.exe"
if exist "%PROJECT_VENV%" (
  set "ANALYZER_PY=%PROJECT_VENV%"
  goto launch
)
set "LOCAL_VENV=%~dp0.venv\Scripts\python.exe"
if exist "%LOCAL_VENV%" (
  set "ANALYZER_PY=%LOCAL_VENV%"
  goto launch
)
set "BUNDLED_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED_PY%" (
  set "ANALYZER_PY=%BUNDLED_PY%"
  goto launch
)
where python >nul 2>nul
if %errorlevel%==0 (
  set "ANALYZER_PY=python"
  goto launch
)
echo Python was not found. Install Python 3.10+ and librosa, then run this file again.
pause
exit /b 1

:launch
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
exit /b %errorlevel%
