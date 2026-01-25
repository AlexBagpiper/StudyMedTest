"""
FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
import traceback
import json

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.database import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения
    """
    # Startup
    print(f"[*] Starting {settings.PROJECT_NAME}...")
    
    # Создание таблиц (в production использовать Alembic)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    
    print("[+] Application started successfully")
    
    yield
    
    # Shutdown
    print("[*] Shutting down...")
    await engine.dispose()
    print("[+] Shutdown complete")


# Создание FastAPI приложения
app = FastAPI(
    title=f"{settings.PROJECT_NAME} API",
    description=f"API для {settings.PROJECT_NAME}",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
if settings.ENVIRONMENT == "development":
    # В development разрешаем типичные локальные origins
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ]
else:
    cors_origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(api_v1_router, prefix="/api/v1")

# Глобальный обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Глобальный обработчик всех необработанных исключений
    """
    # #region agent log
    error_traceback = traceback.format_exc()
    error_info = {
        "path": str(request.url.path),
        "method": request.method,
        "error": str(exc),
        "error_type": type(exc).__name__,
        "traceback": error_traceback
    }
    
    # Логирование в файл (если доступен)
    log_path = r"e:\pythonProject\StudyMedTest\.cursor\debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"main.py:exception_handler","message":"unhandled exception","data":error_info,"timestamp":int(__import__("time").time()*1000)})+"\n")
    except: pass
    
    # Логирование в stdout (видно в логах сервера)
    print(f"[ERROR] {request.method} {request.url.path}: {type(exc).__name__}: {str(exc)}")
    print(f"[ERROR] Traceback:\n{error_traceback}")
    # #endregion
    
    # Временно возвращаем детальную информацию для отладки (можно убрать после исправления)
    # В development режиме возвращаем детальную информацию об ошибке
    if settings.ENVIRONMENT == "development" or "/api/v1/tests" in str(request.url.path):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "error_type": type(exc).__name__,
                "path": str(request.url.path),
                "traceback": error_traceback
            }
        )
    else:
        # В production возвращаем только общую ошибку, но логируем детали
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint для мониторинга
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "version": settings.VERSION,
            "service": f"{settings.PROJECT_NAME.lower().replace(' ', '-')}-backend"
        }
    )


@app.get("/", tags=["Root"])
async def root():
    """
    Корневой endpoint
    """
    return {
        "message": "MedTest Platform API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

