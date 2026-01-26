"""
Email service для отправки писем
"""

import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None
) -> bool:
    """
    Отправка email через SMTP.
    В dev режиме просто логирует письмо.
    """
    # В dev режиме или без SMTP настроек - просто логируем
    if settings.ENVIRONMENT == "development" or not settings.SMTP_HOST:
        logger.info(f"[DEV EMAIL] To: {to_email}")
        logger.info(f"[DEV EMAIL] Subject: {subject}")
        logger.info(f"[DEV EMAIL] Body: {body}")
        print(f"\n{'='*50}")
        print(f"📧 EMAIL (dev mode - not sent)")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        print(f"{'='*50}\n")
        return True
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        
        # Text part
        part1 = MIMEText(body, "plain", "utf-8")
        msg.attach(part1)
        
        # HTML part (если есть)
        if html_body:
            part2 = MIMEText(html_body, "html", "utf-8")
            msg.attach(part2)
        
        # Отправка
        smtp_class = smtplib.SMTP_SSL if settings.SMTP_PORT == 465 else smtplib.SMTP
        with smtp_class(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_PORT != 465:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
        
        logger.info(f"Email sent to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


async def send_email_change_code(to_email: str, code: str) -> bool:
    """
    Отправка кода подтверждения смены email
    """
    subject = f"Подтверждение смены email - {settings.PROJECT_NAME}"
    body = f"""
Здравствуйте!

Вы запросили смену email на адрес: {to_email}

Ваш код подтверждения: {code}

Код действителен 15 минут.

Если вы не запрашивали смену email, проигнорируйте это письмо.

С уважением,
{settings.PROJECT_NAME}
"""
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #3B82F6;">Подтверждение смены email</h2>
    <p>Здравствуйте!</p>
    <p>Вы запросили смену email на адрес: <strong>{to_email}</strong></p>
    <p>Ваш код подтверждения:</p>
    <div style="background: #f3f4f6; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 20px 0;">
        {code}
    </div>
    <p style="color: #6b7280;">Код действителен 15 минут.</p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
    <p style="color: #9ca3af; font-size: 12px;">
        Если вы не запрашивали смену email, проигнорируйте это письмо.
    </p>
</body>
</html>
"""
    
    return await send_email(to_email, subject, body, html_body)


async def send_verification_email(to_email: str, code: str) -> bool:
    """
    Отправка кода подтверждения регистрации
    """
    subject = f"Подтверждение регистрации - {settings.PROJECT_NAME}"
    body = f"""
Здравствуйте!

Добро пожаловать в {settings.PROJECT_NAME}.

Для завершения регистрации, пожалуйста, используйте следующий код подтверждения:

{code}

Код действителен 24 часа.

Если вы не регистрировались на нашем сервисе, просто проигнорируйте это письмо.

С уважением,
Команда {settings.PROJECT_NAME}
"""
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #374151;">
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="color: #3B82F6; margin: 0;">{settings.PROJECT_NAME}</h1>
    </div>
    <div style="background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 40px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);">
        <h2 style="margin-top: 0; color: #111827;">Подтверждение почты</h2>
        <p>Здравствуйте!</p>
        <p>Спасибо за регистрацию в <strong>{settings.PROJECT_NAME}</strong>. Для подтверждения вашего email адреса используйте код ниже:</p>
        
        <div style="background: #f3f4f6; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 30px 0; color: #111827; border-radius: 4px;">
            {code}
        </div>
        
        <p style="color: #6b7280; font-size: 14px;">Код действителен в течение 24 часов.</p>
        <p>Введите этот код на странице подтверждения в приложении.</p>
        
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
        
        <p style="color: #9ca3af; font-size: 12px; margin-bottom: 0;">
            Если вы не создавали аккаунт, просто проигнорируйте это письмо.
        </p>
    </div>
    <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
        © {datetime.utcnow().year} {settings.PROJECT_NAME}. Все права защищены.
    </div>
</body>
</html>
"""
    
    return await send_email(to_email, subject, body, html_body)


async def send_teacher_application_notification(
    admin_email: str,
    teacher_email: str,
    full_name: str
) -> bool:
    """
    Уведомление администратору о новой заявке преподавателя
    """
    subject = f"Новая заявка на регистрацию преподавателя - {settings.PROJECT_NAME}"
    
    body = f"""
Здравствуйте!

Поступила новая заявка на регистрацию преподавателя.

Преподаватель: {full_name}
Email: {teacher_email}

Для рассмотрения заявки перейдите в панель администратора.

С уважением,
Система {settings.PROJECT_NAME}
"""
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #374151;">
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="color: #3B82F6; margin: 0;">{settings.PROJECT_NAME}</h1>
    </div>
    <div style="background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 40px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);">
        <h2 style="margin-top: 0; color: #111827;">Новая заявка преподавателя</h2>
        <p>Поступила новая заявка на регистрацию в системе.</p>
        
        <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 8px 0;"><strong>Преподаватель:</strong> {full_name}</p>
            <p style="margin: 8px 0;"><strong>Email:</strong> {teacher_email}</p>
        </div>
        
        <p>Для рассмотрения заявки перейдите в панель администратора.</p>
    </div>
    <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
        © {datetime.utcnow().year} {settings.PROJECT_NAME}. Все права защищены.
    </div>
</body>
</html>
"""
    
    return await send_email(admin_email, subject, body, html_body)


async def send_teacher_account_created(
    teacher_email: str,
    full_name: str,
    temporary_password: str
) -> bool:
    """
    Уведомление преподавателю об одобрении заявки и создании аккаунта
    """
    subject = f"Ваш аккаунт преподавателя создан - {settings.PROJECT_NAME}"
    
    body = f"""
Здравствуйте, {full_name}!

Ваша заявка на регистрацию в качестве преподавателя одобрена.
Аккаунт успешно создан!

Данные для входа:
Email: {teacher_email}
Временный пароль: {temporary_password}

ВАЖНО: При первом входе в систему обязательно смените пароль на постоянный.

Для входа перейдите на сайт и используйте указанные данные.

С уважением,
Команда {settings.PROJECT_NAME}
"""
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #374151;">
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="color: #3B82F6; margin: 0;">{settings.PROJECT_NAME}</h1>
    </div>
    <div style="background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 40px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);">
        <h2 style="margin-top: 0; color: #10B981;">✓ Аккаунт создан</h2>
        <p>Здравствуйте, <strong>{full_name}</strong>!</p>
        <p>Ваша заявка на регистрацию в качестве преподавателя <strong style="color: #10B981;">одобрена</strong>.</p>
        
        <div style="background: #f0fdf4; border-left: 4px solid #10B981; padding: 20px; margin: 20px 0;">
            <p style="margin: 8px 0;"><strong>Email:</strong> {teacher_email}</p>
            <p style="margin: 8px 0;"><strong>Временный пароль:</strong></p>
            <div style="background: white; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 4px; margin: 10px 0; color: #111827; border-radius: 4px; border: 2px dashed #10B981;">
                {temporary_password}
            </div>
        </div>
        
        <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
            <p style="margin: 0; color: #92400e;"><strong>⚠️ ВАЖНО:</strong> При первом входе обязательно смените пароль на постоянный!</p>
        </div>
        
        <p>Войдите в систему, используя указанные данные, и начните работу.</p>
    </div>
    <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
        © {datetime.utcnow().year} {settings.PROJECT_NAME}. Все права защищены.
    </div>
</body>
</html>
"""
    
    return await send_email(teacher_email, subject, body, html_body)


async def send_teacher_application_rejected(
    teacher_email: str,
    full_name: str,
    admin_comment: Optional[str] = None
) -> bool:
    """
    Уведомление преподавателю об отклонении заявки
    """
    subject = f"Заявка на регистрацию - {settings.PROJECT_NAME}"
    
    comment_text = f"\n\nКомментарий администратора:\n{admin_comment}" if admin_comment else ""
    
    body = f"""
Здравствуйте, {full_name}!

К сожалению, ваша заявка на регистрацию в качестве преподавателя не была одобрена.{comment_text}

Если у вас есть вопросы, пожалуйста, свяжитесь с администрацией.

С уважением,
Команда {settings.PROJECT_NAME}
"""
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #374151;">
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="color: #3B82F6; margin: 0;">{settings.PROJECT_NAME}</h1>
    </div>
    <div style="background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 40px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);">
        <h2 style="margin-top: 0; color: #ef4444;">Заявка не одобрена</h2>
        <p>Здравствуйте, <strong>{full_name}</strong>!</p>
        <p>К сожалению, ваша заявка на регистрацию в качестве преподавателя не была одобрена.</p>
        
        {f'''<div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 20px; margin: 20px 0;">
            <p style="margin: 0; color: #7f1d1d;"><strong>Комментарий администратора:</strong></p>
            <p style="margin: 10px 0 0 0; color: #991b1b;">{admin_comment}</p>
        </div>''' if admin_comment else ''}
        
        <p>Если у вас есть вопросы или вы хотите повторно подать заявку, пожалуйста, свяжитесь с администрацией.</p>
    </div>
    <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
        © {datetime.utcnow().year} {settings.PROJECT_NAME}. Все права защищены.
    </div>
</body>
</html>
"""
    
    return await send_email(teacher_email, subject, body, html_body)
