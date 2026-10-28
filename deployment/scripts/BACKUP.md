# Холодные бэкапы MedTest

## Идея (3-2-1)

1. **На VPS** — ежедневный снимок в `~/backups/cold-staging/` (`backup_prod.sh`).
2. **Локальный HDD** — раз в неделю (или после важных изменений) `scripts/pull-cold-backup.ps1` на отключённый диск.
3. **Проверка** — раз в квартал восстановление в тестовый compose на другой машине.

Не храни единственную копию `.env` только на VPS. Архив на HDD = offline + отдельно от Reg.ru.

## Состав снимка

| Файл | Содержимое |
|------|------------|
| `medtest_db.dump` | **Вся БД** — все таблицы и данные (`pg_dump -Fc`, проверка `pg_restore --list`) |
| `postgres_globals.sql` | Роли/grants (`pg_dumpall --globals-only`) |
| `minio_data.tar.gz` | Файлы/изображения |
| `redis_data.tar.gz` | Очереди, OTP (опционально можно не тащить на cold) |
| `mox-data.tar.gz` | Почта |
| `nginx_*.tar.gz` | Сертификаты и шаблоны |
| `.env` | Секреты прода |
| `MANIFEST.txt` / `SHA256SUMS.txt` | Метаданные и контрольные суммы |

## VPS

```bash
chmod +x deployment/scripts/backup_prod.sh
./deployment/scripts/backup_prod.sh --keep 7
```

Cron:

```cron
30 3 * * * /home/medtest/StudyMedTest/deployment/scripts/backup_prod.sh --keep 7 >> /home/medtest/backups/backup.log 2>&1
```

## Windows → HDD

```powershell
.\scripts\pull-cold-backup.ps1 -Dest "D:\Archive\StudyMedTest"
```

Диск **отключай** после копирования (настоящий cold).

## Альтернатива «в одну кнопку»

Если нужны инкременты + шифрование на диск:

- **[restic](https://restic.net/)** — репозиторий на смонтированном HDD, `restic backup` с VPS через SFTP или локальный `restic copy` после `pull`.
- **Borg** — похоже, лучше на Linux-only.

Для одного VPS и редкого cold copy текущей пары скриптов обычно достаточно.

## Восстановление

См. миграцию `backups/prod-*`: распаковать tar, `pg_restore`, `docker compose up`, скопировать `.env` и `mox-data`.
