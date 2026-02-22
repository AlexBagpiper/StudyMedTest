# Тестирование системы MedTest

Данный проект использует автоматизированную систему тестирования для бэкенда (FastAPI) и фронтенда (React + Vite).

## Структура тестов

- **Backend**: Находится в `backend/tests/`. Используется `pytest` и `pytest-asyncio`.
- **Frontend**: Находится в `src/**/__tests__/`. Используется `vitest` и `react-testing-library`.

## Настройка окружения

Для разработки и тестов используется **backend/venv** с зависимостями из **requirements-dev.txt** (на сервере при развёртывании — только requirements.txt). Один раз из корня проекта:

```bash
python scripts/setup_dev_venv.py
```

Либо вручную:
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
pip install -r requirements-dev.txt
```

После этого `python scripts/run_tests.py` и `npm run testing` используют этот venv автоматически.

### Настройка тестовой БД
Для тестов бэкенда используется отдельная база данных. Убедитесь, что она создана или измените `TEST_DATABASE_URL` в `backend/tests/conftest.py`.

## Команды

### Запуск всех тестов
Из корня проекта выполните:
```bash
npm run testing
```
Эта команда:
1. Запускает `scripts/auto_test.py`, который анализирует измененные файлы через Git.
2. Автоматически генерирует осмысленные тесты для новых функций, используя `LLMService` (YandexGPT/DeepSeek).
3. Запускает тесты бэкенда.
4. Запускает тесты фронтенда.

### Запуск только бэкенда
```bash
cd backend
.\venv\Scripts\python -m pytest   # Windows; Linux: venv/bin/python -m pytest
```

### Запуск только фронтенда
```bash
cd frontend
npm test
```

## Автоматическая генерация тестов

Система настроена так, что при появлении новых файлов в `backend/app/api/` или `frontend/src/`, при запуске команды `testing` будут созданы соответствующие файлы тестов.

Для корректной работы генерации убедитесь, что в `backend/.env` прописаны ключи для LLM:
- `YANDEX_API_KEY` и `YANDEX_FOLDER_ID`
- Или `DEEPSEEK_API_KEY`, если используется стратегия DeepSeek.

## Инструкции по написанию тестов

### Бэкенд (Python)
- Используйте фикстуру `client` для выполнения запросов.
- Для тестов с БД используйте `db_session`.
- Всегда помечайте асинхронные тесты `@pytest.mark.asyncio`.

### Фронтенд (TypeScript/React)
- Используйте `render` и `screen` из `@testing-library/react`.
- Оборачивайте компоненты в `MemoryRouter`, если они используют навигацию.
- Для моков API используйте `vi.mock`.

## CI/CD
Тесты автоматически запускаются при каждом Push в ветку `main` или создании Pull Request (настроено в `.github/workflows/ci.yml`).
