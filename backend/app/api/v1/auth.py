"""
Authentication endpoints.

Registration flow (see docs/REGISTRATION.md for the full spec):

    POST /register              -> issues OTP, enqueues email, always returns 200
    POST /verify-email          -> atomic verify via OtpService, creates User
    POST /resend-verification   -> re-sends (or reuses) active OTP with cooldown
    POST /login                 -> OAuth2-compatible login
    POST /refresh               -> rotate access token

Design notes:
- Draft (user-entered data) and OTP are separate Redis keys so we can rotate
  the code without re-hashing the password, and so hijacking is avoided.
- `/register` returns generic 200 even for conflicting states to prevent user
  enumeration (audit §2.5).
- All three registration endpoints are rate-limited via slowapi.
- Email dispatch goes through the `EmailSender` abstraction so we can swap
  Celery for sync SMTP in tests without touching this file.
"""

import json
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.otp import OtpResult, otp_service
from app.core.rate_limit import limiter
from app.core.redis import delete_key, get_redis_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.models.user import Role, User
from app.schemas.user import (
    EmailVerificationRequest,
    RefreshTokenRequest,
    RegistrationAccepted,
    ResendVerificationRequest,
    StudentRegisterSchema,
    Token,
    VerifyEmailResponse,
)
from app.services.email import get_email_sender

logger = logging.getLogger(__name__)

router = APIRouter()


def _draft_key(email: str) -> str:
    return f"reg:draft:{email.strip().lower()}"


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _save_draft(email: str, password: str, last_name: str, first_name: str, middle_name: Optional[str]) -> None:
    client = await get_redis_client()
    payload = json.dumps({
        "email": email,
        "password_hash": get_password_hash(password),
        "last_name": last_name,
        "first_name": first_name,
        "middle_name": middle_name,
    })
    await client.set(_draft_key(email), payload, ex=settings.REGISTRATION_DRAFT_TTL_SECONDS)


async def _load_draft(email: str) -> Optional[dict]:
    client = await get_redis_client()
    raw = await client.get(_draft_key(email))
    return json.loads(raw) if raw else None


async def _drop_draft(email: str) -> None:
    await delete_key(_draft_key(email))


@router.post(
    "/register",
    response_model=RegistrationAccepted,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.REGISTER_RATE_LIMIT_PER_IP)
