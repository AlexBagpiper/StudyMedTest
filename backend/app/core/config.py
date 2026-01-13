"""
Конфигурация приложения
"""

import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Настройки приложения из переменных окружения
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra='ignore'
    )
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "MedTest Platform"
    VERSION: str = "0.1.0"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "medtest_user"
    POSTGRES_PASSWORD: str = "change_me"
    POSTGRES_DB: str = "medtest"
    DATABASE_URL: Optional[PostgresDsn] = None
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: Any) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=info.data.get("POSTGRES_USER"),
            password=info.data.get("POSTGRES_PASSWORD"),
            host=info.data.get("POSTGRES_SERVER"),
            path=f"{info.data.get('POSTGRES_DB') or ''}",
        )
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"
    
    # MinIO / S3
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin123"
    MINIO_BUCKET: str = "medtest-storage"
    MINIO_SECURE: bool = False
    
    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LOCAL_LLM_ENABLED: bool = True
    LOCAL_LLM_URL: str = "http://localhost:8001/v1"
    LOCAL_LLM_MODEL: str = "mistral-7b-instruct"
    LLM_STRATEGY: str = "hybrid"  # cloud, local, hybrid
    LLM_FALLBACK_ENABLED: bool = True
    
    # Email (опционально)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[EmailStr] = None
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    ENVIRONMENT: str = "development"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100 MB
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]
    MAX_IMAGE_DIMENSION: int = 8192  # 8K max
    
    # Admin User (для инициализации)
    FIRST_ADMIN_EMAIL: EmailStr = "admin@example.com"
    FIRST_ADMIN_PASSWORD: str = "change_me_admin"
    FIRST_ADMIN_FULL_NAME: str = "System Administrator"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Frontend
    REACT_APP_API_URL: str = "http://localhost:8000"
    
    @property
    def async_database_url(self) -> str:
        """Database URL для async SQLAlchemy"""
        return str(self.DATABASE_URL)    


# Singleton instance
settings = Settings()

