"""
FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
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
    print("[*] Starting MedTest Platform...")
    
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
    title="MedTest Platform API",
    description="API для системы тестирования студентов медицинского института",
    version="0.1.0",
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
            "version": "0.1.0",
            "service": "medtest-backend"
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