async def register(
    request: Request,
    user_in: StudentRegisterSchema,
    db: AsyncSession = Depends(get_db),
) -> RegistrationAccepted:
    """
    Begin student registration. Generates OTP and enqueues verification email.

    Responses are uniform to defeat user enumeration: whether the email is
    new, pending, or already registered, we reply 200 with the same shape.
    """
    email = _normalize_email(user_in.email)
    sender = get_email_sender()

    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Already fully registered — do nothing, look uniform.
        return RegistrationAccepted(
            message="Если email корректен, код подтверждения отправлен.",
            email=email,
            resend_after=settings.OTP_RESEND_COOLDOWN_SECONDS,
        )

    # Detect an in-progress draft with a different password — potential hijack
    # attempt. We cannot tell the attacker "email taken", so we just pretend to
    # send a new code but DO NOT overwrite the victim's draft. The legitimate
    # user still has their original code valid.
    existing_draft = await _load_draft(email)
    if existing_draft and not verify_password(user_in.password, existing_draft["password_hash"]):
        logger.warning("register.draft_conflict email=%s", email)
        return RegistrationAccepted(
            message="Если email корректен, код подтверждения отправлен.",
            email=email,
            resend_after=settings.OTP_RESEND_COOLDOWN_SECONDS,
        )

    # Save/refresh draft (same password — idempotent).
    await _save_draft(
        email,
        user_in.password,
        user_in.last_name,
        user_in.first_name,
        user_in.middle_name,
    )

    # Issue (or reuse) an OTP.
    outcome = await otp_service.issue(email)

    if outcome.limited:
        # Hourly cap reached — treat as "please wait" but uniform shape.
        return RegistrationAccepted(
            message="Если email корректен, код подтверждения отправлен.",
            email=email,
            resend_after=outcome.resend_after,
        )

    if outcome.code is not None:
        try:
            await sender.send_verification(email, outcome.code)
        except Exception as exc:  # noqa: BLE001 — transport layer handles retries
            logger.error("register.email_dispatch_failed email=%s error=%s", email, exc)
            # Best-effort: keep draft + OTP so user can resend; don't leak error.

        if settings.ENVIRONMENT == "development":
            logger.info("register.dev_code email=%s code=%s", email, outcome.code)
            # print() дублирует в stdout: виден в uvicorn-консоли даже если
            # root-логгер не был сконфигурирован (например, при запуске тестов).
            print(f"\n[DEV] Verification code for {email}: {outcome.code}\n", flush=True)

    return RegistrationAccepted(
            message="Если email корректен, код подтверждения отправлен.",
        email=email,
        resend_after=outcome.resend_after,
    )


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
)
@limiter.limit(settings.VERIFY_RATE_LIMIT_PER_IP)
async def verify_email(
    request: Request,
    data: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> VerifyEmailResponse:
    """
    Verify OTP and materialize the user. Atomicity is delegated to OtpService.
    """
    email = _normalize_email(data.email)

    # Fast path: if the user is already verified (e.g., parallel request won
    # the race), report success instead of a confusing error.
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        await _drop_draft(email)
        await otp_service.invalidate(email)
        return VerifyEmailResponse(message="Email уже подтверждён.", email=email)

    outcome = await otp_service.verify_and_consume(email, data.code)

    if outcome.result is OtpResult.OK:
        draft = await _load_draft(email)
        if draft is None:
            # OTP was valid but draft expired — race, we must ask them to start
            # over. Very unlikely but possible if TTLs differ.
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Данные регистрации устарели. Зарегистрируйтесь заново.",
            )

        user = User(
            email=email,
            password_hash=draft["password_hash"],
            last_name=draft["last_name"],
            first_name=draft["first_name"],
            middle_name=draft["middle_name"],
            role=Role.STUDENT,
            is_verified=True,
            is_active=True,
        )
        db.add(user)
        try:
            await db.commit()
        except IntegrityError:
            # Someone else won the race and created the user — treat as success.
            await db.rollback()
        finally:
            await _drop_draft(email)

        return VerifyEmailResponse(message="Email успешно подтверждён.", email=email)

    if outcome.result is OtpResult.INVALID_CODE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверный код подтверждения. Осталось попыток: {outcome.attempts_left}.",
        )

    if outcome.result is OtpResult.TOO_MANY_ATTEMPTS:
        await _drop_draft(email)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много неверных попыток. Зарегистрируйтесь заново.",
        )

    # NOT_FOUND: either the key expired OR a parallel verify already consumed
    # it. Re-check the DB: if the user is present, a concurrent request
    # succeeded — treat this call as idempotent "already verified".
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        await _drop_draft(email)
        return VerifyEmailResponse(message="Email уже подтверждён.", email=email)

    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Срок действия кода истёк или код не найден. Запросите новый.",
    )


@router.post(
    "/resend-verification",
    response_model=RegistrationAccepted,
)
@limiter.limit(settings.RESEND_RATE_LIMIT_PER_IP)
async def resend_verification(
    request: Request,
    data: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> RegistrationAccepted:
    """
    Resend verification code if an active draft exists and cooldown has passed.
    """
    email = _normalize_email(data.email)
    sender = get_email_sender()

    # If already verified, uniform response.
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        return RegistrationAccepted(
            message="Если email корректен, код подтверждения отправлен.",
            email=email,
            resend_after=settings.OTP_RESEND_COOLDOWN_SECONDS,
        )

    draft = await _load_draft(email)
    if draft is None:
        return RegistrationAccepted(
            message="Если email корректен, код подтверждения отправлен.",
            email=email,
            resend_after=settings.OTP_RESEND_COOLDOWN_SECONDS,
        )

    outcome = await otp_service.issue(email)
    if outcome.code is not None and not outcome.limited:
        try:
            await sender.send_verification(email, outcome.code)
        except Exception as exc:  # noqa: BLE001
            logger.error("resend.email_dispatch_failed email=%s error=%s", email, exc)

        if settings.ENVIRONMENT == "development":
            logger.info("resend.dev_code email=%s code=%s", email, outcome.code)
            print(f"\n[DEV] Resent verification code for {email}: {outcome.code}\n", flush=True)

    return RegistrationAccepted(
            message="Если email корректен, код подтверждения отправлен.",
        email=email,
        resend_after=outcome.resend_after,
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth2 compatible authentication (username = email).
    """
    result = await db.execute(select(User).where(User.email == form_data.username.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь деактивирован.",
        )

    access_token = create_access_token(
        subject=str(user.id),
        additional_claims={"role": user.role},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    user.last_login = datetime.utcnow()
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",  # nosec B105
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Rotate access token using a valid refresh token.
    """
    from app.core.security import decode_token

    try:
        payload = decode_token(token_data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный refresh-токен.",
            )

        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пользователь не найден или деактивирован.",
            )

        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={"role": user.role},
        )
        new_refresh_token = create_refresh_token(subject=str(user.id))

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",  # nosec B105
        }

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось проверить refresh-токен.",
        )
