"""
Locust profile for the registration endpoints.

Usage:
    pip install locust
    locust -f backend/tests/load/locustfile_registration.py \
        --host http://localhost:8000 \
        --users 500 --spawn-rate 10 --run-time 10m

SLO targets (audit):
    - p95 /register        < 500 ms
    - p99 /register        < 1000 ms
    - error rate (5xx)     == 0
    - email queue depth    < 200 (Celery Flower / Redis LLEN celery@email)
"""

from __future__ import annotations

import random
import string

from locust import HttpUser, between, task


def rand_email() -> str:
    tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"load_{tag}@example.com"


class RegistrationUser(HttpUser):
    """
    Each virtual user runs the full flow: register -> verify (with wrong code
    to measure validation path) -> resend.
    """
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.email = rand_email()

    @task(3)
    def register(self):
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": self.email,
                "password": "Secret123",
                "last_name": "Иванов",
                "first_name": "Иван",
                "middle_name": "Иванович",
            },
            name="POST /register",
        )

    @task(2)
    def verify_wrong_code(self):
        self.client.post(
            "/api/v1/auth/verify-email",
            json={"email": self.email, "code": "000000"},
            name="POST /verify-email (wrong)",
        )

    @task(1)
    def resend(self):
        self.client.post(
            "/api/v1/auth/resend-verification",
            json={"email": self.email},
            name="POST /resend-verification",
        )
