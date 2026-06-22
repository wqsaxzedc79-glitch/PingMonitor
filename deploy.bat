@echo off
chcp 65001 > nul
title PingMonitor - Deploy

echo ============================================================
echo   PingMonitor Deploy Script
echo   Creates a clean deployment package in: deploy\
echo ============================================================
echo.

:: Python 확인
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    pause
    exit /b 1
)

:: 배포 폴더 초기화
if exist "deploy" rmdir /s /q "deploy"
mkdir "deploy"
mkdir "deploy\logs"
mkdir "deploy\reports"

:: 필수 파일 복사
echo [1/3] Copying source files...
copy /y "ping_monitor_gui.py"      "deploy\ping_monitor_gui.py"     > nul
copy /y "core.py"                  "deploy\core.py"                 > nul
copy /y "startup.py"               "deploy\startup.py"              > nul
copy /y "핑감지 테스트기 실행.bat"  "deploy\핑감지 테스트기 실행.bat" > nul
copy /y "requirements.txt"         "deploy\requirements.txt"        > nul
copy /y "README.md"                "deploy\README.md"               > nul

:: config.json - log_dir 없는 기본값 사용
echo [2/3] Creating default config.json...
(
echo {
echo   "targets": [
echo     {"name": "설비 IP", "host": "192.168.0.101", "role": "equipment"},
echo     {"name": "서버",    "host": "hidc.cps.org",  "role": "server"}
echo   ],
echo   "interval": 5,
echo   "retention_days": 30,
echo   "fault_policy": {
echo     "suspect_fail_count": 3,
echo     "fault_fail_count": 5,
echo     "recovery_success_count": 3
echo   }
echo }
) > "deploy\config.json"

:: logs README
echo.> "deploy\logs\README.txt"
echo reports 폴더에 일별 요약 보고서가 저장됩니다.> "deploy\reports\README.txt"

echo [3/3] Done.
echo.
echo ============================================================
echo   [배포 폴더 구조]
echo   deploy\
echo   +-- ping_monitor_gui.py   (메인 프로그램)
echo   +-- core.py               (핵심 모듈)
echo   +-- startup.py            (자동 실행/트레이)
echo   +-- 핑감지 테스트기 실행.bat
echo   +-- config.json           (설정)
echo   +-- requirements.txt
echo   +-- README.md
echo   +-- logs\                 (로그 자동 생성)
echo   +-- reports\              (일별 보고서 자동 생성)
echo.
echo   [다른 PC 설치]
echo   1. deploy 폴더 전체 복사
echo   2. 핑감지 테스트기 실행.bat 더블클릭
echo ============================================================
echo.
echo EXE 빌드가 필요하면 build.bat을 실행하세요.
pause
