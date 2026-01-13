@echo off
title MedTest Platform - Остановка сервисов
color 0C

echo ========================================
echo   MedTest Platform - Остановка
echo ========================================
echo.

echo Остановка всех сервисов...
echo.

:: Остановка по заголовкам окон
echo [1/4] Остановка MinIO Server...
taskkill /F /FI "WINDOWTITLE eq MinIO*" /T 2>nul
if %errorlevel% equ 0 (echo    - MinIO остановлен) else (echo    - MinIO не запущен)

echo [2/4] Остановка Backend API...
taskkill /F /FI "WINDOWTITLE eq Backend*" /T 2>nul
if %errorlevel% equ 0 (echo    - Backend остановлен) else (echo    - Backend не запущен)

echo [3/4] Остановка Celery Worker...
taskkill /F /FI "WINDOWTITLE eq Celery*" /T 2>nul
if %errorlevel% equ 0 (echo    - Celery остановлен) else (echo    - Celery не запущен)

echo [4/4] Остановка Frontend...
taskkill /F /FI "WINDOWTITLE eq Frontend*" /T 2>nul
if %errorlevel% equ 0 (echo    - Frontend остановлен) else (echo    - Frontend не запущен)

echo.

:: Дополнительная очистка процессов (если они запущены без окон)
echo Дополнительная очистка процессов...
taskkill /F /IM uvicorn.exe /T 2>nul
taskkill /F /IM celery.exe /T 2>nul

echo.
echo ========================================
echo   Все сервисы остановлены!
echo ========================================
echo.
pause

