"""
Object Storage (MinIO/S3) utilities
"""

import io
from typing import BinaryIO, Optional

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class StorageService:
    """
    Сервис для работы с объектным хранилищем MinIO/S3
    """
    
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """
        Проверка и создание bucket если не существует
        """
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                print(f"✅ Created bucket: {self.bucket}")
        except S3Error as e:
            print(f"❌ Error creating bucket: {e}")
    
    def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Загрузка файла в storage
        
        Args:
            file_data: file-like объект с данными
            object_name: имя объекта в storage (путь)
            content_type: MIME type файла
            metadata: дополнительные метаданные
        
        Returns:
            URL файла в storage
        """
        try:
            # Получаем размер файла
            file_data.seek(0, 2)
            file_size = file_data.tell()
            file_data.seek(0)
            
            self.client.put_object(
                self.bucket,
                object_name,
                file_data,
                file_size,
                content_type=content_type,
                metadata=metadata
            )
            
            return f"{self.bucket}/{object_name}"
        
        except S3Error as e:
            raise Exception(f"Failed to upload file: {e}")
    
    def download_file(self, object_name: str) -> bytes:
        """
        Скачивание файла из storage
        
        Args:
            object_name: имя объекта в storage
        
        Returns:
            Содержимое файла в bytes
        """
        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        
        except S3Error as e:
            raise Exception(f"Failed to download file: {e}")
    
    def delete_file(self, object_name: str) -> bool:
        """
        Удаление файла из storage
        
        Args:
            object_name: имя объекта в storage
        
        Returns:
            True если удалено успешно
        """
        try:
            self.client.remove_object(self.bucket, object_name)
            return True
        except S3Error as e:
            print(f"Error deleting file: {e}")
            return False
    
    def get_presigned_url(
        self,
        object_name: str,
        expires_seconds: int = 3600
    ) -> str:
        """
        Получение временной signed URL для доступа к файлу
        
        Args:
            object_name: имя объекта в storage
            expires_seconds: время жизни URL в секундах
        
        Returns:
            Signed URL
        """
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=timedelta(seconds=expires_seconds)
            )
            return url
        except S3Error as e:
            raise Exception(f"Failed to generate presigned URL: {e}")
    
    def file_exists(self, object_name: str) -> bool:
        """
        Проверка существования файла
        
        Args:
            object_name: имя объекта в storage
        
        Returns:
            True если файл существует
        """
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False


# Singleton instance
storage_service = StorageService()

