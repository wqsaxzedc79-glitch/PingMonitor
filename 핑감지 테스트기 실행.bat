@echo off
chcp 65001 > nul
title Ping Monitor v2

set PYTHON_EXE=

:: 1. PATH - python
python --version > nul 2>&1
if %errorlevel% equ 0 ( set PYTHON_EXE=python & goto :found )

:: 2. Python Launcher (py.exe) - PATH 없어도 설치됨
py --version > nul 2>&1
if %errorlevel% equ 0 ( set PYTHON_EXE=py & goto :found )

:: 3. 사용자 설치 경로 (%LOCALAPPDATA%)
for /d %%P in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%P\python.exe" ( set "PYTHON_EXE=%%P\python.exe" & goto :found )
)

:: 4. 시스템 전체 설치 경로
for /d %%P in ("C:\Python3*" "C:\Python\Python3*" "C:\Program Files\Python3*") do (
    if exist "%%P\python.exe" ( set "PYTHON_EXE=%%P\python.exe" & goto :found )
)

:: 5. Windows Store Python
for /d %%P in ("%LOCALAPPDATA%\Microsoft\WindowsApps") do (
    if exist "%%P\python3.exe" ( set "PYTHON_EXE=%%P\python3.exe" & goto :found )
)

:: Python 없음 - 상세 안내
echo.
echo ============================================================
echo   [ERROR] Python not found on this PC.
echo ============================================================
echo.
echo   Option 1 - Install Python (recommended):
echo   1. https://www.python.org/downloads/
echo   2. Click "Download Python 3.x.x"
echo   3. CHECK [Add Python to PATH] at the bottom
echo   4. Complete installation, then run this file again.
echo.
echo   Option 2 - Use EXE (no Python needed):
echo   On a PC that HAS Python, run:  build.bat
echo   This creates PingMonitor.exe which runs anywhere.
echo   Copy only PingMonitor.exe to this PC.
echo.
echo ============================================================
echo.
pause
exit /b 1

:found
echo   Python: %PYTHON_EXE%

:: psutil
%PYTHON_EXE% -c "import psutil" > nul 2>&1
if %errorlevel% neq 0 (
    echo   Installing psutil...
    %PYTHON_EXE% -m pip install psutil
)

:: openpyxl
%PYTHON_EXE% -c "import openpyxl" > nul 2>&1
if %errorlevel% neq 0 (
    echo   Installing openpyxl...
    %PYTHON_EXE% -m pip install openpyxl
)

:: 실행
%PYTHON_EXE% "%~dp0ping_monitor_gui.py"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Program exited with an error. Check logs\system_error.log
    pause
)
