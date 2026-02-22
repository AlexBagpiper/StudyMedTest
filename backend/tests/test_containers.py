import os
import yaml
import pytest

# Находим корень проекта (на один уровень выше папки tests и папки backend)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def test_dockerfiles_exist():
    """Проверка наличия Docker-файлов."""
    assert os.path.exists(os.path.join(BASE_DIR, "backend/Dockerfile"))
    assert os.path.exists(os.path.join(BASE_DIR, "frontend/Dockerfile"))
    assert os.path.exists(os.path.join(BASE_DIR, "deployment/docker-compose.yml"))

def test_docker_compose_valid_yaml():
    """Проверка валидности YAML в docker-compose."""
    path = os.path.join(BASE_DIR, "deployment/docker-compose.yml")
    with open(path, "r", encoding="utf-8") as f:
        try:
            config = yaml.safe_load(f)
            assert "services" in config
            assert "backend" in config["services"]
            assert "frontend" in config["services"]
            assert "db" in config["services"]
        except yaml.YAMLError as exc:
            pytest.fail(f"Ошибка в YAML файле {path}: {exc}")

def test_backend_dockerfile_syntax():
    """Базовая проверка содержимого Dockerfile бэкенда."""
    path = os.path.join(BASE_DIR, "backend/Dockerfile")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "FROM python" in content
        assert "WORKDIR /app" in content
        assert "COPY requirements.txt" in content
        assert "pip install" in content

def test_frontend_dockerfile_syntax():
    """Базовая проверка содержимого Dockerfile фронтенда."""
    path = os.path.join(BASE_DIR, "frontend/Dockerfile")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "FROM node" in content
        assert "npm run build" in content
        assert "FROM nginx" in content

def test_docker_compose_env_vars():
    """Проверка, что в docker-compose используются переменные окружения."""
    path = os.path.join(BASE_DIR, "deployment/docker-compose.yml")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        # Проверяем наличие типичных переменных
        assert "${POSTGRES_PASSWORD}" in content
        assert "${DATABASE_URL}" in content
