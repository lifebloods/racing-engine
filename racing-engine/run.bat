@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in your PATH.
    echo Please install Python 3.11+ from https://www.python.org
    echo During installation, check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Starting Flask app at http://localhost:5000
echo Press Ctrl+C to stop.
echo.
python run.py

if errorlevel 1 (
    echo.
    echo App encountered an error.
    pause
)
