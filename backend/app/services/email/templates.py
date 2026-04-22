"""
Pure template renderers — no I/O, safe to test.

All user-supplied strings are HTML-escaped to prevent XSS in the rendered
HTML body (audit § security tests). CRLF in headers is blocked at the
transport layer (smtplib rejects invalid headers, but we also validate here).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import Optional

from app.core.config import settings


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text: str
    html: str


def _guard_header_value(value: str) -> str:
    """
    Reject CR/LF injection in header-like fields (subject, recipients).
    Returns a sanitized value or raises ValueError.
    """
    if "\r" in value or "\n" in value:
        raise ValueError("CRLF injection attempt in email header")
    return value


def render_verification_email(code: str) -> RenderedEmail:
    project = escape(settings.PROJECT_NAME)
    safe_code = escape(code)
    subject = _guard_header_value(f"Подтверждение регистрации - {settings.PROJECT_NAME}")

    text = (
        "Здравствуйте!\n\n"
        f"Добро пожаловать в {settings.PROJECT_NAME}.\n\n"
        "Для завершения регистрации используйте код подтверждения:\n\n"
        f"{code}\n\n"
        f"Код действителен {settings.OTP_TTL_SECONDS // 60} минут.\n"
        "Если вы не регистрировались на нашем сервисе, проигнорируйте это письмо.\n"
    )

    html = f"""<!doctype html>
<html lang="ru">
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #374151;">
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="color: #3B82F6; margin: 0;">{project}</h1>
    </div>
    <div style="background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 40px;">
        <h2 style="margin-top: 0; color: #111827;">Подтверждение почты</h2>
        <p>Для завершения регистрации введите код:</p>
        <div style="background: #f3f4f6; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 30px 0; color: #111827; border-radius: 4px;">
            {safe_code}
        </div>
        <p style="color: #6b7280; font-size: 14px;">
            Код действителен {settings.OTP_TTL_SECONDS // 60} минут.
        </p>
    </div>
    <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
        © {datetime.utcnow().year} {project}. Все права защищены.
    </div>
</body>
</html>"""

    return RenderedEmail(subject=subject, text=text, html=html)


def render_email_change(code: str, new_email: str) -> RenderedEmail:
    project = escape(settings.PROJECT_NAME)
    safe_code = escape(code)
    safe_new_email = escape(new_email)
    subject = _guard_header_value(f"Подтверждение смены email - {settings.PROJECT_NAME}")

    text = (
        "Здравствуйте!\n\n"
        f"Вы запросили смену email на: {new_email}\n\n"
        f"Ваш код подтверждения: {code}\n\n"
        "Код действителен 15 минут.\n"
        "Если вы не запрашивали смену email, проигнорируйте это письмо.\n"
    )

    html = f"""<!doctype html>
<html lang="ru">
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #3B82F6;">Подтверждение смены email</h2>
    <p>Вы запросили смену email на: <strong>{safe_new_email}</strong></p>
    <p>Ваш код подтверждения:</p>
    <div style="background: #f3f4f6; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 20px 0;">
        {safe_code}
    </div>
    <p style="color: #6b7280;">Код действителен 15 минут.</p>
</body>
</html>"""

    return RenderedEmail(subject=subject, text=text, html=html)


def render_teacher_application_notification(
    teacher_email: str, full_name: str
) -> RenderedEmail:
    project = escape(settings.PROJECT_NAME)
    safe_name = escape(full_name)
    safe_email = escape(teacher_email)
    subject = _guard_header_value(
        f"Новая заявка на регистрацию преподавателя - {settings.PROJECT_NAME}"
    )
    text = (
        "Здравствуйте!\n\n"
        "Поступила новая заявка на регистрацию преподавателя.\n\n"
        f"Преподаватель: {full_name}\n"
        f"Email: {teacher_email}\n"
    )
    html = f"""<!doctype html>
<html lang="ru">
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #3B82F6;">Новая заявка преподавателя в {project}</h2>
    <p><strong>Преподаватель:</strong> {safe_name}</p>
    <p><strong>Email:</strong> {safe_email}</p>
</body>
</html>"""
    return RenderedEmail(subject=subject, text=text, html=html)


def render_teacher_account_created(
    full_name: str, teacher_email: str, temporary_password: str
) -> RenderedEmail:
    project = escape(settings.PROJECT_NAME)
    safe_name = escape(full_name)
    safe_email = escape(teacher_email)
    safe_pwd = escape(temporary_password)
    subject = _guard_header_value(
        f"Ваш аккаунт преподавателя создан - {settings.PROJECT_NAME}"
    )
    text = (
        f"Здравствуйте, {full_name}!\n\n"
        "Ваша заявка на регистрацию одобрена.\n\n"
        f"Email: {teacher_email}\n"
        f"Временный пароль: {temporary_password}\n\n"
        "ВАЖНО: При первом входе смените пароль.\n"
    )
    html = f"""<!doctype html>
<html lang="ru">
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #10B981;">Аккаунт преподавателя создан</h2>
    <p>Здравствуйте, <strong>{safe_name}</strong>!</p>
    <p><strong>Email:</strong> {safe_email}</p>
    <p><strong>Временный пароль:</strong></p>
    <div style="background: #f3f4f6; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 4px;">
        {safe_pwd}
    </div>
    <p style="color: #f59e0b;">При первом входе обязательно смените пароль.</p>
</body>
</html>"""
    return RenderedEmail(subject=subject, text=text, html=html)


def render_teacher_application_rejected(
    full_name: str, admin_comment: Optional[str] = None
) -> RenderedEmail:
    project = escape(settings.PROJECT_NAME)
    safe_name = escape(full_name)
    subject = _guard_header_value(f"Заявка на регистрацию - {settings.PROJECT_NAME}")

    comment_block_text = f"\n\nКомментарий: {admin_comment}" if admin_comment else ""
    text = (
        f"Здравствуйте, {full_name}!\n\n"
        "К сожалению, ваша заявка не была одобрена."
        f"{comment_block_text}\n"
    )

    comment_block_html = (
        f'<p style="color: #991b1b;"><strong>Комментарий:</strong> {escape(admin_comment)}</p>'
        if admin_comment
        else ""
    )
    html = f"""<!doctype html>
<html lang="ru">
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #ef4444;">Заявка не одобрена</h2>
    <p>Здравствуйте, <strong>{safe_name}</strong>!</p>
    <p>К сожалению, ваша заявка на регистрацию не была одобрена.</p>
    {comment_block_html}
</body>
</html>"""
    return RenderedEmail(subject=subject, text=text, html=html)
