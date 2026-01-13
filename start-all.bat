@echo off
title MedTest Platform - Запуск всех сервисов
color 0A

echo ========================================
echo   MedTest Platform - Автозапуск
echo ========================================
echo.

:: Проверка запуска MinIO
echo [1/4] Запуск MinIO...
start "MinIO Server" /MIN cmd /k "C:\minio\start-minio.bat"
timeout /t 3 /nobreak >nul

:: Запуск Backend
echo [2/4] Запуск Backend API...
start "Backend API" cmd /k "cd /d E:\pythonProject\StudyMedTest && .\venv\Scripts\activate && cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 5 /nobreak >nul

:: Запуск Celery
echo [3/4] Запуск Celery Worker...
start "Celery Worker" cmd /k "cd /d E:\pythonProject\StudyMedTest && .\venv\Scripts\activate && cd backend && celery -A app.tasks.celery_app worker --loglevel=info --pool=solo"
timeout /t 3 /nobreak >nul

:: Запуск Frontend
echo [4/4] Запуск Frontend...
start "Frontend Dev Server" cmd /k "cd /d E:\pythonProject\StudyMedTest\frontend && npm run dev"

echo.
echo ========================================
echo   Все сервисы запущены!
echo ========================================
echo.
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8000/docs
echo   MinIO:     http://localhost:9001
echo.
echo   Логин: admin@example.com
echo   Пароль: admin123
echo.
echo   Для остановки закройте все окна или
echo   нажмите Ctrl+C в каждом окне.
echo.
pause

