"""
Diagnostic helper for local dev and remote ops.

Usage:
    python scripts/dev_diag.py
    python scripts/dev_diag.py --migrate-legacy     # convert pending_reg:* to reg:draft:*
    python scripts/dev_diag.py --cleanup-legacy     # delete pending_reg:* (safe)
    python scripts/dev_diag.py --drain-email        # drain email queue (DANGEROUS)

Проверяет:
- Доступность Redis, Postgres.
- Текущие настройки (EMAIL_TRANSPORT, ENVIRONMENT).
- Глубину очередей celery/email в Redis DB 1.
- Количество активных регистраций (reg:draft/reg:otp) и legacy (pending_reg).
- Какие воркеры Celery онлайн и какие очереди слушают.

Безопасен по умолчанию — ничего не удаляет без явного флага.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List

# Windows console uses cp1252 by default — force stdout/stderr to UTF-8
# so Russian text and any unicode diagnostics print correctly.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


async def _migrate_legacy_drafts(r) -> int:
    """
    Convert old `pending_reg:{email}` keys to the new `reg:draft:{email}` format.

    The OTP (code) is NOT migrated — old codes had a different format (plaintext
    vs. HMAC hash) and a different TTL (24h vs 10min), so mixing them would
    break the security contract. Users keep their password_hash/name and simply
    need to click "Send code again" on the verify page.
    """
    import json
    from app.core.config import settings

    legacy = await r.keys("pending_reg:*")
    if not legacy:
        return 0

    migrated = 0
    for key in legacy:
        raw = await r.get(key)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        email = data.get("email")
        if not email:
            continue

        draft_key = f"reg:draft:{email.strip().lower()}"
        # Do not overwrite if new-format draft already exists.
        if await r.exists(draft_key):
            await r.delete(key)
            continue

        new_payload = json.dumps({
            "email": data.get("email"),
            "password_hash": data.get("password_hash"),
            "last_name": data.get("last_name"),
            "first_name": data.get("first_name"),
            "middle_name": data.get("middle_name"),
        })
        await r.set(draft_key, new_payload, ex=settings.REGISTRATION_DRAFT_TTL_SECONDS)
        await r.delete(key)
        migrated += 1

    return migrated


async def _check_redis(cleanup_legacy: bool, drain_email: bool, migrate_legacy: bool = False) -> int:
    import redis.asyncio as redis
    from app.core.config import settings

    r = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

    _print_section("Redis")
    try:
        await r.ping()
        print(f"[OK] PING ok ({settings.REDIS_URL})")
    except Exception as exc:
        print(f"[FAIL] Redis unreachable: {exc}")
        return 1

    # DB 0 — основной: драфты регистрации.
    pending_old = await r.keys("pending_reg:*")
    drafts = await r.keys("reg:draft:*")
    otps = await r.keys("reg:otp:*")
    print(f"  reg:draft  (active drafts):   {len(drafts)}")
    print(f"  reg:otp    (active OTPs):     {len(otps)}")
    print(f"  pending_reg (LEGACY):         {len(pending_old)}")

    if pending_old and migrate_legacy:
        migrated = await _migrate_legacy_drafts(r)
        print(f"  [migrate] converted {migrated} legacy key(s) to reg:draft:* format")
        print("            users can click 'Resend code' on /verify-email to get a fresh OTP")
    elif pending_old and cleanup_legacy:
        await r.delete(*pending_old)
        print(f"  [cleanup] deleted {len(pending_old)} legacy pending_reg:* keys")
    elif pending_old:
        print("  hint: --migrate-legacy keeps users' drafts; --cleanup-legacy deletes them")

    # DB 1 — брокер Celery.
    import redis.asyncio as aredis
    broker = aredis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
    try:
        celery_depth = await broker.llen("celery")
        email_depth = await broker.llen("email")
        print(f"\n  Celery queue 'celery' depth:  {celery_depth}")
        print(f"  Celery queue 'email'  depth:  {email_depth}")

        if email_depth and drain_email:
            await broker.delete("email")
            print(f"  [cleanup] DROPPED {email_depth} tasks from 'email' queue")
    finally:
        await broker.aclose()

    # DB 4 — slowapi.
    try:
        from urllib.parse import urlparse
        parsed = urlparse(settings.REDIS_URL)
        rl_url = parsed._replace(path="/4").geturl()
        rl = aredis.from_url(rl_url, decode_responses=True)
        keys = await rl.keys("*")
        print(f"\n  Rate-limit storage (DB 4):    {len(keys)} keys")
        await rl.aclose()
    except Exception as exc:
        print(f"  [warn] rate-limit DB check skipped: {exc}")

    await r.aclose()
    return 0


async def _check_db() -> int:
    from app.core.database import engine
    from sqlalchemy import text

    _print_section("PostgreSQL")
    try:
        async with engine.connect() as conn:
            version = (await conn.execute(text("select version()"))).scalar_one()
            users_count = (await conn.execute(text("select count(*) from users"))).scalar_one()
            verified = (await conn.execute(text("select count(*) from users where is_verified"))).scalar_one()
        print(f"[OK] {version.split(',')[0]}")
        print(f"  users total:     {users_count}")
        print(f"  users verified:  {verified}")
        return 0
    except Exception as exc:
        print(f"[FAIL] DB error: {exc}")
        return 1
    finally:
        await engine.dispose()


def _check_celery_workers() -> int:
    """Опрашивает Celery через control ping — какие воркеры онлайн и что слушают."""
    _print_section("Celery workers")
    try:
        from app.tasks.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=2.0)
        pings = inspect.ping() or {}
        if not pings:
            print("[warn] Нет живых Celery-воркеров. Письма и оценки накапливаются в очереди.")
            return 1

        active_q = inspect.active_queues() or {}
        for worker, q_list in active_q.items():
            queues = [q["name"] for q in q_list]
            print(f"  {worker}: listens on {queues}")

        # Проверка соответствия воркеров ожидаемым очередям.
        all_queues = {q for lst in active_q.values() for q in (item["name"] for item in lst)}
        missing = {"celery", "email"} - all_queues
        if missing:
            print(f"\n[warn] Нет воркера для очередей: {sorted(missing)}")
            print("  Задачи будут накапливаться без обработки.")
            return 1
        return 0
    except Exception as exc:
        print(f"[warn] Проверка Celery невозможна: {exc}")
        return 1


def _check_settings() -> int:
    from app.core.config import settings

    _print_section("Settings")
    print(f"  ENVIRONMENT:      {settings.ENVIRONMENT}")
    print(f"  EMAIL_TRANSPORT:  {settings.EMAIL_TRANSPORT}")
    print(f"  SMTP_HOST:        {settings.SMTP_HOST or '(empty — dev stdout mode)'}")
    print(f"  OTP_TTL_SECONDS:  {settings.OTP_TTL_SECONDS}")
    print(f"  OTP_MAX_ATTEMPTS: {settings.OTP_MAX_ATTEMPTS}")

    warnings: List[str] = []
    if settings.EMAIL_TRANSPORT == "celery" and settings.ENVIRONMENT == "development":
        warnings.append(
            "EMAIL_TRANSPORT=celery в dev. Убедитесь что Celery-воркер для очереди 'email' запущен, "
            "иначе рассылка не работает. Для локалки проще использовать EMAIL_TRANSPORT=sync."
        )
    if settings.ENVIRONMENT == "development" and not settings.SMTP_HOST:
        print("  note: SMTP_HOST пустой — письма печатаются в stdout (dev-режим).")

    if warnings:
        print()
        for w in warnings:
            print(f"[warn] {w}")
    return 0


async def _amain(cleanup_legacy: bool, drain_email: bool, migrate_legacy: bool) -> int:
    code = 0
    code |= _check_settings()
    code |= await _check_db()
    code |= await _check_redis(cleanup_legacy, drain_email, migrate_legacy)
    code |= _check_celery_workers()
    print()
    return 0 if code == 0 else 1


def main() -> None:
    # Сделаем доступным импорт `app.*` без установки пакета.
    here = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(here))

    parser = argparse.ArgumentParser(description="MedTest diagnostic")
    parser.add_argument("--migrate-legacy", action="store_true",
                        help="Конвертировать pending_reg:* в reg:draft:* (сохраняет данные пользователей)")
    parser.add_argument("--cleanup-legacy", action="store_true",
                        help="Удалить ключи pending_reg:* (legacy от старой регистрации)")
    parser.add_argument("--drain-email", action="store_true",
                        help="ОПАСНО: удалить все pending задачи из очереди email")
    args = parser.parse_args()

    if args.migrate_legacy and args.cleanup_legacy:
        print("Используйте ОДИН из флагов: --migrate-legacy ИЛИ --cleanup-legacy")
        sys.exit(2)

    rc = asyncio.run(_amain(args.cleanup_legacy, args.drain_email, args.migrate_legacy))
    sys.exit(rc)


if __name__ == "__main__":
    main()
