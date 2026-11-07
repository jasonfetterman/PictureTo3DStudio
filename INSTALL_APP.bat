@echo off
cd /d "%~dp0"
py -3.11 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo.
echo Base application installed. Next follow INSTALL_AI_WINDOWS.md to install the AI engine.
pause
exit /b 0
:fail
echo Installation failed. Install Python 3.11 x64 and try again.
pause
exit /b 1
