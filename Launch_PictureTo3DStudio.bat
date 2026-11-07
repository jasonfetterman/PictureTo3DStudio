@echo off
title Picture to 3D Model Studio

cd /d "C:\PictureTo3DStudio_MVP\PictureTo3DStudio"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment not found.
    pause
    exit /b 1
)

if not exist "app\main.py" (
    echo ERROR: Application entry point not found.
    pause
    exit /b 1
)

echo Starting Picture to 3D Model Studio...
echo GPU: NVIDIA RTX 3050 Ti
echo.

".venv\Scripts\python.exe" -m app.main

if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
