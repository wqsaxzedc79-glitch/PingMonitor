@echo off
chcp 65001 > nul
title PingMonitor - EXE Build

echo ============================================================
echo   PingMonitor EXE Builder
echo   Python required for build only.
echo   Output EXE runs on any Windows PC without Python.
echo ============================================================
echo.

:: Python 탐색 (실행 bat와 동일 로직)
set PYTHON_EXE=

python --version > nul 2>&1
if %errorlevel% equ 0 ( set PYTHON_EXE=python & goto :py_found )

py --version > nul 2>&1
if %errorlevel% equ 0 ( set PYTHON_EXE=py & goto :py_found )

for /d %%P in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%P\python.exe" ( set "PYTHON_EXE=%%P\python.exe" & goto :py_found )
)

for /d %%P in ("C:\Python3*" "C:\Program Files\Python3*") do (
    if exist "%%P\python.exe" ( set "PYTHON_EXE=%%P\python.exe" & goto :py_found )
)

echo [ERROR] Python not found.
echo Install: https://www.python.org/downloads/
pause
exit /b 1

:py_found
echo   Python: %PYTHON_EXE%
echo.

echo [1/4] Installing PyInstaller and dependencies...
%PYTHON_EXE% -m pip install pyinstaller psutil openpyxl
echo.

echo [2/4] Generating icon...
%PYTHON_EXE% generate_icon.py
echo.

echo [3/4] Building EXE (1-3 minutes)...
pyinstaller --onefile ^
            --windowed ^
            --name "PingMonitor" ^
            --icon app_icon.ico ^
            --hidden-import psutil ^
            --hidden-import psutil._psutil_windows ^
            --hidden-import psutil._psutil_common ^
            --hidden-import core ^
            --hidden-import startup ^
            --add-data "core.py;." ^
            --add-data "startup.py;." ^
            --collect-all psutil ^
            --collect-all openpyxl ^
            ping_monitor_gui.py
echo.

echo [4/4] Copying output...
if exist "dist\PingMonitor.exe" (
    copy /y "dist\PingMonitor.exe" "PingMonitor.exe" > nul
    echo.
    echo ============================================================
    echo   BUILD SUCCESS
    echo.
    echo   PingMonitor.exe  <- copy this to any Windows PC
    echo   No Python needed on target PC.
    echo ============================================================
) else (
    echo [ERROR] Build failed.
)

echo.
pause
