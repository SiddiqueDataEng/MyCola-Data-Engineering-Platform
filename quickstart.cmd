@echo off
REM MyCola Data Generator — Windows Quick Start Script

echo ========================================
echo MyCola Data Generator — Quick Start
echo ========================================
echo.

echo [1/3] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.8+ first.
    pause
    exit /b 1
)
python --version
echo.

echo [2/3] Installing dependencies...
pip install -q -r data_generator\requirements.txt
if %errorlevel% neq 0 (
    echo WARNING: Dependency installation had warnings. Continuing...
)
echo Dependencies installed.
echo.

echo [3/3] Launching Data Generator GUI...
python run_data_generator.py

pause
