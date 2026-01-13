from minio import Minio
from minio.error import S3Error
import json


def setup_minio():
    """Создание бакета для хранения файлов"""
    client = Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin123",
        secure=False
    )
    
    bucket_name = "medtest"
    
    try:
        # Создание бакета
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"✅ Бакет '{bucket_name}' создан")
        else:
            print(f"⚠️  Бакет '{bucket_name}' уже существует")
        
        # Публичная политика (для разработки)
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                }
            ]
        }
        
        client.set_bucket_policy(bucket_name, json.dumps(policy))
        print(f"✅ Политика доступа установлена")
        
    except S3Error as e:
        print(f"❌ Ошибка: {e}")


if __name__ == '__main__':
    setup_minio()