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
                print(f"[+] Created bucket: {self.bucket}")
            
            # В режиме разработки делаем bucket публичным для чтения
            # Это решает проблемы с presigned URLs через прокси
            if settings.ENVIRONMENT == "development":
                self._set_public_read_policy()
        except S3Error as e:
            print(f"[-] Error with bucket: {e}")
            
    def _set_public_read_policy(self):
        """
        Установка публичного доступа на чтение для bucket
        """
        import json
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self.bucket}/*"],
                },
            ],
        }
        try:
            self.client.set_bucket_policy(self.bucket, json.dumps(policy))
            print(f"[+] Set public read policy for bucket: {self.bucket}")
        except Exception as e:
            print(f"[-] Error setting bucket policy: {e}")
    
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
        Получение временной signed URL для доступа к файлу.
        В режиме разработки, если bucket публичный, возвращает прямую ссылку.
        """
        try:
            # В разработке используем прямые ссылки без подписи, 
            # так как мы сделали bucket публичным. Это надежнее через прокси.
            if settings.ENVIRONMENT == "development":
                base = settings.MINIO_PUBLIC_URL or f"http://{settings.MINIO_ENDPOINT}"
                base = base.rstrip('/')
                # Если мы используем прокси /storage, то bucket уже не нужен в пути 
                # (зависит от настроек прокси, но обычно MinIO хочет bucket в пути)
                return f"{base}/{self.bucket}/{object_name}"

            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=timedelta(seconds=expires_seconds)
            )
            
            # Если задан публичный URL, заменяем внутренний адрес на публичный
            if settings.MINIO_PUBLIC_URL:
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                internal_base = f"{parsed_url.scheme}://{parsed_url.netloc}"
                public_base = settings.MINIO_PUBLIC_URL.rstrip('/')
                url = url.replace(internal_base, public_base)
                
            return url
        except S3Error as e:
            raise Exception(f"Failed to generate URL: {e}")
    
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

