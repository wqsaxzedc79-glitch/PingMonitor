@echo off
chcp 65001 > nul
title Ping Monitor v2

python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python not found.
    echo Install Python: https://www.python.org/downloads/
    echo Check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

python -c "import psutil" > nul 2>&1
if %errorlevel% neq 0 (
    echo Installing psutil...
    pip install psutil
)

python -c "import openpyxl" > nul 2>&1
if %errorlevel% neq 0 (
    echo Installing openpyxl...
    pip install openpyxl
)

python "%~dp0ping_monitor_gui.py"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Program exited with an error.
    pause
)
