@echo off
REM CNC Bridge — Quick Start Script for Windows
REM Installs dependencies and launches the application

echo.
echo  ======================================
echo   CNC Bridge - Anilam Crusader M
echo  ======================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo Starting CNC Bridge...
echo.

python -m src.main

pause
