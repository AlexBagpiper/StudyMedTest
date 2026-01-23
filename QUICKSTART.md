# 🚀 Быстрый старт - MedTest Platform

> 💡 **Альтернатива**: Если вы предпочитаете установку без Docker:
> - **Windows**: [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) (упрощенная инструкция)
> - **Все ОС**: [INSTALL_NATIVE.md](INSTALL_NATIVE.md) (полная инструкция)

## Предварительные требования

- Docker 24.0+ и Docker Compose 2.20+
- Git
- 8 GB RAM минимум
- 20 GB свободного места на диске

## Шаг 1: Клонирование и настройка

```bash
# Клонирование репозитория
git clone https://github.com/your-org/StudyMedTest.git
cd StudyMedTest

# Создание .env из примера
cp .env.example .env

# Базовая настройка (для локальной разработки .env уже настроен)
# Для production отредактируйте .env с реальными credentials
```

## Шаг 2: Запуск инфраструктуры

```bash
# Запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps

# Ожидание готовности БД (30-60 секунд)
docker-compose logs -f db
```

## Шаг 3: Инициализация базы данных

```bash
# Применение миграций
docker-compose exec backend alembic upgrade head

# Создание первого администратора
docker-compose exec backend python -c "
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
import asyncio

async def create_admin():
    async with AsyncSessionLocal() as db:
        admin = User(
            email='admin@medtest.local',
            password_hash=get_password_hash('admin123'),
            last_name='Администратор',
            first_name='Системы',
            role='admin',
            is_active=True,
            is_verified=True
        )
        db.add(admin)
        await db.commit()
        print('✅ Admin created: admin@medtest.local / admin123')

asyncio.run(create_admin())
"
```

## Шаг 4: Доступ к приложению

Откройте в браузере:

- **Frontend**: http://localhost
- **Backend API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (minioadmin / minioadmin123)

**Вход в систему:**
- Email: `admin@medtest.local`
- Password: `admin123`

## Шаг 5: Создание тестовых данных

### Создание преподавателя

Войдите как админ и создайте преподавателя:

```bash
# Или через API
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher@medtest.local",
    "password": "teacher123",
    "last_name": "Петров",
    "first_name": "Иван",
    "role": "teacher"
  }'
```

### Регистрация студента

Студенты могут регистрироваться самостоятельно:

1. Перейдите на http://localhost/register
2. Заполните форму регистрации
3. Войдите в систему

## Распространённые проблемы

### Backend недоступен

```bash
# Проверка логов
docker-compose logs backend

# Перезапуск
docker-compose restart backend
```

### Frontend не загружается

```bash
# Проверка логов
docker-compose logs frontend

# Пересборка
docker-compose up -d --build frontend
```

### База данных недоступна

```bash
# Проверка здоровья БД
docker-compose exec db pg_isready -U medtest_user

# Перезапуск БД
docker-compose restart db
```

### Очистка и перезапуск

```bash
# Остановка всех сервисов
docker-compose down

# Удаление volumes (ВНИМАНИЕ: удалит все данные!)
docker-compose down -v

# Полная пересборка
docker-compose build --no-cache
docker-compose up -d
```

## Следующие шаги

1. **Создайте вопросы**: Войдите как преподаватель → Вопросы → Создать вопрос
2. **Создайте тест**: Тесты → Создать тест → Добавьте вопросы
3. **Опубликуйте тест**: Тест → Опубликовать
4. **Пройдите тест**: Войдите как студент → Доступные тесты

## Полезные команды

```bash
# Просмотр логов
docker-compose logs -f

# Просмотр логов конкретного сервиса
docker-compose logs -f backend

# Вход в контейнер backend
docker-compose exec backend bash

# Запуск тестов
docker-compose exec backend pytest

# Просмотр очереди Celery
docker-compose exec backend celery -A app.tasks.celery_app inspect active

# Остановка всех сервисов
docker-compose down

# Обновление кода и перезапуск
git pull
docker-compose up -d --build
```

## Дополнительная документация

- [Полная документация по Deployment](docs/DEPLOYMENT.md)
- [API документация](docs/API.md)
- [Архитектура системы](docs/ARCHITECTURE.md)
- [README](README.md)

## Поддержка

Если возникли проблемы:
1. Проверьте логи: `docker-compose logs`
2. Убедитесь, что все сервисы запущены: `docker-compose ps`
3. Проверьте, что порты не заняты: `netstat -tulpn | grep -E '(80|8000|5432)'`
4. Создайте issue в GitHub репозитории

---

**Важно для production:**
- Измените пароли в `.env`
- Настройте SSL сертификаты
- Настройте backup
- Настройте мониторинг
- См. [DEPLOYMENT.md](docs/DEPLOYMENT.md) для деталей

