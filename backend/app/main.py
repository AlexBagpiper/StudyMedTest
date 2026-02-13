"""
FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

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
    version=settings.APP_VERSION,
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
    # Логирование ошибки в stdout (видно в логах сервера)
    import traceback
    error_traceback = traceback.format_exc()
    print(f"[ERROR] {request.method} {request.url.path}: {type(exc).__name__}: {str(exc)}")
    if settings.ENVIRONMENT == "development":
        print(f"[ERROR] Traceback:\n{error_traceback}")
    
    # В development режиме возвращаем детальную информацию об ошибке
    if settings.ENVIRONMENT == "development":
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
        # В production возвращаем только общую ошибку
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
            "version": settings.APP_VERSION,
            "revision": settings.APP_REVISION,
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
        "version": settings.APP_VERSION,
        "revision": settings.APP_REVISION,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # nosec B104
        port=8000,
        reload=True,
        log_level="info"
    )

