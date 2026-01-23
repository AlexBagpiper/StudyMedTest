# Инструкция по деплою StudyMedTest

Эта папка содержит все необходимое для развертывания проекта на сервере с использованием Docker.

## Требования
- Linux сервер (Ubuntu 22.04+ рекомендуется)
- Docker и Docker Compose установленные на сервере

## Шаги по развертыванию

1. **Копирование файлов на сервер**
   Скопируйте содержимое всего проекта на сервер (или только папку `deployment`, но тогда убедитесь, что пути в `docker-compose.yml` к `../backend` и `../frontend` корректны).
   Рекомендуется клонировать репозиторий прямо на сервере.

2. **Подготовка окружения**
   В папке `deployment` создайте файл `.env` на основе `env.example`:
   ```bash
   cp env.example .env
   ```
   Отредактируйте `.env` и установите надежные пароли и ключи:
   - `POSTGRES_PASSWORD`
   - `SECRET_KEY`
   - `MINIO_ROOT_PASSWORD`
   - Настройки LLM (OpenAI/Anthropic), если планируете использовать.

3. **Запуск проекта**
   Находясь в папке `deployment`, выполните:
   ```bash
   docker compose up -d --build
   ```

4. **Проверка работы**
   - API будет доступно по адресу `http://your-server-ip/api/docs`
   - Frontend будет доступен по адресу `http://your-server-ip/`
   - MinIO Console: `http://your-server-ip:9001` (нужно пробросить порт или добавить в nginx)

## Управление
- Просмотр логов: `docker compose logs -f`
- Остановка: `docker compose down`
- Обновление проекта:
  ```bash
  git pull
  docker compose up -d --build
  ```

## Важные замечания
- **База данных**: При первом запуске `alembic upgrade head` выполнится автоматически внутри контейнера `backend`.
- **Администратор**: Скрипт `create_admin.py` также запускается автоматически.
- **SSL**: Для настройки HTTPS отредактируйте `nginx/nginx.conf`, раскомментируйте секцию SSL и положите сертификаты в `nginx/certs/`.
- **GPU**: Если вы планируете использовать локальные LLM с поддержкой GPU, раскомментируйте соответствующую секцию в `docker-compose.yml` и установите `nvidia-container-toolkit` на сервере.
