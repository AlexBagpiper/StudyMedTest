import random
import string
from locust import HttpUser, task, between

class MedTestUser(HttpUser):
    wait_time = between(1, 5)

    @task(3)
    def register_flow(self):
        # Генерируем случайный email для каждого теста
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email = f"test_{random_str}@example.com"
        password = "TestPassword123!"
        
        # 1. Регистрация
        with self.client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "first_name": "Test",
                "last_name": "User",
                "middle_name": "Load"
            },
            name="/auth/register",
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Register failed: {response.status_code}")
                return

        # В реальном тесте здесь была бы пауза на получение письма
        # Код мы не знаем, поэтому для нагрузки можем просто слать неверный код 
        # или настроить тестовый режим на бэкенде, где код всегда 123456.
        
        # 2. Попытка верификации (имитация нагрузки на Redis/DB)
        with self.client.post(
            "/api/v1/auth/verify-email",
            json={
                "email": email,
                "code": "123456" # Скорее всего будет 400, но создаст нагрузку
            },
            name="/auth/verify-email",
            catch_response=True
        ) as response:
            if response.status_code not in [200, 400, 410, 429]:
                response.failure(f"Verify failed with unexpected status: {response.status_code}")
            else:
                response.success()

    @task(1)
    def resend_verification(self):
        # Тестируем повторную отправку
        email = "test_resend@example.com"
        self.client.post(
            "/api/v1/auth/resend-verification",
            json={"email": email},
            name="/auth/resend-verification"
        )

# Инструкция по запуску:
# 1. Установить locust: pip install locust
# 2. Запустить: locust -f locustfile.py
# 3. Открыть http://localhost:8089
