# Development & Deployment Workflow

Практическая памятка: как разрабатывать локально (Windows, без Docker) и
катить на production (Linux-сервер с Docker).

## Обзор потока

```
┌──────────────┐   git push   ┌───────────┐   webhook / manual   ┌──────────┐
│ Local (Win)  │ ───────────> │  GitHub   │ ───────────────────> │  Server  │
│ venv+uvicorn │              │  Actions  │                       │  Docker  │
└──────────────┘              └─────┬─────┘                       └──────────┘
       │                            │                                   ▲
       │  локальные pytest          │  CI прогоняет тесты              │
       │  перед push                │  blocks merge if red              │
       └────────────────────────────┴───────────────────────────────────┘
```

Три независимых среды:

| Среда | Где | Docker | БД/Redis | Python |
|---|---|---|---|---|
| **Local dev** | Windows | — | нативно (Postgres+Redis на host) | `backend/venv` |
| **CI** | GitHub Actions runner | — | service containers (в workflow) | setup-python@v4 |
| **Production** | Linux server | docker compose | контейнеры | в образе medtest-backend |

Один набор кода, разные способы запустить — за счёт:
- `requirements.txt` — прод-зависимости, одинаковые во всех средах;
- `requirements-dev.txt` — только для local+CI (pytest, fakeredis и т.п.);
- env-переменные через `settings` — единственный источник конфигурации.

## 1. Local development

### Первый запуск

```powershell
# Из корня репо
python scripts/setup_dev_venv.py
# Создаёт backend/venv и ставит requirements-dev.txt (всё, включая slowapi/fakeredis).
```

Локально должны быть запущены **Postgres** и **Redis** (Windows-сервисы или
portable-бинарники — см. `INSTALL_WINDOWS.md`). Docker НЕ нужен.

### Запуск backend

```powershell
.\backend\venv\Scripts\Activate
cd backend
uvicorn app.main:app --reload
# API: http://localhost:8000/docs
```

Логи видны в консоли. OTP-коды печатаются в stdout, т.к. `ENVIRONMENT=development`.

### Запуск frontend

```powershell
cd frontend
npm install   # один раз
npm run dev
# UI: http://localhost:5173
```

### Celery-воркер локально (опционально)

Тесты интеграции работают без Celery (sync email sender или in-memory mock).
Но если нужен реальный флоу с асинхронной доставкой:

```powershell
# Отдельные два терминала (ВАЖНО: раздельные очереди, как в prod)
# Terminal 1 — LLM queue
cd backend
..\backend\venv\Scripts\celery.exe -A app.tasks.celery_app worker --loglevel=info --queues=celery --pool=solo

# Terminal 2 — Email queue
..\backend\venv\Scripts\celery.exe -A app.tasks.celery_app worker --loglevel=info --queues=email --pool=solo
```

На Windows обязателен `--pool=solo` (multiprocessing broken). В prod (Linux)
используется дефолтный prefork.

### SMTP локально

Для локального теста писем запусти **MailHog** (portable exe):

```powershell
# https://github.com/mailhog/MailHog/releases — скачать .exe
.\MailHog_windows_amd64.exe
# SMTP: localhost:1025, Web UI: http://localhost:8025
```

В `backend/.env`:
```
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_FROM=no-reply@localhost
EMAIL_TRANSPORT=sync    # не обязателен, но чуть проще для отладки
```

Либо вообще не запускать SMTP — при `SMTP_HOST=` (пусто) backend печатает
письмо в stdout, чего достаточно для отладки.

## 2. Тестирование перед push

Минимальный чеклист локально:

```powershell
cd backend
.\venv\Scripts\Activate

# 1) Модульные + интеграционные регистрационные тесты (~50 сек)
pytest tests/registration/ -v

# 2) Регрессия существующих тестов (~30 сек)
pytest tests/ --ignore=tests/registration -q

# 3) Линтеры (не блокируют, но желательно)
black --check app/
isort --check-only app/
flake8 app/ --max-line-length=100

# 4) Frontend
cd ..\frontend
npm test
```

Если всё зелёное — `git push`. CI автоматически прогонит тот же набор в
ubuntu-окружении + bandit + pip-audit.

## 3. Commit / push

```powershell
git add backend/app frontend/src docs deployment .github
git commit -m "feat(auth): OTP-based registration with Celery email queue"
git push origin main
```

CI запустится автоматически. Смотри статус: https://github.com/.../actions

Правила бранчинга на ваш вкус; `ci.yml` реагирует на push в `main`/`develop` и
на pull request.

## 4. Deployment на сервер

Сценарий: вы запушили в main, CI зелёный. Дальше — на сервере.

### SSH-доступ

```bash
ssh user@your-server.med-testing.ru
cd /path/to/StudyMedTest
```

### Стандартный деплой

```bash
./deploy.sh
```

Скрипт сам сделает:
1. `git pull --ff-only` — подтянет новый код.
2. Проверит что `deployment/.env` существует и содержит не-placeholder секреты.
3. Экспортирует `APP_VERSION` из git-тегов и `APP_REVISION` из короткого SHA.
4. `docker compose build` — пересоберёт backend/frontend images.
5. `docker compose up -d --remove-orphans --force-recreate` — поднимет всё,
   включая **новый сервис** `celery_email_worker`.
