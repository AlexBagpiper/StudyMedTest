@echo off
setlocal enabledelayedexpansion
title MedTest Platform - Stopping Services
color 0C

echo ========================================
echo   MedTest Platform - Shutdown
echo ========================================
echo.

echo Stopping all services and closing windows...
echo.

:: Method 1: Stop by window titles (closes console windows)
echo [1/4] Stopping MinIO window...
taskkill /F /FI "WINDOWTITLE eq MedTest-MinIO*" /T 2>nul
if %errorlevel% equ 0 (echo     [OK] MinIO window closed) else (echo     [--] MinIO window not found)

echo [2/4] Stopping Backend window...
taskkill /F /FI "WINDOWTITLE eq MedTest-Backend*" /T 2>nul
if %errorlevel% equ 0 (echo     [OK] Backend window closed) else (echo     [--] Backend window not found)

echo [3/4] Stopping Celery window...
taskkill /F /FI "WINDOWTITLE eq MedTest-Celery*" /T 2>nul
if %errorlevel% equ 0 (echo     [OK] Celery window closed) else (echo     [--] Celery window not found)

echo [4/4] Stopping Frontend window...
taskkill /F /FI "WINDOWTITLE eq MedTest-Frontend*" /T 2>nul
if %errorlevel% equ 0 (echo     [OK] Frontend window closed) else (echo     [--] Frontend window not found)

:: Method 2: Kill processes by name (if windows were closed manually)
echo.
echo Additional cleanup by process name...
set cleaned=0

taskkill /F /IM minio.exe /T 2>nul
if %errorlevel% equ 0 set cleaned=1

taskkill /F /IM uvicorn.exe /T 2>nul
if %errorlevel% equ 0 set cleaned=1

taskkill /F /IM celery.exe /T 2>nul
if %errorlevel% equ 0 set cleaned=1

:: Kill Node.js on port 5173
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| find ":5173" ^| find "LISTENING"') do (
    taskkill /F /PID %%a /T 2>nul
    if !errorlevel! equ 0 set cleaned=1
)

:: Kill Python processes from StudyMedTest
for /f "tokens=2" %%a in ('wmic process where "commandline like '%%StudyMedTest%%' and name='python.exe'" get processid 2^>nul ^| find /v "ProcessId"') do (
    taskkill /F /PID %%a /T 2>nul
    if !errorlevel! equ 0 set cleaned=1
)

if %cleaned% equ 1 (echo     [OK] Additional processes cleaned) else (echo     [--] No additional processes found)

echo.
echo ========================================
echo   All services stopped!
echo   All console windows closed!
echo ========================================
echo.
pause

