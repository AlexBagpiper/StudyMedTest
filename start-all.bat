@echo off
title MedTest Platform - Starting All Services
color 0A

echo ========================================
echo   MedTest Platform - Auto Start
echo ========================================
echo.

cd /d E:\pythonProject\StudyMedTest

:: Starting MinIO
echo [1/4] Starting MinIO...
start /MIN "MedTest-MinIO" cmd /k "C:\minio\start-minio.bat"
timeout /t 3 /nobreak >nul
echo     [OK] MinIO started

:: Starting Backend
echo [2/4] Starting Backend API...
start /MIN "MedTest-Backend" cmd /k "call venv\Scripts\activate.bat && cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 5 /nobreak >nul
echo     [OK] Backend started

:: Starting Celery
echo [3/4] Starting Celery Worker...
start /MIN "MedTest-Celery" cmd /k "call venv\Scripts\activate.bat && cd backend && celery -A app.tasks.celery_app worker --loglevel=info --pool=solo"
timeout /t 3 /nobreak >nul
echo     [OK] Celery started

:: Starting Frontend
echo [4/4] Starting Frontend...
cd frontend
start /MIN "MedTest-Frontend" cmd /k "npm run dev"
timeout /t 2 /nobreak >nul
echo     [OK] Frontend started

echo.
echo ========================================
echo   All services started successfully!
echo ========================================
echo.
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8000/docs
echo   MinIO:     http://localhost:9001
echo.
echo   Login:    admin@example.com
echo   Password: admin123
echo.
echo   4 minimized windows are running in taskbar
echo   To stop all services, run stop-all.bat
echo.
pause