6. Smoke-проверки: `/health`, ping обоих Celery-воркеров.

### С полным smoke-тестом регистрации

```bash
./deploy.sh --smoke
```

Дополнительно дёрнет `POST /api/v1/auth/register` с тестовым email, проверит:
- ответ имеет поле `resend_after`;
- задача попала в Redis-очередь `email`;
- убирает за собой draft + OTP.

### Полная пересборка (если кэш сломан или критичная зависимость обновилась)

```bash
./deploy.sh --clean
```

Снесёт контейнеры, удалит локальные images, соберёт `--no-cache`. Дольше, но
гарантированно подтягивает свежие слои.

### Откат

```bash
./deploy.sh --rollback
```

`git reset --hard HEAD~1` + полный deploy на предыдущий коммит. Подходит если
последний деплой сломал прод; миграций БД в этой версии нет, откат безопасен.

Для отката на произвольный тег:
```bash
git checkout v1.2.3
./deploy.sh
```

## 5. Что именно меняется в этом релизе

При первом деплое после мержа registration-overhaul будут следующие
инфраструктурные изменения:

| Объект | До | После |
|---|---|---|
| docker-compose services | 7 | **8** (+`celery_email_worker`) |
| Celery queue routing | всё в `celery` | `celery` (LLM) + `email` (SMTP) |
| Backend image deps | базовые | + `slowapi`, `limits[redis]` |
| Redis DB usage | 0,1,2 | 0,1,2 + **4** (slowapi storage) |
| env.example | SMTP creds в открытом виде | плейсхолдер `CHANGE_ME_SMTP_PASSWORD` |

**Внимание:** если у вас сейчас `deployment/.env` на сервере содержит старый
пароль `SMTP_PASSWORD=aAdVxP*DFHR-` — он **продолжит работать**, т.к. реальный
файл не меняется deploy'ем. Но учтите: этот пароль уже утёк в git history
через прежний env.example и должен быть **ротирован** в ближайшее время.

## 6. Операционные чеки после деплоя

### Быстрая диагностика одной командой

```bash
# На сервере (внутри backend-контейнера):
docker compose -f deployment/docker-compose.yml exec backend python scripts/dev_diag.py

# Локально:
python backend/scripts/dev_diag.py
```

Выведет состояние Postgres/Redis, настройки, глубину очередей Celery, список работающих воркеров и сопоставит их с ожидаемыми очередями. Предупредит, если `EMAIL_TRANSPORT=celery`, но воркер для `email` не слушает.

### Ручные чеки

```bash
# Статус всех сервисов
docker compose -f deployment/docker-compose.yml ps

# Логи email-воркера в реальном времени
docker compose -f deployment/docker-compose.yml logs -f celery_email_worker

# Глубина email-очереди (норма < 50 в спокойном режиме)
docker exec medtest-redis redis-cli -n 1 LLEN email

# Активные регистрации в процессе
docker exec medtest-redis redis-cli -n 0 KEYS 'reg:draft:*' | wc -l

# Проверка rate-limit storage
docker exec medtest-redis redis-cli -n 4 KEYS 'LIMITS*' | head

# Health
curl -sS https://your-domain.ru/health
```

### Очистка застрявших очередей

```bash
# Принудительно удалить email-очередь (ТОЛЬКО если задачи стали устаревшими)
docker exec medtest-redis redis-cli -n 1 DEL email

# Или: ./deploy.sh --smoke автоматически проверит что очередь обрабатывается
```

### Legacy-ключи старой регистрации

Если на сервере оставались `pending_reg:*` от старой версии регистрации — они продолжают жить по своему TTL (24 ч), но новый код их не читает. Можно удалить безопасно:

```bash
./deploy.sh --cleanup-legacy      # в составе деплоя
# или в любое время вручную:
docker exec medtest-redis redis-cli -n 0 --scan --pattern "pending_reg:*" | \
  xargs -r docker exec -i medtest-redis redis-cli -n 0 DEL
```

## 7. Runbook известных симптомов

Подробнее — в [REGISTRATION.md §7.4](REGISTRATION.md). Здесь короткая шпаргалка:

| Симптом | Первая диагностика |
|---|---|
| "Неверный код" массово | `redis-cli -n 0 HGETALL reg:otp:{email}` — смотреть `attempts`, TTL. |
| Письма не приходят | `logs celery_email_worker` + `LLEN email`. Если очередь растёт — поднять concurrency. |
| Массовые 429 | `redis-cli -n 4 KEYS 'LIMITS*'` — найти атакующие IP. |
| 500 на /register | `logs backend --tail=100` — скорее всего Redis/Postgres/Celery недоступен. |

## 8. Git / релизный цикл (рекомендация)

```
feature/auth-otp   ──┐
feature/ui-polish  ──┼── PR → main (CI gate) ── tag v1.2.0 ── ssh deploy
hotfix/rate-limit  ──┘
```

Рекомендуется:
- релизы из `main` после тега (`git tag v1.2.0 && git push --tags`);
- hotfix с cherry-pick в main + повторный тег `v1.2.1`;
- `deploy.sh` автоматически берёт текущий тег как `APP_VERSION`, версия
  попадает в `/health` и Sentry для трекинга.
