@echo off
chcp 65001 > nul
title PingMonitor - EXE Build

echo ============================================================
echo   PingMonitor EXE Builder
echo   Python is required only for building.
echo   The output EXE runs on any Windows PC without Python.
echo ============================================================
echo.

:: Python 확인
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    echo Install: https://www.python.org/downloads/
    echo Check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [1/4] Installing PyInstaller and dependencies...
pip install pyinstaller psutil openpyxl
echo.

echo [2/4] Generating icon...
python generate_icon.py
echo.

echo [3/4] Building EXE (this may take 1-2 minutes)...
pyinstaller --onefile ^
            --windowed ^
            --name "PingMonitor" ^
            --icon app_icon.ico ^
            --hidden-import psutil ^
            --hidden-import psutil._psutil_windows ^
            --hidden-import psutil._psutil_common ^
            --collect-all psutil ^
            --collect-all openpyxl ^
            ping_monitor_gui.py
echo.

echo [4/4] Copying output...
if exist "dist\PingMonitor.exe" (
    copy /y "dist\PingMonitor.exe" "PingMonitor.exe" > nul
    echo.
    echo ============================================================
    echo   BUILD SUCCESS!
    echo.
    echo   Output: PingMonitor\PingMonitor.exe
    echo.
    echo   [배포 방법]
    echo   PingMonitor.exe 파일 하나만 복사하면 됩니다.
    echo   어떤 Windows PC에서도 Python 없이 실행 가능합니다.
    echo ============================================================
) else (
    echo.
    echo [ERROR] Build failed. Check the output above for errors.
)

echo.
echo Build temp files (build\, dist\, *.spec) are kept.
echo You can delete them manually if not needed.
echo.
pause
