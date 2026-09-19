@echo off
chcp 65001 >nul
title MediMind AI - 스마트 복약 관리 시스템

echo ======================================================================
echo    MediMind AI - 스마트 복약 스케줄러 및 약물 상호작용 알림 시스템
echo ======================================================================
echo.

cd /d "%~dp0"

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [오류] Python이 설치되어 있지 않거나 PATH 환경변수에 등록되어 있지 않습니다.
    echo Python 3.8 이상을 설치한 후 다시 시도해 주세요.
    echo.
    pause
    exit /b 1
)

echo [*] MediMind AI 서비스를 시작합니다...
python start_service.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] 서비스 실행 중 오류가 발생했습니다. (오류 코드: %ERRORLEVEL%)
    pause
)
